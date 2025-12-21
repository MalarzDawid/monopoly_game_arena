import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { KpiGrid, TimeSeriesChart, BarChart, PlayersTable } from '@/components/dashboard'
import { useGameStats, useCashHistory, useHistoricalGames } from '@/hooks/useGameData'
import { mockStats, mockCashHistory } from '@/api/mocks'
import { RefreshCw, AlertCircle } from 'lucide-react'

export function DashboardPage() {
  const [selectedGameId, setSelectedGameId] = useState<string | null>(null)

  // Fetch historical games
  const { data: games, isLoading: gamesLoading, error: gamesError, refetch: refetchGames } = useHistoricalGames({ limit: 10 })

  // Use first game if none selected
  const activeGameId = selectedGameId || (games && games.length > 0 ? games[0].game_id : null)

  // Fetch stats for selected game
  const { data: stats, isLoading: statsLoading, error: statsError } = useGameStats(activeGameId)
  const { data: cashHistory, isLoading: cashLoading } = useCashHistory(activeGameId)

  // Use mock data if API unavailable
  const displayStats = stats || mockStats
  const displayCashHistory = cashHistory || mockCashHistory

  const isLoading = gamesLoading || statsLoading
  const hasError = gamesError || statsError

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Real-time game analytics and player performance
          </p>
        </div>

        <Button variant="outline" size="icon" onClick={() => refetchGames()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Error Banner */}
      {hasError && (
        <Card className="border-yellow-200 bg-yellow-50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600" />
            <div>
              <p className="font-medium text-yellow-800">Using Demo Data</p>
              <p className="text-sm text-yellow-700">
                Could not connect to API. Displaying mock data for demonstration.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Game Selector */}
      {games && games.length > 0 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-4 overflow-x-auto pb-2">
              <span className="text-sm font-medium text-muted-foreground whitespace-nowrap">
                Select Game:
              </span>
              {games.slice(0, 5).map((game) => (
                <Button
                  key={game.game_id}
                  variant={activeGameId === game.game_id ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setSelectedGameId(game.game_id)}
                  className="whitespace-nowrap"
                >
                  {game.game_id.slice(0, 8)}...
                  <span className="ml-2 text-xs opacity-70">
                    {game.total_turns} turns
                  </span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Grid */}
      <KpiGrid stats={displayStats} loading={isLoading} />

      {/* Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <TimeSeriesChart
          title="Cash Over Time"
          data={displayCashHistory}
          playerNames={displayStats.player_stats.map((p) => p.name)}
          loading={cashLoading}
        />

        <BarChart
          title="Rent Collected by Player"
          data={displayStats.player_stats}
          dataKey="total_rent_collected"
          loading={statsLoading}
        />
      </div>

      {/* Additional Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        <BarChart
          title="Net Worth Comparison"
          data={displayStats.player_stats}
          dataKey="net_worth"
          loading={statsLoading}
        />

        <BarChart
          title="Properties Owned"
          data={displayStats.player_stats}
          dataKey="properties_owned"
          loading={statsLoading}
        />
      </div>

      {/* Players Table */}
      <PlayersTable data={displayStats.player_stats} loading={statsLoading} />

      {/* Recent Games */}
      {games && games.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">Recent Games</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {games.map((game) => (
                <div
                  key={game.game_id}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-muted/50 cursor-pointer"
                  onClick={() => setSelectedGameId(game.game_id)}
                >
                  <div>
                    <p className="font-medium">{game.game_id}</p>
                    <p className="text-sm text-muted-foreground">
                      {game.created_at ? new Date(game.created_at).toLocaleDateString() : 'N/A'} • {game.players.length} players
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium">{game.total_turns} turns</p>
                    <p className="text-sm text-muted-foreground capitalize">{game.status}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
