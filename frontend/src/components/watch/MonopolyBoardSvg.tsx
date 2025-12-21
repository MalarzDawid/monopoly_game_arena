import { cn } from '@/lib/utils'
import type { Player } from '@/types/game'

interface MonopolyBoardSvgProps {
  players: Player[]
  currentPlayerId: number
  className?: string
}

// Board positions (40 spaces, going clockwise from GO)
const BOARD_SPACES = [
  { name: 'GO', color: '#ffffff', type: 'corner' },
  { name: 'Mediterranean', color: '#8B4513', type: 'property' },
  { name: 'Community Chest', color: '#ffffff', type: 'card' },
  { name: 'Baltic', color: '#8B4513', type: 'property' },
  { name: 'Income Tax', color: '#ffffff', type: 'tax' },
  { name: 'Reading RR', color: '#ffffff', type: 'railroad' },
  { name: 'Oriental', color: '#87CEEB', type: 'property' },
  { name: 'Chance', color: '#ffffff', type: 'card' },
  { name: 'Vermont', color: '#87CEEB', type: 'property' },
  { name: 'Connecticut', color: '#87CEEB', type: 'property' },
  { name: 'JAIL', color: '#ffffff', type: 'corner' },
  { name: 'St. Charles', color: '#FF69B4', type: 'property' },
  { name: 'Electric Co', color: '#ffffff', type: 'utility' },
  { name: 'States', color: '#FF69B4', type: 'property' },
  { name: 'Virginia', color: '#FF69B4', type: 'property' },
  { name: 'Pennsylvania RR', color: '#ffffff', type: 'railroad' },
  { name: 'St. James', color: '#FFA500', type: 'property' },
  { name: 'Community Chest', color: '#ffffff', type: 'card' },
  { name: 'Tennessee', color: '#FFA500', type: 'property' },
  { name: 'New York', color: '#FFA500', type: 'property' },
  { name: 'FREE PARKING', color: '#ffffff', type: 'corner' },
  { name: 'Kentucky', color: '#FF0000', type: 'property' },
  { name: 'Chance', color: '#ffffff', type: 'card' },
  { name: 'Indiana', color: '#FF0000', type: 'property' },
  { name: 'Illinois', color: '#FF0000', type: 'property' },
  { name: 'B&O RR', color: '#ffffff', type: 'railroad' },
  { name: 'Atlantic', color: '#FFFF00', type: 'property' },
  { name: 'Ventnor', color: '#FFFF00', type: 'property' },
  { name: 'Water Works', color: '#ffffff', type: 'utility' },
  { name: 'Marvin Gardens', color: '#FFFF00', type: 'property' },
  { name: 'GO TO JAIL', color: '#ffffff', type: 'corner' },
  { name: 'Pacific', color: '#228B22', type: 'property' },
  { name: 'North Carolina', color: '#228B22', type: 'property' },
  { name: 'Community Chest', color: '#ffffff', type: 'card' },
  { name: 'Pennsylvania', color: '#228B22', type: 'property' },
  { name: 'Short Line', color: '#ffffff', type: 'railroad' },
  { name: 'Chance', color: '#ffffff', type: 'card' },
  { name: 'Park Place', color: '#0000FF', type: 'property' },
  { name: 'Luxury Tax', color: '#ffffff', type: 'tax' },
  { name: 'Boardwalk', color: '#0000FF', type: 'property' },
]

const PLAYER_COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']

function getSpacePosition(index: number, size: number) {
  const cornerSize = 60
  const spaceSize = (size - 2 * cornerSize) / 9

  if (index === 0) return { x: size - cornerSize / 2, y: size - cornerSize / 2 }
  if (index <= 9) return { x: size - cornerSize - (index - 0.5) * spaceSize, y: size - cornerSize / 2 }
  if (index === 10) return { x: cornerSize / 2, y: size - cornerSize / 2 }
  if (index <= 19) return { x: cornerSize / 2, y: size - cornerSize - (index - 10 - 0.5) * spaceSize }
  if (index === 20) return { x: cornerSize / 2, y: cornerSize / 2 }
  if (index <= 29) return { x: cornerSize + (index - 20 - 0.5) * spaceSize, y: cornerSize / 2 }
  if (index === 30) return { x: size - cornerSize / 2, y: cornerSize / 2 }
  if (index <= 39) return { x: size - cornerSize / 2, y: cornerSize + (index - 30 - 0.5) * spaceSize }
  return { x: 0, y: 0 }
}

