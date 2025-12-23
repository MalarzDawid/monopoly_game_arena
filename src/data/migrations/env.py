"""
Alembic environment configuration for async migrations.

This file is configured to:
1. Load database URL from DatabaseSettings (.env)
2. Import all SQLAlchemy models for autogenerate support
3. Run migrations asynchronously using asyncpg
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add project root to sys.path for imports (env.py is at src/data/migrations)
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import settings and models directly (avoid server.__init__ circular import)
import importlib.util

def load_module_from_file(module_name: str, file_path: Path):
    """Load a module from file path without importing parent packages."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Load database modules directly
config_module = load_module_from_file(
    "db_config",
    project_root / "src" / "data" / "config.py"
)
models_module = load_module_from_file(
    "db_models",
    project_root / "src" / "data" / "models.py"
)

get_settings = config_module.get_settings
Base = models_module.Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load database URL from settings (not from alembic.ini)
settings = get_settings()
# IMPORTANT: Use SYNC URL for Alembic (it converts to async internally)
# Actually, for async template we need async URL with asyncpg driver
config.set_main_option("sqlalchemy.url", settings.database_url)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations synchronously within an async connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        # Include object names in migration
        include_object=lambda obj, name, type_, reflected, compare_to: True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Build engine configuration from alembic.ini section
    configuration = config.get_section(config.config_ini_section, {})
    # Override with our database URL
    configuration["sqlalchemy.url"] = settings.database_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't pool connections for migrations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
