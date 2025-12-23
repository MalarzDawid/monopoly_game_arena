#!/usr/bin/env python3
"""
Batch game runner for generating test data.

Usage:
    # Run N games with same strategy for all players
    python scripts/batch_games.py --games 10 --players 4 --agent greedy --max-turns 100

    # Run N games with LLM agents (same strategy)
    python scripts/batch_games.py --games 5 --players 4 --agent llm --llm-strategy balanced

    # Run N games with different LLM strategies (rotating)
    python scripts/batch_games.py --games 9 --players 4 --agent llm --multi-strategy

    # Run with custom roles
    python scripts/batch_games.py --games 5 --roles llm,greedy,greedy,random

    # Run N games in PARALLEL (e.g., 5 games with 3 workers)
    python scripts/batch_games.py --games 5 --workers 3 --roles llm,llm,greedy,greedy

Examples:
    # 10 games with 4 greedy agents, max 100 turns each
    uv run python scripts/batch_games.py -n 10 -p 4 -a greedy -t 100

    # 5 games with LLM balanced strategy
    uv run python scripts/batch_games.py -n 5 -p 4 -a llm -s balanced

    # 9 games rotating through all LLM strategies (3 each)
    uv run python scripts/batch_games.py -n 9 -p 4 -a llm --multi-strategy

    # 5 games in parallel with 5 workers (all at once)
    uv run python scripts/batch_games.py -n 5 -w 5 --roles llm,llm,greedy,greedy -s balanced
"""

import argparse
import asyncio
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from src.core import GameConfig, Player, create_game
from src.core.game.game import ActionType
from src.core.game.rules import apply_action, get_legal_actions
from game_logger import GameLogger
from src.core.agents import GreedyAgent, LLMAgent, RandomAgent


def _save_game_to_db(
    db_game_id: str,
    config: dict,
    num_players: int,
    player_names: List[str],
    agent_type: str,
    llm_strategy: Optional[str],
    game,
    logger: GameLogger,
    llm_decisions: Optional[List[dict]] = None,
) -> bool:
    """Save complete game to database (create, events, finalize). Returns success."""
    async def _save():
        from src.data import init_db, close_db, session_scope, GameRepository
        import uuid as uuid_module

        await init_db()

        try:
            # Create game and players
            async with session_scope() as session:
                repo = GameRepository(session)
                db_game = await repo.create_game(
                    game_id=db_game_id,
                    config=config,
                    metadata={"llm_strategy": llm_strategy} if llm_strategy else {},
                )
                game_uuid = db_game.id

                for i in range(num_players):
                    await repo.add_player(
                        game_uuid=game_uuid,
                        player_id=i,
                        name=player_names[i],
                        agent_type=agent_type,
                    )

            # Flush pending events to database
            await logger.flush_to_db()

            # Save LLM decisions if any
            if llm_decisions:
                async with session_scope() as session:
                    repo = GameRepository(session)
                    for decision in llm_decisions:
                        await repo.add_llm_decision(
                            game_uuid=game_uuid,
                            player_id=decision["player_id"],
                            turn_number=decision["turn_number"],
                            sequence_number=decision.get("sequence_number", 0),
                            game_state=decision.get("game_state", {}),
                            player_state=decision.get("player_state", {}),
                            available_actions=decision.get("available_actions", {}),
                            prompt=decision.get("prompt", ""),
                            reasoning=decision.get("reasoning", ""),
                            chosen_action=decision.get("chosen_action", {}),
                            strategy_description=decision.get("strategy"),
                            processing_time_ms=decision.get("processing_time_ms"),
                            model_version=decision.get("model_version"),
                        )

            # Update game status and player results
            async with session_scope() as session:
                repo = GameRepository(session)

                await repo.update_game_status(
                    game_id=db_game_id,
                    status="finished",
                    finished_at=datetime.now(),
                    winner_id=game.winner,
                    total_turns=game.turn_number,
                )

                for player_id, player in game.players.items():
                    net_worth = game._calculate_net_worth(player_id)
                    await repo.update_player_results(
                        game_uuid=game_uuid,
                        player_id=player_id,
                        final_cash=player.cash,
                        final_net_worth=net_worth,
                        is_winner=(player_id == game.winner),
                        is_bankrupt=player.is_bankrupt,
                    )

            return True
        finally:
            await close_db()

    try:
        return asyncio.run(_save())
    except Exception as e:
        print(f"[DB] Failed to save game to database: {e}")
        return False

# LLM strategies available
LLM_STRATEGIES = ["aggressive", "balanced", "defensive"]


