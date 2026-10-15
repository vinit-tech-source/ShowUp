"""Unit and integration tests for background scoring worker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from showup.domain.enums import Outcome, RiskBand, RunStatus
from showup.domain.models import Booking, ScoringRun
from showup.jobs.worker import (
    execute_scoring_job,
    get_scored_upcoming_ranked,
    is_scoring_in_progress,
)
from showup.storage.models import Base
from showup.storage.repositories import BookingRepo, ClientRepo, ScoringRepo


@pytest.fixture
def memory_session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_execute_scoring_job_empty_upcoming(
    memory_session_factory: sessionmaker[Session],
) -> None:
    run = execute_scoring_job(session_factory=memory_session_factory)
    assert run.status == RunStatus.COMPLETED
    assert run.progress_pct == 100
    assert "No upcoming bookings found" in run.explanation


def test_execute_scoring_job_tier1_rules(
    memory_session_factory: sessionmaker[Session],
) -> None:
    now = datetime.now(UTC)
    with memory_session_factory() as session:
        client = ClientRepo.get_or_create(
            session, external_id="client_1", name="Alice", phone="+1234567890"
        )

        # 1 past no-show
        past_booking = Booking(
            client_id=client.id,
            appointment_at=now - timedelta(days=2),
            booking_created_at=now - timedelta(days=4),
            service_type="Consult",
            price=50.0,
            outcome=Outcome.NO_SHOW,
        )

        # 1 upcoming booking
        upcoming = Booking(
            client_id=client.id,
            appointment_at=now + timedelta(days=1),
            booking_created_at=now - timedelta(hours=2),
            service_type="Consult",
            price=50.0,
            outcome=Outcome.PENDING,
        )
        BookingRepo.add_batch(session, [past_booking, upcoming])
        session.commit()

    run = execute_scoring_job(session_factory=memory_session_factory)
    assert run.status == RunStatus.COMPLETED
    assert run.tier == 1
    assert run.model_selected == "rules"

    with memory_session_factory() as session:
        upcoming_ranked = get_scored_upcoming_ranked(session)
        assert len(upcoming_ranked) == 1
        b, result, c = upcoming_ranked[0]
        assert b.id == upcoming.id
        assert result is not None
        assert result.risk_band == RiskBand.HIGH  # prior no show
        assert c.name == "Alice"


def test_is_scoring_in_progress(memory_session_factory: sessionmaker[Session]) -> None:
    with memory_session_factory() as session:
        assert is_scoring_in_progress(session) is False

        # Add a running run
        active_run = ScoringRun(
            id=uuid4(),
            started_at=datetime.now(UTC),
            status=RunStatus.RUNNING,
            tier=1,
            model_selected="pending",
            progress_pct=25,
        )
        ScoringRepo.create_scoring_run(session, active_run)
        session.commit()

        assert is_scoring_in_progress(session) is True
