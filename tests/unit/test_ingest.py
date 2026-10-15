"""Tests for showup.ingest: reader, mapper, validator, dedupe, and property tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from showup.domain.enums import Outcome
from showup.domain.models import Booking
from showup.ingest.dedupe import dedupe_bookings
from showup.ingest.mapper import (
    apply_mapping,
    suggest_mappings,
    validate_mapping,
)
from showup.ingest.reader import (
    CsvReadError,
    detect_delimiter,
    detect_encoding,
    read_csv_safe,
)
from showup.ingest.validator import (
    sanitize_formula_injection,
    validate_and_transform_df,
)


class TestReader:
    """Verify encoding detection, delimiter sniffing, and safe reading."""

    def test_detect_encoding_utf8(self) -> None:
        raw = b"Name,Age,City\nAlice,30,New York\n"
        assert detect_encoding(raw).lower() in ("utf-8", "ascii")

    def test_detect_encoding_latin1(self) -> None:
        # 'é' in latin1
        raw = "Client,Service\nRené,Physiothérapie\n".encode("latin1")
        assert detect_encoding(raw).lower() in ("latin1", "iso-8859-1", "windows-1252", "utf-8")

    def test_detect_delimiters(self) -> None:
        assert detect_delimiter("a,b,c\n1,2,3") == ","
        assert detect_delimiter("a;b;c\n1;2;3") == ";"
        assert detect_delimiter("a\tb\tc\n1\t2\t3") == "\t"
        assert detect_delimiter("a|b|c\n1|2|3") == "|"

    def test_read_csv_safe_from_fixture(self) -> None:
        fixture_path = Path("tests/fixtures/sample_data.csv")
        df, _encoding, delimiter = read_csv_safe(fixture_path)
        assert len(df) == 8
        assert delimiter == ","
        assert "Client Email" in df.columns

    def test_read_csv_safe_rejects_empty(self) -> None:
        with pytest.raises(CsvReadError, match="empty"):
            read_csv_safe(b"")

    def test_read_csv_safe_rejects_oversized(self) -> None:
        with pytest.raises(CsvReadError, match="exceeds limit"):
            read_csv_safe(b"a,b,c\n1,2,3", max_bytes=5)


class TestMapper:
    """Verify header fuzzy mapping suggestions and application."""

    def test_suggest_mappings_common_headers(self) -> None:
        headers = ["Client Email", "Start Time", "Status", "Treatment Type", "Fee", "Channel"]
        suggestions = suggest_mappings(headers)
        assert suggestions.get("client_id") == "Client Email"
        assert suggestions.get("appointment_datetime") == "Start Time"
        assert suggestions.get("outcome") == "Status"
        assert suggestions.get("service_type") == "Treatment Type"
        assert suggestions.get("price") == "Fee"

    def test_validate_mapping_passes(self) -> None:
        headers = ["Email", "Appointment", "Attended"]
        mapping = {
            "client_id": "Email",
            "appointment_datetime": "Appointment",
            "outcome": "Attended",
        }
        errors = validate_mapping(mapping, headers)
        assert len(errors) == 0

    def test_validate_mapping_fails_missing_required(self) -> None:
        headers = ["Email", "Appointment"]
        mapping = {
            "client_id": "Email",
            "appointment_datetime": "Appointment",
        }
        errors = validate_mapping(mapping, headers)
        assert any("outcome" in err for err in errors)

    def test_apply_mapping(self) -> None:
        df = pd.DataFrame(
            {
                "Client Email": ["c1@test.com"],
                "Start Time": ["2026-05-01 10:00:00"],
                "Attendance": ["Attended"],
                "Random Column": ["Ignore me"],
            }
        )
        mapping = {
            "client_id": "Client Email",
            "appointment_datetime": "Start Time",
            "outcome": "Attendance",
        }
        mapped = apply_mapping(df, mapping)
        assert list(mapped.columns) == ["client_id", "appointment_datetime", "outcome"]
        assert mapped.iloc[0]["client_id"] == "c1@test.com"


class TestValidatorAndSanitization:
    """Verify formula injection sanitization, row validation, and reporting."""

    def test_sanitize_formula_injection(self) -> None:
        assert sanitize_formula_injection("=cmd|'/C calc'!A0") == "'=cmd|'/C calc'!A0"
        assert sanitize_formula_injection("+12345678") == "'+12345678"
        assert sanitize_formula_injection("@SUM(A1:A10)") == "'@SUM(A1:A10)"
        assert sanitize_formula_injection("Regular String") == "Regular String"
        assert sanitize_formula_injection(None) is None

    def test_validate_and_transform_df(self) -> None:
        df = pd.DataFrame(
            {
                "client_id": ["C1", "C2", "", "C4"],
                "appointment_datetime": [
                    "2026-01-01 10:00:00",
                    "2026-01-02 11:00:00",
                    "2026-01-03 12:00:00",
                    "NOT A DATE",
                ],
                "outcome": ["Attended", "No-Show", "Attended", "Attended"],
                "price": ["$50.00", "60", "invalid", "70"],
                "deposit_paid": ["Yes", "0", "None", "True"],
            }
        )

        clients, bookings, report = validate_and_transform_df(df)
        assert report.total_rows == 4
        assert report.valid_rows == 2
        assert report.error_rows == 2
        assert len(clients) == 2
        assert len(bookings) == 2
        assert bookings[0].price == 50.0
        assert bookings[0].deposit_paid is True
        assert bookings[1].deposit_paid is False

    def test_validate_skips_cancelled(self) -> None:
        df = pd.DataFrame(
            {
                "client_id": ["C1", "C2"],
                "appointment_datetime": ["2026-01-01 10:00:00", "2026-01-02 11:00:00"],
                "outcome": ["Cancelled", "Attended"],
            }
        )
        _clients, _bookings, report = validate_and_transform_df(df)
        assert report.valid_rows == 1
        assert report.skipped_cancelled == 1


class TestDeduplication:
    """Verify deduplication by (client_id, appointment_at)."""

    def test_dedupe_bookings(self) -> None:
        client_id = uuid4()
        dt1 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
        dt2 = datetime(2026, 3, 1, 14, 0, tzinfo=UTC)

        b1 = Booking(client_id=client_id, appointment_at=dt1, outcome=Outcome.PENDING)
        b2 = Booking(client_id=client_id, appointment_at=dt1, outcome=Outcome.ATTENDED)
        b3 = Booking(client_id=client_id, appointment_at=dt2, outcome=Outcome.ATTENDED)

        unique, dup_count = dedupe_bookings([b1, b2, b3])
        assert dup_count == 1
        assert len(unique) == 2
        # Verify b2 (with attended outcome) replaced b1
        b_dt1 = next(b for b in unique if b.appointment_at == dt1)
        assert b_dt1.outcome == Outcome.ATTENDED


class TestPropertyBasedCsvParsing:
    """Hypothesis property tests for robust CSV reading under random text inputs."""

    @settings(max_examples=25)
    @given(
        st.lists(
            st.tuples(
                st.text(
                    min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))
                ),
                st.text(
                    min_size=1, max_size=20, alphabet=st.characters(blacklist_categories=("Cs",))
                ),
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_delimiter_sniffer_never_crashes(self, rows: list[tuple[str, str]]) -> None:
        csv_text = "\n".join(f"{r[0]},{r[1]}" for r in rows)
        delim = detect_delimiter(csv_text)
        assert delim in [",", ";", "\t", "|"]
