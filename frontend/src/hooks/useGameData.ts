import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { mockSnapshot, mockStats, mockEvents, mockHistoricalGames, mockCashHistory } from '../api/mocks'
import type { DashboardEvent, PlayerLiveStats, LlmDecision, TurnInfo } from '../types/game'

const POLLING_INTERVAL = 2000 // 2 seconds

export function useGameStatus(gameId: string | null) {
  return useQuery({
    queryKey: ['gameStatus', gameId],
    queryFn: () => api.getStatus(gameId!),
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL,
    retry: false,
  })
}

export function useGameSnapshot(gameId: string | null) {
  return useQuery({
    queryKey: ['gameSnapshot', gameId],
    queryFn: async () => {
      if (!gameId) throw new Error('No game ID')
      try {
        return await api.getSnapshot(gameId)
      } catch {
        console.warn('Using mock snapshot data')
        return mockSnapshot
      }
    },
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL,
    retry: false,
  })
}

export function useGameStats(gameId: string | null) {
  return useQuery({
    queryKey: ['gameStats', gameId],
    queryFn: async () => {
      if (!gameId) throw new Error('No game ID')
      try {
        return await api.getGameStats(gameId)
      } catch {
        console.warn('Using mock stats data')
        return mockStats
      }
    },
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL * 2,
    staleTime: 0,
    retry: false,
  })
}

export function useTurnEvents(gameId: string | null, turnNumber: number | null) {
  return useQuery({
    // Keep a stable key per game; inside we pick the best turn
    queryKey: ['turnEvents', gameId],
    queryFn: async () => {
      if (!gameId) throw new Error('No game ID')
      try {
        // First, discover available turns from /games/{id}/turns
        const turnsResponse = await api.getTurns(gameId)
        const turns: TurnInfo[] = Array.isArray((turnsResponse as any).turns)
          ? (turnsResponse as any).turns
          : (Array.isArray(turnsResponse) ? (turnsResponse as any as TurnInfo[]) : [])

        if (!turns.length) {
          console.warn('No turns available from API, using mock events')
          return mockEvents
        }

        const lastTurn = turns[turns.length - 1]?.turn_number
        // Prefer explicit turnNumber if it exists in the list; otherwise use latest
        const effectiveTurn =
          turnNumber !== null && turns.some((t) => t.turn_number === turnNumber)
            ? turnNumber
            : lastTurn

        if (effectiveTurn === null || effectiveTurn === undefined) {
          console.warn('No effective turn resolved, using mock events')
          return mockEvents
        }

        const response = await api.getTurnEvents(gameId, effectiveTurn)
        // API may return { events: [...] } or just [...] - handle both
        if (Array.isArray(response)) {
          return response
        }
        if (response && typeof response === 'object' && 'events' in response) {
          return (response as { events: typeof mockEvents }).events
        }
        console.warn('Unexpected turn events format, using mock events')
        return mockEvents
      } catch (e) {
        console.warn('Using mock events due to error loading turn events', e)
        return mockEvents
      }
    },
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL,
    retry: false,
  })
}

export function useHistoricalGames(params?: { limit?: number; offset?: number; status?: string }) {
  return useQuery({
    queryKey: ['historicalGames', params],
    queryFn: async () => {
      try {
        return await api.listGames(params)
      } catch {
        console.warn('Using mock historical games')
        return mockHistoricalGames
      }
    },
    retry: false,
  })
}

export function useLegalActions(gameId: string | null, playerId?: number) {
  return useQuery({
    queryKey: ['legalActions', gameId, playerId],
    queryFn: () => api.getLegalActions(gameId!, playerId),
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL,
    retry: false,
  })
}

export function useCreateGame() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.createGame,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['historicalGames'] })
    },
  })
}

export function useSubmitAction(gameId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: { player_id: number; action_type: string; params: Record<string, unknown> }) =>
      api.submitAction(gameId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gameSnapshot', gameId] })
      queryClient.invalidateQueries({ queryKey: ['gameStatus', gameId] })
      queryClient.invalidateQueries({ queryKey: ['legalActions', gameId] })
    },
  })
}

export function useGameControl(gameId: string) {
  const queryClient = useQueryClient()

  const pause = useMutation({
    mutationFn: () => api.pauseGame(gameId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gameStatus', gameId] })
    },
  })

  const resume = useMutation({
    mutationFn: () => api.resumeGame(gameId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gameStatus', gameId] })
    },
  })

  const setSpeed = useMutation({
    mutationFn: (tickMs: number) => api.setSpeed(gameId, tickMs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gameStatus', gameId] })
    },
  })

  return { pause, resume, setSpeed }
}

