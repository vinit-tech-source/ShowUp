"""Tests for showup.config."""

from __future__ import annotations

from pathlib import Path

import pytest

from showup.config import ShowUpSettings, get_settings


class TestShowUpSettingsDefaults:
    """Verify sane defaults without any env vars set."""

    def test_default_log_level(self, test_settings: ShowUpSettings) -> None:
        # test_settings overrides to DEBUG, so test the factory default
        settings = ShowUpSettings(data_dir=str(test_settings.data_dir))
        assert settings.log_level == "INFO"

    def test_default_ollama_url(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.ollama_url == "http://localhost:11434"

    def test_default_ollama_model(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.ollama_model == "gemma3:4b"

    def test_default_ollama_timeout(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.ollama_timeout == 30

    def test_default_max_upload_mb(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.max_upload_mb == 50

    def test_default_seed(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.seed == 42

    def test_default_min_sample_whatif(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.min_sample_whatif == 20

    def test_default_min_labeled_for_tier2(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.min_labeled_for_tier2 == 100

    def test_default_min_no_shows_for_tier2(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.min_no_shows_for_tier2 == 10

    def test_default_db_name(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.db_name == "showup.db"


class TestShowUpSettingsEnvOverrides:
    """Verify that environment variables override defaults."""

    def test_env_override_log_level(
        self, monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path
    ) -> None:
        monkeypatch.setenv("SHOWUP_LOG_LEVEL", "DEBUG")
        settings = ShowUpSettings(data_dir=str(tmp_data_dir))
        assert settings.log_level == "DEBUG"

    def test_env_override_ollama_url(
        self, monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path
    ) -> None:
        monkeypatch.setenv("SHOWUP_OLLAMA_URL", "http://localhost:9999")
        settings = ShowUpSettings(data_dir=str(tmp_data_dir))
        assert settings.ollama_url == "http://localhost:9999"

    def test_env_override_seed(self, monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path) -> None:
        monkeypatch.setenv("SHOWUP_SEED", "123")
        settings = ShowUpSettings(data_dir=str(tmp_data_dir))
        assert settings.seed == 123

    def test_env_override_max_upload_mb(
        self, monkeypatch: pytest.MonkeyPatch, tmp_data_dir: Path
    ) -> None:
        monkeypatch.setenv("SHOWUP_MAX_UPLOAD_MB", "100")
        settings = ShowUpSettings(data_dir=str(tmp_data_dir))
        assert settings.max_upload_mb == 100


class TestShowUpSettingsProperties:
    """Verify computed properties."""

    def test_db_url(self, test_settings: ShowUpSettings) -> None:
        url = test_settings.db_url
        assert url.startswith("sqlite:///")
        assert "showup.db" in url

    def test_db_path(self, test_settings: ShowUpSettings) -> None:
        db_path = test_settings.db_path
        assert db_path.name == "showup.db"
        assert str(test_settings.data_dir) in str(db_path)

    def test_log_dir(self, test_settings: ShowUpSettings) -> None:
        log_dir = test_settings.log_dir
        assert log_dir.name == "logs"
        assert str(test_settings.data_dir) in str(log_dir)

    def test_max_upload_bytes(self, test_settings: ShowUpSettings) -> None:
        assert test_settings.max_upload_bytes == 50 * 1024 * 1024

    def test_ensure_dirs_creates_directories(self, test_settings: ShowUpSettings) -> None:
        test_settings.ensure_dirs()
        assert Path(test_settings.data_dir).is_dir()
        assert test_settings.log_dir.is_dir()


class TestShowUpSettingsValidation:
    """Verify validation constraints."""

    def test_invalid_log_level_rejected(self, tmp_data_dir: Path) -> None:
        with pytest.raises(Exception):  # noqa: B017
            ShowUpSettings(data_dir=str(tmp_data_dir), log_level="INVALID")  # type: ignore[arg-type]

    def test_negative_seed_rejected(self, tmp_data_dir: Path) -> None:
        with pytest.raises(Exception):  # noqa: B017
            ShowUpSettings(data_dir=str(tmp_data_dir), seed=-1)

    def test_timeout_too_low_rejected(self, tmp_data_dir: Path) -> None:
        with pytest.raises(Exception):  # noqa: B017
            ShowUpSettings(data_dir=str(tmp_data_dir), ollama_timeout=1)

    def test_timeout_too_high_rejected(self, tmp_data_dir: Path) -> None:
        with pytest.raises(Exception):  # noqa: B017
            ShowUpSettings(data_dir=str(tmp_data_dir), ollama_timeout=999)

    def test_data_dir_tilde_expanded(self, tmp_path: Path) -> None:
        settings = ShowUpSettings(data_dir="~/showup_test_expand")
        assert "~" not in settings.data_dir
        assert Path(settings.data_dir).is_absolute()


class TestGetSettings:
    """Verify the factory function."""

    def test_get_settings_returns_instance(self, tmp_data_dir: Path) -> None:
        settings = get_settings(data_dir=str(tmp_data_dir))
        assert isinstance(settings, ShowUpSettings)
        assert str(tmp_data_dir) in settings.data_dir

    def test_get_settings_accepts_overrides(self, tmp_data_dir: Path) -> None:
        settings = get_settings(data_dir=str(tmp_data_dir), seed=99)
        assert settings.seed == 99
