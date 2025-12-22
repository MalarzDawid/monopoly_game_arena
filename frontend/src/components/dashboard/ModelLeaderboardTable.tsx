import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import type { ModelLeaderboardEntry } from '@/types/game'
import { Trophy, TrendingUp, TrendingDown, ArrowUpDown } from 'lucide-react'

interface ModelLeaderboardTableProps {
  data: ModelLeaderboardEntry[] | undefined
  loading?: boolean
}

type SortKey = 'win_rate' | 'games_played' | 'avg_net_worth' | 'bankruptcies'
type SortOrder = 'asc' | 'desc'

function getStrategyBadgeVariant(strategy: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  const lower = strategy.toLowerCase()
  if (lower === 'aggressive') return 'destructive'
  if (lower === 'defensive') return 'secondary'
  if (lower === 'balanced') return 'default'
  return 'outline'
}

export function ModelLeaderboardTable({ data, loading = false }: ModelLeaderboardTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('win_rate')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortOrder('desc')
    }
  }

  const sortedData = [...(data || [])].sort((a, b) => {
    const aVal = Number(a[sortKey]) || 0
    const bVal = Number(b[sortKey]) || 0
    return sortOrder === 'asc' ? aVal - bVal : bVal - aVal
  })

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Model Leaderboard</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Model Leaderboard</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-8">
            No game data available yet. Play some games to see the leaderboard.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Trophy className="h-5 w-5 text-yellow-500" />
          Model Leaderboard
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="pb-3 font-medium">#</th>
                <th className="pb-3 font-medium">Model / Agent</th>
                <th className="pb-3 font-medium">Strategy</th>
                <th className="pb-3 font-medium">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium hover:bg-transparent"
                    onClick={() => handleSort('win_rate')}
                  >
                    Win Rate
                    <ArrowUpDown className="ml-1 h-3 w-3" />
                  </Button>
                </th>
                <th className="pb-3 font-medium">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium hover:bg-transparent"
                    onClick={() => handleSort('games_played')}
                  >
                    Games
                    <ArrowUpDown className="ml-1 h-3 w-3" />
                  </Button>
                </th>
                <th className="pb-3 font-medium">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium hover:bg-transparent"
                    onClick={() => handleSort('avg_net_worth')}
                  >
                    Avg Net Worth
                    <ArrowUpDown className="ml-1 h-3 w-3" />
                  </Button>
                </th>
                <th className="pb-3 font-medium">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-auto p-0 font-medium hover:bg-transparent"
                    onClick={() => handleSort('bankruptcies')}
                  >
                    Bankruptcies
                    <ArrowUpDown className="ml-1 h-3 w-3" />
                  </Button>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedData.map((entry, index) => {
                const isLlm = !['greedy', 'random', 'human'].includes(entry.model_name.toLowerCase())
                const winRate = Number(entry.win_rate) || 0

                return (
                  <tr
                    key={`${entry.model_name}-${entry.strategy_profile}`}
                    className="border-b last:border-0 hover:bg-muted/50"
                  >
                    <td className="py-3">
                      {index === 0 && sortKey === 'win_rate' && sortOrder === 'desc' ? (
                        <Trophy className="h-4 w-4 text-yellow-500" />
                      ) : (
                        <span className="text-muted-foreground">{index + 1}</span>
                      )}
                    </td>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <span className={isLlm ? 'font-medium text-blue-600' : 'font-medium'}>
                          {entry.model_name}
                        </span>
                        {isLlm && (
                          <Badge variant="outline" className="text-xs">LLM</Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3">
                      <Badge variant={getStrategyBadgeVariant(entry.strategy_profile)}>
                        {entry.strategy_profile}
                      </Badge>
                    </td>
                    <td className="py-3">
                      <div className="flex items-center gap-1">
                        {winRate >= 50 ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : winRate >= 25 ? (
                          <span className="w-4" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                        <span className={winRate >= 50 ? 'text-green-600 font-medium' : winRate < 25 ? 'text-red-600' : ''}>
                          {winRate.toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {entry.games_played}
                      <span className="text-xs ml-1">({entry.wins}W)</span>
                    </td>
                    <td className="py-3">
                      ${(entry.avg_net_worth ?? 0).toLocaleString()}
                    </td>
                    <td className="py-3">
                      <span className={entry.bankruptcies > 5 ? 'text-red-600' : ''}>
                        {entry.bankruptcies}
                      </span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
