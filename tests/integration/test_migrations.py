"""Integration tests for Alembic database migrations up and down."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


@pytest.mark.integration
def test_alembic_upgrade_and_downgrade(tmp_path: Path) -> None:
    """Verify that Alembic runs migrations up to head and downgrades back to base cleanly."""
    db_file = tmp_path / "migration_test.db"
    db_url = f"sqlite:///{db_file}"

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    # 1. Upgrade to head
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(db_url)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = {
        "clients",
        "bookings",
        "scoring_results",
        "scoring_runs",
        "column_mappings",
        "app_settings",
        "alembic_version",
    }
    assert expected_tables.issubset(set(tables))

    # 2. Downgrade to base
    command.downgrade(alembic_cfg, "base")

    # Re-inspect tables after downgrade
    inspector = inspect(engine)
    remaining_tables = set(inspector.get_table_names())
    # All domain tables should be dropped
    assert "clients" not in remaining_tables
    assert "bookings" not in remaining_tables
    assert "scoring_results" not in remaining_tables

    # 3. Upgrade back to head to verify idempotent re-application
    command.upgrade(alembic_cfg, "head")
    inspector = inspect(engine)
    tables_again = inspector.get_table_names()
    assert expected_tables.issubset(set(tables_again))
