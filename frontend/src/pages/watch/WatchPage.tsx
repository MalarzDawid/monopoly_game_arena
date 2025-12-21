import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { MonopolyBoardSvg, EventFeed, PlayerCards, GameControls, LlmDecisionFeed } from '@/components/watch'
import {
  useGameSnapshot,
  useGameStatus,
  useTurnEvents,
  useGameControl,
  useCreateGame,
  useLivePlayerStats,
  useLlmDecisions,
  useHistoricalGames,
} from '@/hooks/useGameData'
import { mockSnapshot, mockEvents } from '@/api/mocks'
import { Plus, Gamepad2, AlertCircle } from 'lucide-react'

type AgentRole = 'greedy' | 'random' | 'llm'
type LlmStrategy = 'aggressive' | 'balanced' | 'defensive'

interface CreateConfig {
  players: number
  maxTurns: number
  tickMs: number
  llmStrategy: LlmStrategy
  roles: AgentRole[]
}

export function WatchPage() {
  const [gameId, setGameId] = useState<string | null>(null)
  const [inputGameId, setInputGameId] = useState('')
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createConfig, setCreateConfig] = useState<CreateConfig>({
    players: 4,
    maxTurns: 100,
    tickMs: 500,
    llmStrategy: 'balanced',
    roles: ['greedy', 'greedy', 'greedy', 'greedy'],
  })

  // Fetch game data
  const { data: snapshot, isLoading: snapshotLoading, error: snapshotError } = useGameSnapshot(gameId)
  const { data: status, isLoading: statusLoading, error: statusError } = useGameStatus(gameId)
  const { data: events, isLoading: eventsLoading } = useTurnEvents(
    gameId,
    status?.turn_number ?? null
  )
  const { data: liveStats } = useLivePlayerStats(gameId)
  const { data: llmDecisions, isLoading: llmLoading } = useLlmDecisions(gameId)
  const { data: recentGames } = useHistoricalGames({ limit: 10 })

  // Game control mutations
  const { pause, resume, setSpeed } = useGameControl(gameId || '')
  const createGame = useCreateGame()

  // Use mock data if API unavailable
  const displaySnapshot = snapshot || mockSnapshot
  const displayEvents = events || mockEvents
  const displayStatus = status || {
    game_id: 'demo',
    turn_number: 42,
    current_player_id: 1,
    phase: 'turn',
    actors: [1],
    roles: ['greedy', 'greedy', 'greedy', 'greedy'],
    game_over: false,
    paused: false,
    tick_ms: 500,
  }

  const hasError = snapshotError || statusError
  const isLoading = snapshotLoading || statusLoading

  const handleCreateGame = async () => {
    try {
      const roles =
        createConfig.roles.length > 0
          ? createConfig.roles.slice(0, createConfig.players)
          : Array.from({ length: createConfig.players }, () => 'greedy' as AgentRole)

      const agent: AgentRole = roles[0] ?? 'greedy'

      const result = await createGame.mutateAsync({
        players: createConfig.players,
        agent,
        roles,
        max_turns: createConfig.maxTurns,
        tick_ms: createConfig.tickMs,
        llm_strategy: createConfig.llmStrategy,
      })
      setGameId(result.game_id)
      setShowCreateForm(false)
    } catch (error) {
      console.error('Failed to create game:', error)
    }
  }

  const handleJoinGame = () => {
    if (inputGameId.trim()) {
      setGameId(inputGameId.trim())
      setInputGameId('')
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Watch Game</h1>
          <p className="text-muted-foreground">
            {gameId ? `Watching game: ${gameId}` : 'Create or join a game to watch'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Input
            placeholder="Enter game ID..."
            value={inputGameId}
            onChange={(e) => setInputGameId(e.target.value)}
            className="w-48"
            onKeyDown={(e) => e.key === 'Enter' && handleJoinGame()}
          />
          <Button variant="outline" onClick={handleJoinGame}>
            Join
          </Button>
          <Button onClick={() => setShowCreateForm(!showCreateForm)}>
            <Plus className="h-4 w-4 mr-1" />
            New Game
          </Button>
        </div>
      </div>

      {/* Create Game Form */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Gamepad2 className="h-4 w-4" />
              Create New Game
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <label className="text-sm font-medium">Players</label>
                <Select
                  value={String(createConfig.players)}
                  onValueChange={(v) =>
                    setCreateConfig((prev) => {
                      const players = Number(v)
                      const roles = [...prev.roles]
                      if (roles.length < players) {
                        for (let i = roles.length; i < players; i += 1) {
                          roles.push('greedy')
                        }
                      } else if (roles.length > players) {
                        roles.length = players
                      }
                      return { ...prev, players, roles }
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2, 3, 4, 5, 6, 7, 8].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n} Players
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium">Max Turns</label>
                <Input
                  type="number"
                  value={createConfig.maxTurns}
                  onChange={(e) =>
                    setCreateConfig({
                      ...createConfig,
                      maxTurns: Number(e.target.value),
                    })
                  }
                />
              </div>

              <div>
                <label className="text-sm font-medium">Tick (ms)</label>
                <Input
                  type="number"
                  value={createConfig.tickMs}
                  onChange={(e) =>
                    setCreateConfig({
                      ...createConfig,
                      tickMs: Number(e.target.value),
                    })
                  }
                />
              </div>
            </div>

            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div>
                <label className="text-sm font-medium">LLM Strategy</label>
                <Select
                  value={createConfig.llmStrategy}
                  onValueChange={(v) =>
                    setCreateConfig((prev) => ({ ...prev, llmStrategy: v as LlmStrategy }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="aggressive">Aggressive</SelectItem>
                    <SelectItem value="balanced">Balanced</SelectItem>
                    <SelectItem value="defensive">Defensive</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm font-medium">Player Roles</label>
                <div className="mt-2 space-y-2">
                  {Array.from({ length: createConfig.players }).map((_, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <span className="text-xs text-muted-foreground w-16">
                        Player {index + 1}
                      </span>
                      <Select
                        value={createConfig.roles[index] ?? 'greedy'}
                        onValueChange={(v) =>
                          setCreateConfig((prev) => {
                            const roles = [...prev.roles]
                            roles[index] = v as AgentRole
                            return { ...prev, roles }
                          })
                        }
                      >
                        <SelectTrigger className="h-8 w-28">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="greedy">Greedy</SelectItem>
                          <SelectItem value="random">Random</SelectItem>
                          <SelectItem value="llm">LLM</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" onClick={() => setShowCreateForm(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateGame} disabled={createGame.isPending}>
                {createGame.isPending ? 'Creating...' : 'Create Game'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active / recent games */}
      {!showCreateForm && (!gameId || hasError) && (recentGames && recentGames.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">Recent Games</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentGames.map((g) => (
                <div key={g.game_id} className="flex items-center justify-between text-sm">
                  <div>
                    <div className="font-medium">{g.game_id}</div>
                    <div className="text-xs text-muted-foreground">
                      {g.status} · {g.total_turns} turns
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setGameId(g.game_id)
                      setShowCreateForm(false)
                      setInputGameId('')
                    }}
                  >
                    Join
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Banner */}
      {hasError && gameId && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <p className="font-medium text-yellow-800">Using Demo Data</p>
              <p className="text-sm text-yellow-700">
                Could not connect to game. Displaying mock data for demonstration.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Game Controls */}
      {(gameId || hasError) && (
        <GameControls
          paused={displayStatus.paused}
          tickMs={displayStatus.tick_ms}
          turnNumber={displayStatus.turn_number}
          phase={displayStatus.phase}
          gameOver={displayStatus.game_over}
          onPause={() => pause.mutate()}
          onResume={() => resume.mutate()}
          onSpeedChange={(tickMs) => setSpeed.mutate(tickMs)}
        />
      )}

      {/* Player Cards */}
      {(gameId || hasError) && (
        <PlayerCards
          players={displaySnapshot.players}
          currentPlayerId={displaySnapshot.current_player_id}
          stats={liveStats}
          loading={isLoading}
        />
      )}

      {/* Main Content */}
      {(gameId || hasError) && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Board */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-medium">Game Board</CardTitle>
            </CardHeader>
            <CardContent>
              <MonopolyBoardSvg
                players={displaySnapshot.players}
                currentPlayerId={displaySnapshot.current_player_id}
              />
            </CardContent>
          </Card>

          {/* Feeds */}
          <div className="space-y-4">
            <EventFeed
              events={displayEvents}
              players={displaySnapshot.players}
              loading={eventsLoading}
            />
            <LlmDecisionFeed
              decisions={llmDecisions}
              players={displaySnapshot.players}
              loading={llmLoading}
            />
          </div>
        </div>
      )}

      {/* Empty State */}
      {!gameId && !hasError && !showCreateForm && (
        <Card className="p-12">
          <div className="text-center">
            <Gamepad2 className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Game Selected</h3>
            <p className="text-muted-foreground mb-4">
              Create a new game or enter an existing game ID to start watching
            </p>
            <Button onClick={() => setShowCreateForm(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Create New Game
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
