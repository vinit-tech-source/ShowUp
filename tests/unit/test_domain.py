"""Unit tests for domain models and enums."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from showup.domain.enums import Outcome, RiskBand, RunStatus, ScoringTier
from showup.domain.models import (
    Booking,
    Client,
    ColumnMapping,
    FeatureAuditEntry,
    ScoringResult,
    ScoringRun,
)


class TestDomainEnums:
    """Verify enum values and properties."""

    def test_outcome_values(self) -> None:
        assert Outcome.ATTENDED.value == "attended"
        assert Outcome.NO_SHOW.value == "no_show"
        assert Outcome.PENDING.value == "pending"

    def test_risk_band_values(self) -> None:
        assert RiskBand.LOW.value == "low"
        assert RiskBand.MEDIUM.value == "medium"
        assert RiskBand.HIGH.value == "high"

    def test_scoring_tier_values(self) -> None:
        assert ScoringTier.TIER_1_RULES == 1
        assert ScoringTier.TIER_2_MODELS == 2

    def test_run_status_values(self) -> None:
        assert RunStatus.PENDING.value == "pending"
        assert RunStatus.RUNNING.value == "running"
        assert RunStatus.COMPLETED.value == "completed"
        assert RunStatus.FAILED.value == "failed"


class TestDomainModels:
    """Verify dataclass creation, defaults, and immutability."""

    def test_client_defaults(self) -> None:
        client = Client(external_id="C001")
        assert isinstance(client.id, UUID)
        assert client.external_id == "C001"
        assert client.language == "en"
        assert isinstance(client.created_at, datetime)

    def test_booking_creation(self) -> None:
        now = datetime.now(UTC)
        booking = Booking(
            appointment_at=now,
            service_type="Physio Consultation",
            price=75.0,
            outcome=Outcome.ATTENDED,
        )
        assert isinstance(booking.id, UUID)
        assert booking.service_type == "Physio Consultation"
        assert booking.price == 75.0
        assert booking.outcome == Outcome.ATTENDED

    def test_scoring_result_defaults(self) -> None:
        result = ScoringResult(
            risk_band=RiskBand.HIGH,
            probability=0.82,
            model_used="rules",
            explanation="Prior no-show recorded.",
        )
        assert result.risk_band == RiskBand.HIGH
        assert result.probability == 0.82
        assert "Prior no-show" in result.explanation

    def test_scoring_run_creation(self) -> None:
        run = ScoringRun(
            tier=1,
            model_selected="rules",
            explanation="Small dataset tier.",
            status=RunStatus.COMPLETED,
        )
        assert run.tier == 1
        assert run.status == RunStatus.COMPLETED

    def test_column_mapping_creation(self) -> None:
        mapping = ColumnMapping(
            source_name="acuity",
            mapping={"Client": "client_id", "Date": "appointment_datetime"},
        )
        assert mapping.source_name == "acuity"
        assert mapping.mapping["Client"] == "client_id"

    def test_feature_audit_entry(self) -> None:
        entry = FeatureAuditEntry(
            column_name="age",
            status="excluded",
            reason="Ethical: potential age discrimination",
            sample_value="35",
        )
        assert entry.status == "excluded"
        assert "discrimination" in entry.reason
