"""Row-level validation, date parsing, sanitization, and import report generation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from showup.domain.enums import Outcome
from showup.domain.models import Booking, Client
from showup.logging_setup import get_logger

logger = get_logger(__name__)

# Dangerous prefixes for formula injection in Excel/Calc/Sheets
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_formula_injection(value: str | None) -> str | None:
    """Neutralize potential CSV formula injection attacks.

    Escapes dangerous leading characters with a single quote.
    """
    if not value or not isinstance(value, str):
        return value
    stripped = value.lstrip()
    if stripped.startswith(FORMULA_PREFIXES):
        # Prefix with single quote to force spreadsheet programs to treat as text
        return f"'{value}"
    return value


def _parse_outcome(raw_val: Any) -> Outcome | str:
    """Parse raw outcome string into domain Outcome enum or 'CANCELLED'."""
    if pd.isna(raw_val) or raw_val is None:
        return Outcome.PENDING

    val = str(raw_val).strip().lower()
    if val in ("", "pending", "upcoming", "scheduled", "booked", "future", "active"):
        return Outcome.PENDING
    if val in (
        "attended",
        "show",
        "showed",
        "showed_up",
        "completed",
        "present",
        "yes",
        "true",
        "1",
    ):
        return Outcome.ATTENDED
    if val in ("no_show", "noshow", "no-show", "no show", "missed", "absent", "no", "false", "0"):
        return Outcome.NO_SHOW
    if val in ("cancelled", "canceled", "refunded", "void"):
        return "CANCELLED"

    return Outcome.PENDING


def _parse_bool(raw_val: Any) -> bool | None:
    """Flexible boolean parser for deposit_paid and confirmed columns."""
    if pd.isna(raw_val) or raw_val is None:
        return None
    val = str(raw_val).strip().lower()
    if val in ("true", "yes", "y", "1", "paid", "confirmed"):
        return True
    if val in ("false", "no", "n", "0", "unpaid", "not confirmed", "unconfirmed"):
        return False
    # If numeric amount > 0, consider True
    try:
        num = float(val)
        return num > 0
    except ValueError:
        return None


def _parse_float(raw_val: Any) -> float | None:
    """Flexible float parser for currency amounts."""
    if pd.isna(raw_val) or raw_val is None:
        return None
    # Strip currency symbols and whitespace
    cleaned = re.sub(r"[^\d.-]", "", str(raw_val))
    if not cleaned:
        return None
    try:
        val = float(cleaned)
        return max(0.0, val)
    except ValueError:
        return None


def _parse_datetime(raw_val: Any) -> datetime | None:
    """Parse appointment or creation datetime and guarantee UTC timezone."""
    if pd.isna(raw_val) or raw_val is None:
        return None
    val_str = str(raw_val).strip()
    if val_str:
        try:
            dt = pd.to_datetime(val_str, errors="coerce")
            if pd.notna(dt):
                py_dt = dt.to_pydatetime()
                if isinstance(py_dt, datetime):
                    return py_dt if py_dt.tzinfo else py_dt.replace(tzinfo=UTC)
        except Exception as e:
            logger.debug("datetime_parse_failed", raw=val_str, error=str(e))
    return None


class RowValidationError(BaseModel):
    """Validation error for an individual row and field."""

    row_index: int
    field: str
    message: str
    raw_value: str | None = None


@dataclass
class ValidationReport:
    """Summary and details of CSV import validation."""

    total_rows: int = 0
    valid_rows: int = 0
    error_rows: int = 0
    skipped_cancelled: int = 0
    duplicate_rows: int = 0
    labeled_rows: int = 0
    upcoming_rows: int = 0
    errors: list[RowValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if there is at least one valid row and valid rows exceed errors."""
        return self.valid_rows > 0


class ValidatedRow(BaseModel):
    """Pydantic validated row representation."""

    client_id: str = Field(min_length=1)
    appointment_datetime: datetime
    outcome: Outcome
    booking_created_at: datetime | None = None
    service_type: str | None = None
    price: float | None = None
    channel: str | None = None
    deposit_paid: bool | None = None
    confirmed: bool | None = None
    language: str | None = "en"
    client_name: str | None = None
    phone: str | None = None