def create_agents(
    num_players: int,
    agent_type: str,
    player_names: List[str],
    llm_strategy: str = "balanced",
    roles: Optional[List[str]] = None,
    decision_callback=None,
):
    """Create agents based on type or custom roles."""
    agents = []

    if roles:
        # Custom roles provided
        for i, role in enumerate(roles[:num_players]):
            name = player_names[i]
            if role == "random":
                agents.append(RandomAgent(i, name))
            elif role == "llm":
                agents.append(LLMAgent(i, name, strategy=llm_strategy, decision_callback=decision_callback))
            else:  # greedy or default
                agents.append(GreedyAgent(i, name))
    else:
        # Same agent type for all
        for i in range(num_players):
            name = player_names[i]
            if agent_type == "random":
                agents.append(RandomAgent(i, name))
            elif agent_type == "llm":
                agents.append(LLMAgent(i, name, strategy=llm_strategy, decision_callback=decision_callback))
            else:  # greedy
                agents.append(GreedyAgent(i, name))

    return agents


def run_single_game(
    game_id: int,
    num_players: int,
    agent_type: str,
    max_turns: int,
    llm_strategy: str = "balanced",
    roles: Optional[List[str]] = None,
    seed: Optional[int] = None,
    verbose: bool = False,
    save_to_db: bool = True,
) -> dict:
    """Run a single game and return results."""
    player_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"][:num_players]
    players = [Player(i, player_names[i]) for i in range(num_players)]

    # Generate database game ID upfront (will be used at the end)
    db_game_id = f"batch-{uuid.uuid4().hex[:12]}" if save_to_db else None

    # Create logger with game_id for event buffering
    logger = GameLogger(game_id=db_game_id)

    # Buffer for LLM decisions (for database persistence)
    llm_decisions_buffer: List[dict] = []

    def llm_decision_callback(decision_data: dict) -> None:
        """Callback to log LLM decisions to JSONL and buffer for DB."""
        player_id = decision_data["player_id"]
        # Log to JSONL
        logger.log_llm_decision(
            turn_number=decision_data["turn_number"],
            player_id=player_id,
            player_name=player_names[player_id],
            action_type=decision_data["chosen_action"]["action_type"],
            params=decision_data["chosen_action"]["params"],
            reasoning=decision_data["reasoning"],
            used_fallback=decision_data["used_fallback"],
            processing_time_ms=decision_data["processing_time_ms"],
            model_version=decision_data["model_version"],
            strategy=decision_data["strategy"],
            error=decision_data.get("error"),
            raw_response=decision_data.get("raw_response"),
        )
        # Buffer for database
        llm_decisions_buffer.append(decision_data)

    # Create agents
    agents = create_agents(
        num_players=num_players,
        agent_type=agent_type,
        player_names=player_names,
        llm_strategy=llm_strategy,
        roles=roles,
        decision_callback=llm_decision_callback,
    )

    # Create game
    config = GameConfig(seed=seed, time_limit_turns=max_turns)
    game = create_game(config, players)
    logger.flush_engine_events(game)

    start_time = time.time()

    # Game loop (same structure as play_monopoly.py)
    iteration = 0
    max_iterations = 10000
    auction_bidder_rotation = {}
    last_turn_number = -1

    while not game.game_over and iteration < max_iterations:
        iteration += 1
        current_player = game.get_current_player()

        # Flush any pending engine events
        logger.flush_engine_events(game)

        # Track turn changes
        if game.turn_number != last_turn_number:
            last_turn_number = game.turn_number

        # Get agent for current player
        agent = agents[current_player.player_id]

        # Actions within this turn
        actions_this_turn = 0
        max_actions_per_turn = 100

        while not game.game_over and actions_this_turn < max_actions_per_turn:
            # Handle active auction - cycle through bidders
            if game.active_auction and game.active_auction.active_bidders:
                auction_id = id(game.active_auction)

                active_bidders = sorted([
                    pid for pid in game.active_auction.active_bidders
                    if game.active_auction.can_player_bid(pid)
                ])

                if not active_bidders:
                    # No one can bid, pass all remaining
                    for pid in list(game.active_auction.active_bidders):
                        game.active_auction.pass_turn(pid)
                    continue

                if auction_id not in auction_bidder_rotation:
                    auction_bidder_rotation[auction_id] = 0

                bidder_idx = auction_bidder_rotation[auction_id] % len(active_bidders)
                auction_player_id = active_bidders[bidder_idx]

                legal_actions = get_legal_actions(game, auction_player_id)

                if legal_actions:
                    auction_agent = agents[auction_player_id]
                    action = auction_agent.choose_action(game, legal_actions)
                    if action:
                        apply_action(game, action, player_id=auction_player_id)
                        logger.flush_engine_events(game)
                    actions_this_turn += 1
                    auction_bidder_rotation[auction_id] += 1

                    if not game.active_auction:
                        if auction_id in auction_bidder_rotation:
                            del auction_bidder_rotation[auction_id]
                    continue
                else:
                    game.active_auction.pass_turn(auction_player_id)
                    auction_bidder_rotation[auction_id] += 1
                    continue

            # Normal turn flow
            legal_actions = get_legal_actions(game, current_player.player_id)

            if not legal_actions:
                # No legal actions - force end turn
                game.end_turn()
                break

            action = agent.choose_action(game, legal_actions)

            if action is None:
                break

            # Apply action
            success = apply_action(game, action)
            if success:
                logger.flush_engine_events(game)

            actions_this_turn += 1

            # End turn check
            if action.action_type == ActionType.END_TURN:
                break

            # Check if current player changed
            if game.get_current_player().player_id != current_player.player_id:
                break

        if actions_this_turn >= max_actions_per_turn:
            game.end_turn()

    # Final flush
    logger.flush_engine_events(game)

    # Save to database (all in one async call)
    if save_to_db and db_game_id:
        has_llm = agent_type == "llm" or (roles and "llm" in roles)
        config_dict = {
            "seed": seed,
            "max_turns": max_turns,
            "num_players": num_players,
            "agent_type": agent_type,
            "batch_game_id": game_id,
        }
        _save_game_to_db(
            db_game_id=db_game_id,
            config=config_dict,
            num_players=num_players,
            player_names=player_names,
            agent_type=agent_type,
            llm_strategy=llm_strategy if has_llm else None,
            game=game,
            logger=logger,
            llm_decisions=llm_decisions_buffer if llm_decisions_buffer else None,
        )

    elapsed = time.time() - start_time

    # Collect results
    has_llm = agent_type == "llm" or (roles and "llm" in roles)
    result = {
        "game_id": game_id,
        "db_game_id": db_game_id,
        "turns": game.turn_number,
        "winner": game.winner,
        "winner_name": player_names[game.winner] if game.winner is not None else None,
        "elapsed_seconds": round(elapsed, 2),
        "agent_type": agent_type,
        "roles": roles,
        "llm_strategy": llm_strategy if has_llm else None,
        "log_file": logger.log_file,
    }

    if verbose:
        winner_str = f"{result['winner_name']} (Player {result['winner']})" if result['winner'] is not None else "No winner"
        print(f"  Game {game_id}: {result['turns']} turns, Winner: {winner_str}, Time: {result['elapsed_seconds']}s")

    return result


