import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  GlobalStatsGrid,
  ModelLeaderboardTable,
  LuckVsSkillScatter,
  KillZonesChart,
  GameDurationHistogram,
  StrategyPropertyHeatmap,
  LLMReasoningList,
} from '@/components/dashboard'
import {
  useGlobalStats,
  useModelLeaderboard,
  useLuckVsSkill,
  useKillZones,
  useGameDurationHistogram,
  useStrategyPropertyCorrelation,
  useLLMReasonings,
} from '@/hooks/useGameData'
import { api } from '@/api/client'
import type { LLMReasoningEntry } from '@/types/game'
import { RefreshCw, AlertCircle, BarChart3 } from 'lucide-react'

const PAGE_SIZE = 50

export function DashboardPage() {
  // State for LLM reasoning search
  const [reasoningSearch, setReasoningSearch] = useState('')

  // Pagination state for LLM reasonings
  const [accumulatedReasonings, setAccumulatedReasonings] = useState<LLMReasoningEntry[]>([])
  const [loadingMore, setLoadingMore] = useState(false)

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

  const {
    data: strategyProperty,
    isLoading: strategyPropertyLoading,
    refetch: refetchStrategyProperty,
  } = useStrategyPropertyCorrelation()

  const {
    data: llmReasonings,
    isLoading: reasoningsLoading,
    refetch: refetchReasonings,
  } = useLLMReasonings({ limit: PAGE_SIZE, offset: 0, search: reasoningSearch || undefined })

  // Reset accumulated items when search changes or initial data loads
  useEffect(() => {
    if (llmReasonings?.items) {
      setAccumulatedReasonings(llmReasonings.items)
    }
  }, [llmReasonings?.items, reasoningSearch])

  // Handle Load More for LLM reasonings
  const handleLoadMoreReasonings = useCallback(async () => {
    if (loadingMore || !llmReasonings) return

    setLoadingMore(true)
    try {
      const newOffset = accumulatedReasonings.length
      const response = await api.getLLMReasonings({
        limit: PAGE_SIZE,
        offset: newOffset,
        search: reasoningSearch || undefined,
      })

      setAccumulatedReasonings((prev) => [...prev, ...response.items])
    } catch (error) {
      console.error('Failed to load more reasonings:', error)
    } finally {
      setLoadingMore(false)
    }
  }, [loadingMore, llmReasonings, accumulatedReasonings.length, reasoningSearch])

  // Handle search change - reset pagination
  const handleSearchChange = useCallback((search: string) => {
    setReasoningSearch(search)
    setAccumulatedReasonings([])
  }, [])

  const isLoading = statsLoading || leaderboardLoading || luckLoading || killZonesLoading || durationLoading || strategyPropertyLoading
  const hasError = statsError

  const handleRefreshAll = () => {
    refetchStats()
    refetchLeaderboard()
    refetchLuck()
    refetchKillZones()
    refetchDuration()
    refetchStrategyProperty()
    refetchReasonings()
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

      {/* Section 4: Game Duration & Strategy Correlation */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Game Patterns</h2>
        <div className="grid gap-6 lg:grid-cols-2">
          <GameDurationHistogram data={durationHistogram} loading={durationLoading} />
          <StrategyPropertyHeatmap data={strategyProperty} loading={strategyPropertyLoading} />
        </div>
      </section>

      {/* Section 5: LLM Decision Reasonings */}
      <section>
        <h2 className="text-lg font-semibold mb-4">LLM Decision Analysis</h2>
        <LLMReasoningList
          data={llmReasonings}
          loading={reasoningsLoading}
          onSearchChange={handleSearchChange}
          onLoadMore={handleLoadMoreReasonings}
          loadingMore={loadingMore}
          accumulatedItems={accumulatedReasonings.length > 0 ? accumulatedReasonings : undefined}
        />
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
