## Database Configuration

Database settings loaded from environment variables via Pydantic.

### Environment Variables

Create `.env` file in project root:

```bash
# Async URL for SQLAlchemy (required)
DATABASE_URL=postgresql+asyncpg://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena

# Sync URL for Alembic migrations (required)
DATABASE_URL_SYNC=postgresql://monopoly_user:monopoly_pass@localhost:5432/monopoly_arena
```

### Connection Pool Settings

| Variable | Default | Range | Description |
|----------|---------|-------|-------------|
| `DB_POOL_SIZE` | 20 | 1‑100 | Base connection pool size |
| `DB_MAX_OVERFLOW` | 10 | 0‑50 | Max overflow connections |
| `DB_POOL_TIMEOUT` | 30 | 1‑120 | Timeout waiting for connection (seconds) |
| `DB_POOL_RECYCLE` | 3600 | 60+ | Recycle connections after (seconds) |

### Debug Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_ECHO` | false | Echo SQL queries to logs |
| `DEBUG` | false | Debug mode |
| `LOG_LEVEL` | INFO | Logging level |

### Usage

```python
from server.database.config import get_settings

settings = get_settings()

# Access settings
print(settings.database_url)
print(settings.db_pool_size)

# Get engine kwargs for SQLAlchemy
engine_kwargs = settings.get_engine_kwargs()
# {
#   "pool_size": 20,
#   "max_overflow": 10,
#   "pool_timeout": 30,
#   "pool_recycle": 3600,
#   "echo": False,
#   "pool_pre_ping": True
# }
```

### Session Management

```python
from server.database import init_db, close_db, session_scope, get_session

# Initialize at startup
await init_db()

# Use context manager
async with session_scope() as session:
    # Auto-commits on success
    # Auto-rollback on exception
    pass

# FastAPI dependency injection
@app.get("/games/{game_id}")
async def get_game(
    game_id: str,
    session: AsyncSession = Depends(get_session)
):
    repo = GameRepository(session)
    return await repo.get_game_by_id(game_id)

# Cleanup at shutdown
await close_db()
```

### Database Management Commands

```bash
# Start PostgreSQL container
make db-up

# Apply migrations
make db-migrate

# Create new migration
make db-create-migration MSG="add new table"

# Rollback last migration
make db-downgrade

# Show migration status
make db-current
make db-history

# Reset database (destructive!)
make db-reset

# Backup and restore
make db-backup
make db-restore
```

### Reference

::: server.database.config.DatabaseSettings

::: server.database.config.get_settings
