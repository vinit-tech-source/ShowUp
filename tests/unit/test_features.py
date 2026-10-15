"""Tests for showup.features: allowlist enforcement, leakage prevention, correctness, and audit."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from showup.domain.enums import Outcome
from showup.domain.models import Booking
from showup.features.allowlist import (
    ALLOWED_FEATURES,
    NonAllowedFeatureError,
    assert_features_allowed,
    enforce_allowlist,
)
from showup.features.audit import generate_feature_audit
from showup.features.builder import build_features_matrix, compute_booking_features


class TestAllowlistEnforcement:
    """Verify that forbidden demographic, geographic, and PII columns can never pass."""

    def test_allowlist_exact_features(self) -> None:
        assert len(ALLOWED_FEATURES) == 14
        expected = {
            "lead_time_hours",
            "lead_time_bucket",
            "day_of_week",
            "hour_of_day",
            "prior_visits",
            "prior_no_shows",
            "prior_no_show_rate",
            "is_new_client",
            "days_since_last_visit",
            "booking_channel",
            "service_type",
            "price",
            "deposit_paid",
            "confirmation_received",
        }
        assert expected == ALLOWED_FEATURES

    @pytest.mark.parametrize(
        "forbidden_feature",
        ["age", "gender", "sex", "name", "client_name", "phone", "neighbourhood", "zip_code"],
    )
    def test_forbidden_features_rejected(self, forbidden_feature: str) -> None:
        bad_cols = ["lead_time_hours", "price", forbidden_feature]
        with pytest.raises(NonAllowedFeatureError, match="Non-allowed features detected"):
            assert_features_allowed(bad_cols)

    def test_enforce_allowlist_drops_forbidden_columns(self) -> None:
        df = pd.DataFrame(
            {
                "lead_time_hours": [24.0],
                "price": [50.0],
                "age": [35],
                "gender": ["F"],
                "neighbourhood": ["Downtown"],
            }
        )
        filtered = enforce_allowlist(df)
        assert "age" not in filtered.columns
        assert "gender" not in filtered.columns
        assert "neighbourhood" not in filtered.columns
        assert list(filtered.columns) == ["lead_time_hours", "price"]


class TestLeakagePrevention:
    """Verify strictly temporal feature calculation without any future information leakage."""

    def test_zero_leakage_in_client_history(self) -> None:
        client_id = uuid4()
        t0 = datetime(2026, 1, 10, 10, 0, tzinfo=UTC)
        t1 = datetime(2026, 2, 10, 10, 0, tzinfo=UTC)
        t2 = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)

        b0 = Booking(client_id=client_id, appointment_at=t0, outcome=Outcome.ATTENDED)
        b1 = Booking(client_id=client_id, appointment_at=t1, outcome=Outcome.NO_SHOW)
        b2 = Booking(client_id=client_id, appointment_at=t2, outcome=Outcome.ATTENDED)

        all_bookings = [b0, b1, b2]

        matrix = build_features_matrix(
            target_bookings=all_bookings, all_client_history=all_bookings
        )

        # For b0 (first booking ever):
        assert matrix.iloc[0]["prior_visits"] == 0
        assert matrix.iloc[0]["prior_no_shows"] == 0
        assert matrix.iloc[0]["is_new_client"] == 1
        assert matrix.iloc[0]["days_since_last_visit"] == 999.0

        # For b1 (second booking):
        # Must only see b0 (attended)
        assert matrix.iloc[1]["prior_visits"] == 1
        assert matrix.iloc[1]["prior_no_shows"] == 0
        assert matrix.iloc[1]["is_new_client"] == 0
        assert matrix.iloc[1]["days_since_last_visit"] == pytest.approx(31.0, abs=1.0)

        # For b2 (third booking):
        # Must see b0 (attended) and b1 (no_show)
        assert matrix.iloc[2]["prior_visits"] == 2
        assert matrix.iloc[2]["prior_no_shows"] == 1
        assert matrix.iloc[2]["prior_no_show_rate"] == 0.5
        assert matrix.iloc[2]["is_new_client"] == 0


class TestFeatureBuilderCorrectness:
    """Verify specific mathematical computations of features."""

    def test_lead_time_and_timing_features(self) -> None:
        client_id = uuid4()
        app_time = datetime(2026, 6, 15, 14, 30, tzinfo=UTC)  # Monday
        created_time = app_time - timedelta(hours=48)

        booking = Booking(
            client_id=client_id,
            appointment_at=app_time,
            booking_created_at=created_time,
            service_type="Massage",
            price=80.0,
            channel="Online",
            deposit_paid=True,
            confirmed=True,
        )

        feats = compute_booking_features(booking, prior_bookings=[])
        assert feats["lead_time_hours"] == 48.0
        assert feats["lead_time_bucket"] == "24_to_72h"
        assert feats["day_of_week"] == 0  # Monday
        assert feats["hour_of_day"] == 14
        assert feats["deposit_paid"] == 1
        assert feats["confirmation_received"] == 1
        assert feats["service_type"] == "massage"
        assert feats["booking_channel"] == "online"
        assert feats["price"] == 80.0


class TestFeatureAudit:
    """Verify feature audit panel generation."""

    def test_audit_report_identifies_used_and_excluded(self) -> None:
        headers = ["price", "deposit_paid", "client_name", "phone", "age", "random_notes"]
        entries = generate_feature_audit(headers)

        entries_by_col = {e.column_name: e for e in entries}

        assert entries_by_col["price"].status == "used"
        assert entries_by_col["deposit_paid"].status == "used"
        assert entries_by_col["client_name"].status == "excluded"
        assert entries_by_col["phone"].status == "excluded"
        assert entries_by_col["age"].status == "excluded"
        assert entries_by_col["random_notes"].status == "excluded"
        assert "Fairness" in entries_by_col["client_name"].reason


class TestPropertyBasedFeatureBuilder:
    """Hypothesis property tests: builder never emits columns outside ALLOWED_FEATURES."""

    @settings(max_examples=25)
    @given(
        lead_hours=st.floats(min_value=0.0, max_value=1000.0),
        price=st.floats(min_value=0.0, max_value=500.0),
        deposit=st.booleans(),
        confirmed=st.booleans(),
    )
    def test_features_matrix_columns_strictly_in_allowlist(
        self, lead_hours: float, price: float, deposit: bool, confirmed: bool
    ) -> None:
        client_id = uuid4()
        now = datetime.now(UTC)
        b = Booking(
            client_id=client_id,
            appointment_at=now,
            booking_created_at=now - timedelta(hours=lead_hours),
            price=price,
            deposit_paid=deposit,
            confirmed=confirmed,
        )
        matrix = build_features_matrix([b], [])
        assert set(matrix.columns).issubset(ALLOWED_FEATURES)
