"""Database engine, session management, and file security for SQLite."""

from __future__ import annotations

import functools
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


@functools.lru_cache(maxsize=1)
def get_default_engine() -> Engine:
    """Return or lazily create the default SQLAlchemy engine."""
    return create_db_engine()


@functools.lru_cache(maxsize=1)
def get_default_session_factory() -> sessionmaker[Session]:
    """Return or lazily create the default session factory."""
    return get_session_factory(get_default_engine())


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db(engine: Engine | None = None, db_path: Path | None = None) -> None:
    """Initialize database tables and set file permissions."""
    target_engine = engine or get_default_engine()
    Base.metadata.create_all(bind=target_engine)
    target_path = db_path or get_settings().db_path
    if target_path is not None and target_path.exists():
        set_db_file_permissions(target_path)


@contextmanager
def get_session(
    session_factory: sessionmaker[Session] | None = None,
) -> Generator[Session, None, None]:
    """Provide a transactional session context."""
    factory = session_factory or get_default_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
