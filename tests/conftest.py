"""Shared test fixtures for ShowUp."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from showup.config import ShowUpSettings


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from reading the real .env or env vars."""
    # Clear any SHOWUP_ env vars that might leak into tests
    for key in list(os.environ.keys()):
        if key.startswith("SHOWUP_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture()
def tmp_data_dir(tmp_path: Path) -> Path:
    """Return a temporary data directory for test isolation."""
    data_dir = tmp_path / "showup_test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture()
def test_settings(tmp_data_dir: Path) -> ShowUpSettings:
    """Return a ShowUpSettings pointing at a temp directory."""
    return ShowUpSettings(
        data_dir=str(tmp_data_dir),
        log_level="DEBUG",
        seed=42,
    )


@pytest.fixture()
def db_path(test_settings: ShowUpSettings) -> Path:
    """Return the path where the test DB would live."""
    return test_settings.db_path


@pytest.fixture()
def fixtures_dir() -> Path:
    """Return the path to the test fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _disable_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable all known telemetry env vars during tests."""
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")
    monkeypatch.setenv("DO_NOT_TRACK", "1")
    monkeypatch.setenv("HF_HUB_DISABLE_TELEMETRY", "1")
