// Property owned by a player (from snapshot)
export interface PlayerProperty {
  position: number
  name: string
  houses: number
  mortgaged: boolean
  color_group?: string
}

// Player from /games/{id}/snapshot
export interface Player {
  player_id: number
  name: string
  cash: number
  position: number
  in_jail: boolean
  jail_turns: number
  jail_cards: number
  is_bankrupt: boolean
  properties: PlayerProperty[]
}

// Auction state
export interface Auction {
  property_position: number
  property_name: string
  current_bid: number
  high_bidder: number | null
  active_bidders: number[]
  is_complete: boolean
}

// Game snapshot from /games/{id}/snapshot
export interface GameSnapshot {
  turn_number: number
  current_player_id: number
  players: Player[]
  bank: {
    houses_available: number
    hotels_available: number
  }
  auction: Auction | null
  decks: {
    chance: { cards_remaining: number; discard_count: number; held_count: number }
    community_chest: { cards_remaining: number; discard_count: number; held_count: number }
  }
}

// Game status from /games/{id}/status
export interface GameStatus {
  game_id: string
  turn_number: number
  current_player_id: number
  phase: string
  actors: number[]
  roles: string[]
  llm_strategies?: string[]
  game_over: boolean
  paused: boolean
  tick_ms: number
}

// Turn events response from /games/{id}/turns/{turn}
export interface TurnEventsResponse {
  game_id: string
  turn_number: number
  events: GameEvent[]
}

export interface GameEvent {
  // Canonical event type from backend (e.g. "move", "rent_payment")
  event_type?: string
  // Legacy / mock type (e.g. "MOVE", "RENT_PAID")
  type?: string
  // Optional human-readable text (mostly for mocks)
  text?: string
  player_id?: number
  amount?: number
  position?: number
  timestamp?: string
  [key: string]: unknown
}

export interface TurnInfo {
  turn_number: number
  from_index: number
  to_index: number
}

// Historical game from /api/games
export interface PlayerSummary {
  player_id: number
  name: string
  agent_type: string
  is_winner: boolean
  final_cash: number | null
  final_net_worth: number | null
}

export interface GameSummary {
  game_id: string
  status: string
  total_turns: number
  created_at: string | null
  started_at: string | null
  finished_at: string | null
  winner_id: number | null
  config: Record<string, unknown>
  players: PlayerSummary[]
}

export interface GameListResponse {
  games: GameSummary[]
  limit: number
  offset: number
}

// Game stats from /api/games/{id}/stats
export interface GameStatsResponse {
  game_id: string
  status: string
  total_turns: number
  statistics: Record<string, unknown>
}

// Raw events from /api/dashboard/games/{id}/events
export interface DashboardEvent {
  sequence_number: number
  turn_number: number
  event_type: string
  timestamp: string
  payload: Record<string, unknown>
  actor_player_id: number | null
}

// For dashboard display (mock or computed)
export interface GameStats {
  total_turns: number
  total_transactions: number
  total_rent_paid: number
  total_properties_bought: number
  bankruptcies: number
  cash_in_circulation: number
  avg_rent_per_turn: number
  player_stats: PlayerStats[]
}

export interface PlayerStats {
  player_id: number
  name: string
  total_rent_collected: number
  total_rent_paid: number
  properties_owned: number
  houses_built: number
  net_worth: number
  roi: number
}

// Live per-player stats computed on the watch page from events
export interface PlayerLiveStats {
  player_id: number
  total_paid: number
  total_received: number
  rent_paid: number
  rent_received: number
  taxes_paid: number
  houses_built: number
  hotels_built: number
}

// LLM decision logs from /api/dashboard/games/{id}/llm_decisions
export interface LlmDecision {
  sequence_number: number
  turn_number: number
  player_id: number
  timestamp: string
  reasoning: string
  chosen_action: {
    action_type: string
    params: Record<string, unknown>
  }
  strategy_description?: string | null
  processing_time_ms?: number | null
  model_version?: string | null
}

export interface LegalAction {
  action_type: string
  params: Record<string, unknown>
}

export interface LegalActionsResponse {
  game_id: string
  player_id: number | null
  actions: LegalAction[]
}

export interface ActionResult {
  accepted: boolean
  reason: string | null
}

export interface CreateGameRequest {
  players: number
  agent: string
  roles?: string[]
  seed?: number
  max_turns?: number
  tick_ms?: number
  llm_strategy?: string
  llm_strategies?: string[]  // Per-player LLM strategies
}

export interface CreateGameResponse {
  game_id: string
}

// ============================================================================
// GLOBAL ANALYTICS TYPES
// ============================================================================

// Global KPI stats from /api/dashboard/global_stats
export interface GlobalStats {
  total_games: number
  total_turns: number
  finished_games: number
  total_bankruptcies: number
  total_properties_bought: number
  total_transactions: number
}

// Model leaderboard entry from /api/dashboard/model_leaderboard
export interface ModelLeaderboardEntry {
  model_name: string
  strategy_profile: string
  games_played: number
  wins: number
  bankruptcies: number
  win_rate: number | null
  avg_net_worth: number
  avg_final_cash: number
}

// Luck vs Skill data point from /api/dashboard/luck_vs_skill
export interface LuckVsSkillData {
  model_name: string
  avg_dice_roll: number
  win_rate: number | null
  total_games: number
}

// Kill zone data from /api/dashboard/kill_zones
export interface KillZoneData {
  position: number
  property_name: string
  bankruptcy_count: number
}

// Game duration histogram bucket from /api/dashboard/game_duration_histogram
export interface GameDurationBucket {
  bucket_start: number
  bucket_end: number
  bucket_label: string
  game_count: number
}

// Strategy-Property correlation data for heatmap
export interface StrategyPropertyData {
  strategy: string
  position: number
  color_group: string
  purchase_count: number
}

// LLM Reasoning entry from llm_decisions table
export interface LLMReasoningEntry {
  id: string
  game_uuid: string
  player_id: number
  turn_number: number
  reasoning: string
  strategy_description: string | null
  model_version: string | null
  timestamp: string
  player_name: string
  strategy: string
  model_name: string
  action_type: string
  chosen_action: Record<string, unknown>
}

// Paginated response for LLM reasonings
export interface LLMReasoningsResponse {
  items: LLMReasoningEntry[]
  total: number
  limit: number
  offset: number
}
