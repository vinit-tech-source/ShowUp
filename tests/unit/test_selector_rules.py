"""Unit tests verifying strict model-selection explanation rules."""

from __future__ import annotations

from showup.scoring.backtest import BacktestSummary, ModelMetrics
from showup.scoring.selector import select_scoring_model


def test_selector_never_says_equally_well_when_auc_below_half() -> None:
    """When TabPFN has AUC < 0.5, selector reports worse than chance and never 'equally well'."""
    summary = BacktestSummary(
        models={
            "logistic": ModelMetrics(
                model_name="logistic",
                roc_auc=0.58,
                roc_auc_ci_low=0.42,
                roc_auc_ci_high=0.74,
                brier_score=0.23,
            ),
            "tabpfn": ModelMetrics(
                model_name="tabpfn",
                roc_auc=0.47,
                roc_auc_ci_low=0.36,
                roc_auc_ci_high=0.60,
                brier_score=0.14,
            ),
        },
        total_evaluated=160,
        total_no_shows=25,
    )
    result = select_scoring_model(total_labeled=160, total_no_shows=25, backtest=summary)
    assert result.selected_model == "logistic"
    assert "performed equally well" not in result.explanation
    assert "performed worse than chance on this data" in result.explanation


def test_selector_labels_ci_including_half_as_no_reliable_signal() -> None:
    """When a model's CI includes 0.5, selector labels it 'no reliable signal detected'."""
    summary = BacktestSummary(
        models={
            "logistic": ModelMetrics(
                model_name="logistic",
                roc_auc=0.52,
                roc_auc_ci_low=0.45,
                roc_auc_ci_high=0.61,
                brier_score=0.22,
            ),
            "tabpfn": ModelMetrics(
                model_name="tabpfn",
                roc_auc=0.51,
                roc_auc_ci_low=0.43,
                roc_auc_ci_high=0.59,
                brier_score=0.20,
            ),
        },
        total_evaluated=120,
        total_no_shows=20,
    )
    result = select_scoring_model(total_labeled=120, total_no_shows=20, backtest=summary)
    assert "no reliable signal detected" in result.explanation


def test_selector_warns_when_brier_good_but_auc_near_half() -> None:
    """When Brier <= 0.22 and AUC <= 0.52, selector flags average prediction behavior."""
    summary = BacktestSummary(
        models={
            "logistic": ModelMetrics(
                model_name="logistic",
                roc_auc=0.58,
                roc_auc_ci_low=0.51,
                roc_auc_ci_high=0.66,
                brier_score=0.22,
            ),
            "tabpfn": ModelMetrics(
                model_name="tabpfn",
                roc_auc=0.50,
                roc_auc_ci_low=0.40,
                roc_auc_ci_high=0.60,
                brier_score=0.13,
            ),
        },
        total_evaluated=150,
        total_no_shows=20,
    )
    result = select_scoring_model(total_labeled=150, total_no_shows=20, backtest=summary)
    assert "mostly predicts the average no-show rate" in result.explanation


def test_selector_says_equally_well_only_when_both_above_half_and_overlapping() -> None:
    """When both AUC > 0.5 and CIs overlap, selector reports equally well."""
    summary = BacktestSummary(
        models={
            "logistic": ModelMetrics(
                model_name="logistic",
                roc_auc=0.75,
                roc_auc_ci_low=0.68,
                roc_auc_ci_high=0.82,
                brier_score=0.16,
            ),
            "tabpfn": ModelMetrics(
                model_name="tabpfn",
                roc_auc=0.76,
                roc_auc_ci_low=0.67,
                roc_auc_ci_high=0.83,
                brier_score=0.15,
            ),
        },
        total_evaluated=150,
        total_no_shows=30,
    )
    result = select_scoring_model(total_labeled=150, total_no_shows=30, backtest=summary)
    assert result.selected_model == "logistic"
    assert "performed equally well" in result.explanation


def test_selector_explains_why_rules_not_selected_despite_higher_auc() -> None:
    """When rules engine has higher AUC than winning statistical model, explanation notes why."""
    summary = BacktestSummary(
        models={
            "rules": ModelMetrics(
                model_name="rules",
                roc_auc=0.68,
                roc_auc_ci_low=0.58,
                roc_auc_ci_high=0.77,
                brier_score=0.21,
            ),
            "logistic": ModelMetrics(
                model_name="logistic",
                roc_auc=0.58,
                roc_auc_ci_low=0.45,
                roc_auc_ci_high=0.70,
                brier_score=0.23,
            ),
            "tabpfn": ModelMetrics(
                model_name="tabpfn",
                roc_auc=0.48,
                roc_auc_ci_low=0.36,
                roc_auc_ci_high=0.60,
                brier_score=0.14,
            ),
        },
        total_evaluated=160,
        total_no_shows=25,
    )
    result = select_scoring_model(total_labeled=160, total_no_shows=25, backtest=summary)
    assert result.selected_model == "logistic"
    assert "heuristic rules engine achieved a higher ROC-AUC (0.680)" in result.explanation
    assert "calibrated probabilities" in result.explanation
