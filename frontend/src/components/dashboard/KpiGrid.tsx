import {
  TrendingUp,
  Users,
  DollarSign,
  Home,
  RotateCcw,
  AlertTriangle,
} from 'lucide-react'
import { KpiCard } from './KpiCard'
import { formatCurrency, formatNumber } from '@/lib/utils'
import type { GameStats } from '@/types/game'

interface KpiGridProps {
  stats: GameStats | undefined
  loading?: boolean
}

export function KpiGrid({ stats, loading = false }: KpiGridProps) {
  const kpis = [
    {
      title: 'Total Turns',
      value: stats ? formatNumber(stats.total_turns) : '--',
      subtitle: 'game progress',
      icon: RotateCcw,
    },
    {
      title: 'Cash in Circulation',
      value: stats ? formatCurrency(stats.cash_in_circulation) : '--',
      subtitle: 'total liquidity',
      icon: DollarSign,
    },
    {
      title: 'Total Transactions',
      value: stats ? formatNumber(stats.total_transactions) : '--',
      subtitle: 'rent + purchases',
      icon: TrendingUp,
    },
    {
      title: 'Properties Bought',
      value: stats ? formatNumber(stats.total_properties_bought) : '--',
      subtitle: 'ownership changes',
      icon: Home,
    },
    {
      title: 'Avg Rent/Turn',
      value: stats ? formatCurrency(stats.avg_rent_per_turn) : '--',
      subtitle: 'per turn',
      icon: Users,
    },
    {
      title: 'Bankruptcies',
      value: stats ? formatNumber(stats.bankruptcies) : '--',
      subtitle: 'eliminated players',
      icon: AlertTriangle,
    },
  ]

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
      {kpis.map((kpi) => (
        <KpiCard
          key={kpi.title}
          title={kpi.title}
          value={kpi.value}
          subtitle={kpi.subtitle}
          icon={kpi.icon}
          loading={loading}
        />
      ))}
    </div>
  )
}
