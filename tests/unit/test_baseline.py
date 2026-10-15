"""Unit tests for Logistic Regression baseline model."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from showup.domain.enums import RiskBand
from showup.scoring.baseline import LogisticBaseline


@pytest.fixture
def sample_feature_df() -> tuple[pd.DataFrame, np.ndarray]:
    """Generate sample training data."""
    rng = np.random.default_rng(42)
    n = 100
    df = pd.DataFrame(
        {
            "lead_time_hours": rng.uniform(2, 200, n),
            "lead_time_bucket": rng.choice(["0_to_24h", "24_to_72h", "3_to_7_days"], n),
            "day_of_week": rng.integers(0, 7, n),
            "hour_of_day": rng.integers(8, 20, n),
            "prior_visits": rng.integers(0, 10, n),
            "prior_no_shows": rng.integers(0, 3, n),
            "prior_no_show_rate": rng.uniform(0, 0.5, n),
            "is_new_client": rng.choice([0, 1], n),
            "days_since_last_visit": rng.uniform(5, 100, n),
            "booking_channel": rng.choice(["online", "phone"], n),
            "service_type": rng.choice(["standard", "premium"], n),
            "price": rng.uniform(30, 150, n),
            "deposit_paid": rng.choice([0, 1], n),
            "confirmation_received": rng.choice([0, 1], n),
        }
    )
    y = rng.choice([0, 1], n, p=[0.8, 0.2])
    return df, y


class TestLogisticBaseline:
    """Verify LogisticBaseline training, prediction, calibration, and explanations."""

    def test_fit_and_predict_proba(
        self, sample_feature_df: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        X, y = sample_feature_df
        model = LogisticBaseline(random_state=42)
        model.fit(X, y)
        assert model.is_fitted

        probas = model.predict_proba(X)
        assert len(probas) == len(X)
        assert np.all(probas >= 0.0)
        assert np.all(probas <= 1.0)

    def test_unfitted_raises_runtime_error(
        self, sample_feature_df: tuple[pd.DataFrame, np.ndarray]
    ) -> None:
        X, _ = sample_feature_df
        model = LogisticBaseline()
        with pytest.raises(RuntimeError, match="fitted before predict_proba"):
            model.predict_proba(X)

    def test_classify_risk_band(self) -> None:
        assert LogisticBaseline.classify_risk_band(0.10) == RiskBand.LOW
        assert LogisticBaseline.classify_risk_band(0.35) == RiskBand.MEDIUM
        assert LogisticBaseline.classify_risk_band(0.70) == RiskBand.HIGH

    def test_explain_prediction(self, sample_feature_df: tuple[pd.DataFrame, np.ndarray]) -> None:
        X, y = sample_feature_df
        model = LogisticBaseline().fit(X, y)
        row = X.iloc[0]
        proba = model.predict_proba(X.iloc[[0]])[0]
        explanation = model.explain_prediction(row, proba)
        assert "risk (" in explanation
        assert "% chance):" in explanation
