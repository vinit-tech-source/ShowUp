"""Initial schema for ShowUp.

Revision ID: 001_initial
Revises:
Create Date: 2026-10-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── clients ────────────────────────────────────────────────────────
    op.create_table(
        "clients",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clients_external_id", "clients", ["external_id"])

    # ── bookings ───────────────────────────────────────────────────────
    op.create_table(
        "bookings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "client_id",
            sa.String(length=36),
            sa.ForeignKey("clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("booking_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("service_type", sa.String(length=100), nullable=True),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("channel", sa.String(length=50), nullable=True),
        sa.Column("deposit_paid", sa.Boolean(), nullable=True),
        sa.Column("confirmed", sa.Boolean(), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=True),
        sa.Column("source_file", sa.String(length=255), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bookings_client_id", "bookings", ["client_id"])
    op.create_index("ix_bookings_appointment_at", "bookings", ["appointment_at"])
    op.create_index("ix_bookings_outcome", "bookings", ["outcome"])

    # ── scoring_results ────────────────────────────────────────────────
    op.create_table(
        "scoring_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "booking_id",
            sa.String(length=36),
            sa.ForeignKey("bookings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("risk_band", sa.String(length=20), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("model_used", sa.String(length=50), nullable=False),
        sa.Column("scored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_scoring_results_booking_id", "scoring_results", ["booking_id"])
    op.create_index("ix_scoring_results_risk_band", "scoring_results", ["risk_band"])

    # ── scoring_runs ───────────────────────────────────────────────────
    op.create_table(
        "scoring_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("tier", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("model_selected", sa.String(length=50), nullable=False, server_default=""),
        sa.Column("metrics_json", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # ── column_mappings ────────────────────────────────────────────────
    op.create_table(
        "column_mappings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("mapping_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── app_settings ───────────────────────────────────────────────────
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("column_mappings")
    op.drop_table("scoring_runs")
    op.drop_index("ix_scoring_results_risk_band", table_name="scoring_results")
    op.drop_index("ix_scoring_results_booking_id", table_name="scoring_results")
    op.drop_table("scoring_results")
    op.drop_index("ix_bookings_outcome", table_name="bookings")
    op.drop_index("ix_bookings_appointment_at", table_name="bookings")
    op.drop_index("ix_bookings_client_id", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_clients_external_id", table_name="clients")
    op.drop_table("clients")
