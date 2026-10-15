"""Logistic Regression baseline classifier with calibrated probabilities and explainability."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from showup.domain.enums import RiskBand
from showup.features.allowlist import enforce_allowlist

NUMERIC_FEATURES = [
    "lead_time_hours",
    "day_of_week",
    "hour_of_day",
    "prior_visits",
    "prior_no_shows",
    "prior_no_show_rate",
    "is_new_client",
    "days_since_last_visit",
    "price",
    "deposit_paid",
    "confirmation_received",
]

CATEGORICAL_FEATURES = [
    "lead_time_bucket",
    "booking_channel",
    "service_type",
]


class LogisticBaseline:
    """Scikit-learn logistic regression model trained on allowlisted behavioral features."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.is_fitted = False

        numeric_transformer = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ]
        )

        categorical_transformer = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
                ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, NUMERIC_FEATURES),
                ("cat", categorical_transformer, CATEGORICAL_FEATURES),
            ],
            remainder="drop",
        )

        self.pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=self.random_state,
                        solver="lbfgs",
                    ),
                ),
            ]
        )

    def fit(self, X: pd.DataFrame, y: np.ndarray | list[int]) -> LogisticBaseline:
        """Fit the pipeline on allowlisted features."""
        clean_X = enforce_allowlist(X)
        y_arr = np.asarray(y, dtype=int)
        self.pipeline.fit(clean_X, y_arr)
        self.is_fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Predict no-show probabilities (class 1). Returns 1D array of floats."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict_proba.")
        clean_X = enforce_allowlist(X)
        proba_2d = self.pipeline.predict_proba(clean_X)
        # Handle case where training data only had a single class
        if proba_2d.shape[1] == 1:
            return np.zeros(len(clean_X), dtype=float)
        return np.asarray(proba_2d[:, 1], dtype=float)

    @staticmethod
    def classify_risk_band(proba: float) -> RiskBand:
        """Map a calibrated probability to a human-readable risk band."""
        if proba >= 0.55:
            return RiskBand.HIGH
        if proba >= 0.25:
            return RiskBand.MEDIUM
        return RiskBand.LOW

    def explain_prediction(self, row: dict[str, Any] | pd.Series, proba: float) -> str:
        """Generate a transparent explanation for a booking's risk score."""
        band = self.classify_risk_band(proba)
        reasons: list[str] = []

        prior_ns = int(row.get("prior_no_shows", 0))
        is_new = int(row.get("is_new_client", 1))
        lead_time = float(row.get("lead_time_hours", 48.0))
        has_deposit = int(row.get("deposit_paid", 0))
        confirmed = int(row.get("confirmation_received", 0))

        if prior_ns > 0:
            reasons.append(f"{prior_ns} past no-show(s)")
        if is_new == 1:
            reasons.append("first-time booking")
        if lead_time < 24.0:
            reasons.append("same-day appointment")
        elif lead_time > 168.0:
            reasons.append(f"booked far in advance ({lead_time / 24.0:.0f} days)")

        if has_deposit == 1:
            reasons.append("deposit paid (protective)")
        if confirmed == 1:
            reasons.append("confirmed by client (protective)")

        if not reasons:
            reasons.append("standard booking timeline and attendance pattern")

        detail = ", ".join(reasons)
        return (
            f"{band.value.capitalize()} risk ({proba * 100:.0f}% chance): influenced by {detail}."
        )
