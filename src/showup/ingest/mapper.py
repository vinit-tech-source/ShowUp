"""Column mapper with fuzzy header matching and mapping application."""

from __future__ import annotations

import re
from typing import Final

import pandas as pd

REQUIRED_CANONICAL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "client_id",
        "appointment_datetime",
        "outcome",
    }
)

OPTIONAL_CANONICAL_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "booking_created_at",
        "service_type",
        "price",
        "channel",
        "deposit_paid",
        "confirmed",
        "language",
        "client_name",
        "phone",
    }
)

ALL_CANONICAL_FIELDS: Final[frozenset[str]] = REQUIRED_CANONICAL_FIELDS | OPTIONAL_CANONICAL_FIELDS

# Common aliases and synonyms for appointment scheduling platforms
SYNONYMS: Final[dict[str, list[str]]] = {
    "client_id": [
        "client_id",
        "clientid",
        "customer_id",
        "customerid",
        "patient_id",
        "patientid",
        "user_id",
        "userid",
        "client_email",
        "customer_email",
        "email",
        "client_number",
        "id",
        "client",
        "customer",
        "patient",
    ],
    "appointment_datetime": [
        "appointment_datetime",
        "appointment_date",
        "appointment_time",
        "start_time",
        "start_datetime",
        "booking_time",
        "booking_date",
        "datetime",
        "date_time",
        "date",
        "scheduled_time",
        "session_date",
        "time",
    ],
    "outcome": [
        "outcome",
        "status",
        "appointment_status",
        "attendance",
        "attended",
        "show_up",
        "showup",
        "no_show",
        "result",
        "state",
    ],
    "booking_created_at": [
        "booking_created_at",
        "created_at",
        "booked_at",
        "booking_date",
        "created_date",
        "creation_date",
        "date_booked",
    ],
    "service_type": [
        "service_type",
        "service",
        "treatment",
        "service_name",
        "appointment_type",
        "session_type",
        "class",
        "lesson",
        "category",
    ],
    "price": [
        "price",
        "amount",
        "cost",
        "fee",
        "total",
        "charge",
        "rate",
        "service_price",
    ],
    "channel": [
        "channel",
        "booking_channel",
        "source",
        "booking_source",
        "booked_via",
        "medium",
        "platform",
    ],
    "deposit_paid": [
        "deposit_paid",
        "deposit",
        "deposit_amount",
        "prepaid",
        "downpayment",
        "has_deposit",
    ],
    "confirmed": [
        "confirmed",
        "is_confirmed",
        "confirmation",
        "confirmed_by_client",
        "confirmation_status",
    ],
    "language": [
        "language",
        "lang",
        "client_language",
        "preferred_language",
        "locale",
    ],
    "client_name": [
        "client_name",
        "name",
        "full_name",
        "first_name",
        "customer_name",
        "patient_name",
    ],
    "phone": [
        "phone",
        "phone_number",
        "mobile",
        "cell",
        "contact_number",
        "telephone",
        "client_phone",
    ],
}


def _normalize(text: str) -> str:
    """Normalize a column header for matching."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return cleaned.strip("_")


def suggest_mappings(headers: list[str]) -> dict[str, str]:
    """Suggest canonical-to-raw header mappings based on synonym matching.

    Returns a dictionary of: {canonical_field_name: matched_raw_header}.
    """
    normalized_headers = {header: _normalize(header) for header in headers}
    used_headers: set[str] = set()
    suggestions: dict[str, str] = {}

    # Pass 1: Exact matches against canonical or synonyms
    for canonical, synonyms in SYNONYMS.items():
        for raw_header, norm in normalized_headers.items():
            if raw_header in used_headers:
                continue
            if norm == canonical or norm in synonyms:
                suggestions[canonical] = raw_header
                used_headers.add(raw_header)
                break

    # Pass 2: Substring matching for unmapped fields
    for canonical, synonyms in SYNONYMS.items():
        if canonical in suggestions:
            continue
        for raw_header, norm in normalized_headers.items():
            if raw_header in used_headers:
                continue
            for syn in synonyms:
                if syn in norm or norm in syn:
                    suggestions[canonical] = raw_header
                    used_headers.add(raw_header)
                    break
            if canonical in suggestions:
                break

    return suggestions


def validate_mapping(mapping: dict[str, str], headers: list[str]) -> list[str]:
    """Verify that all required canonical fields are mapped to valid headers.

    Returns a list of error strings (empty if valid).
    """
    errors: list[str] = []
    header_set = set(headers)

    for req in REQUIRED_CANONICAL_FIELDS:
        mapped_col = mapping.get(req)
        if not mapped_col:
            errors.append(f"Required field '{req}' is not mapped.")
        elif mapped_col not in header_set:
            errors.append(f"Mapped column '{mapped_col}' for '{req}' does not exist in CSV.")

    return errors


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    """Rename columns according to mapping and select mapped columns."""
    reverse_mapping = {raw_col: canonical for canonical, raw_col in mapping.items() if raw_col}
    mapped_df = df.rename(columns=reverse_mapping)

    # Keep mapped columns in the order defined by the mapping
    keep_cols = [c for c in mapping if c in mapped_df.columns]
    return mapped_df[keep_cols].copy()
