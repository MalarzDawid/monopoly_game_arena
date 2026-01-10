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

export interface StrategyChangeEvent {
  turn: number
  playerId: number
  playerName: string
  fromStrategy: string
  toStrategy: string
  reasoning: string
  netWorth: number
}

interface NetWorthOverTimeChartProps {
  data: NetWorthDataPoint[]
  players: Player[]
  strategyChanges?: StrategyChangeEvent[]
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
  strategyChanges = [],
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

  // Create scatter data for strategy change markers
  const strategyChangeMarkers = strategyChanges.map((change) => {
    const turnIndex = data.findIndex((d) => d.turn === change.turn)
    const playerIndex = players.findIndex((p) => p.player_id === change.playerId)
    return {
      value: [turnIndex, change.netWorth],
      change,
      playerIndex,
    }
  }).filter((m) => m.value[0] >= 0)

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
      formatter: (params: any) => {
        // Handle strategy change marker tooltip
        if (params.seriesName === 'Strategy Changes' && params.data?.change) {
          const change = params.data.change as StrategyChangeEvent
          const color = PLAYER_COLORS[params.data.playerIndex % PLAYER_COLORS.length]
          return `
            <div style="max-width: 350px;">
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                <span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:${color};border:2px solid white;box-shadow:0 0 0 2px ${color}"></span>
                <span style="font-weight: 600; font-size: 14px;">${change.playerName}</span>
                <span style="color: #6b7280; font-size: 12px;">Turn ${change.turn}</span>
              </div>
              <div style="background: linear-gradient(135deg, #f0f9ff, #e0f2fe); padding: 8px 12px; border-radius: 6px; margin-bottom: 8px;">
                <div style="font-weight: 600; color: #0369a1; font-size: 13px; margin-bottom: 4px;">
                  STRATEGY CHANGE
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                  <span style="background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;">
                    ${change.fromStrategy}
                  </span>
                  <span style="color: #6b7280;">→</span>
                  <span style="background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;">
                    ${change.toStrategy}
                  </span>
                </div>
              </div>
              <div style="font-size: 12px; color: #374151; line-height: 1.5; max-height: 120px; overflow-y: auto;">
                ${change.reasoning}
              </div>
              <div style="margin-top: 8px; font-size: 11px; color: #6b7280;">
                Net Worth: <strong>$${change.netWorth.toLocaleString()}</strong>
              </div>
            </div>
          `
        }

        // Handle line chart tooltip (axis trigger simulation)
        if (params.seriesType === 'line') {
          const turnIndex = params.dataIndex
          const turnData = data[turnIndex]
          if (!turnData) return ''

          let html = `<div style="font-weight: 500; margin-bottom: 8px;">Turn ${turnData.turn}</div>`
          turnData.players.forEach((playerData, index) => {
            const color = PLAYER_COLORS[index % PLAYER_COLORS.length]
            html += `
              <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color}"></span>
                <span style="font-weight: 500;">${playerData.name}</span>
              </div>
              <div style="padding-left: 18px; font-size: 12px; color: #6b7280; margin-bottom: 8px;">
                <div>Net Worth: <strong style="color: #1f2937;">$${playerData.netWorth.toLocaleString()}</strong></div>
                <div>Cash: $${playerData.cash.toLocaleString()}</div>
                <div>Properties: $${playerData.propertyValue.toLocaleString()}</div>
                <div>Houses/Hotels: $${playerData.houseValue.toLocaleString()}</div>
              </div>
            `
          })
          return html
        }

        return ''
      },
    },
    legend: {
      data: [...playerNames, ...(strategyChanges.length > 0 ? ['Strategy Changes'] : [])],
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
    series: [
      // Line series for each player
      ...playerNames.map((name, index) => ({
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
      // Scatter series for strategy change markers
      ...(strategyChangeMarkers.length > 0
        ? [
            {
              name: 'Strategy Changes',
              type: 'scatter',
              data: strategyChangeMarkers,
              symbol: 'circle',
              symbolSize: 16,
              itemStyle: {
                color: '#ffffff',
                borderWidth: 3,
                borderColor: '#8b5cf6',
                shadowColor: 'rgba(139, 92, 246, 0.5)',
                shadowBlur: 8,
              },
              emphasis: {
                itemStyle: {
                  borderWidth: 4,
                  borderColor: '#7c3aed',
                  shadowBlur: 12,
                },
                scale: 1.3,
              },
              z: 10,
            },
          ]
        : []),
    ],
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
