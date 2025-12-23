import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { KillZoneData } from '@/types/game'
import { Skull } from 'lucide-react'

interface KillZonesChartProps {
  data: KillZoneData[] | undefined
  loading?: boolean
}

// Color groups for Monopoly properties
const PROPERTY_COLORS: Record<number, string> = {
  1: '#8B4513', 3: '#8B4513', // Brown
  6: '#87CEEB', 8: '#87CEEB', 9: '#87CEEB', // Light Blue
  11: '#FF69B4', 13: '#FF69B4', 14: '#FF69B4', // Pink
  16: '#FFA500', 18: '#FFA500', 19: '#FFA500', // Orange
  21: '#FF0000', 23: '#FF0000', 24: '#FF0000', // Red
  26: '#FFFF00', 27: '#FFFF00', 29: '#FFFF00', // Yellow
  31: '#228B22', 32: '#228B22', 34: '#228B22', // Green
  37: '#0000FF', 39: '#0000FF', // Dark Blue
  5: '#1f2937', 15: '#1f2937', 25: '#1f2937', 35: '#1f2937', // Railroads
  12: '#6b7280', 28: '#6b7280', // Utilities
}

function getPropertyColor(position: number): string {
  return PROPERTY_COLORS[position] || '#6b7280'
}

export function KillZonesChart({ data, loading = false }: KillZonesChartProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Kill Zones</CardTitle>
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
            <Skull className="h-5 w-5 text-red-500" />
            Kill Zones
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] flex items-center justify-center text-muted-foreground">
            No bankruptcy data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  // Sort by bankruptcy count and take top 10
  const sortedData = [...data].sort((a, b) => (Number(b.bankruptcy_count) || 0) - (Number(a.bankruptcy_count) || 0)).slice(0, 10)

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
        const dataItem = sortedData[item.dataIndex]
        if (!dataItem) return ''
        return `
          <div class="font-medium">${dataItem.property_name}</div>
          <div class="text-sm mt-1">
            <div>Bankruptcies: <strong class="text-red-600">${dataItem.bankruptcy_count}</strong></div>
            <div class="text-xs text-gray-500">Position: ${dataItem.position}</div>
          </div>
        `
      },
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
      data: sortedData.map((d) => d.property_name),
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: {
        color: '#6b7280',
        rotate: 45,
        interval: 0,
        fontSize: 11,
      },
    },
    yAxis: {
      type: 'value',
      name: 'Bankruptcies',
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
      axisLabel: { color: '#6b7280' },
    },
    series: [
      {
        type: 'bar',
        data: sortedData.map((d) => ({
          value: Number(d.bankruptcy_count) || 0,
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: getPropertyColor(Number(d.position) || 0) },
                { offset: 1, color: '#ef4444' },
              ],
            },
            borderRadius: [4, 4, 0, 0],
          },
        })),
        barWidth: '60%',
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.2)',
          },
        },
        label: {
          show: true,
          position: 'top',
          formatter: '{c}',
          fontSize: 11,
          color: '#6b7280',
        },
      },
    ],
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Skull className="h-5 w-5 text-red-500" />
          Kill Zones
          <span className="text-xs font-normal text-muted-foreground ml-2">
            (Properties causing most bankruptcies)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '350px' }} />
        <p className="text-xs text-muted-foreground text-center mt-2">
          Shows properties where players most frequently went bankrupt due to rent payments.
        </p>
      </CardContent>
    </Card>
  )
}
