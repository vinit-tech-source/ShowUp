"""Data access repositories and wipe_all functionality for ShowUp."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from showup.config import get_settings
from showup.domain.enums import Outcome, RiskBand, RunStatus
from showup.domain.models import Booking, Client, ColumnMapping, ScoringResult, ScoringRun
from showup.logging_setup import get_logger
from showup.storage.models import (
    AppSettingModel,
    BookingModel,
    ClientModel,
    ColumnMappingModel,
    ScoringResultModel,
    ScoringRunModel,
)

logger = get_logger(__name__)


def _to_uuid(val: str | UUID) -> UUID:
    return val if isinstance(val, UUID) else UUID(val)


def _ensure_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _ensure_utc_opt(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


# ── Model <-> Domain Conversions ──────────────────────────────────────────


def _client_to_domain(m: ClientModel) -> Client:
    return Client(
        id=_to_uuid(m.id),
        external_id=m.external_id,
        name=m.name,
        phone=m.phone,
        language=m.language,
        created_at=_ensure_utc(m.created_at),
    )


def _booking_to_domain(m: BookingModel) -> Booking:
    outcome = Outcome(m.outcome) if m.outcome else None
    return Booking(
        id=_to_uuid(m.id),
        client_id=_to_uuid(m.client_id),
        appointment_at=_ensure_utc(m.appointment_at),
        booking_created_at=_ensure_utc_opt(m.booking_created_at),
        service_type=m.service_type,
        price=m.price,
        channel=m.channel,
        deposit_paid=m.deposit_paid,
        confirmed=m.confirmed,
        outcome=outcome,
        source_file=m.source_file,
        imported_at=_ensure_utc(m.imported_at),
    )


def _scoring_result_to_domain(m: ScoringResultModel) -> ScoringResult:
    return ScoringResult(
        id=_to_uuid(m.id),
        booking_id=_to_uuid(m.booking_id),
        risk_band=RiskBand(m.risk_band),
        probability=m.probability,
        model_used=m.model_used,
        scored_at=_ensure_utc(m.scored_at),
        explanation=m.explanation,
    )


def _scoring_run_to_domain(m: ScoringRunModel) -> ScoringRun:
    metrics = json.loads(m.metrics_json) if m.metrics_json else None
    return ScoringRun(
        id=_to_uuid(m.id),
        started_at=_ensure_utc(m.started_at),
        completed_at=_ensure_utc_opt(m.completed_at),
        status=RunStatus(m.status),
        tier=m.tier,
        model_selected=m.model_selected,
        metrics_json=metrics,
        explanation=m.explanation,
        progress_pct=m.progress_pct,
        error_message=m.error_message,
    )


# ── Repositories ──────────────────────────────────────────────────────────


class ClientRepo:
    """Repository for client records."""

    @staticmethod
    def get_or_create(
        session: Session,
        external_id: str,
        name: str | None = None,
        phone: str | None = None,
        language: str | None = "en",
    ) -> Client:
        stmt = select(ClientModel).where(ClientModel.external_id == external_id)
        existing = session.scalar(stmt)
        if existing:
            # Update fields if provided and changed
            if name and not existing.name:
                existing.name = name
            if phone and not existing.phone:
                existing.phone = phone
            if language and existing.language != language:
                existing.language = language
            session.flush()
            return _client_to_domain(existing)

        client = Client(
            external_id=external_id,
            name=name,
            phone=phone,
            language=language or "en",
        )
        model = ClientModel(
            id=str(client.id),
            external_id=client.external_id,
            name=client.name,
            phone=client.phone,
            language=client.language,
            created_at=client.created_at,
        )
        session.add(model)
        session.flush()
        return client

    @staticmethod
    def get_by_id(session: Session, client_id: UUID) -> Client | None:
        model = session.get(ClientModel, str(client_id))
        return _client_to_domain(model) if model else None

    @staticmethod
    def get_by_external_id(session: Session, external_id: str) -> Client | None:
        stmt = select(ClientModel).where(ClientModel.external_id == external_id)
        model = session.scalar(stmt)
        return _client_to_domain(model) if model else None

    @staticmethod
    def list_all(session: Session) -> list[Client]:
        stmt = select(ClientModel).order_by(ClientModel.external_id)
        return [_client_to_domain(m) for m in session.scalars(stmt)]


class BookingRepo:
    """Repository for appointment booking records."""

    @staticmethod
    def add_batch(session: Session, bookings: list[Booking]) -> int:
        """Insert bookings in batch. Ignores duplicates already in DB."""
        count = 0
        for b in bookings:
            model = BookingModel(
                id=str(b.id),
                client_id=str(b.client_id),
                appointment_at=b.appointment_at,
                booking_created_at=b.booking_created_at,
                service_type=b.service_type,
                price=b.price,
                channel=b.channel,
                deposit_paid=b.deposit_paid,
                confirmed=b.confirmed,
                outcome=b.outcome.value if b.outcome else None,
                source_file=b.source_file,
                imported_at=b.imported_at,
            )
            session.add(model)
            count += 1
        session.flush()
        return count

    @staticmethod
    def get_by_id(session: Session, booking_id: UUID) -> Booking | None:
        model = session.get(BookingModel, str(booking_id))
        return _booking_to_domain(model) if model else None

    @staticmethod
    def list_all(session: Session) -> list[Booking]:
        stmt = select(BookingModel).order_by(BookingModel.appointment_at.asc())
        return [_booking_to_domain(m) for m in session.scalars(stmt)]

    @staticmethod
    def list_labeled(session: Session) -> list[Booking]:
        """Return all bookings with attended or no_show outcome, ordered chronologically."""
        stmt = (
            select(BookingModel)
            .where(BookingModel.outcome.in_([Outcome.ATTENDED.value, Outcome.NO_SHOW.value]))
            .order_by(BookingModel.appointment_at.asc())
        )
        return [_booking_to_domain(m) for m in session.scalars(stmt)]

    @staticmethod
    def list_upcoming(session: Session) -> list[Booking]:
        """Return bookings with pending outcome or future appointment, ordered chronologically."""
        now = datetime.now(UTC)
        stmt = (
            select(BookingModel)
            .where(
                (BookingModel.outcome.is_(None))
                | (BookingModel.outcome == Outcome.PENDING.value)
                | (BookingModel.appointment_at >= now)
            )
            .order_by(BookingModel.appointment_at.asc())
        )
        return [_booking_to_domain(m) for m in session.scalars(stmt)]

    @staticmethod
    def count_labeled(session: Session) -> tuple[int, int]:
        """Return (total_labeled, total_no_shows)."""
        labeled_stmt = select(func.count(BookingModel.id)).where(
            BookingModel.outcome.in_([Outcome.ATTENDED.value, Outcome.NO_SHOW.value])
        )
        no_show_stmt = select(func.count(BookingModel.id)).where(
            BookingModel.outcome == Outcome.NO_SHOW.value
        )
        total_labeled = session.scalar(labeled_stmt) or 0
        total_no_shows = session.scalar(no_show_stmt) or 0
        return total_labeled, total_no_shows

    @staticmethod
    def get_client_history_before(
        session: Session, client_id: UUID, before_dt: datetime
    ) -> list[Booking]:
        """Fetch client's prior bookings strictly before the given datetime.

        Ensures zero temporal leakage in feature calculation.
        """
        stmt = (
            select(BookingModel)
            .where(
                BookingModel.client_id == str(client_id),
                BookingModel.appointment_at < before_dt,
                BookingModel.outcome.in_([Outcome.ATTENDED.value, Outcome.NO_SHOW.value]),
            )
            .order_by(BookingModel.appointment_at.asc())
        )
        return [_booking_to_domain(m) for m in session.scalars(stmt)]


class ScoringRepo:
    """Repository for scoring results and background run metadata."""

    @staticmethod
    def save_scoring_results(session: Session, results: list[ScoringResult]) -> None:
        """Upsert scoring results for bookings."""
        for r in results:
            stmt = select(ScoringResultModel).where(
                ScoringResultModel.booking_id == str(r.booking_id)
            )
            existing = session.scalar(stmt)
            if existing:
                existing.risk_band = r.risk_band.value
                existing.probability = r.probability
                existing.model_used = r.model_used
                existing.scored_at = r.scored_at
                existing.explanation = r.explanation
            else:
                model = ScoringResultModel(
                    id=str(r.id),
                    booking_id=str(r.booking_id),
                    risk_band=r.risk_band.value,
                    probability=r.probability,
                    model_used=r.model_used,
                    scored_at=r.scored_at,
                    explanation=r.explanation,
                )
                session.add(model)
        session.flush()

    @staticmethod
    def get_results_for_bookings(
        session: Session, booking_ids: list[UUID]
    ) -> dict[UUID, ScoringResult]:
        if not booking_ids:
            return {}
        ids_str = [str(b) for b in booking_ids]
        stmt = select(ScoringResultModel).where(ScoringResultModel.booking_id.in_(ids_str))
        res_map: dict[UUID, ScoringResult] = {}
        for m in session.scalars(stmt):
            res = _scoring_result_to_domain(m)
            res_map[res.booking_id] = res
        return res_map

    @staticmethod
    def list_scored_upcoming(
        session: Session,
    ) -> list[tuple[Booking, ScoringResult | None, Client]]:
        """Return upcoming bookings with their cached scoring result and client info."""
        now = datetime.now(UTC)
        stmt = (
            select(BookingModel, ScoringResultModel, ClientModel)
            .join(ClientModel, BookingModel.client_id == ClientModel.id)
            .outerjoin(ScoringResultModel, BookingModel.id == ScoringResultModel.booking_id)
            .where(
                (BookingModel.outcome.is_(None))
                | (BookingModel.outcome == Outcome.PENDING.value)
                | (BookingModel.appointment_at >= now)
            )
            .order_by(BookingModel.appointment_at.asc())
        )
        rows = session.execute(stmt).all()
        output: list[tuple[Booking, ScoringResult | None, Client]] = []
        for b_m, s_m, c_m in rows:
            booking = _booking_to_domain(b_m)
            scoring = _scoring_result_to_domain(s_m) if s_m else None
            client = _client_to_domain(c_m)
            output.append((booking, scoring, client))
        return output

    @staticmethod
    def create_scoring_run(session: Session, run: ScoringRun) -> ScoringRun:
        model = ScoringRunModel(
            id=str(run.id),
            started_at=run.started_at,
            completed_at=run.completed_at,
            status=run.status.value,
            tier=run.tier,
            model_selected=run.model_selected,
            metrics_json=json.dumps(run.metrics_json) if run.metrics_json else None,
            explanation=run.explanation,
            progress_pct=run.progress_pct,
            error_message=run.error_message,
        )
        session.add(model)
        session.flush()
        return run

    @staticmethod
    def update_scoring_run_progress(
        session: Session, run_id: UUID, progress_pct: int, status: RunStatus | None = None
    ) -> None:
        model = session.get(ScoringRunModel, str(run_id))
        if model:
            model.progress_pct = progress_pct
            if status is not None:
                model.status = status.value
            session.flush()

    @staticmethod
    def complete_scoring_run(
        session: Session,
        run_id: UUID,
        *,
        tier: int,
        model_selected: str,
        metrics: dict[str, Any] | None,
        explanation: str,
    ) -> None:
        model = session.get(ScoringRunModel, str(run_id))
        if model:
            model.status = RunStatus.COMPLETED.value
            model.progress_pct = 100
            model.tier = tier
            model.model_selected = model_selected
            model.metrics_json = json.dumps(metrics) if metrics else None
            model.explanation = explanation
            model.completed_at = datetime.now(UTC)
            session.flush()

    @staticmethod
    def fail_scoring_run(session: Session, run_id: UUID, error_message: str) -> None:
        model = session.get(ScoringRunModel, str(run_id))
        if model:
            model.status = RunStatus.FAILED.value
            model.error_message = error_message
            model.completed_at = datetime.now(UTC)
            session.flush()

    @staticmethod
    def get_latest_scoring_run(session: Session) -> ScoringRun | None:
        stmt = select(ScoringRunModel).order_by(ScoringRunModel.started_at.desc()).limit(1)
        model = session.scalar(stmt)
        return _scoring_run_to_domain(model) if model else None


class MappingRepo:
    """Repository for saved CSV column mappings."""

    @staticmethod
    def save_mapping(session: Session, source_name: str, mapping: dict[str, str]) -> ColumnMapping:
        stmt = select(ColumnMappingModel).where(ColumnMappingModel.source_name == source_name)
        existing = session.scalar(stmt)
        mapping_str = json.dumps(mapping)
        if existing:
            existing.mapping_json = mapping_str
            session.flush()
            return ColumnMapping(
                id=_to_uuid(existing.id),
                source_name=existing.source_name,
                mapping=mapping,
                created_at=existing.created_at,
            )

        new_mapping = ColumnMapping(source_name=source_name, mapping=mapping)
        model = ColumnMappingModel(
            id=str(new_mapping.id),
            source_name=source_name,
            mapping_json=mapping_str,
            created_at=new_mapping.created_at,
        )
        session.add(model)
        session.flush()
        return new_mapping

    @staticmethod
    def get_mapping(session: Session, source_name: str) -> ColumnMapping | None:
        stmt = select(ColumnMappingModel).where(ColumnMappingModel.source_name == source_name)
        model = session.scalar(stmt)
        if not model:
            return None
        return ColumnMapping(
            id=_to_uuid(model.id),
            source_name=model.source_name,
            mapping=json.loads(model.mapping_json),
            created_at=model.created_at,
        )

    @staticmethod
    def list_mappings(session: Session) -> list[ColumnMapping]:
        stmt = select(ColumnMappingModel).order_by(ColumnMappingModel.source_name)
        return [
            ColumnMapping(
                id=_to_uuid(m.id),
                source_name=m.source_name,
                mapping=json.loads(m.mapping_json),
                created_at=m.created_at,
            )
            for m in session.scalars(stmt)
        ]


class SettingsRepo:
    """Repository for key-value application settings."""

    @staticmethod
    def get(session: Session, key: str) -> str | None:
        model = session.get(AppSettingModel, key)
        return model.value if model else None

    @staticmethod
    def set(session: Session, key: str, value: str) -> None:
        model = session.get(AppSettingModel, key)
        if model:
            model.value = value
        else:
            session.add(AppSettingModel(key=key, value=value))
        session.flush()


def wipe_all(
    data_dir: Path | str | None = None,
    session: Session | None = None,
) -> None:
    """Delete all database records, caches, and logs with complete wiping.

    Enforces local-first privacy: no trace of client data remains.
    """
    target_dir = data_dir or get_settings().data_dir
    path = Path(target_dir)
    logger.info("wiping_all_data", data_dir=str(path))

    # If active session provided, delete all records first
    if session is not None:
        session.execute(delete(ScoringResultModel))
        session.execute(delete(BookingModel))
        session.execute(delete(ClientModel))
        session.execute(delete(ScoringRunModel))
        session.execute(delete(ColumnMappingModel))
        session.execute(delete(AppSettingModel))
        session.commit()

    # Clean filesystem data, SQLite wal/shm files, and logs
    if path.exists():
        for file in path.glob("*.db*"):
            try:
                file.unlink(missing_ok=True)
            except OSError as e:
                logger.warning("could_not_delete_db_file", path=str(file), error=str(e))

        log_dir = path / "logs"
        if log_dir.exists():
            shutil.rmtree(log_dir, ignore_errors=True)
