"""Integration tests for backtesting and model selection pipeline."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from showup.domain.enums import Outcome
from showup.domain.models import Booking
from showup.scoring.backtest import BacktestSummary, ModelMetrics, run_time_ordered_backtest
from showup.scoring.selector import select_scoring_model


@pytest.fixture
def sequence_of_bookings() -> list[Booking]:
    """Create a realistic sequence of chronologically ordered bookings."""
    bookings: list[Booking] = []
    base_time = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    clients = [uuid4() for _ in range(15)]

    for i in range(80):
        client_id = clients[i % len(clients)]
        app_time = base_time + timedelta(days=i)
        created_time = app_time - timedelta(days=(i % 5) + 1)
        outcome = Outcome.NO_SHOW if (i % 5 == 0) else Outcome.ATTENDED
        bookings.append(
            Booking(
                client_id=client_id,
                appointment_at=app_time,
                booking_created_at=created_time,
                service_type="Standard",
                price=60.0,
                channel="online" if i % 2 == 0 else "phone",
                deposit_paid=(i % 3 == 0),
                confirmed=(i % 2 == 0),
                outcome=outcome,
            )
        )
    return bookings


@pytest.mark.integration
class TestScoringPipeline:
    """Verify end-to-end backtesting and selector decision logic."""

    def test_backtest_execution(self, sequence_of_bookings: list[Booking]) -> None:
        summary = run_time_ordered_backtest(
            sequence_of_bookings,
            min_train_size=30,
            step_size=15,
            random_state=42,
        )
        assert summary.total_evaluated > 0
        assert "rules" in summary.models
        assert "logistic" in summary.models

        log_metrics = summary.models["logistic"]
        assert 0.0 <= log_metrics.roc_auc <= 1.0
        assert 0.0 <= log_metrics.pr_auc <= 1.0
        assert log_metrics.sample_size == summary.total_evaluated

    def test_selector_tier1_low_sample_gate(self) -> None:
        result = select_scoring_model(total_labeled=45, total_no_shows=5)
        assert result.tier == 1
        assert result.selected_model == "rules"
        assert "require at least 100 labeled bookings" in result.explanation

    def test_selector_tier2_selects_logistic_with_honest_explanation(self) -> None:
        summary = BacktestSummary(
            models={
                "logistic": ModelMetrics(
                    model_name="logistic",
                    roc_auc=0.78,
                    roc_auc_ci_low=0.71,
                    roc_auc_ci_high=0.85,
                    brier_score=0.14,
                ),
                "tabpfn": ModelMetrics(
                    model_name="tabpfn",
                    roc_auc=0.79,
                    roc_auc_ci_low=0.70,
                    roc_auc_ci_high=0.86,
                    brier_score=0.15,
                ),
            },
            total_evaluated=120,
            total_no_shows=25,
        )
        result = select_scoring_model(
            total_labeled=120,
            total_no_shows=25,
            backtest=summary,
        )
        assert result.tier == 2
        # TabPFN did not significantly beat logistic (CIs overlap and diff <= 0.02)
        assert result.selected_model == "logistic"
        assert "simpler model performed equally well" in result.explanation

    def test_selector_tier2_selects_tabpfn_when_significantly_better(self) -> None:
        summary = BacktestSummary(
            models={
                "logistic": ModelMetrics(
                    model_name="logistic",
                    roc_auc=0.70,
                    roc_auc_ci_low=0.62,
                    roc_auc_ci_high=0.77,
                    brier_score=0.18,
                ),
                "tabpfn": ModelMetrics(
                    model_name="tabpfn",
                    roc_auc=0.82,
                    roc_auc_ci_low=0.75,
                    roc_auc_ci_high=0.89,
                    brier_score=0.12,
                ),
            },
            total_evaluated=150,
            total_no_shows=30,
        )
        result = select_scoring_model(
            total_labeled=150,
            total_no_shows=30,
            backtest=summary,
        )
        assert result.tier == 2
        assert result.selected_model == "tabpfn"
        assert "Demonstrated superior out-of-sample predictive accuracy" in result.explanation
