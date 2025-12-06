#!/usr/bin/env python3
"""
Minimal CLI for simulating Monopoly games.

This script demonstrates the game engine by running simulated games with
simple AI players that make random or basic strategic decisions.
"""

import random
import argparse
from typing import List

from monopoly.game import create_game, ActionType
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.rules import get_legal_actions, apply_action, Action


class RandomAgent:
    """
    Simple AI that makes random legal moves.
    """

    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name
        self.rng = random.Random()

    def choose_action(self, game, legal_actions: List[Action]) -> Action:
        """
        Choose a random legal action with basic priorities to avoid infinite loops.
        Prioritize ROLL_DICE and END_TURN to keep the game moving.
        """
        # Strongly prefer ROLL_DICE to keep game moving
        for a in legal_actions:
            if a.action_type == ActionType.ROLL_DICE and self.rng.random() < 0.8:
                return a

        # Prefer END_TURN to avoid getting stuck
        for a in legal_actions:
            if a.action_type == ActionType.END_TURN and self.rng.random() < 0.7:
                return a

        # Otherwise choose randomly
        action = self.rng.choice(legal_actions)

        # Handle bidding - need to set a bid amount
        if action.action_type == ActionType.BID and game.active_auction:
            current_bid = game.active_auction.current_bid
            player_cash = game.players[self.player_id].cash

            # Randomly bid between current_bid + 1 and a reasonable max
            max_bid = min(player_cash, current_bid + 100)
            if max_bid > current_bid:
                action.params["amount"] = self.rng.randint(current_bid + 1, max_bid)
            else:
                # Can't afford to bid, choose PASS instead
                for a in legal_actions:
                    if a.action_type == ActionType.PASS_AUCTION:
                        return a

        return action


class GreedyAgent:
    """
    Simple AI that prefers buying properties and building when possible.
    """

    def __init__(self, player_id: int, name: str):
        self.player_id = player_id
        self.name = name

    def choose_action(self, game, legal_actions: List[Action]) -> Action:
        """Choose action with simple greedy strategy."""
        # Priority order
        priority = [
            ActionType.ROLL_DICE,
            ActionType.BUY_PROPERTY,
            ActionType.BUILD_HOTEL,
            ActionType.BUILD_HOUSE,
            ActionType.UNMORTGAGE_PROPERTY,
            ActionType.PAY_JAIL_FINE,
            ActionType.USE_JAIL_CARD,
            ActionType.BID,  # Will need smart bidding in real implementation
            ActionType.END_TURN,
            ActionType.DECLINE_PURCHASE,
            ActionType.PASS_AUCTION,
        ]

        for action_type in priority:
            for action in legal_actions:
                if action.action_type == action_type:
                    # For bidding, bid a reasonable amount
                    if action_type == ActionType.BID and game.active_auction:
                        current_bid = game.active_auction.current_bid
                        max_bid = game.players[self.player_id].cash // 2
                        if current_bid + 10 <= max_bid:
                            action.params["amount"] = current_bid + 10
                            return action
                        # Otherwise pass
                        continue
                    return action

        return legal_actions[0] if legal_actions else None


def print_game_state(game):
    """Print current game state."""
    print("\n" + "=" * 60)
    print(f"TURN {game.turn_number}")
    print("=" * 60)

    for player_id, player in sorted(game.players.items()):
        if player.is_bankrupt:
            status = "BANKRUPT"
        elif player.in_jail:
            status = f"IN JAIL ({player.jail_turns} turns)"
        else:
            space = game.board.get_space(player.position)
            status = f"at {space.name}"

        print(
            f"Player {player_id} ({player.name}): ${player.cash} | "
            f"{len(player.properties)} properties | {status}"
        )


def print_game_summary(game):
    """Print final game summary."""
    print("\n" + "=" * 60)
    print("GAME OVER")
    print("=" * 60)

    if game.winner is not None:
        winner = game.players[game.winner]
        print(f"\nWinner: {winner.name}")
        print(f"Final Cash: ${winner.cash}")
        print(f"Properties Owned: {len(winner.properties)}")

    print("\nFinal Standings:")
    for player_id, player in sorted(game.players.items()):
        worth = game._calculate_net_worth(player_id)
        status = "BANKRUPT" if player.is_bankrupt else f"${worth}"
        print(f"  {player.name}: {status}")

    print(f"\nTotal Turns: {game.turn_number}")


