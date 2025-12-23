# Monopoly Analytics Frontend

Modern analytics dashboard for the Monopoly game simulator. Built with React, TypeScript, and Vite.

## Tech Stack

- **React 19** + TypeScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - Accessible UI components
- **React Router** - Client-side routing
- **TanStack Query** - Data fetching and caching
- **ECharts** - Interactive charts
- **Lucide React** - Beautiful icons

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (port 3000)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
src/
├── api/
│   ├── client.ts       # API client with fetch wrapper
│   └── mocks.ts        # Mock data for fallback
├── components/
│   ├── ui/             # shadcn/ui base components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── badge.tsx
│   │   ├── tabs.tsx
│   │   ├── select.tsx
│   │   ├── table.tsx
│   │   ├── input.tsx
│   │   └── skeleton.tsx
│   ├── layout/         # App layout components
│   │   ├── MainLayout.tsx
│   │   ├── Sidebar.tsx
│   │   └── Topbar.tsx
│   ├── dashboard/      # Dashboard-specific components
│   │   ├── KpiCard.tsx
│   │   ├── KpiGrid.tsx
│   │   ├── TimeSeriesChart.tsx
│   │   ├── BarChart.tsx
│   │   └── PlayersTable.tsx
│   └── watch/          # Watch page components
│       ├── MonopolyBoardSvg.tsx
│       ├── EventFeed.tsx
│       ├── PlayerCards.tsx
│       └── GameControls.tsx
├── hooks/
│   └── useGameData.ts  # React Query hooks for game data
├── lib/
│   └── utils.ts        # Utility functions (cn, formatters)
├── pages/
│   ├── dashboard/
│   │   └── DashboardPage.tsx
│   └── watch/
│       └── WatchPage.tsx
├── types/
│   └── game.ts         # TypeScript interfaces
├── App.tsx             # Main app with routing
├── main.tsx            # Entry point
└── index.css           # Global styles + Tailwind
```

## Features

### Dashboard (`/dashboard`)

- **KPI Cards** - Key metrics: turns, cash in circulation, transactions, properties, rent, bankruptcies
- **Time Series Chart** - Cash over time per player
- **Bar Charts** - Rent collected, net worth, properties owned
- **Player Rankings Table** - Sortable table with ROI indicators
- **Game Selector** - Switch between historical games
- **Time Range Filter** - 7D / 30D / 90D filtering

### Watch Game (`/watch`)

- **Game Creation** - Create new games with configurable agents
- **Game Board** - SVG visualization of Monopoly board with player positions
- **Player Cards** - Current cash, properties, jail status
- **Event Feed** - Real-time game events
- **Game Controls** - Pause/resume, speed adjustment

## API Integration

The frontend connects to the Monopoly backend API at `http://localhost:8000` (configurable via `VITE_API_URL`).

### Key Endpoints Used

| Endpoint | Description |
|----------|-------------|
| `POST /games` | Create new game |
| `GET /games/{id}/snapshot` | Current game state |
| `GET /games/{id}/status` | Game status (turn, phase, paused) |
| `GET /games/{id}/turns/{n}` | Events for specific turn |
| `GET /api/games` | List historical games |
| `GET /api/games/{id}/stats` | Game statistics |

### Real-time Updates

Data is refreshed using React Query's `refetchInterval` (polling every 2 seconds). If the API is unavailable, mock data is displayed with a warning banner.

## Configuration

### Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

### Proxy Configuration

The Vite dev server proxies `/api` and `/games` routes to the backend:

```typescript
// vite.config.ts
server: {
  port: 3000,
  proxy: {
    '/api': { target: 'http://localhost:8000' },
    '/games': { target: 'http://localhost:8000' },
  },
}
```

## Development

### Adding New Components

UI components follow shadcn/ui patterns:

```tsx
import { cn } from '@/lib/utils'

export function MyComponent({ className, ...props }) {
  return (
    <div className={cn('base-styles', className)} {...props} />
  )
}
```

### Adding New API Hooks

Use TanStack Query for data fetching:

```tsx
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'

export function useMyData(id: string) {
  return useQuery({
    queryKey: ['myData', id],
    queryFn: () => api.getMyData(id),
    refetchInterval: 2000,
  })
}
```

## Build

```bash
# Production build
npm run build

# Output in dist/
```

The build outputs static files that can be served from any static file server or integrated with the backend.

## License

MIT
