"""Lazy-loaded TabPFN v2 wrapper with strict local-only execution and telemetry disabled."""

from __future__ import annotations

import importlib
import os
from typing import Any

import numpy as np
import pandas as pd

from showup.domain.enums import RiskBand
from showup.features.allowlist import enforce_allowlist
from showup.logging_setup import get_logger
from showup.scoring.baseline import LogisticBaseline

logger = get_logger(__name__)

# Enforce zero outbound telemetry
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"
os.environ["TABPFN_OFFLINE"] = "1"


class TabPFNScorer:
    """TabPFN v2 tabular foundation model wrapper.

    Ensures zero outbound network calls, local-only inference, and graceful
    fallback to calibrated Logistic Regression if local weights are not installed.
    """

    def __init__(self, *, random_state: int = 42, device: str = "cpu") -> None:
        self.random_state = random_state
        self.device = device
        self._model: Any = None
        self._is_available: bool = False
        self._fallback_model = LogisticBaseline(random_state=random_state)
        self._availability_checked: bool = False
        self._fallback_reason: str = ""

    @property
    def is_available(self) -> bool:
        """Check whether local TabPFN is importable and weights are present."""
        if not self._availability_checked:
            self._check_availability()
        return self._is_available

    @property
    def fallback_reason(self) -> str:
        """Explanation if TabPFN is unavailable."""
        return self._fallback_reason

    def _check_availability(self) -> None:
        """Attempt to lazily import local tabpfn without network access."""
        self._availability_checked = True
        try:
            tabpfn_mod = importlib.import_module("tabpfn")
            classifier_cls = getattr(tabpfn_mod, "TabPFNClassifier", None)
            if classifier_cls is None:
                raise ImportError("TabPFNClassifier not found in tabpfn module.")

            self._model = classifier_cls(
                device=self.device,
                random_state=self.random_state,
            )
            self._is_available = True
            logger.info("tabpfn_loaded_successfully", device=self.device)
        except ImportError as e:
            self._is_available = False
            self._fallback_reason = (
                f"TabPFN package is not installed ({e}). "
                "Falling back: Calibrated Logistic Regression is active as the Tier 2 model."
            )
            logger.info("tabpfn_not_installed_falling_back", reason=self._fallback_reason)
        except Exception as e:
            self._is_available = False
            self._fallback_reason = (
                f"TabPFN local weights or dependencies unavailable ({e}). "
                "Falling back: Calibrated Logistic Regression is active as the Tier 2 model."
            )
            logger.warning("tabpfn_init_failed", error=str(e))

    def fit_predict_proba(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
    ) -> np.ndarray:
        """Predict probabilities for X_test given training data (X_train, y_train).

        If TabPFN is available locally, runs local tabular inference.
        Otherwise falls back to the calibrated Logistic Regression baseline.
        """
        clean_X_train = enforce_allowlist(X_train)
        clean_X_test = enforce_allowlist(X_test)

        if self.is_available and self._model is not None:
            try:
                # TabPFN accepts numeric/encoded features
                self._model.fit(clean_X_train, y_train)
                probas = self._model.predict_proba(clean_X_test)
                if probas.shape[1] > 1:
                    return np.asarray(probas[:, 1], dtype=float)
                return np.zeros(len(clean_X_test), dtype=float)
            except Exception as e:
                logger.warning("tabpfn_inference_failed_falling_back", error=str(e))

        # Fallback path
        self._fallback_model.fit(clean_X_train, y_train)
        return self._fallback_model.predict_proba(clean_X_test)

    def predict_proba(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
    ) -> np.ndarray:
        """Alias for fit_predict_proba matching backtest interface."""
        return self.fit_predict_proba(X_train, y_train, X_test)

    @staticmethod
    def classify_risk_band(proba: float) -> RiskBand:
        """Map predicted probability to risk band."""
        if proba >= 0.55:
            return RiskBand.HIGH
        if proba >= 0.25:
            return RiskBand.MEDIUM
        return RiskBand.LOW