def simulate_game(
    num_players: int = 4,
    agent_type: str = "greedy",
    seed: int = None,
    verbose: bool = True,
    max_turns: int = None,
) -> None:
    """
    Simulate a complete game of Monopoly.

    Args:
        num_players: Number of players (2-8)
        agent_type: Type of AI ('random' or 'greedy')
        seed: Random seed for reproducibility
        verbose: Whether to print detailed output
        max_turns: Maximum number of turns (for time limit variant)
    """
    # Create players
    player_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Hank"]
    players = [Player(i, player_names[i]) for i in range(num_players)]

    # Create agents
    if agent_type == "random":
        agents = [RandomAgent(i, player_names[i]) for i in range(num_players)]
    else:
        agents = [GreedyAgent(i, player_names[i]) for i in range(num_players)]

    # Create game
    config = GameConfig(seed=seed, time_limit_turns=max_turns)
    game = create_game(config, players)

    if verbose:
        print(f"Starting game with {num_players} players using {agent_type} agents")
        print(f"Seed: {seed}")

    turn_count = 0
    max_game_turns = max_turns or 1000  # Safety limit

    while not game.game_over and turn_count < max_game_turns:
        current_player = game.get_current_player()

        if verbose and turn_count % 10 == 0:
            print_game_state(game)

        # Get agent
        agent = agents[current_player.player_id]

        # Play turn with action limit to prevent infinite loops
        actions_this_turn = 0
        max_actions_per_turn = 100  # Safety limit

        while not game.game_over and actions_this_turn < max_actions_per_turn:
            # Check if there's an active auction - if so, cycle through all active bidders
            if game.active_auction and game.active_auction.active_bidders:
                # Auction in progress - get next active bidder to act
                auction_player_id = min(game.active_auction.active_bidders)  # Simple: pick lowest ID
                legal_actions = get_legal_actions(game, auction_player_id)

                if legal_actions:
                    auction_agent = agents[auction_player_id]
                    action = auction_agent.choose_action(game, legal_actions)
                    if action:
                        apply_action(game, action)
                        actions_this_turn += 1
                        continue

            # Normal turn flow
            legal_actions = get_legal_actions(game, current_player.player_id)

            if not legal_actions:
                break

            # Agent chooses action
            action = agent.choose_action(game, legal_actions)

            if action is None:
                break

            # Apply action
            success = apply_action(game, action)
            actions_this_turn += 1

            if verbose and action.action_type in [
                ActionType.BUY_PROPERTY,
                ActionType.BUILD_HOUSE,
                ActionType.BUILD_HOTEL,
            ]:
                print(f"  {agent.name}: {action.action_type.value}")

            # End turn check
            if action.action_type == ActionType.END_TURN:
                break

            # Check if current player changed (bankruptcy, etc)
            if game.get_current_player().player_id != current_player.player_id:
                break

        if actions_this_turn >= max_actions_per_turn:
            # Force end turn if stuck
            if verbose:
                print(f"  WARNING: Player {current_player.player_id} hit action limit, forcing end turn")
            game.end_turn()

        turn_count += 1

    if verbose:
        print_game_summary(game)

    return game


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(description="Simulate a Monopoly game")
    parser.add_argument(
        "--players",
        type=int,
        default=4,
        choices=range(2, 9),
        help="Number of players (2-8)",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="greedy",
        choices=["random", "greedy"],
        help="AI agent type",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=None,
        help="Maximum number of turns (time limit variant)",
    )

    args = parser.parse_args()

    simulate_game(
        num_players=args.players,
        agent_type=args.agent,
        seed=args.seed,
        verbose=not args.quiet,
        max_turns=args.max_turns,
    )


if __name__ == "__main__":
    main()