// Mock data for charts when API unavailable
export function useCashHistory(gameId: string | null) {
  return useQuery({
    queryKey: ['cashHistory', gameId],
    queryFn: async () => {
      // In real implementation, this would aggregate from events
      // Generate different mock data based on gameId for demo variety
      if (!gameId) return mockCashHistory

      // Use gameId hash to seed slightly different data
      const seed = gameId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0)
      const turns = 30 + (seed % 50)
      const data = []
      const baseCash = [1500, 1500, 1500, 1500]
      const currentCash = [...baseCash]

      for (let turn = 0; turn <= turns; turn++) {
        data.push({
          turn,
          players: currentCash.map(c => Math.round(c)),
        })
        for (let i = 0; i < currentCash.length; i++) {
          const change = Math.floor(Math.sin(seed + turn + i) * 150) + Math.floor(Math.random() * 50 - 25)
          currentCash[i] = Math.max(0, currentCash[i] + change)
        }
      }
      return data
    },
    enabled: !!gameId,
    staleTime: 0,
  })
}

// Live per-player stats computed from persisted events
export function useLivePlayerStats(gameId: string | null, limit: number = 1000) {
  return useQuery({
    queryKey: ['livePlayerStats', gameId, limit],
    queryFn: async () => {
      if (!gameId) throw new Error('No game ID')
      try {
        const events = await api.getDashboardEvents(gameId, limit)
        const statsMap = new Map<number, PlayerLiveStats>()

        const ensureStats = (playerId: number): PlayerLiveStats => {
          let stats = statsMap.get(playerId)
          if (!stats) {
            stats = {
              player_id: playerId,
              total_paid: 0,
              total_received: 0,
              rent_paid: 0,
              rent_received: 0,
              taxes_paid: 0,
              houses_built: 0,
              hotels_built: 0,
            }
            statsMap.set(playerId, stats)
          }
          return stats
        }

        const toNumber = (value: unknown): number => {
          if (typeof value === 'number') return value
          if (typeof value === 'string') {
            const n = Number(value)
            return Number.isFinite(n) ? n : 0
          }
          return 0
        }

        events.forEach((ev: DashboardEvent) => {
          const type = ev.event_type
          const payload = ev.payload || {}

          if (type === 'rent_payment') {
            const payerId = (payload.payer_id as number | undefined) ?? ev.actor_player_id ?? undefined
            const ownerId = payload.owner_id as number | undefined
            const amount = toNumber(payload.amount)
            if (payerId !== undefined) {
              const s = ensureStats(payerId)
              s.total_paid += amount
              s.rent_paid += amount
            }
            if (ownerId !== undefined) {
              const s = ensureStats(ownerId)
              s.total_received += amount
              s.rent_received += amount
            }
          } else if (type === 'tax_payment') {
            const payerId = ev.actor_player_id ?? undefined
            const amount = toNumber(payload.amount)
            if (payerId !== undefined) {
              const s = ensureStats(payerId)
              s.total_paid += amount
              s.taxes_paid += amount
            }
          } else if (type === 'payment' || type === 'transfer') {
            const fromId = (payload.from as number | undefined) ?? ev.actor_player_id ?? undefined
            const toId = payload.to as number | undefined
            const amount = toNumber(payload.amount)
            if (fromId !== undefined) {
              const s = ensureStats(fromId)
              s.total_paid += amount
            }
            if (toId !== undefined) {
              const s = ensureStats(toId)
              s.total_received += amount
            }
          } else if (type === 'build_house') {
            const pid = ev.actor_player_id ?? undefined
            if (pid !== undefined) {
              const s = ensureStats(pid)
              s.houses_built += 1
            }
          } else if (type === 'build_hotel') {
            const pid = ev.actor_player_id ?? undefined
            if (pid !== undefined) {
              const s = ensureStats(pid)
              s.hotels_built += 1
            }
          }
        })

        return Array.from(statsMap.values()).sort((a, b) => a.player_id - b.player_id)
      } catch (e) {
        console.warn('Failed to load live player stats, returning empty stats', e)
        return [] as PlayerLiveStats[]
      }
    },
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL,
    retry: false,
  })
}

// LLM decision feed for a game (optionally filtered by player)
export function useLlmDecisions(gameId: string | null, playerId?: number, limit: number = 100) {
  return useQuery({
    queryKey: ['llmDecisions', gameId, playerId, limit],
    queryFn: async () => {
      if (!gameId) throw new Error('No game ID')
      try {
        return await api.getLlmDecisions(gameId, playerId, limit)
      } catch (e) {
        console.warn('Failed to load LLM decisions, returning empty list', e)
        return [] as LlmDecision[]
      }
    },
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL,
    retry: false,
  })
}
