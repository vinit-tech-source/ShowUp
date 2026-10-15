"""SQLAlchemy 2 declarative models for ShowUp database schema."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""


class ClientModel(Base):
    """Clients table."""

    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True, default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    bookings: Mapped[list[BookingModel]] = relationship(
        "BookingModel", back_populates="client", cascade="all, delete-orphan"
    )


class BookingModel(Base):
    """Bookings table."""

    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    booking_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    service_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    deposit_paid: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )

    client: Mapped[ClientModel] = relationship("ClientModel", back_populates="bookings")
    scoring_result: Mapped[ScoringResultModel | None] = relationship(
        "ScoringResultModel", back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )


class ScoringResultModel(Base):
    """Cached risk scoring results per booking."""

    __tablename__ = "scoring_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    booking_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    risk_band: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(50), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    booking: Mapped[BookingModel] = relationship("BookingModel", back_populates="scoring_result")


class ScoringRunModel(Base):
    """Log of background scoring evaluation runs."""

    __tablename__ = "scoring_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    model_selected: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")
    progress_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ColumnMappingModel(Base):
    """Saved column mappings for CSV sources."""

    __tablename__ = "column_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utc_now
    )


class AppSettingModel(Base):
    """Application settings key-value store."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
