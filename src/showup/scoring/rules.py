"""Tier 1 rule-based scoring engine for small or sparse datasets."""

from __future__ import annotations

from typing import Any

import pandas as pd

from showup.domain.enums import RiskBand


def score_features_row_with_rules(row: dict[str, Any] | pd.Series) -> tuple[RiskBand, float, str]:
    """Score a single appointment using heuristic rules.

    Rules:
    1. If client had prior no-show(s) -> High Risk (~0.75 probability).
    2. If client is new AND lead time < 48 hours -> Medium Risk (~0.40 probability).
    3. Otherwise -> Low Risk (~0.15 probability).

    Returns:
        (RiskBand, probability, plain_language_explanation)
    """
    prior_no_shows = int(row.get("prior_no_shows", 0))
    is_new = int(row.get("is_new_client", 1))
    lead_time = float(row.get("lead_time_hours", 48.0))

    if prior_no_shows > 0:
        return (
            RiskBand.HIGH,
            0.75,
            f"High risk: client had {prior_no_shows} previous unexcused absence(s).",
        )

    if is_new == 1 and lead_time < 48.0:
        return (
            RiskBand.MEDIUM,
            0.40,
            f"Medium risk: first-time client booked on short notice ({lead_time:.0f}h lead time).",
        )

    return (
        RiskBand.LOW,
        0.15,
        "Low risk: established attendance history or standard advance notice.",
    )


def score_dataframe_with_rules(df: pd.DataFrame) -> list[tuple[RiskBand, float, str]]:
    """Score an entire DataFrame of features using the Tier 1 rule engine."""
    results: list[tuple[RiskBand, float, str]] = []
    for _, row in df.iterrows():
        results.append(score_features_row_with_rules(row))
    return results
