"""Tests for TabPFN scorer: fallback behavior, offline execution, and probability bounds."""

from __future__ import annotations

import socket

import numpy as np
import pandas as pd
import pytest

from showup.domain.enums import RiskBand
from showup.scoring.tabpfn_scorer import TabPFNScorer


@pytest.fixture
def mock_dataset() -> tuple[pd.DataFrame, np.ndarray, pd.DataFrame]:
    """Small synthetic dataset for scorer testing."""
    rng = np.random.default_rng(42)
    n_train = 40
    n_test = 10

    def make_df(n: int) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "lead_time_hours": rng.uniform(10, 100, n),
                "lead_time_bucket": rng.choice(["0_to_24h", "24_to_72h"], n),
                "day_of_week": rng.integers(0, 7, n),
                "hour_of_day": rng.integers(9, 18, n),
                "prior_visits": rng.integers(0, 5, n),
                "prior_no_shows": rng.integers(0, 2, n),
                "prior_no_show_rate": rng.uniform(0, 0.4, n),
                "is_new_client": rng.choice([0, 1], n),
                "days_since_last_visit": rng.uniform(10, 60, n),
                "booking_channel": rng.choice(["online", "phone"], n),
                "service_type": rng.choice(["standard", "followup"], n),
                "price": rng.uniform(40, 100, n),
                "deposit_paid": rng.choice([0, 1], n),
                "confirmation_received": rng.choice([0, 1], n),
            }
        )

    X_train = make_df(n_train)
    y_train = rng.choice([0, 1], n_train, p=[0.75, 0.25])
    X_test = make_df(n_test)
    return X_train, y_train, X_test


class TestTabPFNScorer:
    """Verify local execution, fallback, and zero outbound network calls."""

    def test_availability_and_fallback_reason(self) -> None:
        scorer = TabPFNScorer()
        # If tabpfn is not installed in the test environment, is_available must be False
        # and a helpful fallback reason must be documented
        if not scorer.is_available:
            assert "falling back" in scorer.fallback_reason.lower()

    def test_fit_predict_proba_bounds(
        self, mock_dataset: tuple[pd.DataFrame, np.ndarray, pd.DataFrame]
    ) -> None:
        X_train, y_train, X_test = mock_dataset
        scorer = TabPFNScorer(random_state=42)
        probas = scorer.fit_predict_proba(X_train, y_train, X_test)

        assert len(probas) == len(X_test)
        assert np.all(probas >= 0.0)
        assert np.all(probas <= 1.0)

    def test_classify_risk_band(self) -> None:
        assert TabPFNScorer.classify_risk_band(0.15) == RiskBand.LOW
        assert TabPFNScorer.classify_risk_band(0.35) == RiskBand.MEDIUM
        assert TabPFNScorer.classify_risk_band(0.65) == RiskBand.HIGH

    def test_zero_network_calls_during_scoring(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_dataset: tuple[pd.DataFrame, np.ndarray, pd.DataFrame],
    ) -> None:
        """Enforce hard constraint: zero outbound network connections during inference."""
        X_train, y_train, X_test = mock_dataset

        def forbidden_connect(*args: object, **kwargs: object) -> None:
            raise RuntimeError("Non-localhost outbound network call attempted!")

        # Monkeypatch socket.socket.connect to fail on any external call
        original_connect = socket.socket.connect

        def guarded_connect(self: socket.socket, address: tuple[str, int] | str) -> None:
            if isinstance(address, tuple):
                host, _port = address
                if host not in ("127.0.0.1", "localhost", "::1"):
                    raise RuntimeError(f"Forbidden outbound connection to {host}")
            original_connect(self, address)  # type: ignore[arg-type]

        monkeypatch.setattr(socket.socket, "connect", guarded_connect)

        scorer = TabPFNScorer()
        probas = scorer.fit_predict_proba(X_train, y_train, X_test)
        assert len(probas) == len(X_test)
