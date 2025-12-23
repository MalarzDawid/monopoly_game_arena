import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export interface AssetAllocationData {
  playerId: number
  name: string
  cash: number
  propertyValue: number
  houseValue: number
}

interface AssetAllocationChartProps {
  data: AssetAllocationData[]
  loading?: boolean
  showPercentage?: boolean
}

// Color scheme for asset types
const ASSET_COLORS = {
  cash: '#22c55e',        // green - liquid assets
  property: '#3b82f6',    // blue - real estate
  houses: '#f59e0b',      // amber - improvements
}

export function AssetAllocationChart({
  data,
  loading = false,
  showPercentage = false,
}: AssetAllocationChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Asset Allocation</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    )
  }

  if (!data || data.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium">Asset Allocation</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  // Calculate percentages if needed
  const processedData = data.map((player) => {
    const total = player.cash + player.propertyValue + player.houseValue
    if (showPercentage && total > 0) {
      return {
        ...player,
        cashPct: (player.cash / total) * 100,
        propertyPct: (player.propertyValue / total) * 100,
        housePct: (player.houseValue / total) * 100,
        total,
      }
    }
    return {
      ...player,
      cashPct: 0,
      propertyPct: 0,
      housePct: 0,
      total,
    }
  })

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
      formatter: (params: any[]) => {
        if (!params || params.length === 0) return ''
        const playerIndex = params[0].dataIndex
        const playerData = processedData[playerIndex]
        if (!playerData) return ''

        const total = playerData.total
        const cashPct = total > 0 ? ((playerData.cash / total) * 100).toFixed(1) : '0'
        const propPct = total > 0 ? ((playerData.propertyValue / total) * 100).toFixed(1) : '0'
        const housePct = total > 0 ? ((playerData.houseValue / total) * 100).toFixed(1) : '0'

        return `
          <div class="font-medium mb-2">${playerData.name}</div>
          <div class="text-sm mb-2">Total Net Worth: <strong>$${total.toLocaleString()}</strong></div>
          <div class="space-y-1 text-sm">
            <div class="flex items-center gap-2">
              <span style="display:inline-block;width:10px;height:10px;background:${ASSET_COLORS.cash};border-radius:2px"></span>
              <span>Cash: $${playerData.cash.toLocaleString()} (${cashPct}%)</span>
            </div>
            <div class="flex items-center gap-2">
              <span style="display:inline-block;width:10px;height:10px;background:${ASSET_COLORS.property};border-radius:2px"></span>
              <span>Properties: $${playerData.propertyValue.toLocaleString()} (${propPct}%)</span>
            </div>
            <div class="flex items-center gap-2">
              <span style="display:inline-block;width:10px;height:10px;background:${ASSET_COLORS.houses};border-radius:2px"></span>
              <span>Houses/Hotels: $${playerData.houseValue.toLocaleString()} (${housePct}%)</span>
            </div>
          </div>
          <div class="mt-2 pt-2 border-t text-xs text-gray-500">
            ${playerData.cash > playerData.propertyValue + playerData.houseValue
              ? '💵 Cash Rich'
              : '🏠 Asset Rich'
            }
          </div>
        `
      },
    },
    legend: {
      data: ['Cash', 'Properties', 'Houses/Hotels'],
      bottom: 0,
      textStyle: { color: '#6b7280' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '5%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.name),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: {
        color: '#6b7280',
        interval: 0,
        rotate: data.length > 4 ? 15 : 0,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: {
        color: '#6b7280',
        formatter: showPercentage
          ? (value: number) => `${value}%`
          : (value: number) => `$${Math.round(value).toLocaleString()}`,
      },
      max: showPercentage ? 100 : undefined,
    },
    series: [
      {
        name: 'Cash',
        type: 'bar',
        stack: 'total',
        data: processedData.map((d) => showPercentage ? d.cashPct : d.cash),
        itemStyle: {
          color: ASSET_COLORS.cash,
          borderRadius: [0, 0, 0, 0],
        },
        barWidth: '50%',
      },
      {
        name: 'Properties',
        type: 'bar',
        stack: 'total',
        data: processedData.map((d) => showPercentage ? d.propertyPct : d.propertyValue),
        itemStyle: {
          color: ASSET_COLORS.property,
          borderRadius: [0, 0, 0, 0],
        },
        barWidth: '50%',
      },
      {
        name: 'Houses/Hotels',
        type: 'bar',
        stack: 'total',
        data: processedData.map((d) => showPercentage ? d.housePct : d.houseValue),
        itemStyle: {
          color: ASSET_COLORS.houses,
          borderRadius: [4, 4, 0, 0],
        },
        barWidth: '50%',
      },
    ],
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">
          Asset Allocation
          <span className="text-xs font-normal text-muted-foreground ml-2">
            (Current Turn)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '300px' }} />
      </CardContent>
    </Card>
  )
}
