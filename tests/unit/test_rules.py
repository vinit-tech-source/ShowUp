"""Unit tests for Tier 1 rules engine."""

from __future__ import annotations

import pandas as pd

from showup.domain.enums import RiskBand
from showup.scoring.rules import (
    score_dataframe_with_rules,
    score_features_row_with_rules,
)


class TestRulesEngine:
    """Verify all branches of the heuristic rules engine."""

    def test_prior_noshow_yields_high_risk(self) -> None:
        row = {"prior_no_shows": 1, "is_new_client": 0, "lead_time_hours": 72.0}
        band, prob, expl = score_features_row_with_rules(row)
        assert band == RiskBand.HIGH
        assert prob == 0.75
        assert "previous unexcused absence" in expl

    def test_new_client_short_lead_time_yields_medium_risk(self) -> None:
        row = {"prior_no_shows": 0, "is_new_client": 1, "lead_time_hours": 20.0}
        band, prob, expl = score_features_row_with_rules(row)
        assert band == RiskBand.MEDIUM
        assert prob == 0.40
        assert "short notice" in expl

    def test_new_client_ample_lead_time_yields_low_risk(self) -> None:
        row = {"prior_no_shows": 0, "is_new_client": 1, "lead_time_hours": 72.0}
        band, prob, _expl = score_features_row_with_rules(row)
        assert band == RiskBand.LOW
        assert prob == 0.15

    def test_returning_client_clean_history_yields_low_risk(self) -> None:
        row = {"prior_no_shows": 0, "is_new_client": 0, "lead_time_hours": 12.0}
        band, prob, _expl = score_features_row_with_rules(row)
        assert band == RiskBand.LOW
        assert prob == 0.15

    def test_score_dataframe_batch(self) -> None:
        df = pd.DataFrame(
            [
                {"prior_no_shows": 2, "is_new_client": 0, "lead_time_hours": 48.0},
                {"prior_no_shows": 0, "is_new_client": 1, "lead_time_hours": 10.0},
                {"prior_no_shows": 0, "is_new_client": 0, "lead_time_hours": 48.0},
            ]
        )
        results = score_dataframe_with_rules(df)
        assert len(results) == 3
        assert results[0][0] == RiskBand.HIGH
        assert results[1][0] == RiskBand.MEDIUM
        assert results[2][0] == RiskBand.LOW
