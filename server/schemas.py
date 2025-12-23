from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlayerSummary(BaseModel):
    player_id: int
    name: str
    agent_type: str
    is_winner: bool
    final_cash: Optional[int] = None
    final_net_worth: Optional[int] = None


class GameSummary(BaseModel):
    game_id: str
    status: str
    total_turns: int
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    winner_id: Optional[int] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    players: List[PlayerSummary] = Field(default_factory=list)


class GameListResponse(BaseModel):
    games: List[GameSummary]
    limit: int
    offset: int


class GameEventDTO(BaseModel):
    sequence_number: int
    turn_number: int
    event_type: str
    timestamp: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    actor_player_id: Optional[int] = None


class GameHistoryResponse(BaseModel):
    game: GameSummary
    events: List[GameEventDTO]
    total_events: int


class GameStatsResponse(BaseModel):
    game_id: str
    status: str
    total_turns: int
    statistics: Dict[str, Any]
