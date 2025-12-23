import ReactECharts from 'echarts-for-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { LuckVsSkillData } from '@/types/game'
import { Dices } from 'lucide-react'

interface LuckVsSkillScatterProps {
  data: LuckVsSkillData[] | undefined
  loading?: boolean
}

const MODEL_COLORS: Record<string, string> = {
  greedy: '#22c55e',
  random: '#ef4444',
  human: '#8b5cf6',
}

function getModelColor(modelName: string): string {
  const lower = modelName.toLowerCase()
  if (MODEL_COLORS[lower]) return MODEL_COLORS[lower]
  // LLM models get blue-ish colors
  return '#3b82f6'
}

export function LuckVsSkillScatter({ data, loading = false }: LuckVsSkillScatterProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base font-medium">Luck vs Skill Analysis</CardTitle>
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
            <Dices className="h-5 w-5" />
            Luck vs Skill Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] flex items-center justify-center text-muted-foreground">
            No data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  // Filter out items with null avg_dice_roll and transform data for scatter plot
  const validData = data.filter((item) => item.avg_dice_roll !== null && item.avg_dice_roll !== undefined)

  if (validData.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base font-medium flex items-center gap-2">
            <Dices className="h-5 w-5" />
            Luck vs Skill Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[350px] flex items-center justify-center text-muted-foreground">
            No dice roll data available yet
          </div>
        </CardContent>
      </Card>
    )
  }

  const scatterData = validData.map((item) => ({
    name: item.model_name,
    value: [Number(item.avg_dice_roll) || 7, Number(item.win_rate) || 0],
    symbolSize: Math.max(15, Math.min(50, (Number(item.total_games) || 1) * 3)),
    itemStyle: { color: getModelColor(item.model_name) },
    games: Number(item.total_games) || 0,
  }))

  // Calculate averages for reference lines
  const avgDice = validData.reduce((sum, d) => sum + (Number(d.avg_dice_roll) || 7), 0) / validData.length
  const avgWinRate = validData.reduce((sum, d) => sum + (Number(d.win_rate) || 0), 0) / validData.length

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e5e7eb',
      borderWidth: 1,
      textStyle: { color: '#1f2937' },
      formatter: (params: any) => {
        const { name, value, data } = params
        const diceRoll = typeof value[0] === 'number' ? value[0].toFixed(2) : 'N/A'
        const winRate = typeof value[1] === 'number' ? value[1].toFixed(1) : 'N/A'
        const diceVal = value[0] ?? 7
        const winVal = value[1] ?? 0
        return `
          <div class="font-medium mb-1">${name}</div>
          <div class="text-sm">
            <div>Avg Dice Roll: <strong>${diceRoll}</strong></div>
            <div>Win Rate: <strong>${winRate}%</strong></div>
            <div>Games Played: <strong>${data.games}</strong></div>
          </div>
          <div class="text-xs text-gray-500 mt-2">
            ${diceVal < avgDice && winVal > avgWinRate
              ? '⭐ High skill (wins despite bad luck)'
              : diceVal > avgDice && winVal > avgWinRate
              ? '🍀 Lucky & skilled'
              : diceVal > avgDice && winVal < avgWinRate
              ? '😬 Lucky but losing'
              : '📉 Needs improvement'
            }
          </div>
        `
      },
    },
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%',
      top: '10%',
    },
    xAxis: {
      type: 'value',
      name: 'Avg Dice Roll (Luck)',
      nameLocation: 'middle',
      nameGap: 30,
      min: 5,
      max: 10,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
    },
    yAxis: {
      type: 'value',
      name: 'Win Rate % (Skill)',
      nameLocation: 'middle',
      nameGap: 40,
      min: 0,
      max: 100,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280', formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#f3f4f6' } },
    },
    series: [
      {
        type: 'scatter',
        data: scatterData,
        label: {
          show: true,
          formatter: (params: any) => params.name.length > 10
            ? params.name.substring(0, 10) + '...'
            : params.name,
          position: 'top',
          fontSize: 10,
          color: '#6b7280',
        },
        emphasis: {
          focus: 'self',
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)',
          },
        },
        markLine: {
          silent: true,
          lineStyle: { color: '#d1d5db', type: 'dashed' },
          data: [
            { xAxis: avgDice, label: { show: false } },
            { yAxis: avgWinRate, label: { show: false } },
          ],
        },
      },
    ],
    // Quadrant annotations
    graphic: [
      {
        type: 'text',
        left: '12%',
        top: '12%',
        style: { text: '⭐ High Skill', fill: '#6b7280', fontSize: 11 },
      },
      {
        type: 'text',
        right: '12%',
        top: '12%',
        style: { text: '🍀 Lucky & Skilled', fill: '#6b7280', fontSize: 11 },
      },
      {
        type: 'text',
        left: '12%',
        bottom: '18%',
        style: { text: '📉 Low Performance', fill: '#6b7280', fontSize: 11 },
      },
      {
        type: 'text',
        right: '12%',
        bottom: '18%',
        style: { text: '😬 Lucky but Losing', fill: '#6b7280', fontSize: 11 },
      },
    ],
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium flex items-center gap-2">
          <Dices className="h-5 w-5" />
          Luck vs Skill Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ReactECharts option={option} style={{ height: '350px' }} />
        <p className="text-xs text-muted-foreground text-center mt-2">
          Bubble size = number of games played. Top-left quadrant = skilled players who win despite average luck.
        </p>
      </CardContent>
    </Card>
  )
}
