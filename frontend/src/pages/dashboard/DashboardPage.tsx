import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  GlobalStatsGrid,
  ModelLeaderboardTable,
  LuckVsSkillScatter,
  KillZonesChart,
  GameDurationHistogram,
} from '@/components/dashboard'
import {
  useGlobalStats,
  useModelLeaderboard,
  useLuckVsSkill,
  useKillZones,
  useGameDurationHistogram,
} from '@/hooks/useGameData'
import { RefreshCw, AlertCircle, BarChart3 } from 'lucide-react'

export function DashboardPage() {
  // Fetch global analytics data
  const {
    data: globalStats,
    isLoading: statsLoading,
    error: statsError,
    refetch: refetchStats,
  } = useGlobalStats()

  const {
    data: leaderboard,
    isLoading: leaderboardLoading,
    refetch: refetchLeaderboard,
  } = useModelLeaderboard()

  const {
    data: luckVsSkill,
    isLoading: luckLoading,
    refetch: refetchLuck,
  } = useLuckVsSkill()

  const {
    data: killZones,
    isLoading: killZonesLoading,
    refetch: refetchKillZones,
  } = useKillZones()

  const {
    data: durationHistogram,
    isLoading: durationLoading,
    refetch: refetchDuration,
  } = useGameDurationHistogram(20)

  const isLoading = statsLoading || leaderboardLoading || luckLoading || killZonesLoading || durationLoading
  const hasError = statsError

  const handleRefreshAll = () => {
    refetchStats()
    refetchLeaderboard()
    refetchLuck()
    refetchKillZones()
    refetchDuration()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <BarChart3 className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
            <p className="text-muted-foreground">
              Global statistics across all games in the database
            </p>
          </div>
        </div>

        <Button
          variant="outline"
          onClick={handleRefreshAll}
          disabled={isLoading}
          className="gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh Data
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

      {/* Section 1: Global KPI Cards */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Overview</h2>
        <GlobalStatsGrid stats={globalStats} loading={statsLoading} />
      </section>

      {/* Section 2: Model Leaderboard */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Model Performance</h2>
        <ModelLeaderboardTable data={leaderboard} loading={leaderboardLoading} />
      </section>

      {/* Section 3: Analytics Charts Row 1 */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Analytical Insights</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <LuckVsSkillScatter data={luckVsSkill} loading={luckLoading} />
          <KillZonesChart data={killZones} loading={killZonesLoading} />
        </div>
      </section>

      {/* Section 4: Game Duration Histogram */}
      <section>
        <GameDurationHistogram data={durationHistogram} loading={durationLoading} />
      </section>

      {/* Footer Info */}
      <Card className="bg-muted/30">
        <CardContent className="p-4">
          <p className="text-sm text-muted-foreground text-center">
            Data is aggregated from all finished games in the database.
            Statistics update when you click "Refresh Data".
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
