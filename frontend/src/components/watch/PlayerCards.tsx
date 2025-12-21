import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency } from '@/lib/utils'
import type { Player, PlayerLiveStats } from '@/types/game'
import { Home, CreditCard, Lock, ArrowDownToLine, ArrowUpToLine } from 'lucide-react'

interface PlayerCardsProps {
  players: Player[]
  currentPlayerId: number
  stats?: PlayerLiveStats[]
  loading?: boolean
}

const PLAYER_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-amber-500',
  'bg-red-500',
  'bg-violet-500',
  'bg-pink-500',
  'bg-teal-500',
  'bg-orange-500',
]

function findStats(stats: PlayerLiveStats[] | undefined, playerId: number): PlayerLiveStats | undefined {
  return stats?.find((s) => s.player_id === playerId)
}

export function PlayerCards({ players, currentPlayerId, stats, loading = false }: PlayerCardsProps) {
  if (loading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="space-y-1">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-16" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {players.map((player) => (
        <Card
          key={player.player_id}
          className={player.player_id === currentPlayerId ? 'ring-2 ring-primary' : ''}
        >
          <CardContent className="p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={`h-10 w-10 rounded-full ${
                    PLAYER_COLORS[player.player_id % PLAYER_COLORS.length]
                  } flex items-center justify-center text-white font-bold`}
                >
                  {player.player_id + 1}
                </div>
                <div>
                  <p className="font-medium">{player.name}</p>
                  <p className="text-lg font-bold">{formatCurrency(player.cash)}</p>
                </div>
              </div>

              {player.player_id === currentPlayerId && (
                <Badge variant="default" className="text-xs">
                  Active
                </Badge>
              )}
              </div>

            <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Home className="h-3.5 w-3.5" />
                <span>{player.properties.length}</span>
              </div>
              {(() => {
                const s = findStats(stats, player.player_id)
                if (!s) return null
                return (
                  <>
                    <div className="flex items-center gap-1">
                      <ArrowDownToLine className="h-3.5 w-3.5" />
                      <span>-{formatCurrency(s.total_paid)}</span>
                    </div>
                    {s.total_received > 0 && (
                      <div className="flex items-center gap-1">
                        <ArrowUpToLine className="h-3.5 w-3.5" />
                        <span>{formatCurrency(s.total_received)}</span>
                      </div>
                    )}
                  </>
                )
              })()}
              {player.jail_cards > 0 && (
                <div className="flex items-center gap-1">
                  <CreditCard className="h-3.5 w-3.5" />
                  <span>{player.jail_cards}</span>
                </div>
              )}
              {player.in_jail && (
                <Badge variant="destructive" className="text-xs">
                  <Lock className="h-3 w-3 mr-1" />
                  Jail ({player.jail_turns})
                </Badge>
              )}
              {player.is_bankrupt && (
                <Badge variant="outline" className="text-xs text-muted-foreground">
                  Bankrupt
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
