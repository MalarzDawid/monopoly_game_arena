"""
Central application configuration using pydantic-settings.

This module provides typed access to environment-based configuration for:
- LLM providers (Ollama, vLLM, OpenAI-compatible endpoints)
- Dashboard server and API endpoints

Database configuration lives in `data.config.DatabaseSettings`.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM backends."""

    OLLAMA = "ollama"
    VLLM = "vllm"
    OPENAI = "openai"
    CUSTOM = "custom"


class LLMSettings(BaseSettings):
    """
    Configuration for LLM provider endpoints and models.

    Environment variables (prefix: LLM_):
        LLM_PROVIDER       - ollama | vllm | openai | custom (default: ollama)
        LLM_BASE_URL       - Base URL for OpenAI-compatible API
        LLM_MODEL          - Model name or identifier
        LLM_API_KEY        - Optional API key for authenticated providers
        LLM_TIMEOUT_SECONDS- Request timeout in seconds (default: 30)
        LLM_MAX_TOKENS     - Max response tokens (default: 512)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_prefix="LLM_",
    )

    provider: LLMProvider = Field(
        default=LLMProvider.OLLAMA,
        description="LLM backend to use (ollama | vllm | openai | custom).",
    )
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for OpenAI-compatible API, e.g. http://localhost:11434/v1.",
    )
    model: str = Field(
        default="gemma3:4b",
        description="Model name or identifier.",
    )
    api_key: Optional[SecretStr] = Field(
        default=None,
        description="API key for providers that require authentication.",
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="HTTP request timeout in seconds.",
    )
    max_tokens: int = Field(
        default=512,
        gt=0,
        description="Maximum number of tokens to generate.",
    )

    @field_validator("base_url", mode="before")
    @classmethod
    def default_base_url(cls, value: Optional[str], info):
        """
        Provide sensible defaults for base_url depending on the provider.

        - ollama -> http://localhost:11434/v1
        - vllm   -> http://localhost:8000/v1
        - openai/custom -> must be provided explicitly
        """
        if value:
            return value

        provider = info.data.get("provider", LLMProvider.OLLAMA)
        if isinstance(provider, str):
            try:
                provider = LLMProvider(provider)
            except ValueError:
                provider = LLMProvider.OLLAMA

        if provider == LLMProvider.OLLAMA:
            return "http://localhost:11434/v1"
        if provider == LLMProvider.VLLM:
            return "http://localhost:8000/v1"

        # For OPENAI and CUSTOM we require explicit configuration
        return value


class DashboardSettings(BaseSettings):
    """
    Configuration for the analytics dashboard and API endpoints.

    Environment variables:
        DASHBOARD_HOST  - Host for Dash server (default: 127.0.0.1)
        DASHBOARD_PORT  - Port for Dash server (default: 8050)
        DASHBOARD_DEBUG - Run Dash in debug mode (default: true)
        MAIN_SERVER_URL - Base URL for main FastAPI server (default: http://localhost:8000)
        API_BASE_URL    - Base URL for dashboard API (defaults to MAIN_SERVER_URL)
        DATABASE_URL    - Sync database URL for dashboard (postgresql://...)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    dashboard_host: str = Field(default="127.0.0.1", alias="DASHBOARD_HOST")
    dashboard_port: int = Field(default=8050, alias="DASHBOARD_PORT")
    dashboard_debug: bool = Field(default=True, alias="DASHBOARD_DEBUG")

    database_url: str = Field(
        default="postgresql://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena",
        description="Sync database URL for dashboard queries.",
    )

    main_server_url: str = Field(
        default="http://localhost:8000",
        alias="MAIN_SERVER_URL",
        description="Base URL for the main FastAPI server.",
    )
    api_base_url: Optional[str] = Field(
        default=None,
        alias="API_BASE_URL",
        description="Base URL for dashboard API calls (defaults to MAIN_SERVER_URL).",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_db_url(cls, value: Optional[str]) -> str:
        """
        Normalize database URL and convert asyncpg URLs to sync driver.
        """
        if not value:
            value = "postgresql://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena"
        if value.startswith("postgresql+asyncpg://"):
            value = value.replace("postgresql+asyncpg://", "postgresql://")
        return value

    @field_validator("api_base_url", mode="after")
    @classmethod
    def default_api_base(cls, value: Optional[str], info):
        """
        If API_BASE_URL is not set, fall back to MAIN_SERVER_URL.
        """
        if value:
            return value
        return info.data.get("main_server_url", "http://localhost:8000")


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Return cached LLM settings instance."""
    return LLMSettings()


@lru_cache
def get_dashboard_settings() -> DashboardSettings:
    """Return cached dashboard settings instance."""
    return DashboardSettings()

