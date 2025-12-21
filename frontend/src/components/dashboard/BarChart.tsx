import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { PlayerStats } from '@/types/game'

interface BarChartProps {
  title: string
  data: PlayerStats[]
  dataKey: 'total_rent_collected' | 'total_rent_paid' | 'net_worth' | 'properties_owned'
  loading?: boolean
}

const PLAYER_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444']

export function BarChart({ title, data, dataKey, loading = false }: BarChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
        </CardContent>
      </Card>
    )
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.name),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: {
        color: '#6b7280',
        formatter: dataKey === 'properties_owned' ? '{value}' : '${value}',
      },
    },
    series: [
      {
        type: 'bar',
        data: data.map((d, i) => ({
          value: d[dataKey],
          itemStyle: { color: PLAYER_COLORS[i % PLAYER_COLORS.length] },
        })),
        barWidth: '60%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '300px' }} />
      </CardContent>
    </Card>
  )
}
