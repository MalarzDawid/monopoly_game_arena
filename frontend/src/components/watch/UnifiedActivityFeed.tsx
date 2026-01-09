import { useMemo, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import type { GameEvent, Player, LlmDecision } from '@/types/game'
import {
  Move,
  ShoppingCart,
  DollarSign,
  CreditCard,
  RotateCcw,
  Gavel,
  Home,
  AlertTriangle,
  Brain,
  ChevronDown,
  ChevronUp,
  Bot,
  Clock,
  Cpu,
} from 'lucide-react'

interface UnifiedActivityFeedProps {
  events: GameEvent[]
  decisions: LlmDecision[] | undefined
  players?: Player[]
  roles?: string[]
  loading?: boolean
  maxItems?: number
}

// Unified activity item that combines event with optional LLM reasoning
interface ActivityItem {
  id: string
  type: 'event'
  event: GameEvent
  llmDecision?: LlmDecision
  timestamp: Date
  turnNumber: number
  playerId?: number
}

function getPlayerName(players: Player[] | undefined, id: number | undefined): string {
  if (id === undefined || id === null) return 'System'
  const player = players?.find((p) => p.player_id === id)
  return player?.name ?? `P${id}`
}

function isLlmPlayer(playerId: number | undefined, roles: string[] | undefined): boolean {
  if (playerId === undefined || !roles) return false
  return roles[playerId] === 'llm'
}

function formatEventText(event: GameEvent, players?: Player[]): string {
  const type = (event.event_type || event.type || '').toString()
  const t = type.toLowerCase()

  if (event.text) return event.text

  const pidName = (id?: number) => getPlayerName(players, id)

  if (t === 'dice_roll') {
    const die1 = event.die1 as number | undefined
    const die2 = event.die2 as number | undefined
    const total = event.total as number | undefined
    const isDoubles = event.is_doubles as boolean | undefined
    if (die1 !== undefined && die2 !== undefined && total !== undefined) {
      return `${pidName(event.player_id as number | undefined)} rolled ${die1}+${die2}=${total}${
        isDoubles ? ' (doubles!)' : ''
      }`
    }
  } else if (t === 'move') {
    const fromPos = event.from_position as number | undefined
    const toPos = event.to_position as number | undefined
    const spaceName = (event.space_name as string | undefined) || ''
    if (fromPos !== undefined && toPos !== undefined) {
      return `${pidName(event.player_id as number | undefined)} moved to ${spaceName} (${toPos})`
    }
  } else if (t === 'purchase') {
    const property = (event.property_name as string | undefined) || 'property'
    const price = event.price as number | undefined
    if (price !== undefined) {
      return `${pidName(event.player_id as number | undefined)} purchased ${property} for $${price}`
    }
  } else if (t === 'rent_payment') {
    const amount = event.amount as number | undefined
    const prop = (event.property_name as string | undefined) || ''
    if (amount !== undefined) {
      return `${pidName(event.payer_id as number | undefined)} paid $${amount} rent to ${pidName(
        event.owner_id as number | undefined
      )}${prop ? ` for ${prop}` : ''}`
    }
  } else if (t === 'auction_start') {
    const property = (event.property_name as string | undefined) || 'property'
    return `Auction started for ${property}`
  } else if (t === 'auction_bid') {
    const property = (event.property_name as string | undefined) || ''
    const amount = event.bid_amount as number | undefined
    if (amount !== undefined) {
      return `${pidName(event.player_id as number | undefined)} bid $${amount}${property ? ` on ${property}` : ''}`
    }
  } else if (t === 'auction_pass') {
    const property = (event.property_name as string | undefined) || ''
    return `${pidName(event.player_id as number | undefined)} passed${property ? ` on ${property}` : ''}`
  } else if (t === 'auction_end') {
    const winner = event.winner_id as number | undefined
    const bid = event.winning_bid as number | undefined
    const property = (event.property_name as string | undefined) || 'property'
    if (winner !== undefined && bid !== undefined) {
      return `${pidName(winner)} won ${property} for $${bid}`
    }
  } else if (t === 'turn_start') {
    const turn = (event.turn_number as number | undefined) ?? (event.turn as number | undefined)
    return `Turn ${turn ?? ''} - ${pidName(event.player_id as number | undefined)}'s turn`
  } else if (t === 'go_to_jail') {
    return `${pidName(event.player_id as number | undefined)} went to jail`
  } else if (t === 'build_house') {
    const property = (event.property_name as string | undefined) || 'property'
    return `${pidName(event.player_id as number | undefined)} built a house on ${property}`
  } else if (t === 'build_hotel') {
    const property = (event.property_name as string | undefined) || 'property'
    return `${pidName(event.player_id as number | undefined)} built a hotel on ${property}`
  } else if (t === 'decline_purchase') {
    const property = (event.property_name as string | undefined) || 'property'
    return `${pidName(event.player_id as number | undefined)} declined to buy ${property}`
  } else if (t === 'end_turn') {
    return `${pidName(event.player_id as number | undefined)} ended their turn`
  }

  if (type) return type.replace(/_/g, ' ')
  return 'Event'
}

function getEventIcon(event: GameEvent) {
  const rawType = (event.event_type || event.type || '').toString()
  const type = rawType.toLowerCase()

  if (type === 'move') return Move
  if (type === 'purchase') return ShoppingCart
  if (type === 'rent_payment' || type === 'tax_payment' || type === 'payment' || type === 'transfer')
    return DollarSign
  if (type.startsWith('card')) return CreditCard
  if (type.startsWith('auction')) return Gavel
  if (type.startsWith('build')) return Home
  if (type === 'bankruptcy' || type === 'go_to_jail') return AlertTriangle
  return RotateCcw
}

function getEventBadgeVariant(event: GameEvent): 'secondary' | 'success' | 'warning' | 'default' | 'outline' | 'destructive' {
  const rawType = (event.event_type || event.type || '').toString()
  const type = rawType.toLowerCase()

  if (type === 'move' || type === 'dice_roll') return 'secondary'
  if (type === 'purchase' || type.startsWith('build')) return 'success'
  if (type.includes('payment') || type.includes('tax')) return 'warning'
  if (type.startsWith('auction')) return 'default'
  if (type === 'bankruptcy') return 'destructive'
  return 'outline'
}

function LlmReasoningPanel({ decision, playerName }: { decision: LlmDecision; playerName: string }) {
  const [expanded, setExpanded] = useState(false)
  const reasoning = decision.reasoning || ''
  const isLong = reasoning.length > 150
  const displayReasoning = expanded ? reasoning : reasoning.slice(0, 150) + (isLong ? '...' : '')

  return (
    <div className="mt-2 ml-10 p-3 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-950/30 dark:to-blue-950/30 rounded-lg border border-purple-200 dark:border-purple-800">
      <div className="flex items-center gap-2 mb-2">
        <Brain className="h-4 w-4 text-purple-600 dark:text-purple-400" />
        <span className="text-xs font-medium text-purple-700 dark:text-purple-300">
          {playerName}'s Reasoning
        </span>
        <Badge variant="outline" className="text-xs ml-auto">
          {decision.chosen_action.action_type}
        </Badge>
      </div>

      <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
        {displayReasoning}
      </p>

      {isLong && (
        <Button
          variant="ghost"
          size="sm"
          className="mt-1 h-6 text-xs text-purple-600 hover:text-purple-700 p-0"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3 mr-1" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3 mr-1" />
              Show more
            </>
          )}
        </Button>
      )}

      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
        {decision.model_version && (
          <span className="flex items-center gap-1">
            <Cpu className="h-3 w-3" />
            {decision.model_version}
          </span>
        )}
        {decision.processing_time_ms !== null && decision.processing_time_ms !== undefined && (
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {decision.processing_time_ms}ms
          </span>
        )}
      </div>
    </div>
  )
}

