"""Allowlist enforcement for model features.

ShowUp explicitly forbids demographic, geographic, or PII features to prevent bias
and protect privacy. All models are strictly restricted to features in ALLOWED_FEATURES.
"""

from __future__ import annotations

from typing import Final

import pandas as pd

ALLOWED_FEATURES: Final[frozenset[str]] = frozenset(
    {
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
)

# Reasons for explicitly forbidden or excluded fields
EXCLUSION_REASONS: Final[dict[str, str]] = {
    "age": "Ethical constraint: prevents age-based discrimination in scheduling intervention.",
    "gender": "Ethical constraint: prevents gender bias; no operational relevance to attendance.",
    "sex": "Ethical constraint: prevents gender bias; no operational relevance to attendance.",
    "name": "PII & Fairness: client names carry ethnic associations and risk proxy discrimination.",
    "client_name": (
        "PII & Fairness: client names carry ethnic associations and risk proxy discrimination."
    ),
    "first_name": "PII & Fairness: names carry ethnic/cultural associations.",
    "last_name": "PII & Fairness: names carry ethnic/cultural associations.",
    "phone": "Privacy: sensitive PII; used solely for optional owner-initiated wa.me links.",
    "phone_number": (
        "Privacy: sensitive PII; used solely for optional owner-initiated wa.me links."
    ),
    "mobile": "Privacy: phone numbers are sensitive PII.",
    "email": "Privacy: email addresses are PII and not predictive of attendance behavior.",
    "address": (
        "Fairness: postal addresses and neighborhoods risk socioeconomic/redlining proxy bias."
    ),
    "neighbourhood": (
        "Fairness: geographic location correlates with race/income; forbidden to prevent bias."
    ),
    "neighborhood": (
        "Fairness: geographic location correlates with race/income; forbidden to prevent bias."
    ),
    "postcode": "Fairness: postal codes carry socioeconomic proxy bias.",
    "zip_code": "Fairness: zip codes carry socioeconomic proxy bias.",
}


class NonAllowedFeatureError(Exception):
    """Raised when a non-allowed feature attempts to enter the model pipeline."""


def assert_features_allowed(columns: list[str] | pd.Index) -> None:
    """Verify that every column in the given list is in ALLOWED_FEATURES.

    Raises:
        NonAllowedFeatureError: if any forbidden or unlisted feature is present.
    """
    col_set = set(columns)
    disallowed = col_set - ALLOWED_FEATURES
    if disallowed:
        raise NonAllowedFeatureError(
            f"Non-allowed features detected in model dataset: {sorted(disallowed)}. "
            f"ShowUp strictly permits only features defined in ALLOWED_FEATURES."
        )


def enforce_allowlist(df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame columns to include ONLY columns in ALLOWED_FEATURES.

    Silently drops any column not explicitly in the allowlist.
    """
    allowed_cols = [c for c in df.columns if c in ALLOWED_FEATURES]
    return df[allowed_cols].copy()
