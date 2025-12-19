"""
Test script for database integration.

Run this after setting up PostgreSQL and running migrations:
1. docker-compose up -d postgres
2. alembic upgrade head
3. python test_database.py
"""

import asyncio
from datetime import datetime

from src.data import (
    init_db,
    close_db,
    session_scope,
    GameRepository,
)


async def main():
    """Test database operations."""
    print("🚀 Starting database test...\n")

    # Initialize database
    print("1️⃣  Initializing database connection...")
    await init_db()
    print("✅ Database initialized\n")

    try:
        # Create a test game
        async with session_scope() as session:
            repo = GameRepository(session)

            print("2️⃣  Creating test game...")
            game = await repo.create_game(
                game_id=f"test-game-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                config={
                    "seed": 42,
                    "max_turns": 100,
                    "num_players": 4,
                },
                metadata={
                    "test": True,
                    "environment": "development",
                },
            )
            print(f"✅ Created game: {game.game_id} (UUID: {game.id})\n")

            # Add players
            print("3️⃣  Adding players...")
            players = []
            for i in range(4):
                player = await repo.add_player(
                    game_uuid=game.id,
                    player_id=i,
                    name=f"Player {i}",
                    agent_type="greedy" if i % 2 == 0 else "random",
                )
                players.append(player)
                print(f"   → Added {player.name} ({player.agent_type})")
            print()

            # Add some events
            print("4️⃣  Adding game events...")
            events = [
                {
                    "sequence_number": 0,
                    "turn_number": 1,
                    "event_type": "game_start",
                    "payload": {
                        "timestamp": datetime.now().isoformat(),
                        "players": [p.player_id for p in players],
                    },
                },
                {
                    "sequence_number": 1,
                    "turn_number": 1,
                    "event_type": "turn_start",
                    "payload": {"player_id": 0},
                    "actor_player_id": 0,
                },
                {
                    "sequence_number": 2,
                    "turn_number": 1,
                    "event_type": "dice_roll",
                    "payload": {"player_id": 0, "roll": [3, 4], "total": 7},
                    "actor_player_id": 0,
                },
                {
                    "sequence_number": 3,
                    "turn_number": 1,
                    "event_type": "player_moved",
                    "payload": {"player_id": 0, "from": 0, "to": 7},
                    "actor_player_id": 0,
                },
                {
                    "sequence_number": 4,
                    "turn_number": 1,
                    "event_type": "property_purchased",
                    "payload": {
                        "player_id": 0,
                        "property": "Connecticut Avenue",
                        "price": 120,
                    },
                    "actor_player_id": 0,
                },
            ]

            await repo.add_events_batch(game.id, events)
            print(f"✅ Added {len(events)} events\n")

            # Update game status
            print("5️⃣  Updating game status...")
            await repo.update_game_status(
                game_id=game.game_id,
                status="running",
                started_at=datetime.now(),
                total_turns=1,
            )
            print("✅ Game status updated to 'running'\n")

        # Query the data (new session)
        async with session_scope() as session:
            repo = GameRepository(session)

            print("6️⃣  Querying game data...")
            game, events = await repo.get_game_with_events(game.game_id)

            print(f"\n📊 Game Summary:")
            print(f"   Game ID: {game.game_id}")
            print(f"   Status: {game.status}")
            print(f"   Players: {len(game.players)}")
            print(f"   Total Events: {len(events)}")
            print(f"   Created: {game.created_at}")
            print()

            print("📋 Events:")
            for event in events:
                print(
                    f"   [{event.sequence_number}] Turn {event.turn_number}: "
                    f"{event.event_type} - {event.payload.get('player_id', 'N/A')}"
                )
            print()

            # Get statistics
            stats = await repo.get_game_statistics(game.id)
            print("📈 Statistics:")
            print(f"   Total Events: {stats['total_events']}")
            print(f"   Latest Sequence: {stats['latest_sequence']}")
            print("   Events by Type:")
            for event_type, count in stats["events_by_type"].items():
                print(f"      - {event_type}: {count}")
            print()

            # Query specific events
            turn_1_events = await repo.get_game_events(
                game_uuid=game.id,
                turn_number=1,
            )
            print(f"🎲 Turn 1 had {len(turn_1_events)} events")
            print()

        print("✅ All tests passed!\n")

    finally:
        # Cleanup
        print("🧹 Closing database connection...")
        await close_db()
        print("✅ Done!\n")


if __name__ == "__main__":
    asyncio.run(main())
