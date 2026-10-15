"""Application configuration via environment variables with sane defaults.

All settings are read from environment variables prefixed with ``SHOWUP_``.
No configuration file is required — defaults are production-ready for a
single-machine deployment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_data_dir() -> str:
    """Return platform-appropriate default data directory."""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", str(Path.home()))
        return str(Path(base) / "ShowUp" / "data")
    return str(Path.home() / ".showup" / "data")


class ShowUpSettings(BaseSettings):
    """Central configuration for ShowUp.

    Every field maps to a ``SHOWUP_<FIELD>`` environment variable.
    """

    model_config = SettingsConfigDict(
        env_prefix="SHOWUP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Paths ──────────────────────────────────────────────────────────
    data_dir: str = Field(default_factory=_default_data_dir)

    # ── Logging ────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Ollama / LLM ──────────────────────────────────────────────────
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"
    ollama_timeout: int = Field(default=30, ge=5, le=120)

    # ── Upload limits ─────────────────────────────────────────────────
    max_upload_mb: int = Field(default=50, ge=1, le=500)

    # ── Reproducibility ──────────────────────────────────────────────
    seed: int = Field(default=42, ge=0)

    # ── Insights thresholds ──────────────────────────────────────────
    min_sample_whatif: int = Field(default=20, ge=5)

    # ── Scoring ──────────────────────────────────────────────────────
    min_labeled_for_tier2: int = Field(default=100, ge=20)
    min_no_shows_for_tier2: int = Field(default=10, ge=5)

    # ── Database ─────────────────────────────────────────────────────
    db_name: str = "showup.db"

    @field_validator("data_dir")
    @classmethod
    def _ensure_data_dir_absolute(cls, v: str) -> str:
        """Resolve ``~`` and make path absolute."""
        return str(Path(v).expanduser().resolve())

    @property
    def db_url(self) -> str:
        """SQLite connection URL for SQLAlchemy."""
        db_path = Path(self.data_dir) / self.db_name
        return f"sqlite:///{db_path}"

    @property
    def db_path(self) -> Path:
        """Absolute path to the SQLite database file."""
        return Path(self.data_dir) / self.db_name

    @property
    def log_dir(self) -> Path:
        """Directory for log files."""
        return Path(self.data_dir) / "logs"

    @property
    def max_upload_bytes(self) -> int:
        """Upload limit in bytes."""
        return self.max_upload_mb * 1024 * 1024

    def ensure_dirs(self) -> None:
        """Create data and log directories if they don't exist."""
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)


def get_settings(**overrides: object) -> ShowUpSettings:
    """Factory that returns a settings instance, accepting test overrides."""
    return ShowUpSettings(**overrides)  # type: ignore[arg-type]
