"""Database engine, session management, and file security for SQLite."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from showup.config import ShowUpSettings, get_settings
from showup.logging_setup import get_logger
from showup.storage.models import Base

logger = get_logger(__name__)


def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """Configure SQLite with WAL mode, normal sync, and foreign keys enabled."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def set_db_file_permissions(db_path: Path) -> None:
    """Set restrictive file permissions on the SQLite database file.

    On POSIX systems, sets 0600 (read/write for owner only).
    On Windows, uses os.chmod (which restricts read/write permissions for current user).
    """
    if not db_path.exists():
        return
    try:
        db_path.chmod(0o600)
    except OSError as e:
        logger.warning("failed_to_set_db_permissions", path=str(db_path), error=str(e))


def create_db_engine(db_url: str | None = None, *, echo: bool = False) -> Engine:
    """Create a configured SQLAlchemy engine."""
    if db_url is None:
        settings: ShowUpSettings = get_settings()
        settings.ensure_dirs()
        db_url = settings.db_url

    is_sqlite = db_url.startswith("sqlite")
    engine = create_engine(
        db_url,
        echo=echo,
        connect_args={"check_same_thread": False} if is_sqlite else {},
    )

    if is_sqlite and not db_url.endswith(":memory:"):
        event.listen(engine, "connect", _set_sqlite_pragmas)

    return engine


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine, db_path: Path | None = None) -> None:
    """Initialize database tables and set file permissions."""
    Base.metadata.create_all(bind=engine)
    if db_path is not None and db_path.exists():
        set_db_file_permissions(db_path)


@contextmanager
def get_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    """Provide a transactional session context."""
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
