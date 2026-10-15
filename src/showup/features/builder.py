"""Feature builder for appointment bookings with strict zero-leakage enforcement."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pandas as pd

from showup.domain.enums import Outcome
from showup.domain.models import Booking
from showup.features.allowlist import enforce_allowlist


def _get_lead_time_bucket(hours: float) -> str:
    """Categorize lead time in hours into discrete buckets."""
    if hours < 24.0:
        return "0_to_24h"
    if hours < 72.0:
        return "24_to_72h"
    if hours < 168.0:
        return "3_to_7_days"
    if hours < 336.0:
        return "1_to_2_weeks"
    return "2_plus_weeks"


def compute_booking_features(
    booking: Booking,
    prior_bookings: list[Booking],
) -> dict[str, Any]:
    """Compute all 14 allowlisted features for a single booking.

    Args:
        booking: The target appointment booking to featurize.
        prior_bookings: Historical bookings for this client occurring STRICTLY BEFORE
            `booking.appointment_at`. Guaranteed zero temporal leakage.

    Returns:
        Dictionary of feature names matching ALLOWED_FEATURES to computed values.
    """
    # 1. Lead time
    if booking.booking_created_at is not None:
        delta_sec = (booking.appointment_at - booking.booking_created_at).total_seconds()
        lead_time_hours = max(0.0, delta_sec / 3600.0)
    else:
        # Default neutral estimate (48 hours / 2 days) when booking created time is unrecorded
        lead_time_hours = 48.0

    lead_time_bucket = _get_lead_time_bucket(lead_time_hours)

    # 2. Timing features
    day_of_week = booking.appointment_at.weekday()
    hour_of_day = booking.appointment_at.hour

    # 3. Client history features (calculated strictly from prior bookings)
    # Filter to completed historical bookings
    labeled_priors = [
        p
        for p in prior_bookings
        if p.appointment_at < booking.appointment_at
        and p.id != booking.id
        and p.outcome in (Outcome.ATTENDED, Outcome.NO_SHOW)
    ]

    prior_visits = len(labeled_priors)
    prior_no_shows = sum(1 for p in labeled_priors if p.outcome == Outcome.NO_SHOW)
    prior_no_show_rate = float(prior_no_shows) / float(prior_visits) if prior_visits > 0 else 0.0
    is_new_client = 1 if prior_visits == 0 else 0

    if prior_visits > 0:
        # Most recent prior appointment
        most_recent_prior = max(labeled_priors, key=lambda p: p.appointment_at)
        days_diff = (booking.appointment_at - most_recent_prior.appointment_at).total_seconds()
        days_since_last_visit = max(0.0, days_diff / 86400.0)
    else:
        # High constant value for new clients
        days_since_last_visit = 999.0

    # 4. Context & intervention features
    booking_channel = booking.channel.lower().strip() if booking.channel else "unknown"
    service_type = booking.service_type.lower().strip() if booking.service_type else "standard"
    price = float(booking.price) if booking.price is not None else 0.0
    deposit_paid = 1 if booking.deposit_paid is True else 0
    confirmation_received = 1 if booking.confirmed is True else 0

    return {
        "lead_time_hours": lead_time_hours,
        "lead_time_bucket": lead_time_bucket,
        "day_of_week": day_of_week,
        "hour_of_day": hour_of_day,
        "prior_visits": prior_visits,
        "prior_no_shows": prior_no_shows,
        "prior_no_show_rate": prior_no_show_rate,
        "is_new_client": is_new_client,
        "days_since_last_visit": days_since_last_visit,
        "booking_channel": booking_channel,
        "service_type": service_type,
        "price": price,
        "deposit_paid": deposit_paid,
        "confirmation_received": confirmation_received,
    }


def build_features_matrix(
    target_bookings: list[Booking],
    all_client_history: list[Booking],
) -> pd.DataFrame:
    """Construct a clean, allowlisted feature DataFrame for a batch of bookings.

    Organizes historical bookings by client_id and guarantees strictly temporal
    isolation (no future lookahead).
    """
    if not target_bookings:
        return pd.DataFrame()

    # Pre-index history by client_id
    history_by_client: dict[UUID, list[Booking]] = {}
    for h in all_client_history:
        history_by_client.setdefault(h.client_id, []).append(h)

    # Sort each client's history chronologically
    for client_history in history_by_client.values():
        client_history.sort(key=lambda b: b.appointment_at)

    rows: list[dict[str, Any]] = []
    for b in target_bookings:
        client_history = history_by_client.get(b.client_id, [])
        # Only pass historical bookings strictly before b.appointment_at
        priors_before_b = [p for p in client_history if p.appointment_at < b.appointment_at]
        row_feats = compute_booking_features(b, priors_before_b)
        rows.append(row_feats)

    df = pd.DataFrame(rows)
    # Strictly enforce allowlist before returning
    return enforce_allowlist(df)
