"""Pure domain models (dataclasses) for ShowUp.

Free of ORM or external persistence dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from showup.domain.enums import Outcome, RiskBand, RunStatus


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


@dataclass(frozen=True)
class Client:
    """Client record."""

    id: UUID = field(default_factory=uuid4)
    external_id: str = ""
    name: str | None = None
    phone: str | None = None
    language: str | None = "en"
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class Booking:
    """Appointment booking record."""

    id: UUID = field(default_factory=uuid4)
    client_id: UUID = field(default_factory=uuid4)
    appointment_at: datetime = field(default_factory=_utc_now)
    booking_created_at: datetime | None = None
    service_type: str | None = None
    price: float | None = None
    channel: str | None = None
    deposit_paid: bool | None = None
    confirmed: bool | None = None
    outcome: Outcome | None = None
    source_file: str | None = None
    imported_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class ScoringResult:
    """Predicted risk result for a single booking."""

    id: UUID = field(default_factory=uuid4)
    booking_id: UUID = field(default_factory=uuid4)
    risk_band: RiskBand = RiskBand.LOW
    probability: float = 0.0
    model_used: str = ""
    scored_at: datetime = field(default_factory=_utc_now)
    explanation: str = ""


@dataclass(frozen=True)
class ScoringRun:
    """Record of a background scoring evaluation and batch scoring execution."""

    id: UUID = field(default_factory=uuid4)
    started_at: datetime = field(default_factory=_utc_now)
    completed_at: datetime | None = None
    status: RunStatus = RunStatus.PENDING
    tier: int = 1
    model_selected: str = ""
    metrics_json: dict[str, Any] | None = None
    explanation: str = ""
    progress_pct: int = 0
    error_message: str | None = None


@dataclass(frozen=True)
class ColumnMapping:
    """Saved column mapping configuration for CSV imports."""

    id: UUID = field(default_factory=uuid4)
    source_name: str = ""
    mapping: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class FeatureAuditEntry:
    """Audit report item for a data column."""

    column_name: str
    status: Literal["used", "excluded"]
    reason: str
    sample_value: str | None = None
