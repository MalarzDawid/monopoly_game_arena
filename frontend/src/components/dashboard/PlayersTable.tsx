import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { formatCurrency, formatPercent } from '@/lib/utils'
import type { PlayerStats } from '@/types/game'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'

interface PlayersTableProps {
  data: PlayerStats[]
  loading?: boolean
}

export function PlayersTable({ data, loading = false }: PlayersTableProps) {
  // Sort by net worth descending
  const sortedData = [...data].sort((a, b) => b.net_worth - a.net_worth)

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Player Rankings</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">Player Rankings</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>Player</TableHead>
              <TableHead className="text-right">Net Worth</TableHead>
              <TableHead className="text-right">Properties</TableHead>
              <TableHead className="text-right">Rent Collected</TableHead>
              <TableHead className="text-right">Rent Paid</TableHead>
              <TableHead className="text-right">ROI</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedData.map((player, index) => (
              <TableRow key={player.player_id}>
                <TableCell>
                  <Badge
                    variant={index === 0 ? 'default' : 'secondary'}
                    className="w-6 h-6 p-0 flex items-center justify-center"
                  >
                    {index + 1}
                  </Badge>
                </TableCell>
                <TableCell className="font-medium">{player.name}</TableCell>
                <TableCell className="text-right font-semibold">
                  {formatCurrency(player.net_worth)}
                </TableCell>
                <TableCell className="text-right">
                  {player.properties_owned}
                  {player.houses_built > 0 && (
                    <span className="text-muted-foreground text-xs ml-1">
                      (+{player.houses_built}h)
                    </span>
                  )}
                </TableCell>
                <TableCell className="text-right text-green-600">
                  {formatCurrency(player.total_rent_collected)}
                </TableCell>
                <TableCell className="text-right text-red-600">
                  {formatCurrency(player.total_rent_paid)}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    {player.roi > 1 ? (
                      <TrendingUp className="h-3 w-3 text-green-600" />
                    ) : player.roi < 1 ? (
                      <TrendingDown className="h-3 w-3 text-red-600" />
                    ) : (
                      <Minus className="h-3 w-3 text-muted-foreground" />
                    )}
                    <span
                      className={
                        player.roi > 1
                          ? 'text-green-600'
                          : player.roi < 1
                          ? 'text-red-600'
                          : ''
                      }
                    >
                      {formatPercent(player.roi)}
                    </span>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