export function UnifiedActivityFeed({
  events,
  decisions,
  players,
  roles,
  loading = false,
  maxItems = 15,
}: UnifiedActivityFeedProps) {
  // Merge events with LLM decisions
  const activityItems = useMemo(() => {
    const safeEvents = Array.isArray(events) ? events : []
    const safeDecisions = Array.isArray(decisions) ? decisions : []

    // Create a map of decisions by turn_number + player_id for quick lookup
    const decisionMap = new Map<string, LlmDecision>()
    safeDecisions.forEach((d) => {
      // Create key based on action type to match with events
      const key = `${d.turn_number}-${d.player_id}-${d.chosen_action.action_type.toLowerCase()}`
      decisionMap.set(key, d)
    })

    // Map events to activity items with optional LLM decisions
    const items: ActivityItem[] = safeEvents.map((event, index) => {
      const turnNumber = (event.turn_number as number) ?? (event.turn as number) ?? 0
      const playerId = event.player_id as number | undefined
      const eventType = (event.event_type || event.type || '').toString().toLowerCase()

      // Try to find matching LLM decision
      let llmDecision: LlmDecision | undefined
      if (playerId !== undefined && isLlmPlayer(playerId, roles)) {
        // Try exact match first
        const exactKey = `${turnNumber}-${playerId}-${eventType}`
        llmDecision = decisionMap.get(exactKey)

        // If no exact match, try mapping event types to action types
        if (!llmDecision) {
          const actionTypeMap: Record<string, string> = {
            'purchase': 'buy_property',
            'dice_roll': 'roll_dice',
            'auction_bid': 'bid',
            'auction_pass': 'pass_auction',
            'build_house': 'build_house',
            'build_hotel': 'build_hotel',
            'decline_purchase': 'decline_purchase',
          }
          const mappedAction = actionTypeMap[eventType]
          if (mappedAction) {
            const mappedKey = `${turnNumber}-${playerId}-${mappedAction}`
            llmDecision = decisionMap.get(mappedKey)
          }
        }
      }

      return {
        id: `event-${index}-${turnNumber}`,
        type: 'event' as const,
        event,
        llmDecision,
        timestamp: event.timestamp ? new Date(event.timestamp) : new Date(),
        turnNumber,
        playerId,
      }
    })

    return items.slice(-maxItems).reverse()
  }, [events, decisions, roles, maxItems])

  if (loading && activityItems.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Bot className="h-4 w-4" />
            Activity Feed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="space-y-2">
                <div className="flex items-start gap-3">
                  <Skeleton className="h-8 w-8 rounded-full" />
                  <div className="flex-1 space-y-1">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                {i % 2 === 0 && (
                  <div className="ml-10">
                    <Skeleton className="h-16 w-full rounded-lg" />
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Bot className="h-4 w-4" />
          Activity Feed
          {decisions && decisions.length > 0 && (
            <Badge variant="secondary" className="ml-auto text-xs">
              <Brain className="h-3 w-3 mr-1" />
              {decisions.length} LLM decisions
            </Badge>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
          {activityItems.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No activity yet
            </p>
          ) : (
            activityItems.map((item) => {
              const Icon = getEventIcon(item.event)
              const badgeVariant = getEventBadgeVariant(item.event)
              const eventType = (item.event.event_type || item.event.type || '').toString()
              const isLlm = item.playerId !== undefined && isLlmPlayer(item.playerId, roles)
              const playerName = getPlayerName(players, item.playerId)

              return (
                <div key={item.id} className="group">
                  {/* Event row */}
                  <div className="flex items-start gap-3">
                    <div className={`rounded-full p-2 ${isLlm ? 'bg-purple-100 dark:bg-purple-900/50' : 'bg-muted'}`}>
                      {isLlm ? (
                        <Brain className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                      ) : (
                        <Icon className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm">
                        {formatEventText(item.event, players)}
                      </p>
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <Badge variant={badgeVariant} className="text-xs">
                          {eventType ? eventType.toUpperCase().replace(/_/g, ' ') : 'EVENT'}
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          Turn {item.turnNumber}
                        </Badge>
                        {isLlm && (
                          <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300">
                            <Bot className="h-3 w-3 mr-1" />
                            LLM
                          </Badge>
                        )}
                        {item.event.timestamp && (
                          <span className="text-xs text-muted-foreground">
                            {new Date(item.event.timestamp).toLocaleTimeString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* LLM Reasoning panel (if available) */}
                  {item.llmDecision && (
                    <LlmReasoningPanel decision={item.llmDecision} playerName={playerName} />
                  )}
                </div>
              )
            })
          )}
        </div>
      </CardContent>
    </Card>
  )
}
