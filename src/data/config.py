"""
Database configuration using pydantic-settings.

Handles environment variables and provides type-safe config access,
including light validation of connection URLs and secrets.

In development, the default password is allowed but a warning is logged.
For production deployments, configure a strong password via environment
variables and/or a dedicated secrets manager.
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """
    Database configuration loaded from environment variables.

    Required env vars:
    - DATABASE_URL: async connection string (postgresql+asyncpg://...)
    - DATABASE_URL_SYNC: sync connection string for Alembic (postgresql://...)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Async URL for asyncpg (runtime)
    database_url: str = Field(
        default="postgresql+asyncpg://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena",
        description="Async database connection URL",
    )

    # Sync URL for Alembic migrations
    database_url_sync: str = Field(
        default="postgresql://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena",
        description="Sync database connection URL for migrations",
    )

    # Connection pool settings
    db_pool_size: int = Field(default=20, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=50)
    db_pool_timeout: int = Field(default=30, ge=1, le=120)
    db_pool_recycle: int = Field(default=3600, ge=60)

    # Echo SQL queries (debug)
    db_echo: bool = Field(default=False)

    # Application settings
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")

    @field_validator("database_url")
    @classmethod
    def validate_async_url(cls, v: str) -> str:
        """Ensure async URL uses asyncpg driver and warn on default credentials."""
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg:// scheme")
        if "monopoly_pass" in v:
            logging.getLogger(__name__).warning(
                "DATABASE_URL is using the default 'monopoly_pass' password. "
                "This is fine for local development, but MUST be changed in production."
            )
        return v

    @field_validator("database_url_sync")
    @classmethod
    def validate_sync_url(cls, v: str) -> str:
        """Ensure sync URL uses standard postgres driver and warn on default credentials."""
        if not v.startswith("postgresql://"):
            raise ValueError("DATABASE_URL_SYNC must use postgresql:// scheme")
        if "monopoly_pass" in v:
            logging.getLogger(__name__).warning(
                "DATABASE_URL_SYNC is using the default 'monopoly_pass' password. "
                "This is fine for local development, but MUST be changed in production."
            )
        return v

    def get_engine_kwargs(self) -> dict:
        """Return SQLAlchemy engine configuration."""
        return {
            "pool_size": self.db_pool_size,
            "max_overflow": self.db_max_overflow,
            "pool_timeout": self.db_pool_timeout,
            "pool_recycle": self.db_pool_recycle,
            "echo": self.db_echo,
            "pool_pre_ping": True,  # Verify connections before using
        }


@lru_cache
def get_settings() -> DatabaseSettings:
    """
    Cached settings singleton.

    Returns the same DatabaseSettings instance across the application.
    """
    return DatabaseSettings()