export function MonopolyBoardSvg({ players, currentPlayerId, className }: MonopolyBoardSvgProps) {
  const size = 400
  const cornerSize = 60
  const spaceSize = (size - 2 * cornerSize) / 9

  // Group players by position
  const playersByPosition: Record<number, Player[]> = {}
  players.forEach((p) => {
    if (!playersByPosition[p.position]) playersByPosition[p.position] = []
    playersByPosition[p.position].push(p)
  })

  // Property ownership by board position (for highlighting tiles with houses/hotels)
  const ownershipByPosition: Record<number, { ownerId: number; houses: number }> = {}
  players.forEach((player) => {
    player.properties.forEach((prop) => {
      ownershipByPosition[prop.position] = {
        ownerId: player.player_id,
        houses: prop.houses,
      }
    })
  })

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      className={cn('w-full max-w-md mx-auto', className)}
    >
      {/* Board background */}
      <rect x="0" y="0" width={size} height={size} fill="#c8e6c9" rx="4" />

      {/* Center area */}
      <rect
        x={cornerSize}
        y={cornerSize}
        width={size - 2 * cornerSize}
        height={size - 2 * cornerSize}
        fill="#c8e6c9"
        stroke="#388e3c"
        strokeWidth="2"
      />

      {/* Center text */}
      <text
        x={size / 2}
        y={size / 2 - 10}
        textAnchor="middle"
        fill="#388e3c"
        fontSize="24"
        fontWeight="bold"
      >
        MONOPOLY
      </text>
      <text
        x={size / 2}
        y={size / 2 + 15}
        textAnchor="middle"
        fill="#666"
        fontSize="10"
      >
        Turn {players.length > 0 ? 'Active' : 'Waiting'}
      </text>

      {/* Draw spaces */}
      {BOARD_SPACES.map((space, index) => {
        const pos = getSpacePosition(index, size)
        const isCorner = [0, 10, 20, 30].includes(index)
        const spaceW = isCorner ? cornerSize : spaceSize
        const spaceH = cornerSize

        let rectX = pos.x - spaceW / 2
        let rectY = pos.y - spaceH / 2

        // Adjust for side orientation
        if (index > 10 && index < 20) {
          rectX = 0
          rectY = pos.y - spaceSize / 2
        } else if (index > 20 && index < 30) {
          rectY = 0
        } else if (index > 30) {
          rectX = size - cornerSize
          rectY = pos.y - spaceSize / 2
        }

        const spaceRectX = isCorner ? pos.x - cornerSize / 2 : rectX
        const spaceRectY = isCorner ? pos.y - cornerSize / 2 : rectY
        const spaceRectWidth = isCorner
          ? cornerSize
          : index <= 10 || (index > 20 && index < 30)
          ? spaceSize
          : cornerSize
        const spaceRectHeight = isCorner
          ? cornerSize
          : index <= 10 || (index > 20 && index < 30)
          ? cornerSize
          : spaceSize

        const ownership = ownershipByPosition[index]

        return (
          <g key={index}>
            {/* Space background */}
            <rect
              x={spaceRectX}
              y={spaceRectY}
              width={spaceRectWidth}
              height={spaceRectHeight}
              fill="#e8f5e9"
              stroke="#388e3c"
              strokeWidth="0.5"
            />

            {/* Color bar for properties */}
            {space.type === 'property' && (
              <rect
                x={isCorner ? pos.x - cornerSize / 2 : rectX}
                y={
                  index <= 10
                    ? pos.y - cornerSize / 2
                    : index < 20
                    ? pos.y - spaceSize / 2
                    : index < 30
                    ? pos.y - cornerSize / 2 + cornerSize - 10
                    : pos.y - spaceSize / 2
                }
                width={index <= 10 || (index > 20 && index < 30) ? spaceSize : 10}
                height={index <= 10 || (index > 20 && index < 30) ? 10 : spaceSize}
                fill={space.color}
              />
            )}

            {/* Ownership highlight (outline in player color) */}
            {space.type === 'property' && ownership && (
              <rect
                x={spaceRectX + 2}
                y={spaceRectY + 2}
                width={spaceRectWidth - 4}
                height={spaceRectHeight - 4}
                fill="none"
                stroke={PLAYER_COLORS[ownership.ownerId % PLAYER_COLORS.length]}
                strokeWidth={2}
              />
            )}

            {/* Houses / hotel indicator */}
            {space.type === 'property' && ownership && ownership.houses > 0 && (
              <text
                x={spaceRectX + spaceRectWidth / 2}
                y={spaceRectY + spaceRectHeight / 2 + 6}
                textAnchor="middle"
                fill={PLAYER_COLORS[ownership.ownerId % PLAYER_COLORS.length]}
                fontSize="8"
                fontWeight="bold"
              >
                {ownership.houses >= 5 ? 'HOTEL' : 'H'.repeat(Math.min(ownership.houses, 4))}
              </text>
            )}
          </g>
        )
      })}

      {/* Draw players */}
      {Object.entries(playersByPosition).map(([pos, posPlayers]) => {
        const position = parseInt(pos)
        const basePos = getSpacePosition(position, size)

        return posPlayers.map((player, idx) => {
          const offsetX = (idx % 2) * 12 - 6
          const offsetY = Math.floor(idx / 2) * 12 - 6

          return (
            <g key={player.player_id}>
              <circle
                cx={basePos.x + offsetX}
                cy={basePos.y + offsetY}
                r={8}
                fill={PLAYER_COLORS[player.player_id % PLAYER_COLORS.length]}
                stroke={player.player_id === currentPlayerId ? '#000' : '#fff'}
                strokeWidth={player.player_id === currentPlayerId ? 2 : 1}
              />
              <text
                x={basePos.x + offsetX}
                y={basePos.y + offsetY + 3}
                textAnchor="middle"
                fill="#fff"
                fontSize="8"
                fontWeight="bold"
              >
                {player.player_id + 1}
              </text>
              {player.in_jail && position === 10 && (
                <rect
                  x={basePos.x + offsetX - 10}
                  y={basePos.y + offsetY - 10}
                  width={20}
                  height={20}
                  fill="none"
                  stroke="#ff0000"
                  strokeWidth="2"
                  strokeDasharray="4,2"
                />
              )}
            </g>
          )
        })
      })}
    </svg>
  )
}
