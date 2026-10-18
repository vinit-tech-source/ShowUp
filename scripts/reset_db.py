"""CLI script to reset ShowUp local database to a fresh, empty state."""

from __future__ import annotations

from showup.storage.database import get_session
from showup.storage.repositories import wipe_all


def reset_database() -> None:
    """Wipe all appointments, scoring runs, and client profiles from SQLite."""
    with get_session() as session:
        wipe_all(session=session)
    print("Database cleared successfully. ShowUp is now in a fresh empty state (0 appointments).")


if __name__ == "__main__":
    reset_database()