def run_batch(
    num_games: int,
    num_players: int,
    agent_type: str,
    max_turns: int,
    llm_strategy: str = "balanced",
    roles: Optional[List[str]] = None,
    multi_strategy: bool = False,
    verbose: bool = True,
    workers: int = 1,
    save_to_db: bool = True,
) -> List[dict]:
    """Run multiple games and return all results.

    Args:
        workers: Number of parallel workers. 1 = sequential, >1 = parallel execution.
        save_to_db: Whether to save games to database.
    """
    results = []

    print(f"\n{'='*60}")
    print(f"Batch Game Runner")
    print(f"{'='*60}")
    print(f"Games to run: {num_games}")
    print(f"Players: {num_players}")
    print(f"Agent type: {agent_type}")
    print(f"Max turns: {max_turns}")
    print(f"Database: {'enabled' if save_to_db else 'disabled'}")
    if workers > 1:
        print(f"Parallel workers: {workers}")

    if agent_type == "llm":
        if multi_strategy:
            print(f"LLM strategy: ROTATING ({', '.join(LLM_STRATEGIES)})")
        else:
            print(f"LLM strategy: {llm_strategy}")

    if roles:
        print(f"Custom roles: {roles}")

    print(f"{'='*60}\n")

    start_time = time.time()

    # Build list of game configs
    game_configs = []
    for i in range(num_games):
        if multi_strategy and agent_type == "llm":
            current_strategy = LLM_STRATEGIES[i % len(LLM_STRATEGIES)]
        else:
            current_strategy = llm_strategy

        game_configs.append({
            "game_id": i + 1,
            "num_players": num_players,
            "agent_type": agent_type,
            "max_turns": max_turns,
            "llm_strategy": current_strategy,
            "roles": roles,
            "seed": None,
            "verbose": verbose if workers == 1 else False,  # Disable verbose in parallel mode
            "save_to_db": save_to_db,
        })

    if workers > 1:
        # Parallel execution
        print(f"Starting {num_games} games in parallel with {workers} workers...\n")
        completed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all games
            future_to_config = {
                executor.submit(run_single_game, **config): config
                for config in game_configs
            }

            # Collect results as they complete
            for future in as_completed(future_to_config):
                config = future_to_config[future]
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1

                    # Progress update
                    winner_str = f"{result['winner_name']}" if result['winner'] is not None else "No winner"
                    has_llm = agent_type == "llm" or (roles and "llm" in roles)
                    strategy_info = f" [{result.get('llm_strategy')}]" if has_llm else ""
                    print(f"[{completed}/{num_games}] Game {result['game_id']}{strategy_info}: "
                          f"{result['turns']} turns, Winner: {winner_str}, "
                          f"Time: {result['elapsed_seconds']}s")

                except Exception as e:
                    print(f"Game {config['game_id']} failed: {e}")
                    results.append({
                        "game_id": config["game_id"],
                        "turns": 0,
                        "winner": None,
                        "winner_name": None,
                        "elapsed_seconds": 0,
                        "agent_type": agent_type,
                        "llm_strategy": config.get("llm_strategy"),
                        "error": str(e),
                    })

        # Sort results by game_id for consistent output
        results.sort(key=lambda x: x["game_id"])
    else:
        # Sequential execution (original behavior)
        for config in game_configs:
            if verbose:
                strategy_info = f" [{config['llm_strategy']}]" if agent_type == "llm" else ""
                print(f"Running game {config['game_id']}/{num_games}{strategy_info}...")

            result = run_single_game(**config)
            results.append(result)

    total_time = time.time() - start_time

    # Summary
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE")
    print(f"{'='*60}")
    print(f"Total games: {num_games}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Avg time per game: {total_time/num_games:.2f}s")

    # Win statistics
    winners = {}
    for r in results:
        w = r.get("winner_name") or "No winner"
        winners[w] = winners.get(w, 0) + 1

    print(f"\nWin distribution:")
    for name, count in sorted(winners.items(), key=lambda x: -x[1]):
        pct = count / num_games * 100
        print(f"  {name}: {count} wins ({pct:.1f}%)")

    # Turn statistics
    turns = [r["turns"] for r in results]
    print(f"\nTurn statistics:")
    print(f"  Min: {min(turns)}")
    print(f"  Max: {max(turns)}")
    print(f"  Avg: {sum(turns)/len(turns):.1f}")

    # Strategy breakdown (for multi-strategy)
    if multi_strategy and agent_type == "llm":
        print(f"\nStrategy breakdown:")
        for strategy in LLM_STRATEGIES:
            strategy_results = [r for r in results if r.get("llm_strategy") == strategy]
            if strategy_results:
                strategy_wins = sum(1 for r in strategy_results if r["winner"] is not None)
                print(f"  {strategy}: {len(strategy_results)} games, {strategy_wins} completed with winner")

    print(f"{'='*60}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run multiple Monopoly games for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "-n", "--games",
        type=int,
        default=5,
        help="Number of games to run (default: 5)",
    )
    parser.add_argument(
        "-p", "--players",
        type=int,
        default=4,
        choices=range(2, 9),
        help="Number of players (default: 4)",
    )
    parser.add_argument(
        "-a", "--agent",
        type=str,
        default="greedy",
        choices=["random", "greedy", "llm"],
        help="Agent type for all players (default: greedy)",
    )
    parser.add_argument(
        "-t", "--max-turns",
        type=int,
        default=100,
        help="Maximum turns per game (default: 100)",
    )
    parser.add_argument(
        "-s", "--llm-strategy",
        type=str,
        default="balanced",
        choices=LLM_STRATEGIES,
        help="LLM strategy (default: balanced)",
    )
    parser.add_argument(
        "--roles",
        type=str,
        default=None,
        help="Custom roles (comma-separated, e.g., 'llm,greedy,greedy,random')",
    )
    parser.add_argument(
        "--multi-strategy",
        action="store_true",
        help="Rotate through all LLM strategies (aggressive, balanced, defensive)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode (less output)",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (default: 1 = sequential)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Disable database saving (only write to JSONL files)",
    )

    args = parser.parse_args()

    # Parse roles if provided
    roles = None
    if args.roles:
        roles = [r.strip().lower() for r in args.roles.split(",")]

    # Run batch
    run_batch(
        num_games=args.games,
        num_players=args.players,
        agent_type=args.agent,
        max_turns=args.max_turns,
        llm_strategy=args.llm_strategy,
        roles=roles,
        multi_strategy=args.multi_strategy,
        verbose=not args.quiet,
        workers=args.workers,
        save_to_db=not args.no_db,
    )


if __name__ == "__main__":
    main()
