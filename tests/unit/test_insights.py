"""Unit tests for insights: cost report and grounded what-if analysis."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from showup.domain.enums import Outcome
from showup.domain.models import Booking
from showup.insights.cost_report import compute_cost_report
from showup.insights.whatif import compute_grounded_whatif


class TestCostReport:
    """Verify deterministic cost calculations and sample size gating."""

    def test_cost_report_sufficient_data(self) -> None:
        client_id = uuid4()
        base_time = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
        bookings: list[Booking] = []

        # 20 attended at $50, 5 no-shows at $50 (lost revenue: $250, total: 25)
        for i in range(25):
            outcome = Outcome.NO_SHOW if i < 5 else Outcome.ATTENDED
            bookings.append(
                Booking(
                    client_id=client_id,
                    appointment_at=base_time + timedelta(days=i),
                    price=50.0,
                    outcome=outcome,
                )
            )

        report = compute_cost_report(bookings)
        assert report.has_sufficient_data
        assert report.total_labeled == 25
        assert report.overall_no_show_count == 5
        assert report.overall_no_show_rate == 0.20  # 5 / 25
        assert report.total_lost_revenue == 250.0
        assert report.average_booking_price == 50.0
        assert len(report.monthly_breakdown) > 0

    def test_cost_report_insufficient_data(self) -> None:
        client_id = uuid4()
        bookings = [
            Booking(
                client_id=client_id,
                appointment_at=datetime.now(UTC),
                price=60.0,
                outcome=Outcome.ATTENDED,
            )
        ]
        report = compute_cost_report(bookings, min_labeled_threshold=10)
        assert not report.has_sufficient_data
        assert report.overall_no_show_rate is None
        assert "Not enough data" in report.status_message


class TestGroundedWhatIf:
    """Verify what-if empirical comparisons, visibility gating, and confounding notes."""

    def test_whatif_card_visible_when_sample_sufficient(self) -> None:
        client_id = uuid4()
        base_time = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
        bookings: list[Booking] = []

        # 25 bookings with deposit (23 attended = 92% show rate)
        for i in range(25):
            outcome = Outcome.ATTENDED if i < 23 else Outcome.NO_SHOW
            bookings.append(
                Booking(
                    client_id=client_id,
                    appointment_at=base_time + timedelta(days=i),
                    deposit_paid=True,
                    confirmed=True,
                    outcome=outcome,
                )
            )

        # 25 bookings without deposit (15 attended = 60% show rate)
        for i in range(25):
            outcome = Outcome.ATTENDED if i < 15 else Outcome.NO_SHOW
            bookings.append(
                Booking(
                    client_id=client_id,
                    appointment_at=base_time + timedelta(days=i + 30),
                    deposit_paid=False,
                    confirmed=False,
                    outcome=outcome,
                )
            )

        cards = compute_grounded_whatif(bookings, min_sample=20)
        dep_card = cards["deposit_paid"]

        assert dep_card.is_visible
        assert dep_card.with_count == 25
        assert dep_card.without_count == 25
        assert dep_card.with_show_rate == 0.92
        assert dep_card.without_show_rate == 0.60
        assert dep_card.difference_pp == 32.0
        assert "In your history" in dep_card.factual_statement
        assert "confounding" in dep_card.confounding_note.lower()

    def test_whatif_card_hidden_when_sample_insufficient(self) -> None:
        client_id = uuid4()
        # Only 5 with deposit, 5 without
        bookings = [
            Booking(
                client_id=client_id,
                appointment_at=datetime.now(UTC),
                deposit_paid=True,
                outcome=Outcome.ATTENDED,
            ),
            Booking(
                client_id=client_id,
                appointment_at=datetime.now(UTC),
                deposit_paid=False,
                outcome=Outcome.ATTENDED,
            ),
        ]
        cards = compute_grounded_whatif(bookings, min_sample=20)
        dep_card = cards["deposit_paid"]
        assert not dep_card.is_visible
        assert dep_card.difference_pp is None
        assert "Insufficient historical volume" in dep_card.factual_statement
