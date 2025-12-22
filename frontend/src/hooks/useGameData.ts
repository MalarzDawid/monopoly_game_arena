import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { mockSnapshot, mockStats, mockEvents, mockHistoricalGames, mockCashHistory } from '../api/mocks'
import type { DashboardEvent, PlayerLiveStats, LlmDecision, TurnInfo, Player } from '../types/game'
import type { NetWorthDataPoint } from '../components/watch/NetWorthOverTimeChart'
import type { AssetAllocationData } from '../components/watch/AssetAllocationChart'
import type { ColorGroupRentData } from '../components/watch/RentHeatmap'

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

// Property values for net worth calculation
const PROPERTY_BASE_VALUES: Record<number, number> = {
  1: 60, 3: 60, // Brown
  6: 100, 8: 100, 9: 120, // Light Blue
  11: 140, 13: 140, 14: 160, // Pink
  16: 180, 18: 180, 19: 200, // Orange
  21: 220, 23: 220, 24: 240, // Red
  26: 260, 27: 260, 29: 280, // Yellow
  31: 300, 32: 300, 34: 320, // Green
  37: 350, 39: 400, // Dark Blue
  5: 200, 15: 200, 25: 200, 35: 200, // Railroads
  12: 150, 28: 150, // Utilities
}

// House/Hotel cost per property group
const HOUSE_COSTS: Record<number, number> = {
  1: 50, 3: 50, // Brown
  6: 50, 8: 50, 9: 50, // Light Blue
  11: 100, 13: 100, 14: 100, // Pink
  16: 100, 18: 100, 19: 100, // Orange
  21: 150, 23: 150, 24: 150, // Red
  26: 150, 27: 150, 29: 150, // Yellow
  31: 200, 32: 200, 34: 200, // Green
  37: 200, 39: 200, // Dark Blue
}

// Color group mapping for rent aggregation
const POSITION_TO_COLOR_GROUP: Record<number, string> = {
  1: 'brown', 3: 'brown',
  6: 'light_blue', 8: 'light_blue', 9: 'light_blue',
  11: 'pink', 13: 'pink', 14: 'pink',
  16: 'orange', 18: 'orange', 19: 'orange',
  21: 'red', 23: 'red', 24: 'red',
  26: 'yellow', 27: 'yellow', 29: 'yellow',
  31: 'green', 32: 'green', 34: 'green',
  37: 'dark_blue', 39: 'dark_blue',
  5: 'railroad', 15: 'railroad', 25: 'railroad', 35: 'railroad',
  12: 'utility', 28: 'utility',
}

const COLOR_GROUP_INFO: Record<string, { displayName: string; baseColor: string; properties: string[] }> = {
  brown: { displayName: 'Brown', baseColor: '#8B4513', properties: ['Mediterranean', 'Baltic'] },
  light_blue: { displayName: 'Light Blue', baseColor: '#87CEEB', properties: ['Oriental', 'Vermont', 'Connecticut'] },
  pink: { displayName: 'Pink', baseColor: '#FF69B4', properties: ['St. Charles', 'States', 'Virginia'] },
  orange: { displayName: 'Orange', baseColor: '#FFA500', properties: ['St. James', 'Tennessee', 'New York'] },
  red: { displayName: 'Red', baseColor: '#FF0000', properties: ['Kentucky', 'Indiana', 'Illinois'] },
  yellow: { displayName: 'Yellow', baseColor: '#FFFF00', properties: ['Atlantic', 'Ventnor', 'Marvin Gardens'] },
  green: { displayName: 'Green', baseColor: '#228B22', properties: ['Pacific', 'North Carolina', 'Pennsylvania'] },
  dark_blue: { displayName: 'Dark Blue', baseColor: '#0000FF', properties: ['Park Place', 'Boardwalk'] },
  railroad: { displayName: 'Railroads', baseColor: '#1f2937', properties: ['Reading', 'Pennsylvania', 'B&O', 'Short Line'] },
  utility: { displayName: 'Utilities', baseColor: '#6b7280', properties: ['Electric Co', 'Water Works'] },
}