def validate_and_transform_df(
    mapped_df: pd.DataFrame,
    source_file: str = "upload.csv",
) -> tuple[list[Client], list[Booking], ValidationReport]:
    """Validate mapped CSV DataFrame row by row and generate domain models.

    Neutralizes formula injection, converts outcomes, normalizes dates to UTC,
    and returns (clients, bookings, validation_report).
    """
    report = ValidationReport(total_rows=len(mapped_df))
    valid_clients_dict: dict[str, Client] = {}
    valid_bookings: list[Booking] = []

    for idx, row in mapped_df.iterrows():
        row_num = int(idx) + 1  # 1-indexed for user display

        # 1. Parse client identifier
        raw_client_id = row.get("client_id")
        if pd.isna(raw_client_id) or not str(raw_client_id).strip():
            report.errors.append(
                RowValidationError(
                    row_index=row_num,
                    field="client_id",
                    message="Missing or empty client identifier.",
                    raw_value=str(raw_client_id),
                )
            )
            report.error_rows += 1
            continue

        client_external_id = sanitize_formula_injection(str(raw_client_id).strip()) or ""

        # 2. Parse appointment datetime
        raw_app_dt = row.get("appointment_datetime")
        app_dt = _parse_datetime(raw_app_dt)
        if app_dt is None:
            report.errors.append(
                RowValidationError(
                    row_index=row_num,
                    field="appointment_datetime",
                    message="Invalid or unparseable appointment date/time.",
                    raw_value=str(raw_app_dt),
                )
            )
            report.error_rows += 1
            continue

        # 3. Parse outcome
        parsed_outcome = _parse_outcome(row.get("outcome"))
        if parsed_outcome == "CANCELLED":
            report.skipped_cancelled += 1
            continue
        outcome = parsed_outcome if isinstance(parsed_outcome, Outcome) else Outcome.PENDING

        # 4. Parse optional fields
        booking_created_at = _parse_datetime(row.get("booking_created_at"))
        service_type = sanitize_formula_injection(
            str(row["service_type"]).strip() if pd.notna(row.get("service_type")) else None
        )
        price = _parse_float(row.get("price"))
        channel = sanitize_formula_injection(
            str(row["channel"]).strip() if pd.notna(row.get("channel")) else None
        )
        deposit_paid = _parse_bool(row.get("deposit_paid"))
        confirmed = _parse_bool(row.get("confirmed"))
        language = (
            str(row.get("language")).strip().lower() if pd.notna(row.get("language")) else "en"
        )
        client_name = sanitize_formula_injection(
            str(row["client_name"]).strip() if pd.notna(row.get("client_name")) else None
        )
        phone = sanitize_formula_injection(
            str(row["phone"]).strip() if pd.notna(row.get("phone")) else None
        )

        # 5. Pydantic validation
        try:
            ValidatedRow(
                client_id=client_external_id,
                appointment_datetime=app_dt,
                outcome=outcome,
                booking_created_at=booking_created_at,
                service_type=service_type,
                price=price,
                channel=channel,
                deposit_paid=deposit_paid,
                confirmed=confirmed,
                language=language,
                client_name=client_name,
                phone=phone,
            )
        except ValidationError as e:
            msg = "; ".join(err["msg"] for err in e.errors())
            report.errors.append(
                RowValidationError(
                    row_index=row_num,
                    field="row",
                    message=f"Row validation failed: {msg}",
                )
            )
            report.error_rows += 1
            continue

        # 6. Build or retrieve domain Client
        if client_external_id not in valid_clients_dict:
            valid_clients_dict[client_external_id] = Client(
                external_id=client_external_id,
                name=client_name,
                phone=phone,
                language=language,
            )
        client = valid_clients_dict[client_external_id]

        # 7. Build domain Booking
        booking = Booking(
            client_id=client.id,
            appointment_at=app_dt,
            booking_created_at=booking_created_at,
            service_type=service_type,
            price=price,
            channel=channel,
            deposit_paid=deposit_paid,
            confirmed=confirmed,
            outcome=outcome,
            source_file=source_file,
        )
        valid_bookings.append(booking)
        report.valid_rows += 1

        if outcome in (Outcome.ATTENDED, Outcome.NO_SHOW):
            report.labeled_rows += 1
        else:
            report.upcoming_rows += 1

    return list(valid_clients_dict.values()), valid_bookings, report
