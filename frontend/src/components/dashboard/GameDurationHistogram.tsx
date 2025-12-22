import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { GameDurationBucket } from '@/types/game'
import { Clock } from 'lucide-react'

interface GameDurationHistogramProps {
  data: GameDurationBucket[] | undefined
  loading?: boolean
}

export function GameDurationHistogram({ data, loading = false }: GameDurationHistogramProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Game Duration Distribution</CardTitle>
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
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Game Duration Distribution
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            No game duration data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  // Calculate total games and stats
  const totalGames = data.reduce((sum, d) => sum + (Number(d.game_count) || 0), 0)
  const maxCount = Math.max(...data.map((d) => Number(d.game_count) || 0))

  // Find median bucket
  let cumulative = 0
  let medianBucket = data[0]?.bucket_label || 'N/A'
  for (const bucket of data) {
    cumulative += Number(bucket.game_count) || 0
    if (cumulative >= totalGames / 2) {
      medianBucket = bucket.bucket_label
      break
    }
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
      formatter: (params: any) => {
        const item = params[0]
        if (!item) return ''
        const dataItem = data[item.dataIndex]
        if (!dataItem) return ''
        const percentage = totalGames > 0 ? ((dataItem.game_count / totalGames) * 100).toFixed(1) : '0'
        return `
          <div class="font-medium">${dataItem.bucket_label} turns</div>
          <div class="text-sm mt-1">
            <div>Games: <strong>${dataItem.game_count}</strong></div>
            <div class="text-gray-500">${percentage}% of all games</div>
          </div>
        `
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.bucket_label),
      name: 'Number of Turns',
      nameLocation: 'middle',
      nameGap: 30,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
    },
    yAxis: {
      type: 'value',
      name: 'Games',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280' },
    },
    series: [
      {
        type: 'bar',
        data: data.map((d) => {
          const count = Number(d.game_count) || 0
          return {
            value: count,
            itemStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: count === maxCount ? '#3b82f6' : '#60a5fa' },
                  { offset: 1, color: count === maxCount ? '#1d4ed8' : '#3b82f6' },
                ],
              },
              borderRadius: [4, 4, 0, 0],
            },
          }
        }),
        barWidth: '70%',
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.2)',
          },
        },
      },
    ],
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Game Duration Distribution
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '300px' }} />
        <div className="flex justify-center gap-6 mt-3 text-sm">
          <div className="text-center">
            <span className="text-muted-foreground">Total Games</span>
            <p className="font-medium">{totalGames}</p>
          </div>
          <div className="text-center">
            <span className="text-muted-foreground">Median Duration</span>
            <p className="font-medium">{medianBucket} turns</p>
          </div>
          <div className="text-center">
            <span className="text-muted-foreground">Most Common</span>
            <p className="font-medium">
              {data.find((d) => (Number(d.game_count) || 0) === maxCount)?.bucket_label || 'N/A'} turns
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
