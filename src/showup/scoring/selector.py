"""Model selection logic and plain-language explanation generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from showup.scoring.backtest import BacktestSummary


@dataclass
class SelectionResult:
    """Outcome of model selection process."""

    tier: int
    selected_model: str
    explanation: str
    metrics: dict[str, Any]


def select_scoring_model(
    total_labeled: int,
    total_no_shows: int,
    backtest: BacktestSummary | None = None,
    *,
    min_labeled_for_tier2: int = 100,
    min_no_shows_for_tier2: int = 10,
) -> SelectionResult:
    """Decide scoring tier and select the winning model based on factual data criteria.

    Enforces:
    1. Tier 1 (< 100 labeled or < 10 no-shows): rules engine only.
    2. Tier 2 (enough data): backtested comparison between simpler model and TabPFN.
       Chooses TabPFN only if it beats simpler model beyond the bootstrap noise margin;
       otherwise honestly explains that a simpler model was equally effective.
    """
    # ── Tier 1: Small dataset gate ──────────────────────────────────────
    if total_labeled < min_labeled_for_tier2 or total_no_shows < min_no_shows_for_tier2:
        return SelectionResult(
            tier=1,
            selected_model="rules",
            explanation=(
                f"Tier 1 (Rules Engine): Your account has {total_labeled} past bookings "
                f"({total_no_shows} no-shows). Statistical machine learning models require at "
                f"least {min_labeled_for_tier2} labeled bookings and {min_no_shows_for_tier2} "
                f"no-shows to generalize reliably without spurious noise. Transparent heuristic "
                f"rules are used until more history is available."
            ),
            metrics={
                "total_labeled": total_labeled,
                "total_no_shows": total_no_shows,
                "tier": 1,
            },
        )

    # ── Tier 2: Sufficient data for backtested selection ────────────────
    metrics_dict: dict[str, Any] = {
        "total_labeled": total_labeled,
        "total_no_shows": total_no_shows,
        "tier": 2,
    }

    if backtest is not None and backtest.models:
        metrics_dict["backtest"] = {name: asdict(m) for name, m in backtest.models.items()}

        tabpfn_m = backtest.models.get("tabpfn")
        log_m = backtest.models.get("logistic")

        # TabPFN is chosen ONLY if it significantly outperforms logistic baseline
        # (ROC-AUC beats baseline by > 0.02 and lower CI bound is higher than baseline's mean)
        if tabpfn_m and log_m:
            is_better = (
                tabpfn_m.roc_auc > log_m.roc_auc + 0.02 and tabpfn_m.roc_auc_ci_low >= log_m.roc_auc
            )
            if is_better:
                return SelectionResult(
                    tier=2,
                    selected_model="tabpfn",
                    explanation=(
                        f"TabPFN v2 selected: Demonstrated superior out-of-sample "
                        f"predictive accuracy (ROC-AUC: {tabpfn_m.roc_auc:.3f} "
                        f"[95% CI: {tabpfn_m.roc_auc_ci_low:.3f}-{tabpfn_m.roc_auc_ci_high:.3f}] "
                        f"vs Logistic: {log_m.roc_auc:.3f}) across historical "
                        f"expanding backtest windows."
                    ),
                    metrics=metrics_dict,
                )

            return SelectionResult(
                tier=2,
                selected_model="logistic",
                explanation=(
                    f"On your data a simpler model performed equally well "
                    f"(Logistic ROC-AUC: {log_m.roc_auc:.3f} vs TabPFN: {tabpfn_m.roc_auc:.3f}). "
                    f"ShowUp selected the simpler, calibrated logistic regression model for higher "
                    f"interpretability and speed."
                ),
                metrics=metrics_dict,
            )

        if log_m:
            return SelectionResult(
                tier=2,
                selected_model="logistic",
                explanation=(
                    f"Calibrated Logistic Regression selected based on historical evaluation "
                    f"(ROC-AUC: {log_m.roc_auc:.3f}, Brier score: {log_m.brier_score:.3f})."
                ),
                metrics=metrics_dict,
            )

    # Fallback to logistic if backtest summary was incomplete
    return SelectionResult(
        tier=2,
        selected_model="logistic",
        explanation="Logistic Regression selected for Tier 2 evaluation.",
        metrics=metrics_dict,
    )
