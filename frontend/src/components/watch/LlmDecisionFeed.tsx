import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { LlmDecision, Player } from '@/types/game'

interface LlmDecisionFeedProps {
  decisions: LlmDecision[] | undefined
  players?: Player[]
  loading?: boolean
  maxItems?: number
}

function getPlayerName(players: Player[] | undefined, id: number): string {
  const player = players?.find((p) => p.player_id === id)
  return player?.name ?? `P${id}`
}

export function LlmDecisionFeed({
  decisions,
  players,
  loading = false,
  maxItems = 20,
}: LlmDecisionFeedProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">LLM Decisions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-full" />
                <Skeleton className="h-3 w-3/4" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const list = (decisions || []).slice(-maxItems).reverse()

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">LLM Decisions</CardTitle>
      </CardHeader>
      <CardContent>
        {list.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No LLM decisions yet
          </p>
        ) : (
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
            {list.map((d) => {
              const ts = d.timestamp ? new Date(d.timestamp) : null
              const reasoningPreview =
                d.reasoning.length > 220 ? `${d.reasoning.slice(0, 220)}…` : d.reasoning

              return (
                <div key={d.sequence_number} className="space-y-1">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        P{d.player_id + 1} · {getPlayerName(players, d.player_id)}
                      </Badge>
                      <Badge variant="secondary" className="text-xs">
                        Turn {d.turn_number}
                      </Badge>
                    </div>
                    {ts && (
                      <span className="text-xs text-muted-foreground">
                        {ts.toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="font-medium">{d.chosen_action.action_type}</span>
                    {d.processing_time_ms !== null && d.processing_time_ms !== undefined && (
                      <span>· {d.processing_time_ms} ms</span>
                    )}
                    {d.model_version && <span>· {d.model_version}</span>}
                  </div>
                  <p className="text-xs whitespace-pre-wrap">{reasoningPreview}</p>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

