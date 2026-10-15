"""Expanding-window, time-ordered backtesting with bootstrap confidence intervals."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from showup.domain.enums import Outcome
from showup.domain.models import Booking
from showup.features.builder import build_features_matrix
from showup.logging_setup import get_logger
from showup.scoring.baseline import LogisticBaseline
from showup.scoring.rules import score_dataframe_with_rules

logger = get_logger(__name__)


@dataclass
class ModelMetrics:
    """Evaluation metrics for a model candidate."""

    model_name: str
    roc_auc: float = 0.5
    roc_auc_ci_low: float = 0.5
    roc_auc_ci_high: float = 0.5
    pr_auc: float = 0.0
    pr_auc_ci_low: float = 0.0
    pr_auc_ci_high: float = 0.0
    brier_score: float = 0.25
    sample_size: int = 0


@dataclass
class BacktestSummary:
    """Summary of backtest results across models."""

    models: dict[str, ModelMetrics] = field(default_factory=dict)
    total_evaluated: int = 0
    total_no_shows: int = 0


def _compute_bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    metric_fn: Any,
    *,
    n_bootstraps: int = 200,
    random_state: int = 42,
) -> tuple[float, float]:
    """Compute empirical 95% bootstrap confidence interval [2.5%, 97.5%]."""
    rng = np.random.default_rng(random_state)
    n = len(y_true)
    if n < 10 or len(np.unique(y_true)) < 2:
        return 0.0, 1.0

    scores: list[float] = []
    for _ in range(n_bootstraps):
        indices = rng.integers(0, n, size=n)
        sample_y = y_true[indices]
        sample_pred = y_pred[indices]
        if len(np.unique(sample_y)) < 2:
            continue
        try:
            val = float(metric_fn(sample_y, sample_pred))
            scores.append(val)
        except Exception as e:
            logger.debug("bootstrap_metric_failed", error=str(e))
            continue

    if not scores:
        return 0.0, 1.0

    low = float(np.percentile(scores, 2.5))
    high = float(np.percentile(scores, 97.5))
    return max(0.0, low), min(1.0, high)


def _compute_metrics_summary(
    y_true_arr: np.ndarray,
    preds_by_model: dict[str, list[float]],
    random_state: int,
) -> dict[str, ModelMetrics]:
    """Calculate ROC-AUC, PR-AUC, Brier score and bootstrap CIs for all evaluated models."""
    metrics_map: dict[str, ModelMetrics] = {}
    for model_name, preds in preds_by_model.items():
        if len(preds) != len(y_true_arr):
            continue
        pred_arr = np.array(preds)
        try:
            roc = float(roc_auc_score(y_true_arr, pred_arr))
        except Exception:
            roc = 0.5

        try:
            pr = float(average_precision_score(y_true_arr, pred_arr))
        except Exception:
            pr = float(np.mean(y_true_arr))

        brier = float(brier_score_loss(y_true_arr, pred_arr))

        roc_ci_low, roc_ci_high = _compute_bootstrap_ci(
            y_true_arr, pred_arr, roc_auc_score, random_state=random_state
        )
        pr_ci_low, pr_ci_high = _compute_bootstrap_ci(
            y_true_arr, pred_arr, average_precision_score, random_state=random_state
        )

        metrics_map[model_name] = ModelMetrics(
            model_name=model_name,
            roc_auc=round(roc, 3),
            roc_auc_ci_low=round(roc_ci_low, 3),
            roc_auc_ci_high=round(roc_ci_high, 3),
            pr_auc=round(pr, 3),
            pr_auc_ci_low=round(pr_ci_low, 3),
            pr_auc_ci_high=round(pr_ci_high, 3),
            brier_score=round(brier, 3),
            sample_size=len(y_true_arr),
        )
    return metrics_map


def run_time_ordered_backtest(
    labeled_bookings: list[Booking],
    *,
    min_train_size: int = 30,
    step_size: int = 15,
    random_state: int = 42,
    include_tabpfn: bool = False,
    tabpfn_model: Any = None,
) -> BacktestSummary:
    """Execute expanding-window time-ordered evaluation.

    Guarantees that models are trained strictly on chronologically prior bookings
    and evaluated on future unseen bookings.
    """
    sorted_bookings = sorted(labeled_bookings, key=lambda b: b.appointment_at)
    total_n = len(sorted_bookings)

    if total_n < min_train_size + 5:
        logger.info(
            "insufficient_data_for_backtest", count=total_n, min_required=min_train_size + 5
        )
        return BacktestSummary()

    # Collectors for out-of-fold predictions
    y_true_all: list[int] = []
    preds_by_model: dict[str, list[float]] = {
        "rules": [],
        "logistic": [],
    }
    if include_tabpfn and tabpfn_model is not None:
        preds_by_model["tabpfn"] = []

    current_idx = min_train_size
    while current_idx < total_n:
        test_end = min(current_idx + step_size, total_n)
        train_bookings = sorted_bookings[:current_idx]
        test_bookings = sorted_bookings[current_idx:test_end]

        y_train = [1 if b.outcome == Outcome.NO_SHOW else 0 for b in train_bookings]
        y_test = [1 if b.outcome == Outcome.NO_SHOW else 0 for b in test_bookings]

        # Require at least one positive and one negative in training data to fit models
        if len(set(y_train)) < 2:
            current_idx = test_end
            continue

        # Build feature matrices
        X_train = build_features_matrix(train_bookings, train_bookings)
        X_test = build_features_matrix(test_bookings, train_bookings)

        # 1. Rules evaluation
        rule_results = score_dataframe_with_rules(X_test)
        preds_by_model["rules"].extend([r[1] for r in rule_results])

        # 2. Logistic baseline evaluation
        log_model = LogisticBaseline(random_state=random_state)
        log_model.fit(X_train, np.array(y_train))
        log_probs = log_model.predict_proba(X_test)
        preds_by_model["logistic"].extend(log_probs.tolist())

        # 3. Optional TabPFN evaluation
        if include_tabpfn and tabpfn_model is not None:
            try:
                tp_probs = tabpfn_model.predict_proba(X_train, np.array(y_train), X_test)
                preds_by_model["tabpfn"].extend(tp_probs.tolist())
            except Exception as e:
                logger.warning("tabpfn_backtest_step_failed", error=str(e))
                preds_by_model["tabpfn"].extend(log_probs.tolist())

        y_true_all.extend(y_test)
        current_idx = test_end

    if not y_true_all or len(set(y_true_all)) < 2:
        return BacktestSummary()

    y_true_arr = np.array(y_true_all)
    metrics_map = _compute_metrics_summary(y_true_arr, preds_by_model, random_state)

    return BacktestSummary(
        models=metrics_map,
        total_evaluated=len(y_true_arr),
        total_no_shows=int(np.sum(y_true_arr)),
    )
