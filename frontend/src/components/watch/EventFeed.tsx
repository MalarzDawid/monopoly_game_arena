import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { GameEvent, Player } from '@/types/game'
import {
  Move,
  ShoppingCart,
  DollarSign,
  CreditCard,
  RotateCcw,
  Gavel,
  Home,
  AlertTriangle,
} from 'lucide-react'

interface EventFeedProps {
  events: GameEvent[]
  players?: Player[]
  loading?: boolean
  maxItems?: number
}

function getPlayerName(players: Player[] | undefined, id: number | undefined): string {
  if (id === undefined || id === null) return 'System'
  const player = players?.find((p) => p.player_id === id)
  return player?.name ?? `P${id}`
}

function formatEventText(event: GameEvent, players?: Player[]): string {
  const type = (event.event_type || event.type || '').toString()
  const t = type.toLowerCase()

  // Prefer explicit text if provided (e.g. mocks)
  if (event.text) return event.text

  const pidName = (id?: number) => getPlayerName(players, id)

  if (t === 'dice_roll') {
    const die1 = event.die1 as number | undefined
    const die2 = event.die2 as number | undefined
    const total = event.total as number | undefined
    const isDoubles = event.is_doubles as boolean | undefined
    if (die1 !== undefined && die2 !== undefined && total !== undefined) {
      return `🎲 ${pidName(event.player_id as number | undefined)}: ${die1}+${die2}=${total}${
        isDoubles ? ' (dbl)' : ''
      }`
    }
  } else if (t === 'move') {
    const fromPos = event.from_position as number | undefined
    const toPos = event.to_position as number | undefined
    const spaceName = (event.space_name as string | undefined) || ''
    if (fromPos !== undefined && toPos !== undefined) {
      return `🚶 ${pidName(event.player_id as number | undefined)}: ${fromPos}→${toPos} (${spaceName})`
    }
  } else if (t === 'purchase') {
    const property = (event.property_name as string | undefined) || 'property'
    const price = event.price as number | undefined
    if (price !== undefined) {
      return `💰 ${pidName(event.player_id as number | undefined)} buys ${property} for $${price}`
    }
  } else if (t === 'rent_payment') {
    const amount = event.amount as number | undefined
    const prop = (event.property_name as string | undefined) || ''
    if (amount !== undefined) {
      return `💸 ${pidName(event.payer_id as number | undefined)} → ${pidName(
        event.owner_id as number | undefined
      )} $${amount} ${prop ? `(${prop})` : ''}`
    }
  } else if (t === 'auction_start') {
    const property = (event.property_name as string | undefined) || 'Auction'
    return `🔨 Auction: ${property}`
  } else if (t === 'auction_bid') {
    const property = (event.property_name as string | undefined) || 'Auction'
    const amount = event.bid_amount as number | undefined
    if (amount !== undefined) {
      return `🤑 ${pidName(event.player_id as number | undefined)} bids $${amount} on ${property}`
    }
    return `🤑 ${pidName(event.player_id as number | undefined)} bids on ${property}`
  } else if (t === 'auction_pass') {
    const property = (event.property_name as string | undefined) || 'Auction'
    return `⏭️ ${pidName(event.player_id as number | undefined)} passes on ${property}`
  } else if (t === 'auction_end') {
    const winner = event.winner_id as number | undefined
    const bid = event.winning_bid as number | undefined
    if (winner !== undefined && bid !== undefined) {
      return `🔨 Winner: ${pidName(winner)} for $${bid}`
    }
  } else if (t === 'turn_start') {
    const turn = (event.turn_number as number | undefined) ?? (event.turn as number | undefined)
    return `▶️ Turn ${turn ?? ''} (${pidName(event.player_id as number | undefined)})`
  } else if (t === 'go_to_jail') {
    return `🚔 ${pidName(event.player_id as number | undefined)} to jail`
  } else if (t === 'build_house') {
    const property = (event.property_name as string | undefined) || 'property'
    return `🏠 ${pidName(event.player_id as number | undefined)} builds on ${property}`
  } else if (t === 'build_hotel') {
    const property = (event.property_name as string | undefined) || 'property'
    return `🏨 ${pidName(event.player_id as number | undefined)} builds hotel on ${property}`
  }

  // Fallbacks
  if (type) return type
  return 'Event'
}

function getEventMeta(event: GameEvent) {
  const rawType = (event.event_type || event.type || '').toString()
  const type = rawType.toLowerCase()

  let Icon = RotateCcw
  if (type === 'move') Icon = Move
  else if (type === 'purchase') Icon = ShoppingCart
  else if (type === 'rent_payment' || type === 'tax_payment' || type === 'payment' || type === 'transfer')
    Icon = DollarSign
  else if (type.startsWith('card')) Icon = CreditCard
  else if (type.startsWith('auction')) Icon = Gavel
  else if (type.startsWith('build')) Icon = Home
  else if (type === 'bankruptcy' || type === 'go_to_jail') Icon = AlertTriangle

  let badgeVariant: 'secondary' | 'success' | 'warning' | 'default' | 'outline' | 'destructive' = 'outline'
  if (type === 'move') badgeVariant = 'secondary'
  else if (type === 'purchase' || type.startsWith('build')) badgeVariant = 'success'
  else if (type.includes('payment') || type.includes('tax')) badgeVariant = 'warning'
  else if (type.startsWith('auction')) badgeVariant = 'default'
  else if (type === 'bankruptcy') badgeVariant = 'destructive'

  const label = rawType ? rawType.toUpperCase() : 'EVENT'

  return { Icon, badgeVariant, label }
}

export function EventFeed({ events, players, loading = false, maxItems = 10 }: EventFeedProps) {
  const safeEvents = Array.isArray(events) ? events : []
  const displayEvents = safeEvents.slice(-maxItems).reverse()

  // Show skeleton only on initial load (no events yet)
  if (loading && displayEvents.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Event Feed</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-start gap-3">
                <Skeleton className="h-8 w-8 rounded-full" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-3 w-20" />
                </div>
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
        <CardTitle className="text-base font-medium">Event Feed</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
          {displayEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-4">
              No events yet
            </p>
          ) : (
            displayEvents.map((event, index) => {
              const { Icon, badgeVariant, label } = getEventMeta(event)

              return (
                <div key={index} className="flex items-start gap-3">
                  <div className="rounded-full bg-muted p-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      {formatEventText(event, players)}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={badgeVariant} className="text-xs">
                        {label}
                      </Badge>
                      {event.timestamp && (
                        <span className="text-xs text-muted-foreground">
                          {new Date(event.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </CardContent>
    </Card>
  )
}
