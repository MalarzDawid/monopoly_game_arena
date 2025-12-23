"""
Async session management for SQLAlchemy.

Provides:
- Async engine and session factory
- FastAPI dependency for injecting sessions
- Lifecycle management (init_db, close_db)
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from data.config import get_settings
from data.models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory (initialized once)
_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get or create the global async engine.

    Raises:
        RuntimeError: If engine not initialized (call init_db first)
    """
    if _engine is None:
        raise RuntimeError(
            "Database engine not initialized. Call init_db() first."
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the global async session factory.

    Raises:
        RuntimeError: If session factory not initialized
    """
    if _async_session_factory is None:
        raise RuntimeError(
            "Session factory not initialized. Call init_db() first."
        )
    return _async_session_factory


async def init_db() -> None:
    """
    Initialize the database engine and session factory.

    This should be called once at application startup (e.g., in FastAPI lifespan).
    """
    global _engine, _async_session_factory

    settings = get_settings()
    logger.info(f"Initializing database connection: {settings.database_url.split('@')[-1]}")

    # Create async engine
    _engine = create_async_engine(
        settings.database_url,
        **settings.get_engine_kwargs(),
    )

    # Create session factory
    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Don't expire objects after commit (performance)
        autoflush=False,  # Manual control over when to flush
        autocommit=False,  # Explicit transaction control
    )

    logger.info("Database initialized successfully")


async def close_db() -> None:
    """
    Close the database engine and cleanup resources.

    This should be called at application shutdown (e.g., in FastAPI lifespan).
    """
    global _engine, _async_session_factory

    if _engine is not None:
        logger.info("Closing database connection")
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection closed")


async def create_tables() -> None:
    """
    Create all tables defined in Base.metadata.

    WARNING: This is for development only. In production, use Alembic migrations.
    """
    engine = get_engine()
    logger.warning("Creating tables directly (dev mode) - use Alembic in production!")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Tables created successfully")


async def drop_tables() -> None:
    """
    Drop all tables defined in Base.metadata.

    WARNING: This is destructive and for testing only!
    """
    engine = get_engine()
    logger.warning("Dropping all tables (testing mode)")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    logger.info("Tables dropped successfully")


# ---- FastAPI Dependency ----


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage in endpoints:
        @app.get("/games/{game_id}")
        async def get_game(
            game_id: str,
            session: AsyncSession = Depends(get_session)
        ):
            ...

    The session is automatically committed on success and rolled back on error.
    """
    factory = get_session_factory()

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---- Context Manager (Alternative Usage) ----


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions.

    Usage outside FastAPI:
        async with session_scope() as session:
            game = await session.get(Game, game_id)
            ...

    Auto-commits on success, rolls back on exception.
    """
    factory = get_session_factory()

    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
