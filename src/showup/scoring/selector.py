"""Model selection logic and plain-language explanation generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from showup.scoring.backtest import BacktestSummary, ModelMetrics


@dataclass
class SelectionResult:
    """Outcome of model selection process."""

    tier: int
    selected_model: str
    explanation: str
    metrics: dict[str, Any]


def _format_model_diagnostic(m: ModelMetrics, model_label: str) -> str:
    """Produce honest, scientifically grounded diagnostic text for a model."""
    parts: list[str] = []
    if m.roc_auc < 0.5:
        parts.append(
            f"{model_label} performed worse than chance on this data (ROC-AUC: {m.roc_auc:.3f})"
        )
    elif m.roc_auc_ci_low <= 0.5 <= m.roc_auc_ci_high:
        parts.append(
            f"{model_label}: no reliable signal detected (ROC-AUC: {m.roc_auc:.3f}, "
            f"95% CI: [{m.roc_auc_ci_low:.3f}-{m.roc_auc_ci_high:.3f}])"
        )
    else:
        parts.append(
            f"{model_label} achieved ROC-AUC: {m.roc_auc:.3f} "
            f"[95% CI: {m.roc_auc_ci_low:.3f}-{m.roc_auc_ci_high:.3f}]"
        )

    if m.roc_auc <= 0.52 and m.brier_score <= 0.22:
        parts.append(
            "This model mostly predicts the average no-show rate and does not "
            "separate high-risk from low-risk appointments."
        )

    return " ".join(parts)


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
       otherwise honestly explains model performance without claiming equality when AUC <= 0.5.
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
                "baseline_model": "Heuristic Rules",
            },
        )

    # ── Tier 2: Sufficient data for backtested selection ────────────────
    metrics_dict: dict[str, Any] = {
        "total_labeled": total_labeled,
        "total_no_shows": total_no_shows,
        "tier": 2,
        "baseline_model": "Calibrated Logistic Regression",
    }

    if backtest is not None and backtest.models:
        metrics_dict["backtest"] = {name: asdict(m) for name, m in backtest.models.items()}

        tabpfn_m = backtest.models.get("tabpfn")
        log_m = backtest.models.get("logistic")
        rules_m = backtest.models.get("rules")

        # TabPFN is chosen ONLY if it significantly outperforms logistic baseline
        # (ROC-AUC beats baseline by > 0.02 and lower CI bound is higher than baseline's mean)
        if tabpfn_m and log_m:
            is_better = (
                tabpfn_m.roc_auc > log_m.roc_auc + 0.02 and tabpfn_m.roc_auc_ci_low >= log_m.roc_auc
            )
            if is_better:
                rules_note = ""
                if rules_m and rules_m.roc_auc > tabpfn_m.roc_auc:
                    rules_note = (
                        f" (Note: Rules engine achieved ROC-AUC {rules_m.roc_auc:.3f}, but is not "
                        f"selected because heuristic rules output coarse step scores rather than "
                        f"calibrated probability distributions)."
                    )
                return SelectionResult(
                    tier=2,
                    selected_model="tabpfn",
                    explanation=(
                        f"TabPFN v2 selected (Baseline: Calibrated Logistic Regression): "
                        f"Demonstrated superior out-of-sample predictive accuracy "
                        f"(ROC-AUC: {tabpfn_m.roc_auc:.3f} "
                        f"[95% CI: {tabpfn_m.roc_auc_ci_low:.3f}-{tabpfn_m.roc_auc_ci_high:.3f}] "
                        f"vs Logistic: {log_m.roc_auc:.3f}) across historical "
                        f"expanding backtest windows.{rules_note}"
                    ),
                    metrics=metrics_dict,
                )

            # TabPFN did not beat baseline. Determine honest explanation.
            # Only say "performed equally well" if BOTH models have reliable signal
            # (CI strictly above 0.5) and CIs overlap.
            ci_overlap = not (
                tabpfn_m.roc_auc_ci_low > log_m.roc_auc_ci_high
                or log_m.roc_auc_ci_low > tabpfn_m.roc_auc_ci_high
            )
            both_reliable_signal = (
                log_m.roc_auc_ci_low > 0.5
                and tabpfn_m.roc_auc_ci_low > 0.5
                and log_m.roc_auc > 0.5
                and tabpfn_m.roc_auc > 0.5
            )

            rules_note = ""
            if rules_m and rules_m.roc_auc > log_m.roc_auc:
                rules_note = (
                    f" While the heuristic rules engine achieved a higher ROC-AUC "
                    f"({rules_m.roc_auc:.3f}), ShowUp selected Calibrated Logistic Regression "
                    f"to provide smooth calibrated probabilities required for financial loss "
                    f"estimation and to continuously adapt to new data."
                )

            if both_reliable_signal and ci_overlap:
                explanation = (
                    f"On your data a simpler model performed equally well "
                    f"(Logistic ROC-AUC: {log_m.roc_auc:.3f} vs TabPFN: {tabpfn_m.roc_auc:.3f}). "
                    f"ShowUp selected the simpler, calibrated logistic regression baseline for "
                    f"higher interpretability and speed.{rules_note}"
                )
            else:
                # Diagnostic explanation when one or both failed to demonstrate reliable signal
                diag_tabpfn = _format_model_diagnostic(tabpfn_m, "TabPFN")
                diag_log = _format_model_diagnostic(log_m, "Logistic Regression")
                explanation = (
                    f"Historical backtest comparison (Baseline: Calibrated Logistic Regression): "
                    f"{diag_tabpfn}. {diag_log}. "
                    f"ShowUp retained Calibrated Logistic Regression as the Tier 2 baseline."
                    f"{rules_note}"
                )

            return SelectionResult(
                tier=2,
                selected_model="logistic",
                explanation=explanation,
                metrics=metrics_dict,
            )

        if log_m:
            rules_note = ""
            if rules_m and rules_m.roc_auc > log_m.roc_auc:
                rules_note = (
                    f" (Rules engine ROC-AUC: {rules_m.roc_auc:.3f}; "
                    f"logistic selected for calibrated probabilities)."
                )
            diag_log = _format_model_diagnostic(log_m, "Calibrated Logistic Regression")
            return SelectionResult(
                tier=2,
                selected_model="logistic",
                explanation=(
                    f"{diag_log} (Brier score: {log_m.brier_score:.3f}). "
                    f"Selected as the Tier 2 baseline.{rules_note}"
                ),
                metrics=metrics_dict,
            )

    # Fallback to logistic if backtest summary was incomplete
    return SelectionResult(
        tier=2,
        selected_model="logistic",
        explanation="Calibrated Logistic Regression selected as the baseline Tier 2 model.",
        metrics=metrics_dict,
    )
