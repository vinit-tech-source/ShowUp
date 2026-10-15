"""Domain enumerations for ShowUp."""

from __future__ import annotations

from enum import Enum, StrEnum


class Outcome(StrEnum):
    """Booking outcome."""

    ATTENDED = "attended"
    NO_SHOW = "no_show"
    PENDING = "pending"


class RiskBand(StrEnum):
    """Risk band for no-show likelihood."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Intervention(StrEnum):
    """Intervention type for what-if and action tracking."""

    DEPOSIT = "deposit"
    CONFIRMATION = "confirmation"
    REMINDER_MESSAGE = "reminder_message"


class ScoringTier(int, Enum):
    """Scoring tier based on dataset size."""

    TIER_1_RULES = 1
    TIER_2_MODELS = 2


class RunStatus(StrEnum):
    """Status of a background scoring run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
