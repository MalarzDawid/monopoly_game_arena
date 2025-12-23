import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

// Color group definitions matching Monopoly board
export interface ColorGroupRentData {
  colorGroup: string
  displayName: string
  totalRent: number
  rentCount: number
  properties: string[]
  baseColor: string
}

interface RentHeatmapProps {
  data: ColorGroupRentData[]
  loading?: boolean
}

// Monopoly color groups with their base colors
const COLOR_GROUPS = [
  { id: 'brown', name: 'Brown', baseColor: '#8B4513', positions: [1, 3] },
  { id: 'light_blue', name: 'Light Blue', baseColor: '#87CEEB', positions: [6, 8, 9] },
  { id: 'pink', name: 'Pink', baseColor: '#FF69B4', positions: [11, 13, 14] },
  { id: 'orange', name: 'Orange', baseColor: '#FFA500', positions: [16, 18, 19] },
  { id: 'red', name: 'Red', baseColor: '#FF0000', positions: [21, 23, 24] },
  { id: 'yellow', name: 'Yellow', baseColor: '#FFFF00', positions: [26, 27, 29] },
  { id: 'green', name: 'Green', baseColor: '#228B22', positions: [31, 32, 34] },
  { id: 'dark_blue', name: 'Dark Blue', baseColor: '#0000FF', positions: [37, 39] },
  { id: 'railroad', name: 'Railroads', baseColor: '#1f2937', positions: [5, 15, 25, 35] },
  { id: 'utility', name: 'Utilities', baseColor: '#6b7280', positions: [12, 28] },
]

// Calculate heat intensity (0-1) based on rent value
function calculateHeatIntensity(rent: number, maxRent: number): number {
  if (maxRent === 0) return 0
  return Math.min(1, rent / maxRent)
}

// Generate color with intensity overlay
function getHeatColor(baseColor: string, intensity: number): string {
  // Convert intensity to opacity for overlay
  const opacity = 0.2 + intensity * 0.8
  return `${baseColor}${Math.round(opacity * 255).toString(16).padStart(2, '0')}`
}

