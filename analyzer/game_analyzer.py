"""
Monopoly Game Analyzer
Analysis of saved Monopoly games from JSONL files.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from datetime import datetime


@dataclass
class GameSummary:
    """Game summary data."""
    game_id: str
    num_players: int
    player_names: List[str]
    total_turns: int
    winner: Optional[str]
    winner_networth: int
    game_duration: str
    end_reason: str


@dataclass
class PlayerStats:
    """Player statistics."""
    player_id: int
    player_name: str
    final_networth: int
    final_cash: int
    properties_owned: List[str]
    total_properties: int
    total_houses: int
    total_hotels: int
    times_in_jail: int
    total_rent_paid: int
    total_rent_received: int
    bankrupted: bool


class MonopolyGameAnalyzer:
    """Monopoly game analyzer."""

    def __init__(self, jsonl_file: str):
        self.jsonl_file = Path(jsonl_file)
        self.events: List[Dict[str, Any]] = []
        self.game_summary: Optional[GameSummary] = None
        self.player_stats: Dict[int, PlayerStats] = {}
        self._load_events()
        self._analyze()

    def _load_events(self):
        """Load all events from JSONL file."""
        with open(self.jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                event = json.loads(line.strip())
                self.events.append(event)

    def _analyze(self):
        """Analyze all events and create statistics."""
        # Find game_start event
        game_start_event = next((e for e in self.events if e.get('event_type') == 'game_start'), None)
        if not game_start_event:
            raise ValueError("No game_start event found in file!")

        # Find game_end event
        game_end_event = next((e for e in self.events if e.get('event_type') == 'game_end'), None)

        # Initialize player statistics
        num_players = game_start_event.get('num_players', 0)
        player_names = game_start_event.get('player_names', [])

        for i in range(num_players):
            self.player_stats[i] = PlayerStats(
                player_id=i,
                player_name=player_names[i] if i < len(player_names) else f"Player {i}",
                final_networth=0,
                final_cash=0,
                properties_owned=[],
                total_properties=0,
                total_houses=0,
                total_hotels=0,
                times_in_jail=0,
                total_rent_paid=0,
                total_rent_received=0,
                bankrupted=False
            )

        # Analyze events
        for event in self.events:
            event_type = event.get('event_type')
            player_id = event.get('player_id')

            # Track rent payments
            if event_type == 'rent_payment':
                payer_id = event.get('payer_id')
                owner_id = event.get('owner_id')
                amount = event.get('amount', 0)

                if payer_id is not None:
                    self.player_stats[payer_id].total_rent_paid += amount
                if owner_id is not None:
                    self.player_stats[owner_id].total_rent_received += amount

            # Track jail visits
            if event_type == 'jail_enter' and player_id is not None:
                self.player_stats[player_id].times_in_jail += 1

            # Update player state (take LAST state for each player)
            if event_type == 'player_state_detailed' and player_id is not None:
                stats = self.player_stats[player_id]
                stats.final_cash = event.get('cash', 0)
                stats.final_networth = event.get('net_worth', 0)

                # Properties is a LIST, not a string
                properties = event.get('properties', [])
                if isinstance(properties, list):
                    stats.properties_owned = properties
                    stats.total_properties = len(properties)
                else:
                    stats.properties_owned = []
                    stats.total_properties = 0

                # Houses is a DICT {property_name: count}
                houses = event.get('houses', {})
                if isinstance(houses, dict):
                    stats.total_houses = sum(houses.values())
                else:
                    stats.total_houses = 0

                # Hotels is a LIST of property names with hotels
                hotels = event.get('hotels', [])
                if isinstance(hotels, list):
                    stats.total_hotels = len(hotels)
                else:
                    stats.total_hotels = 0

            # Track bankruptcy
            if event_type == 'bankruptcy' and player_id is not None:
                self.player_stats[player_id].bankrupted = True

        # Create game summary
        if game_end_event:
            winner_id = game_end_event.get('winner_id')
            winner_name = game_end_event.get('winner_name', 'Unknown')

            # Get winner's networth
            winner_networth = 0
            if winner_id is not None and winner_id in self.player_stats:
                winner_networth = self.player_stats[winner_id].final_networth

            self.game_summary = GameSummary(
                game_id=self.jsonl_file.stem,
                num_players=num_players,
                player_names=player_names,
                total_turns=game_end_event.get('turn_number', 0),
                winner=winner_name,
                winner_networth=winner_networth,
                game_duration=self._calculate_duration(),
                end_reason=game_end_event.get('reason', 'unknown')
            )
        else:
            # Game didn't finish
            last_turn = max((e.get('turn_number', 0) for e in self.events if 'turn_number' in e), default=0)
            self.game_summary = GameSummary(
                game_id=self.jsonl_file.stem,
                num_players=num_players,
                player_names=player_names,
                total_turns=last_turn,
                winner=None,
                winner_networth=0,
                game_duration=self._calculate_duration(),
                end_reason='incomplete'
            )

    def _calculate_duration(self) -> str:
        """Calculate game duration from timestamps."""
        if len(self.events) < 2:
            return "N/A"

        first_event = self.events[0]
        last_event = self.events[-1]

        try:
            start_time = datetime.fromisoformat(first_event['timestamp'])
            end_time = datetime.fromisoformat(last_event['timestamp'])
            duration = end_time - start_time

            seconds = duration.total_seconds()
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                return f"{seconds/60:.1f}min"
            else:
                return f"{seconds/3600:.1f}h"
        except:
            return "N/A"

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.get('event_type') == event_type]

    def get_events_by_player(self, player_id: int) -> List[Dict[str, Any]]:
        """Get all events for a specific player."""
        return [e for e in self.events if e.get('player_id') == player_id]

    def get_turn_events(self, turn_number: int) -> List[Dict[str, Any]]:
        """
        Get all events from a specific turn.
        Action events (dice_roll, move, etc.) DON'T HAVE turn_number,
        so we need to group by event_id between turn_start events.
        """
        # Find all turn_start events
        turn_starts = [(i, e) for i, e in enumerate(self.events)
                      if e.get('event_type') == 'turn_start']

        # Find turn_start for requested turn
        current_turn_idx = None
        next_turn_idx = None

        for i, (event_idx, event) in enumerate(turn_starts):
            if event.get('turn_number') == turn_number:
                current_turn_idx = event_idx
                # Find next turn_start (if exists)
                if i + 1 < len(turn_starts):
                    next_turn_idx = turn_starts[i + 1][0]
                break

        if current_turn_idx is None:
            return []

        # Get all events between current_turn_start and next_turn_start
        if next_turn_idx is not None:
            return self.events[current_turn_idx:next_turn_idx]
        else:
            # Last turn - take everything to the end
            return self.events[current_turn_idx:]

    def get_turn_player_name(self, turn_number: int) -> str:
        """Get the name of the player who played a specific turn."""
        turn_start = next((e for e in self.events
                          if e.get('event_type') == 'turn_start'
                          and e.get('turn_number') == turn_number), None)
        if turn_start:
            return turn_start.get('player_name', '?')
        return '?'
