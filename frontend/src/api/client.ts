// Use empty string for relative URLs (works with Vite proxy in dev)
// In production, set VITE_API_URL to the backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(response.status, `API Error: ${response.statusText}`)
  }

  return response.json()
}

export const api = {
  // Game Creation
  createGame: (data: import('../types/game').CreateGameRequest) => fetchApi<{ game_id: string }>('/games', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Game State
  getSnapshot: (gameId: string) =>
    fetchApi<import('../types/game').GameSnapshot>(`/games/${gameId}/snapshot`),

  getStatus: (gameId: string) =>
    fetchApi<import('../types/game').GameStatus>(`/games/${gameId}/status`),

  getLegalActions: (gameId: string, playerId?: number) => {
    const params = playerId !== undefined ? `?player_id=${playerId}` : ''
    return fetchApi<import('../types/game').LegalAction[]>(`/games/${gameId}/legal_actions${params}`)
  },

  // Player Actions
  submitAction: (gameId: string, data: {
    player_id: number
    action_type: string
    params: Record<string, unknown>
  }) => fetchApi<import('../types/game').ActionResult>(`/games/${gameId}/actions`, {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  // Game Control
  pauseGame: (gameId: string) =>
    fetchApi<void>(`/games/${gameId}/pause`, { method: 'POST' }),

  resumeGame: (gameId: string) =>
    fetchApi<void>(`/games/${gameId}/resume`, { method: 'POST' }),

  setSpeed: (gameId: string, tickMs: number) =>
    fetchApi<void>(`/games/${gameId}/speed`, {
      method: 'POST',
      body: JSON.stringify({ tick_ms: tickMs }),
    }),

  // Event Queries
  getTurns: (gameId: string) =>
    fetchApi<{ game_id: string; turns: import('../types/game').TurnInfo[] }>(
      `/games/${gameId}/turns`,
    ),

  getTurnEvents: (gameId: string, turnNumber: number) =>
    fetchApi<import('../types/game').TurnEventsResponse | import('../types/game').GameEvent[]>(
      `/games/${gameId}/turns/${turnNumber}`,
    ),

  // Historical Queries
  listGames: (params?: { limit?: number; offset?: number; status?: string }) => {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set('limit', String(params.limit))
    if (params?.offset) searchParams.set('offset', String(params.offset))
    if (params?.status) searchParams.set('status', params.status)
    const query = searchParams.toString()
    return fetchApi<import('../types/game').GameSummary[]>(`/api/games${query ? `?${query}` : ''}`)
  },

  getGameHistory: (gameId: string) =>
    fetchApi<{ game: import('../types/game').GameSummary; events: import('../types/game').GameEvent[] }>(`/api/games/${gameId}/history`),

  getGameStats: (gameId: string) =>
    fetchApi<import('../types/game').GameStats>(`/api/games/${gameId}/stats`),

  // Dashboard / analytics
  getDashboardEvents: (gameId: string, limit?: number) => {
    const query = typeof limit === 'number' ? `?limit=${limit}` : ''
    return fetchApi<import('../types/game').DashboardEvent[]>(
      `/api/dashboard/games/${gameId}/events${query}`,
    )
  },

  getLatestEvents: (gameId: string, limit: number = 20) => {
    return fetchApi<import('../types/game').DashboardEvent[]>(
      `/api/dashboard/games/${gameId}/latest_events?limit=${limit}`,
    )
  },

  getLlmDecisions: (gameId: string, playerId?: number, limit?: number) => {
    const params = new URLSearchParams()
    if (typeof playerId === 'number') params.set('player_id', String(playerId))
    if (typeof limit === 'number') params.set('limit', String(limit))
    const query = params.toString()
    const path = `/api/dashboard/games/${gameId}/llm_decisions${query ? `?${query}` : ''}`
    return fetchApi<import('../types/game').LlmDecision[]>(path)
  },

  // Global Analytics API
  getGlobalStats: () =>
    fetchApi<import('../types/game').GlobalStats>('/api/dashboard/global_stats'),

  getModelLeaderboard: () =>
    fetchApi<import('../types/game').ModelLeaderboardEntry[]>('/api/dashboard/model_leaderboard'),

  getLuckVsSkill: () =>
    fetchApi<import('../types/game').LuckVsSkillData[]>('/api/dashboard/luck_vs_skill'),

  getKillZones: () =>
    fetchApi<import('../types/game').KillZoneData[]>('/api/dashboard/kill_zones'),

  getGameDurationHistogram: (bucketSize: number = 20) =>
    fetchApi<import('../types/game').GameDurationBucket[]>(
      `/api/dashboard/game_duration_histogram?bucket_size=${bucketSize}`
    ),
}

export { ApiError }
