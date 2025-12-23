#!/usr/bin/env python3
"""
Test script for LLM decision tracking functionality.

This script tests the new LLM-related database functionality:
1. Creates a test game
2. Adds an LLM player
3. Records LLM decisions
4. Retrieves and verifies LLM decisions
5. Updates LLM player strategy
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import pytest

from data import init_db, close_db, session_scope, GameRepository
from data.models import Game, Player, LLMDecision

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_llm_functionality():
    """Test LLM-related database functionality."""
    logger.info("🚀 Starting LLM database test...")

    # Initialize database connection
    logger.info("1️⃣  Initializing database connection...")
    await init_db()
    logger.info("✅ Database initialized")

    # Create a test game
    game_id = f"llm-test-game-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    async with session_scope() as session:
        repo = GameRepository(session)
        
        # Create game
        logger.info("2️⃣  Creating test game...")
        game = await repo.create_game(
            game_id=game_id,
            config={"seed": 42, "max_turns": 100},
            metadata={"test": True, "type": "llm_test"},
        )
        logger.info(f"✅ Created game: {game_id} (UUID: {game.id})")
        
        # Add players including an LLM player
        logger.info("3️⃣  Adding players...")
        
        # Regular player
        regular_player = await repo.add_player(
            game_uuid=game.id,
            player_id=0,
            name="Regular Player",
            agent_type="greedy",
        )
        logger.info(f"   → Added regular player: {regular_player.name}")
        
        # LLM player with strategy profile
        llm_player = await repo.add_player(
            game_uuid=game.id,
            player_id=1,
            name="LLM Player",
            agent_type="llm",
        )
        
        # Update LLM player with LLM-specific fields
        llm_player.llm_model_name = "gpt-4"
        llm_player.llm_parameters = {
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        llm_player.llm_strategy_profile = {
            "risk_tolerance": 0.7,
            "property_focus": ["orange", "red", "light_blue"],
            "trading_style": "aggressive",
            "building_threshold": 500,
        }
        await session.flush()
        logger.info(f"   → Added LLM player: {llm_player.name}")
        
        # Add some game events
        logger.info("4️⃣  Adding game events...")
        await repo.add_events_batch(
            game_uuid=game.id,
            events=[
                {
                    "sequence_number": 0,
                    "turn_number": 1,
                    "event_type": "game_start",
                    "payload": {"players": [0, 1]},
                },
                {
                    "sequence_number": 1,
                    "turn_number": 1,
                    "event_type": "turn_start",
                    "payload": {"player_id": 1},
                    "actor_player_id": 1,
                },
            ],
        )
        logger.info("✅ Added game events")
        
        # Record LLM decision
        logger.info("5️⃣  Recording LLM decision...")
        
        # Example game state
        game_state = {
            "board": {
                "current_spaces": ["GO", "Mediterranean Avenue", "Community Chest"],
                "properties_owned": {"0": [3, 6, 9], "1": []}
            },
            "current_turn": 1,
            "active_player_id": 1,
            "dice_roll": [3, 4],
            "players_status": {
                "0": {"cash": 1200, "position": 10, "in_jail": True},
                "1": {"cash": 1500, "position": 7, "in_jail": False}
            }
        }
        
        # Example player state
        player_state = {
            "cash": 1500,
            "position": 7,
            "properties": [],
            "cards": [],
            "in_jail": False,
            "net_worth": 1500,
        }
        
        # Example available actions
        available_actions = {
            "actions": [
                {"type": "buy_property", "position": 7, "price": 100},
                {"type": "decline_purchase", "position": 7},
            ]
        }
        
        # Example LLM reasoning
        reasoning = """
        I'm currently on Chance space (position 7) with $1500 cash.
        Looking at the board, I see that the other player owns properties in the light blue group.
        I should focus on acquiring properties to build my portfolio.
        If I land on a property, I'll buy it if it's affordable.
        """
        
        # Record the decision
        llm_decision = await repo.add_llm_decision(
            game_uuid=game.id,
            player_id=1,
            turn_number=1,
            sequence_number=2,
            game_state=game_state,
            player_state=player_state,
            available_actions=available_actions,
            prompt="What action should I take?",
            reasoning=reasoning,
            chosen_action={"type": "buy_property", "position": 7, "price": 100},
            strategy_description="Aggressive property acquisition",
            processing_time_ms=250,
            model_version="gpt-4-0613",
        )
        logger.info(f"✅ Recorded LLM decision: {llm_decision.id}")
        
        # Retrieve LLM decisions
        logger.info("6️⃣  Retrieving LLM decisions...")
        decisions = await repo.get_llm_decisions_for_game(game.id)
        logger.info(f"✅ Retrieved {len(decisions)} LLM decisions")
        
        if len(decisions) != 1:
            logger.error(f"❌ Expected 1 decision, got {len(decisions)}")
            return
        
        # Verify decision content
        decision = decisions[0]
        logger.info(f"📊 Decision details:")
        logger.info(f"   Player: {decision.player_id}")
        logger.info(f"   Turn: {decision.turn_number}")
        logger.info(f"   Sequence: {decision.sequence_number}")
        logger.info(f"   Action: {decision.chosen_action['type']}")
        
        # Update LLM player strategy
        logger.info("7️⃣  Updating LLM player strategy...")
        new_strategy = {
            "risk_tolerance": 0.5,  # More conservative
            "property_focus": ["orange", "red"],  # Narrower focus
            "trading_style": "cautious",  # Changed from aggressive
            "building_threshold": 600,  # Higher threshold
            "jail_strategy": "stay_if_properties_developed",  # New strategy element
        }
        
        updated_player = await repo.update_llm_player_strategy(
            game_uuid=game.id,
            player_id=1,
            strategy_profile=new_strategy,
        )
        
        if updated_player:
            logger.info("✅ Updated LLM player strategy")
            logger.info(f"📊 New strategy: {updated_player.llm_strategy_profile}")
        else:
            logger.error("❌ Failed to update LLM player strategy")
        
        # Test search functionality
        logger.info("8️⃣  Testing LLM reasoning search...")
        search_results = await repo.search_llm_reasoning("acquiring properties")
        logger.info(f"✅ Search found {len(search_results)} results")
        
        # Final verification
        logger.info("9️⃣  Final verification...")
        
        # Get the game with all related data
        game_data = await repo.get_game_by_id(game_id)
        if game_data:
            logger.info("✅ Successfully retrieved game data")
        else:
            logger.error("❌ Failed to retrieve game data")
            
    # Close database connection
    logger.info("🧹 Closing database connection...")
    await close_db()
    logger.info("✅ Done!")


if __name__ == "__main__":
    asyncio.run(test_llm_functionality())
