import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { StrategyPropertyData } from '@/types/game'
import { Grid3X3 } from 'lucide-react'

interface StrategyPropertyHeatmapProps {
  data: StrategyPropertyData[] | undefined
  loading?: boolean
}

// Color groups in board order (roughly by price/position)
const COLOR_GROUPS_ORDER = [
  'Brown',
  'Light Blue',
  'Pink',
  'Orange',
  'Red',
  'Yellow',
  'Green',
  'Dark Blue',
  'Railroad',
  'Utility',
]

// Colors for the heatmap gradient
const HEATMAP_COLORS = [
  '#f7fbff',
  '#deebf7',
  '#c6dbef',
  '#9ecae1',
  '#6baed6',
  '#4292c6',
  '#2171b5',
  '#08519c',
  '#08306b',
]

export function StrategyPropertyHeatmap({ data, loading = false }: StrategyPropertyHeatmapProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Strategy vs Property Preferences</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[350px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Grid3X3 className="h-5 w-5" />
            Strategy vs Property Preferences
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] flex items-center justify-center text-muted-foreground">
            No purchase data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  // Aggregate data by strategy and color group
  const aggregated = new Map<string, Map<string, number>>()

  data.forEach((item) => {
    const strategy = item.strategy
    const colorGroup = item.color_group
    const count = Number(item.purchase_count) || 0

    if (!aggregated.has(strategy)) {
      aggregated.set(strategy, new Map())
    }
    const strategyMap = aggregated.get(strategy)!
    strategyMap.set(colorGroup, (strategyMap.get(colorGroup) || 0) + count)
  })

  // Get unique strategies
  const strategies = Array.from(aggregated.keys()).sort()

  // Build heatmap data: [colorGroupIndex, strategyIndex, value]
  const heatmapData: [number, number, number][] = []
  let maxValue = 0

  strategies.forEach((strategy, strategyIdx) => {
    const strategyMap = aggregated.get(strategy)!
    COLOR_GROUPS_ORDER.forEach((colorGroup, colorIdx) => {
      const value = strategyMap.get(colorGroup) || 0
      heatmapData.push([colorIdx, strategyIdx, value])
      if (value > maxValue) maxValue = value
    })
  })

  // Normalize values for better visualization (percentage of max per strategy)
  const normalizedData: [number, number, number, number][] = heatmapData.map(([x, y, value]) => {
    // Get total purchases for this strategy
    const strategyMap = aggregated.get(strategies[y])!
    const strategyTotal = Array.from(strategyMap.values()).reduce((a, b) => a + b, 0)
    const percentage = strategyTotal > 0 ? Math.round((value / strategyTotal) * 100) : 0
    return [x, y, value, percentage]
  })

  const option = {
    tooltip: {
      position: 'top',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
      formatter: (params: any) => {
        const [colorIdx, strategyIdx, value, percentage] = params.data
        const colorGroup = COLOR_GROUPS_ORDER[colorIdx]
        const strategy = strategies[strategyIdx]
        return `
          <div class="font-medium">${strategy}</div>
          <div class="text-sm mt-1">
            <div>${colorGroup}: <strong>${value}</strong> purchases</div>
            <div class="text-gray-500">${percentage}% of strategy's purchases</div>
          </div>
        `
      },
    },
    grid: {
      left: '15%',
      right: '12%',
      top: '10%',
      bottom: '15%',
    },
    xAxis: {
      type: 'category',
      data: COLOR_GROUPS_ORDER,
      splitArea: { show: true },
      axisLabel: {
        rotate: 45,
        interval: 0,
        fontSize: 10,
        color: '#6b7280',
      },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    yAxis: {
      type: 'category',
      data: strategies,
      splitArea: { show: true },
      axisLabel: {
        fontSize: 11,
        color: '#6b7280',
      },
      axisLine: { lineStyle: { color: '#e5e7eb' } },
    },
    visualMap: {
      min: 0,
      max: maxValue || 1,
      calculable: true,
      orient: 'vertical',
      right: '2%',
      top: 'center',
      itemHeight: 150,
      inRange: {
        color: HEATMAP_COLORS,
      },
      textStyle: { color: '#6b7280', fontSize: 10 },
    },
    series: [
      {
        type: 'heatmap',
        data: normalizedData,
        label: {
          show: true,
          formatter: (params: any) => {
            const value = params.data[2]
            return value > 0 ? value : ''
          },
          fontSize: 10,
          color: (params: any) => {
            // Dark text on light cells, light text on dark cells
            const value = params.data[2]
            return value > maxValue * 0.6 ? '#fff' : '#374151'
          },
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)',
          },
        },
      },
    ],
  }

  // Calculate correlation insights
  const insights: string[] = []
  strategies.forEach((strategy) => {
    const strategyMap = aggregated.get(strategy)!
    let maxGroup = ''
    let maxCount = 0
    strategyMap.forEach((count, group) => {
      if (count > maxCount) {
        maxCount = count
        maxGroup = group
      }
    })
    if (maxGroup && maxCount > 0) {
      insights.push(`${strategy}: prefers ${maxGroup}`)
    }
  })

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Grid3X3 className="h-5 w-5" />
          Strategy vs Property Preferences
          <span className="text-xs font-normal text-muted-foreground ml-2">
            (Purchase patterns by strategy)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '350px' }} />
        {insights.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2 justify-center">
            {insights.slice(0, 4).map((insight, i) => (
              <span
                key={i}
                className="text-xs bg-muted px-2 py-1 rounded-full text-muted-foreground"
              >
                {insight}
              </span>
            ))}
          </div>
        )}
        <p className="text-xs text-muted-foreground text-center mt-2">
          Shows which property color groups each strategy tends to purchase most frequently.
        </p>
      </CardContent>
    </Card>
  )
}
