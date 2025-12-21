import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Play, Pause, RotateCcw } from 'lucide-react'

interface GameControlsProps {
  paused: boolean
  tickMs: number
  turnNumber: number
  phase: string
  gameOver: boolean
  onPause: () => void
  onResume: () => void
  onSpeedChange: (tickMs: number) => void
}

const SPEED_OPTIONS = [
  { value: 100, label: '10x' },
  { value: 250, label: '4x' },
  { value: 500, label: '2x' },
  { value: 1000, label: '1x' },
  { value: 2000, label: '0.5x' },
]

export function GameControls({
  paused,
  tickMs,
  turnNumber,
  phase,
  gameOver,
  onPause,
  onResume,
  onSpeedChange,
}: GameControlsProps) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <RotateCcw className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Turn {turnNumber}</span>
            </div>

            <Badge variant={gameOver ? 'destructive' : 'secondary'}>
              {gameOver ? 'Game Over' : phase}
            </Badge>

            {paused && !gameOver && (
              <Badge variant="warning">Paused</Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Speed:</span>
            <Select
              value={String(tickMs)}
              onValueChange={(v) => onSpeedChange(Number(v))}
              disabled={gameOver}
            >
              <SelectTrigger className="w-20 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SPEED_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={String(opt.value)}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {!gameOver && (
              <Button
                size="sm"
                variant={paused ? 'default' : 'outline'}
                onClick={paused ? onResume : onPause}
              >
                {paused ? (
                  <>
                    <Play className="h-4 w-4 mr-1" />
                    Resume
                  </>
                ) : (
                  <>
                    <Pause className="h-4 w-4 mr-1" />
                    Pause
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
