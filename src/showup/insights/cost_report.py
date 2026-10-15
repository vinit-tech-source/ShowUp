"""Deterministic cost report computed strictly from the owner's historical bookings."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Final

from showup.domain.enums import Outcome
from showup.domain.models import Booking

MIN_BOOKINGS_FOR_MONTHLY_METRIC: Final[int] = 5
MIN_TOTAL_LABELED_FOR_REPORT: Final[int] = 10


@dataclass(frozen=True)
class MonthlyCostItem:
    """Monthly aggregate of attendance and lost revenue."""

    year_month: str
    total_bookings: int
    no_show_count: int
    attended_count: int
    no_show_rate: float | None
    lost_revenue: float
    total_revenue_collected: float
    has_sufficient_data: bool
    status_message: str


@dataclass(frozen=True)
class CostReport:
    """Complete cost report computed purely from owner data."""

    total_bookings: int
    total_labeled: int
    overall_no_show_count: int
    overall_no_show_rate: float | None
    total_lost_revenue: float
    average_monthly_lost_revenue: float | None
    average_booking_price: float | None
    priced_no_show_count: int
    unpriced_no_show_count: int
    has_sufficient_data: bool
    status_message: str
    monthly_breakdown: list[MonthlyCostItem]


def compute_cost_report(
    bookings: list[Booking],
    *,
    min_labeled_threshold: int = MIN_TOTAL_LABELED_FOR_REPORT,
    min_monthly_threshold: int = MIN_BOOKINGS_FOR_MONTHLY_METRIC,
) -> CostReport:
    """Calculate historical no-show costs using ONLY the owner's deterministic data.

    Never quotes industry stats or fabricates benchmarks.
    If sample sizes are too small, returns None for noisy rates and marks status.
    """
    labeled_bookings = [b for b in bookings if b.outcome in (Outcome.ATTENDED, Outcome.NO_SHOW)]
    total_labeled = len(labeled_bookings)

    if total_labeled < min_labeled_threshold:
        return CostReport(
            total_bookings=len(bookings),
            total_labeled=total_labeled,
            overall_no_show_count=sum(1 for b in labeled_bookings if b.outcome == Outcome.NO_SHOW),
            overall_no_show_rate=None,
            total_lost_revenue=0.0,
            average_monthly_lost_revenue=None,
            average_booking_price=None,
            priced_no_show_count=0,
            unpriced_no_show_count=0,
            has_sufficient_data=False,
            status_message=(
                f"Not enough data: {total_labeled} labeled booking(s) recorded. "
                f"At least {min_labeled_threshold} are required to calculate reliable cost metrics."
            ),
            monthly_breakdown=[],
        )

    # 1. Overall metrics
    total_no_shows = sum(1 for b in labeled_bookings if b.outcome == Outcome.NO_SHOW)
    overall_rate = float(total_no_shows) / float(total_labeled)

    total_lost_rev = 0.0
    priced_ns_count = 0
    unpriced_ns_count = 0

    known_prices: list[float] = []
    for b in labeled_bookings:
        if b.price is not None and b.price > 0.0:
            known_prices.append(b.price)
            if b.outcome == Outcome.NO_SHOW:
                total_lost_rev += b.price
                priced_ns_count += 1
        elif b.outcome == Outcome.NO_SHOW:
            unpriced_ns_count += 1

    avg_price = float(sum(known_prices)) / float(len(known_prices)) if known_prices else None

    # 2. Monthly aggregation
    monthly_data: dict[str, list[Booking]] = defaultdict(list)
    for b in labeled_bookings:
        ym = b.appointment_at.strftime("%Y-%m")
        monthly_data[ym].append(b)

    monthly_items: list[MonthlyCostItem] = []
    monthly_lost_revs: list[float] = []

    for ym in sorted(monthly_data.keys()):
        m_bookings = monthly_data[ym]
        m_total = len(m_bookings)
        m_no_shows = sum(1 for b in m_bookings if b.outcome == Outcome.NO_SHOW)
        m_attended = m_total - m_no_shows

        m_lost = sum(
            b.price for b in m_bookings if b.outcome == Outcome.NO_SHOW and b.price is not None
        )
        m_collected = sum(
            b.price for b in m_bookings if b.outcome == Outcome.ATTENDED and b.price is not None
        )

        has_data = m_total >= min_monthly_threshold
        m_rate = (float(m_no_shows) / float(m_total)) if has_data else None
        status = (
            "Sufficient data"
            if has_data
            else f"Low sample size (N={m_total}; min={min_monthly_threshold})"
        )

        monthly_items.append(
            MonthlyCostItem(
                year_month=ym,
                total_bookings=m_total,
                no_show_count=m_no_shows,
                attended_count=m_attended,
                no_show_rate=round(m_rate, 3) if m_rate is not None else None,
                lost_revenue=round(m_lost, 2),
                total_revenue_collected=round(m_collected, 2),
                has_sufficient_data=has_data,
                status_message=status,
            )
        )
        if has_data:
            monthly_lost_revs.append(m_lost)

    avg_monthly_lost = (
        float(sum(monthly_lost_revs)) / float(len(monthly_lost_revs)) if monthly_lost_revs else None
    )

    return CostReport(
        total_bookings=len(bookings),
        total_labeled=total_labeled,
        overall_no_show_count=total_no_shows,
        overall_no_show_rate=round(overall_rate, 3),
        total_lost_revenue=round(total_lost_rev, 2),
        average_monthly_lost_revenue=(
            round(avg_monthly_lost, 2) if avg_monthly_lost is not None else None
        ),
        average_booking_price=round(avg_price, 2) if avg_price is not None else None,
        priced_no_show_count=priced_ns_count,
        unpriced_no_show_count=unpriced_ns_count,
        has_sufficient_data=True,
        status_message="Computed strictly from your historical booking records.",
        monthly_breakdown=monthly_items,
    )