// Calculate asset allocation from current player state
export function useAssetAllocation(players: Player[] | undefined): AssetAllocationData[] {
  if (!players || players.length === 0) {
    return []
  }

  return players.map((player) => {
    let propertyValue = 0
    let houseValue = 0

    player.properties.forEach((prop) => {
      // Add base property value
      propertyValue += PROPERTY_BASE_VALUES[prop.position] ?? 0

      // Add house/hotel value (hotels count as 5 houses)
      const houseCost = HOUSE_COSTS[prop.position] ?? 0
      houseValue += houseCost * prop.houses
    })

    return {
      playerId: player.player_id,
      name: player.name,
      cash: player.cash,
      propertyValue,
      houseValue,
    }
  })
}

// Net worth history computed from events
export function useNetWorthHistory(gameId: string | null, players: Player[] | undefined, limit: number = 2000) {
  return useQuery({
    queryKey: ['netWorthHistory', gameId, limit],
    queryFn: async (): Promise<NetWorthDataPoint[]> => {
      if (!gameId || !players || players.length === 0) {
        return []
      }

      try {
        const events = await api.getDashboardEvents(gameId, limit)

        // Group events by turn
        const eventsByTurn = new Map<number, DashboardEvent[]>()
        events.forEach((ev) => {
          const existing = eventsByTurn.get(ev.turn_number) || []
          existing.push(ev)
          eventsByTurn.set(ev.turn_number, existing)
        })

        // Initialize player states
        const playerStates = new Map<number, {
          cash: number
          properties: Map<number, number> // position -> houses
        }>()

        players.forEach((p) => {
          playerStates.set(p.player_id, {
            cash: 1500, // Starting cash
            properties: new Map(),
          })
        })

        const dataPoints: NetWorthDataPoint[] = []
        const sortedTurns = Array.from(eventsByTurn.keys()).sort((a, b) => a - b)

        // Process events turn by turn
        sortedTurns.forEach((turn) => {
          const turnEvents = eventsByTurn.get(turn) || []

          turnEvents.forEach((ev) => {
            const payload = ev.payload || {}
            const type = ev.event_type

            if (type === 'purchase' || type === 'property_purchase') {
              const playerId = ev.actor_player_id ?? (payload.player_id as number | undefined)
              const position = payload.position as number | undefined
              const price = (payload.price as number | undefined) ?? (payload.amount as number | undefined) ?? 0

              if (playerId !== undefined && position !== undefined) {
                const state = playerStates.get(playerId)
                if (state) {
                  state.cash -= price
                  state.properties.set(position, 0)
                }
              }
            } else if (type === 'rent_payment') {
              const payerId = (payload.payer_id as number | undefined) ?? ev.actor_player_id ?? undefined
              const ownerId = payload.owner_id as number | undefined
              const amount = (payload.amount as number | undefined) ?? 0

              if (payerId !== undefined) {
                const state = playerStates.get(payerId)
                if (state) state.cash -= amount
              }
              if (ownerId !== undefined) {
                const state = playerStates.get(ownerId)
                if (state) state.cash += amount
              }
            } else if (type === 'go_income' || type === 'pass_go') {
              const playerId = ev.actor_player_id ?? (payload.player_id as number | undefined) ?? undefined
              const amount = (payload.amount as number | undefined) ?? 200

              if (playerId !== undefined) {
                const state = playerStates.get(playerId)
                if (state) state.cash += amount
              }
            } else if (type === 'tax_payment') {
              const playerId = ev.actor_player_id ?? undefined
              const amount = (payload.amount as number | undefined) ?? 0

              if (playerId !== undefined) {
                const state = playerStates.get(playerId)
                if (state) state.cash -= amount
              }
            } else if (type === 'build_house' || type === 'build_hotel') {
              const playerId = ev.actor_player_id ?? undefined
              const position = payload.position as number | undefined
              const cost = (payload.cost as number | undefined) ?? 0

              if (playerId !== undefined && position !== undefined) {
                const state = playerStates.get(playerId)
                if (state) {
                  state.cash -= cost
                  const currentHouses = state.properties.get(position) ?? 0
                  state.properties.set(position, type === 'build_hotel' ? 5 : currentHouses + 1)
                }
              }
            }
          })

          // Record data point for this turn
          const turnPlayers = players.map((p) => {
            const state = playerStates.get(p.player_id)
            if (!state) {
              return {
                playerId: p.player_id,
                name: p.name,
                cash: 0,
                propertyValue: 0,
                houseValue: 0,
                netWorth: 0,
              }
            }

            let propertyValue = 0
            let houseValue = 0

            state.properties.forEach((houses, position) => {
              propertyValue += PROPERTY_BASE_VALUES[position] ?? 0
              const houseCost = HOUSE_COSTS[position] ?? 0
              houseValue += houseCost * houses
            })

            return {
              playerId: p.player_id,
              name: p.name,
              cash: Math.max(0, state.cash),
              propertyValue,
              houseValue,
              netWorth: Math.max(0, state.cash) + propertyValue + houseValue,
            }
          })

          dataPoints.push({
            turn,
            players: turnPlayers,
          })
        })

        // Sample data if too many points
        if (dataPoints.length > 50) {
          const step = Math.ceil(dataPoints.length / 50)
          return dataPoints.filter((_, i) => i % step === 0 || i === dataPoints.length - 1)
        }

        return dataPoints
      } catch (e) {
        console.warn('Failed to load net worth history', e)
        return []
      }
    },
    enabled: !!gameId && !!players && players.length > 0,
    refetchInterval: POLLING_INTERVAL * 2,
    retry: false,
  })
}