export function RentHeatmap({ data, loading = false }: RentHeatmapProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Rent Heatmap</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[400px] w-full" />
        </CardContent>
      </Card>
    )
  }

  // Create lookup map for rent data
  const rentByGroup = new Map<string, ColorGroupRentData>()
  data.forEach((d) => {
    rentByGroup.set(d.colorGroup.toLowerCase().replace(' ', '_'), d)
  })

  // Find max rent for scaling
  const maxRent = Math.max(...data.map((d) => d.totalRent), 1)

  // Calculate totals
  const totalRent = data.reduce((sum, d) => sum + d.totalRent, 0)
  const totalTransactions = data.reduce((sum, d) => sum + d.rentCount, 0)

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base font-medium">
          Rent Heatmap by Color Group
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Board representation using CSS Grid */}
        <div className="relative w-full max-w-md mx-auto">
          {/* Outer board container */}
          <div className="grid grid-cols-11 grid-rows-11 gap-0.5 bg-green-200 p-2 rounded-lg aspect-square">
            {/* TOP ROW (positions 20-30): Free Parking to Go To Jail */}
            {[20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30].map((pos) => (
              <BoardCell
                key={`top-${pos}`}
                position={pos}
                rentByGroup={rentByGroup}
                maxRent={maxRent}
                row="top"
              />
            ))}

            {/* MIDDLE ROWS */}
            {[19, 18, 17, 16, 15, 14, 13, 12, 11].map((leftPos, rowIdx) => (
              <div key={`row-${rowIdx}`} className="contents">
                {/* Left cell */}
                <BoardCell
                  position={leftPos}
                  rentByGroup={rentByGroup}
                  maxRent={maxRent}
                  row="left"
                />
                {/* Center (empty for middle cells) */}
                {rowIdx === 4 ? (
                  <div className="col-span-9 row-span-1 bg-green-100 flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-xs font-medium text-green-800">
                        Total Rent
                      </div>
                      <div className="text-lg font-bold text-green-700">
                        ${totalRent.toLocaleString()}
                      </div>
                      <div className="text-xs text-green-600">
                        {totalTransactions} payments
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="col-span-9 row-span-1 bg-green-100" />
                )}
                {/* Right cell */}
                <BoardCell
                  position={31 + rowIdx}
                  rentByGroup={rentByGroup}
                  maxRent={maxRent}
                  row="right"
                />
              </div>
            ))}

            {/* BOTTOM ROW (positions 10-0): Jail to GO */}
            {[10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0].map((pos) => (
              <BoardCell
                key={`bottom-${pos}`}
                position={pos}
                rentByGroup={rentByGroup}
                maxRent={maxRent}
                row="bottom"
              />
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
          {COLOR_GROUPS.slice(0, 8).map((group) => {
            const groupData = rentByGroup.get(group.id)
            const rent = groupData?.totalRent ?? 0
            const intensity = calculateHeatIntensity(rent, maxRent)

            return (
              <div
                key={group.id}
                className="flex items-center gap-1.5 p-1.5 rounded border bg-muted/30"
              >
                <div
                  className="w-4 h-4 rounded-sm border border-black/20"
                  style={{ backgroundColor: getHeatColor(group.baseColor, intensity) }}
                />
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{group.name}</div>
                  <div className="text-muted-foreground">
                    ${rent.toLocaleString()}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* Intensity scale */}
        <div className="mt-3 flex items-center justify-center gap-2 text-xs text-muted-foreground">
          <span>Low</span>
          <div className="flex h-3 w-32 rounded overflow-hidden">
            {[0, 0.2, 0.4, 0.6, 0.8, 1].map((intensity, i) => (
              <div
                key={i}
                className="flex-1"
                style={{
                  backgroundColor: `rgba(239, 68, 68, ${0.2 + intensity * 0.8})`,
                }}
              />
            ))}
          </div>
          <span>High</span>
        </div>
      </CardContent>
    </Card>
  )
}

// Individual board cell component
interface BoardCellProps {
  position: number
  rentByGroup: Map<string, ColorGroupRentData>
  maxRent: number
  row: 'top' | 'bottom' | 'left' | 'right'
}

function BoardCell({ position, rentByGroup, maxRent, row }: BoardCellProps) {
  // Find which color group this position belongs to
  const colorGroup = COLOR_GROUPS.find((g) => g.positions.includes(position))

  // Get rent data for this group
  const groupData = colorGroup ? rentByGroup.get(colorGroup.id) : null
  const rent = groupData?.totalRent ?? 0
  const intensity = calculateHeatIntensity(rent, maxRent)

  // Corner positions (don't show heat)
  const isCorner = [0, 10, 20, 30].includes(position)

  // Non-property positions
  const isNonProperty =
    [2, 4, 7, 17, 22, 33, 36, 38].includes(position) || // Cards, taxes
    !colorGroup

  // Base styling
  const baseStyle = cn(
    'flex items-center justify-center text-[6px] font-medium transition-all',
    isCorner ? 'bg-gray-100' : isNonProperty ? 'bg-gray-50' : '',
    row === 'top' || row === 'bottom' ? 'aspect-square' : 'aspect-[1/1.2]'
  )

  // Calculate background color with heat overlay
  const bgColor = isCorner
    ? '#f3f4f6'
    : isNonProperty
    ? '#fafafa'
    : colorGroup
    ? getHeatColor(colorGroup.baseColor, intensity)
    : '#e5e7eb'

  // Get position label
  const positionLabels: Record<number, string> = {
    0: 'GO',
    10: 'JAIL',
    20: 'FREE',
    30: 'GO TO JAIL',
    5: 'RR',
    15: 'RR',
    25: 'RR',
    35: 'RR',
    12: 'ELEC',
    28: 'WATER',
    2: 'CC',
    17: 'CC',
    33: 'CC',
    7: '?',
    22: '?',
    36: '?',
    4: 'TAX',
    38: 'TAX',
  }

  const label = positionLabels[position] ?? ''

  return (
    <div
      className={baseStyle}
      style={{ backgroundColor: bgColor }}
      title={
        colorGroup
          ? `${colorGroup.name}: $${rent.toLocaleString()} rent collected`
          : label
      }
    >
      {isCorner || isNonProperty ? (
        <span className="text-gray-400">{label}</span>
      ) : (
        intensity > 0.3 && (
          <span className="text-white text-shadow font-bold drop-shadow-md">
            $
          </span>
        )
      )}
    </div>
  )
}
