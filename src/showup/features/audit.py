"""Feature audit reporting: plain-language explanation of columns used and excluded."""

from __future__ import annotations

import re

from showup.domain.models import FeatureAuditEntry
from showup.features.allowlist import ALLOWED_FEATURES, EXCLUSION_REASONS

FEATURE_EXPLANATIONS: dict[str, str] = {
    "lead_time_hours": "Hours between when booking was created and the scheduled appointment time.",
    "lead_time_bucket": "Operational window bucket (e.g., same day, 1-3 days, 1-2 weeks).",
    "day_of_week": "Day of the week (Monday through Sunday) to capture weekly attendance patterns.",
    "hour_of_day": "Time of day (0-23) to capture morning vs. evening appointment patterns.",
    "prior_visits": "Total count of historical attended or missed appointments by this client.",
    "prior_no_shows": "Total count of appointments where this client previously failed to attend.",
    "prior_no_show_rate": "Fraction of prior appointments resulting in a no-show.",
    "is_new_client": (
        "Whether this is client's first recorded booking (1) or a returning client (0)."
    ),
    "days_since_last_visit": "Days elapsed since the client's most recent prior appointment.",
    "booking_channel": "Method used to book the appointment (online, phone, walk-in).",
    "service_type": "The category or treatment booked.",
    "price": "Scheduled appointment fee or service value.",
    "deposit_paid": "Whether an upfront deposit or prepayment was collected.",
    "confirmation_received": "Whether the client confirmed their attendance in advance.",
}


def _normalize(col: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", col.strip().lower()).strip("_")


def generate_feature_audit(
    raw_columns: list[str],
    sample_values: dict[str, str] | None = None,
) -> list[FeatureAuditEntry]:
    """Generate an audit list of columns in the dataset showing usage and exclusion reasons.

    Args:
        raw_columns: Original column headers from the imported CSV.
        sample_values: Optional sample values per header for display.

    Returns:
        List of FeatureAuditEntry records.
    """
    entries: list[FeatureAuditEntry] = []
    samples = sample_values or {}

    for col in raw_columns:
        norm = _normalize(col)
        sample = samples.get(col)

        # Check if explicitly excluded
        matched_exclusion = None
        for exc_key, reason in EXCLUSION_REASONS.items():
            if norm == exc_key or exc_key in norm:
                matched_exclusion = reason
                break

        if matched_exclusion:
            entries.append(
                FeatureAuditEntry(
                    column_name=col,
                    status="excluded",
                    reason=matched_exclusion,
                    sample_value=sample,
                )
            )
        elif norm in ALLOWED_FEATURES:
            entries.append(
                FeatureAuditEntry(
                    column_name=col,
                    status="used",
                    reason=FEATURE_EXPLANATIONS.get(norm, "Used directly as a behavioral feature."),
                    sample_value=sample,
                )
            )
        else:
            entries.append(
                FeatureAuditEntry(
                    column_name=col,
                    status="excluded",
                    reason=(
                        "Excluded by allowlist: not an approved behavioral scheduling indicator. "
                        "ShowUp strictly limits model inputs to non-demographic booking variables."
                    ),
                    sample_value=sample,
                )
            )

    return entries
