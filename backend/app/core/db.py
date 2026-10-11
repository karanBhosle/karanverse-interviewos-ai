from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
        _engine = create_async_engine(
            settings.database_url, future=True, pool_pre_ping=not settings.database_url.startswith("sqlite"), connect_args=connect_args
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False, class_=AsyncSession)
    return _session_factory


def reset_engine() -> None:
    global _engine, _session_factory
    _engine = None
    _session_factory = None


async def get_db() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_models() -> None:
    from app import models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_job_match_questions)


def _ensure_job_match_questions(sync_conn) -> None:
    try:
        rows = sync_conn.exec_driver_sql("PRAGMA table_info(job_matches)").fetchall()
        columns = {row[1] for row in rows}
        if rows and "prepared_questions" not in columns:
            sync_conn.exec_driver_sql("ALTER TABLE job_matches ADD COLUMN prepared_questions JSON")
    except Exception:
        return