// Rent by color group computed from events
export function useRentByColorGroup(gameId: string | null, limit: number = 2000) {
  return useQuery({
    queryKey: ['rentByColorGroup', gameId, limit],
    queryFn: async (): Promise<ColorGroupRentData[]> => {
      if (!gameId) {
        return []
      }

      try {
        const events = await api.getDashboardEvents(gameId, limit)

        // Aggregate rent by color group
        const rentByGroup = new Map<string, { totalRent: number; rentCount: number }>()

        // Initialize all groups
        Object.keys(COLOR_GROUP_INFO).forEach((group) => {
          rentByGroup.set(group, { totalRent: 0, rentCount: 0 })
        })

        events.forEach((ev) => {
          if (ev.event_type === 'rent_payment') {
            const payload = ev.payload || {}
            const position = payload.position as number | undefined
            const amount = (payload.amount as number | undefined) ?? 0

            if (position !== undefined) {
              const colorGroup = POSITION_TO_COLOR_GROUP[position]
              if (colorGroup) {
                const current = rentByGroup.get(colorGroup) || { totalRent: 0, rentCount: 0 }
                current.totalRent += amount
                current.rentCount += 1
                rentByGroup.set(colorGroup, current)
              }
            }
          }
        })

        // Convert to array format
        return Array.from(rentByGroup.entries()).map(([group, data]) => {
          const info = COLOR_GROUP_INFO[group]
          return {
            colorGroup: group,
            displayName: info?.displayName ?? group,
            totalRent: data.totalRent,
            rentCount: data.rentCount,
            properties: info?.properties ?? [],
            baseColor: info?.baseColor ?? '#888888',
          }
        }).sort((a, b) => b.totalRent - a.totalRent)
      } catch (e) {
        console.warn('Failed to load rent by color group', e)
        return []
      }
    },
    enabled: !!gameId,
    refetchInterval: POLLING_INTERVAL * 2,
    retry: false,
  })
}
