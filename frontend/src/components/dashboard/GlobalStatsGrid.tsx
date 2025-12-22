import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { GlobalStats } from '@/types/game'
import { Gamepad2, RotateCcw, ArrowRightLeft, Home, Skull } from 'lucide-react'

interface GlobalStatsGridProps {
  stats: GlobalStats | undefined
  loading?: boolean
}

interface StatCardProps {
  title: string
  value: number | string
  icon: React.ReactNode
  subtitle?: string
  loading?: boolean
}

function StatCard({ title, value, icon, subtitle, loading }: StatCardProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <Skeleton className="h-12 w-12 rounded-lg" />
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-16" />
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className="text-2xl font-bold">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
            {subtitle && (
              <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function GlobalStatsGrid({ stats, loading = false }: GlobalStatsGridProps) {
  const finishedGames = stats?.finished_games ?? 0
  const totalGames = stats?.total_games ?? 0
  const completionRate = totalGames > 0 ? Math.round((finishedGames / totalGames) * 100) : 0

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <StatCard
        title="Total Games Played"
        value={stats?.total_games ?? 0}
        icon={<Gamepad2 className="h-6 w-6" />}
        subtitle={`${finishedGames} finished (${completionRate}%)`}
        loading={loading}
      />
      <StatCard
        title="Total Turns Played"
        value={stats?.total_turns ?? 0}
        icon={<RotateCcw className="h-6 w-6" />}
        subtitle={totalGames > 0 ? `~${Math.round((stats?.total_turns ?? 0) / totalGames)} avg/game` : undefined}
        loading={loading}
      />
      <StatCard
        title="Total Transactions"
        value={stats?.total_transactions ?? 0}
        icon={<ArrowRightLeft className="h-6 w-6" />}
        subtitle="Purchases, trades, rent"
        loading={loading}
      />
      <StatCard
        title="Properties Bought"
        value={stats?.total_properties_bought ?? 0}
        icon={<Home className="h-6 w-6" />}
        loading={loading}
      />
      <StatCard
        title="Total Bankruptcies"
        value={stats?.total_bankruptcies ?? 0}
        icon={<Skull className="h-6 w-6" />}
        subtitle={totalGames > 0 ? `~${(((stats?.total_bankruptcies ?? 0) / totalGames)).toFixed(1)}/game` : undefined}
        loading={loading}
      />
    </div>
  )
}
