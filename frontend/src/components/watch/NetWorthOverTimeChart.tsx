import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { Player } from '@/types/game'

export interface NetWorthDataPoint {
  turn: number
  players: {
    playerId: number
    name: string
    cash: number
    propertyValue: number
    houseValue: number
    netWorth: number
  }[]
}

interface NetWorthOverTimeChartProps {
  data: NetWorthDataPoint[]
  players: Player[]
  loading?: boolean
}

const PLAYER_COLORS = [
  '#3b82f6', // blue
  '#22c55e', // green
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#14b8a6', // teal
  '#f97316', // orange
]

export function NetWorthOverTimeChart({
  data,
  players,
  loading = false,
}: NetWorthOverTimeChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Net Worth Over Time</CardTitle>
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
          <CardTitle className="text-base font-medium">Net Worth Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  const playerNames = players.map((p) => p.name)

  const option = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
      formatter: (params: any[]) => {
        if (!params || params.length === 0) return ''
        const turnIndex = params[0].dataIndex
        const turnData = data[turnIndex]
        if (!turnData) return ''

        let html = `<div class="font-medium mb-2">Turn ${turnData.turn}</div>`
        params.forEach((_param: any, index: number) => {
          const playerData = turnData.players[index]
          if (!playerData) return
          const color = PLAYER_COLORS[index % PLAYER_COLORS.length]
          html += `
            <div class="flex items-center gap-2 mb-1">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color}"></span>
              <span class="font-medium">${playerData.name}</span>
            </div>
            <div class="pl-4 text-xs text-gray-600 mb-2">
              <div>Net Worth: <strong>$${playerData.netWorth.toLocaleString()}</strong></div>
              <div>Cash: $${playerData.cash.toLocaleString()}</div>
              <div>Properties: $${playerData.propertyValue.toLocaleString()}</div>
              <div>Houses/Hotels: $${playerData.houseValue.toLocaleString()}</div>
            </div>
          `
        })
        return html
      },
    },
    legend: {
      data: playerNames,
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
      data: data.map((d) => `Turn ${d.turn}`),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: {
        color: '#6b7280',
        rotate: data.length > 20 ? 45 : 0,
        interval: data.length > 30 ? Math.floor(data.length / 15) : 0,
      },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: {
        color: '#6b7280',
        formatter: (value: number) => `$${Math.round(value).toLocaleString()}`,
      },
    },
    series: playerNames.map((name, index) => ({
      name,
      type: 'line',
      smooth: true,
      data: data.map((d) => {
        const playerData = d.players.find((p) => p.name === name)
        return playerData ? Math.round(playerData.netWorth) : 0
      }),
      lineStyle: { color: PLAYER_COLORS[index % PLAYER_COLORS.length], width: 2 },
      itemStyle: { color: PLAYER_COLORS[index % PLAYER_COLORS.length] },
      symbol: 'circle',
      symbolSize: 4,
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: `${PLAYER_COLORS[index % PLAYER_COLORS.length]}20` },
            { offset: 1, color: `${PLAYER_COLORS[index % PLAYER_COLORS.length]}05` },
          ],
        },
      },
    })),
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">Net Worth Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '300px' }} />
      </CardContent>
    </Card>
  )
}
