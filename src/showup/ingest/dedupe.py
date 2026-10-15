"""Deduplication logic for bookings imported from CSV."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from showup.domain.enums import Outcome
from showup.domain.models import Booking


def dedupe_bookings(bookings: list[Booking]) -> tuple[list[Booking], int]:
    """Deduplicate bookings by (client_id, appointment_at).

    If duplicate bookings occur for the same client at the exact same appointment time,
    the later one (or the one with outcome if earlier was pending) is retained.

    Returns:
        (deduplicated_bookings_list, count_of_duplicates_removed)
    """
    if not bookings:
        return [], 0

    seen: dict[tuple[UUID, datetime], Booking] = {}
    duplicate_count = 0

    for booking in bookings:
        key = (booking.client_id, booking.appointment_at)
        if key in seen:
            duplicate_count += 1
            existing = seen[key]
            # If earlier booking had no outcome or was pending,
            # and new has concrete outcome, replace
            is_existing_unlabeled = existing.outcome is None or existing.outcome == Outcome.PENDING
            is_new_labeled = booking.outcome in (Outcome.ATTENDED, Outcome.NO_SHOW)
            if is_existing_unlabeled and is_new_labeled:
                seen[key] = booking
        else:
            seen[key] = booking

    return list(seen.values()), duplicate_count
