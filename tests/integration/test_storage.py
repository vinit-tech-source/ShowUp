"""Integration tests for database, repositories, and wipe_all."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from showup.domain.enums import Outcome, RiskBand, RunStatus
from showup.domain.models import Booking, ScoringResult, ScoringRun
from showup.storage.database import (
    create_db_engine,
    get_session,
    get_session_factory,
    init_db,
    set_db_file_permissions,
)
from showup.storage.models import Base
from showup.storage.repositories import (
    BookingRepo,
    ClientRepo,
    MappingRepo,
    ScoringRepo,
    SettingsRepo,
    wipe_all,
)


@pytest.fixture
def in_memory_session() -> Session:
    """Provide an in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


class TestClientRepo:
    """Verify Client repository CRUD operations."""

    def test_get_or_create_new(self, in_memory_session: Session) -> None:
        client = ClientRepo.get_or_create(
            in_memory_session, external_id="C100", name="Alice Smith", phone="+1234567890"
        )
        assert client.external_id == "C100"
        assert client.name == "Alice Smith"

        # Fetch existing
        fetched = ClientRepo.get_by_id(in_memory_session, client.id)
        assert fetched is not None
        assert fetched.external_id == "C100"

    def test_get_or_create_updates_existing(self, in_memory_session: Session) -> None:
        client1 = ClientRepo.get_or_create(in_memory_session, external_id="C101")
        assert client1.name is None

        client2 = ClientRepo.get_or_create(in_memory_session, external_id="C101", name="Bob Jones")
        assert client2.id == client1.id
        assert client2.name == "Bob Jones"


class TestBookingRepo:
    """Verify Booking repository CRUD, queries, and leakage prevention filter."""

    def test_add_and_list_bookings(self, in_memory_session: Session) -> None:
        client = ClientRepo.get_or_create(in_memory_session, external_id="C200")
        now = datetime.now(UTC)

        b1 = Booking(
            client_id=client.id,
            appointment_at=now - timedelta(days=7),
            outcome=Outcome.ATTENDED,
            price=50.0,
        )
        b2 = Booking(
            client_id=client.id,
            appointment_at=now - timedelta(days=2),
            outcome=Outcome.NO_SHOW,
            price=60.0,
        )
        b3 = Booking(
            client_id=client.id,
            appointment_at=now + timedelta(days=5),
            outcome=Outcome.PENDING,
            price=50.0,
        )

        count = BookingRepo.add_batch(in_memory_session, [b1, b2, b3])
        assert count == 3

        labeled = BookingRepo.list_labeled(in_memory_session)
        assert len(labeled) == 2

        upcoming = BookingRepo.list_upcoming(in_memory_session)
        assert len(upcoming) == 1
        assert upcoming[0].id == b3.id

        total_labeled, total_no_shows = BookingRepo.count_labeled(in_memory_session)
        assert total_labeled == 2
        assert total_no_shows == 1

    def test_get_client_history_before_prevents_leakage(self, in_memory_session: Session) -> None:
        """Verify that history query returns ONLY bookings strictly before appointment_at."""
        client = ClientRepo.get_or_create(in_memory_session, external_id="C300")
        t0 = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
        t1 = datetime(2026, 2, 1, 10, 0, tzinfo=UTC)
        t2 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)

        b0 = Booking(client_id=client.id, appointment_at=t0, outcome=Outcome.ATTENDED)
        b1 = Booking(client_id=client.id, appointment_at=t1, outcome=Outcome.NO_SHOW)
        b2 = Booking(client_id=client.id, appointment_at=t2, outcome=Outcome.ATTENDED)
        BookingRepo.add_batch(in_memory_session, [b0, b1, b2])

        # Query history before t1: should only have b0 (not b1, not b2)
        history_before_t1 = BookingRepo.get_client_history_before(
            in_memory_session, client.id, before_dt=t1
        )
        assert len(history_before_t1) == 1
        assert history_before_t1[0].appointment_at == t0

        # Query history before t2: should have b0 and b1
        history_before_t2 = BookingRepo.get_client_history_before(
            in_memory_session, client.id, before_dt=t2
        )
        assert len(history_before_t2) == 2


