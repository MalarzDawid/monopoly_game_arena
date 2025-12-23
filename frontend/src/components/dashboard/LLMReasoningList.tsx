import { useState, useMemo, useEffect, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import type { LLMReasoningsResponse, LLMReasoningEntry } from '@/types/game'
import { Brain, Search, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'

interface LLMReasoningListProps {
  data: LLMReasoningsResponse | undefined
  loading?: boolean
  onSearchChange?: (search: string) => void
  onLoadMore?: () => void
  loadingMore?: boolean
  accumulatedItems?: LLMReasoningEntry[]
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

// Strategy badge colors
function getStrategyColor(strategy: string): string {
  const lower = strategy.toLowerCase()
  if (lower === 'aggressive') return 'bg-red-100 text-red-800 border-red-200'
  if (lower === 'balanced') return 'bg-blue-100 text-blue-800 border-blue-200'
  if (lower === 'defensive') return 'bg-green-100 text-green-800 border-green-200'
  return 'bg-gray-100 text-gray-800 border-gray-200'
}

// Action type badge colors
function getActionColor(action: string): string {
  const lower = action.toLowerCase()
  if (lower === 'buy' || lower === 'purchase') return 'bg-emerald-100 text-emerald-800'
  if (lower === 'build') return 'bg-amber-100 text-amber-800'
  if (lower === 'sell') return 'bg-orange-100 text-orange-800'
  if (lower === 'mortgage') return 'bg-purple-100 text-purple-800'
  if (lower === 'bid') return 'bg-cyan-100 text-cyan-800'
  if (lower === 'end_turn') return 'bg-slate-100 text-slate-800'
  return 'bg-gray-100 text-gray-800'
}

// Format timestamp
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('pl-PL', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return timestamp
  }
}

export function LLMReasoningList({
  data,
  loading = false,
  onSearchChange,
  onLoadMore,
  loadingMore = false,
  accumulatedItems,
}: LLMReasoningListProps) {
  const [localSearch, setLocalSearch] = useState('')
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set())
  const inputRef = useRef<HTMLInputElement>(null)

  // Debounce the search value - only trigger API call after 400ms of no typing
  const debouncedSearch = useDebounce(localSearch, 400)

  // Call onSearchChange only when debounced value changes
  useEffect(() => {
    onSearchChange?.(debouncedSearch)
  }, [debouncedSearch, onSearchChange])

  // Handle search input - only update local state immediately
  const handleSearchChange = (value: string) => {
    setLocalSearch(value)
  }

  // Toggle expand/collapse for reasoning text
  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  // Use accumulated items if available (for pagination), otherwise use data.items
  const itemsSource = accumulatedItems ?? data?.items ?? []

  // Filter items locally if no server-side search
  const filteredItems = useMemo(() => {
    if (!itemsSource.length) return []
    if (!localSearch.trim() || onSearchChange) return itemsSource

    const search = localSearch.toLowerCase()
    return itemsSource.filter(
      (item) =>
        item.reasoning.toLowerCase().includes(search) ||
        item.strategy.toLowerCase().includes(search) ||
        item.model_name.toLowerCase().includes(search) ||
        item.action_type.toLowerCase().includes(search)
    )
  }, [itemsSource, localSearch, onSearchChange])

  // Calculate if there are more items to load
  const hasMore = data ? (accumulatedItems?.length ?? data.items.length) < data.total : false

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">LLM Decision Reasonings</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-10 w-full mb-4" />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Brain className="h-5 w-5 text-purple-500" />
          LLM Decision Reasonings
          {data && (
            <span className="text-xs font-normal text-muted-foreground ml-2">
              ({data.total} total)
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Search Input */}
        <div className="relative mb-4">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            type="text"
            placeholder="Search reasonings, strategies, models..."
            value={localSearch}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Reasoning List */}
        {filteredItems.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {localSearch ? 'No reasonings match your search' : 'No LLM decision data available yet'}
          </div>
        ) : (
          <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
            {filteredItems.map((item) => {
              const isExpanded = expandedItems.has(item.id)
              const isLongText = item.reasoning.length > 200

              return (
                <div
                  key={item.id}
                  className="border rounded-lg p-3 hover:bg-muted/30 transition-colors"
                >
                  {/* Header Row */}
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <Badge className={getStrategyColor(item.strategy)} variant="outline">
                      {item.strategy}
                    </Badge>
                    <Badge className={getActionColor(item.action_type)} variant="secondary">
                      {item.action_type}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {item.model_name}
                    </span>
                    <span className="text-xs text-muted-foreground ml-auto">
                      Turn {item.turn_number} | {formatTime(item.timestamp)}
                    </span>
                  </div>

                  {/* Reasoning Text */}
                  <div
                    className={`text-sm text-foreground ${!isExpanded && isLongText ? 'line-clamp-3' : ''}`}
                  >
                    {item.reasoning || <span className="text-muted-foreground italic">No reasoning provided</span>}
                  </div>

                  {/* Expand/Collapse Button */}
                  {isLongText && (
                    <button
                      onClick={() => toggleExpand(item.id)}
                      className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 mt-2"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="h-3 w-3" />
                          Show less
                        </>
                      ) : (
                        <>
                          <ChevronDown className="h-3 w-3" />
                          Show more
                        </>
                      )}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}

        {/* Load More Button */}
        {hasMore && onLoadMore && !localSearch && (
          <div className="flex justify-center mt-4">
            <Button
              variant="outline"
              onClick={onLoadMore}
              disabled={loadingMore}
              className="gap-2"
            >
              {loadingMore ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading...
                </>
              ) : (
                <>
                  Load More ({data?.total ? data.total - filteredItems.length : 0} remaining)
                </>
              )}
            </Button>
          </div>
        )}

        {/* Footer info */}
        {data && (
          <p className="text-xs text-muted-foreground text-center mt-3">
            Showing {filteredItems.length} of {data.total} reasonings
          </p>
        )}
      </CardContent>
    </Card>
  )
}
