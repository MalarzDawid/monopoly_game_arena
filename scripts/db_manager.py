#!/usr/bin/env python3
"""
Database management utility script.

Usage:
    python scripts/db_manager.py init     # Initialize database
    python scripts/db_manager.py reset    # Drop and recreate tables (DEV ONLY!)
    python scripts/db_manager.py test     # Test connection
    python scripts/db_manager.py stats    # Show database statistics
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from server.database import (
    init_db,
    close_db,
    create_tables,
    drop_tables,
    session_scope,
    GameRepository,
    get_engine,
)
from sqlalchemy import text


async def init():
    """Initialize database connection and create tables."""
    print("🔧 Initializing database...")
    await init_db()
    print("✅ Database initialized")

    print("\n📋 Creating tables (using Alembic is recommended)...")
    await create_tables()
    print("✅ Tables created")

    await close_db()


async def reset():
    """Drop all tables and recreate them (DESTRUCTIVE!)."""
    print("⚠️  WARNING: This will DELETE ALL DATA!")
    response = input("Are you sure? Type 'yes' to continue: ")

    if response.lower() != "yes":
        print("❌ Aborted")
        return

    print("\n🗑️  Dropping all tables...")
    await init_db()
    await drop_tables()
    print("✅ Tables dropped")

    print("\n📋 Recreating tables...")
    await create_tables()
    print("✅ Tables created")

    await close_db()


async def test():
    """Test database connection."""
    print("🔍 Testing database connection...")

    try:
        await init_db()
        print("✅ Connected to database")

        # Test query
        async with session_scope() as session:
            result = await session.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"📊 PostgreSQL version: {version}")

            # Count tables
            result = await session.execute(
                text(
                    """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """
                )
            )
            table_count = result.scalar()
            print(f"📋 Tables in database: {table_count}")

        await close_db()
        print("✅ Connection test successful")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        await close_db()
        sys.exit(1)


async def stats():
    """Show database statistics."""
    print("📊 Database Statistics\n")

    await init_db()

    async with session_scope() as session:
        # Count games
        result = await session.execute(text("SELECT COUNT(*) FROM games"))
        game_count = result.scalar()
        print(f"🎲 Total Games: {game_count}")

        # Count players
        result = await session.execute(text("SELECT COUNT(*) FROM players"))
        player_count = result.scalar()
        print(f"👥 Total Players: {player_count}")

        # Count events
        result = await session.execute(text("SELECT COUNT(*) FROM game_events"))
        event_count = result.scalar()
        print(f"📝 Total Events: {event_count}")

        # Recent games
        result = await session.execute(
            text(
                """
            SELECT game_id, status, total_turns, created_at
            FROM games
            ORDER BY created_at DESC
            LIMIT 5
        """
            )
        )
        recent_games = result.fetchall()

        if recent_games:
            print(f"\n📅 Recent Games:")
            for game in recent_games:
                print(
                    f"   - {game[0]}: {game[1]} "
                    f"({game[2]} turns) - {game[3].strftime('%Y-%m-%d %H:%M:%S')}"
                )

        # Event type distribution
        result = await session.execute(
            text(
                """
            SELECT event_type, COUNT(*) as count
            FROM game_events
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        """
            )
        )
        event_types = result.fetchall()

        if event_types:
            print(f"\n📈 Event Type Distribution:")
            for event_type, count in event_types:
                print(f"   - {event_type}: {count}")

        # Database size
        result = await session.execute(
            text(
                """
            SELECT pg_size_pretty(pg_database_size(current_database()))
        """
            )
        )
        db_size = result.scalar()
        print(f"\n💾 Database Size: {db_size}")

    await close_db()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    commands = {
        "init": init,
        "reset": reset,
        "test": test,
        "stats": stats,
    }

    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(__doc__)
        sys.exit(1)

    await commands[command]()


if __name__ == "__main__":
    asyncio.run(main())