class TestScoringRepo:
    """Verify ScoringResult and ScoringRun repository operations."""

    def test_save_and_retrieve_scoring_results(self, in_memory_session: Session) -> None:
        client = ClientRepo.get_or_create(in_memory_session, external_id="C400")
        booking = Booking(
            client_id=client.id,
            appointment_at=datetime.now(UTC) + timedelta(days=3),
            outcome=Outcome.PENDING,
        )
        BookingRepo.add_batch(in_memory_session, [booking])

        result = ScoringResult(
            booking_id=booking.id,
            risk_band=RiskBand.HIGH,
            probability=0.78,
            model_used="tabpfn",
            explanation="Multiple risk factors identified.",
        )
        ScoringRepo.save_scoring_results(in_memory_session, [result])

        fetched = ScoringRepo.get_results_for_bookings(in_memory_session, [booking.id])
        assert booking.id in fetched
        assert fetched[booking.id].risk_band == RiskBand.HIGH
        assert fetched[booking.id].probability == 0.78

    def test_scoring_run_lifecycle(self, in_memory_session: Session) -> None:
        run = ScoringRun(
            tier=2,
            model_selected="logistic",
            explanation="Logistic regression selected as simpler baseline.",
        )
        ScoringRepo.create_scoring_run(in_memory_session, run)
        ScoringRepo.update_scoring_run_progress(in_memory_session, run.id, 50, RunStatus.RUNNING)

        ScoringRepo.complete_scoring_run(
            in_memory_session,
            run_id=run.id,
            tier=2,
            model_selected="logistic",
            metrics={"roc_auc": 0.82, "brier": 0.12},
            explanation="Completed with good calibration.",
        )

        latest = ScoringRepo.get_latest_scoring_run(in_memory_session)
        assert latest is not None
        assert latest.id == run.id
        assert latest.status == RunStatus.COMPLETED
        assert latest.metrics_json is not None
        assert latest.metrics_json["roc_auc"] == 0.82


class TestMappingAndSettingsRepos:
    """Verify mapping and settings repos."""

    def test_save_and_get_mapping(self, in_memory_session: Session) -> None:
        m = MappingRepo.save_mapping(
            in_memory_session,
            source_name="acuity",
            mapping={"Email": "client_id", "Start time": "appointment_datetime"},
        )
        assert m.source_name == "acuity"

        retrieved = MappingRepo.get_mapping(in_memory_session, "acuity")
        assert retrieved is not None
        assert retrieved.mapping["Email"] == "client_id"

    def test_settings_get_set(self, in_memory_session: Session) -> None:
        assert SettingsRepo.get(in_memory_session, "theme") is None
        SettingsRepo.set(in_memory_session, "theme", "dark")
        assert SettingsRepo.get(in_memory_session, "theme") == "dark"


class TestDatabaseAndWipeAll:
    """Verify database initialization, file permissions, and wipe_all."""

    def test_init_db_and_permissions(self, tmp_path: Path) -> None:
        db_file = tmp_path / "test_perm.db"
        engine = create_db_engine(f"sqlite:///{db_file}")
        init_db(engine, db_file)
        assert db_file.exists()
        set_db_file_permissions(db_file)

    def test_wipe_all_removes_data(self, tmp_path: Path) -> None:
        db_file = tmp_path / "wipe_test.db"
        log_dir = tmp_path / "logs"
        log_dir.mkdir(parents=True)
        (log_dir / "app.log").write_text("log data")

        engine = create_db_engine(f"sqlite:///{db_file}")
        init_db(engine, db_file)
        factory = get_session_factory(engine)

        with get_session(factory) as s:
            ClientRepo.get_or_create(s, external_id="WIPE_CLIENT")

        wipe_all(tmp_path)
        assert not (log_dir / "app.log").exists()
