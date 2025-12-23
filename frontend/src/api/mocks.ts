import type { GameSnapshot, GameStats, GameEvent, GameSummary, Player } from '../types/game'

export const mockPlayers: Player[] = [
  {
    player_id: 0,
    name: 'Player 1',
    cash: 1500,
    position: 0,
    in_jail: false,
    jail_turns: 0,
    jail_cards: 0,
    is_bankrupt: false,
    properties: [
      { position: 1, name: 'Mediterranean Avenue', houses: 0, mortgaged: false, color_group: 'brown' },
      { position: 3, name: 'Baltic Avenue', houses: 0, mortgaged: false, color_group: 'brown' },
    ],
  },
  {
    player_id: 1,
    name: 'Player 2',
    cash: 1200,
    position: 5,
    in_jail: false,
    jail_turns: 0,
    jail_cards: 1,
    is_bankrupt: false,
    properties: [
      { position: 11, name: 'St. Charles Place', houses: 1, mortgaged: false, color_group: 'pink' },
      { position: 13, name: 'States Avenue', houses: 0, mortgaged: false, color_group: 'pink' },
    ],
  },
  {
    player_id: 2,
    name: 'Player 3',
    cash: 800,
    position: 10,
    in_jail: true,
    jail_turns: 2,
    jail_cards: 0,
    is_bankrupt: false,
    properties: [
      { position: 21, name: 'Kentucky Avenue', houses: 0, mortgaged: false, color_group: 'red' },
    ],
  },
  {
    player_id: 3,
    name: 'Player 4',
    cash: 2100,
    position: 28,
    in_jail: false,
    jail_turns: 0,
    jail_cards: 0,
    is_bankrupt: false,
    properties: [
      { position: 31, name: 'Pacific Avenue', houses: 2, mortgaged: false, color_group: 'green' },
      { position: 32, name: 'North Carolina Avenue', houses: 2, mortgaged: false, color_group: 'green' },
      { position: 39, name: 'Boardwalk', houses: 1, mortgaged: false, color_group: 'blue' },
    ],
  },
]

export const mockSnapshot: GameSnapshot = {
  turn_number: 42,
  current_player_id: 1,
  players: mockPlayers,
  bank: {
    houses_available: 20,
    hotels_available: 10,
  },
  auction: null,
  decks: {
    chance: { cards_remaining: 14, discard_count: 2, held_count: 0 },
    community_chest: { cards_remaining: 15, discard_count: 1, held_count: 0 },
  },
}

export const mockStats: GameStats = {
  total_turns: 42,
  total_transactions: 156,
  total_rent_paid: 4250,
  total_properties_bought: 18,
  bankruptcies: 0,
  cash_in_circulation: 5600,
  avg_rent_per_turn: 101,
  player_stats: [
    { player_id: 0, name: 'Player 1', total_rent_collected: 850, total_rent_paid: 320, properties_owned: 2, houses_built: 0, net_worth: 2150, roi: 1.65 },
    { player_id: 1, name: 'Player 2', total_rent_collected: 620, total_rent_paid: 450, properties_owned: 2, houses_built: 1, net_worth: 1850, roi: 1.38 },
    { player_id: 2, name: 'Player 3', total_rent_collected: 380, total_rent_paid: 880, properties_owned: 1, houses_built: 0, net_worth: 1200, roi: 0.43 },
    { player_id: 3, name: 'Player 4', total_rent_collected: 1200, total_rent_paid: 520, properties_owned: 3, houses_built: 5, net_worth: 3800, roi: 2.31 },
  ],
}

export const mockEvents: GameEvent[] = [
  { type: 'TURN_START', text: 'Turn 42 started', player_id: 1 },
  { type: 'DICE_ROLL', text: 'Player 2 rolled 7', player_id: 1 },
  { type: 'MOVE', text: 'Player 2 moved to St. James Place', player_id: 1, position: 16 },
  { type: 'RENT_PAID', text: 'Player 2 paid $150 rent to Player 3', player_id: 1, amount: 150 },
  { type: 'CARD_DRAWN', text: 'Player 1 drew Community Chest', player_id: 0 },
  { type: 'PROPERTY_BOUGHT', text: 'Player 4 bought Pacific Avenue for $300', player_id: 3, amount: 300 },
]

export const mockHistoricalGames: GameSummary[] = [
  {
    game_id: 'abc123',
    status: 'completed',
    total_turns: 85,
    created_at: '2024-01-15T10:30:00Z',
    started_at: '2024-01-15T10:30:05Z',
    finished_at: '2024-01-15T11:15:00Z',
    winner_id: 3,
    config: { players: 4, agent: 'greedy' },
    players: [
      { player_id: 0, name: 'Player 1', agent_type: 'greedy', is_winner: false, final_cash: 500, final_net_worth: 1200 },
      { player_id: 1, name: 'Player 2', agent_type: 'greedy', is_winner: false, final_cash: 0, final_net_worth: 0 },
      { player_id: 2, name: 'Player 3', agent_type: 'greedy', is_winner: false, final_cash: 200, final_net_worth: 800 },
      { player_id: 3, name: 'Player 4', agent_type: 'greedy', is_winner: true, final_cash: 5000, final_net_worth: 8500 },
    ],
  },
  {
    game_id: 'def456',
    status: 'completed',
    total_turns: 120,
    created_at: '2024-01-14T14:20:00Z',
    started_at: '2024-01-14T14:20:10Z',
    finished_at: '2024-01-14T15:30:00Z',
    winner_id: 1,
    config: { players: 4, agent: 'random' },
    players: [
      { player_id: 0, name: 'Player 1', agent_type: 'random', is_winner: false, final_cash: 100, final_net_worth: 500 },
      { player_id: 1, name: 'Player 2', agent_type: 'random', is_winner: true, final_cash: 4500, final_net_worth: 7200 },
      { player_id: 2, name: 'Player 3', agent_type: 'random', is_winner: false, final_cash: 0, final_net_worth: 0 },
      { player_id: 3, name: 'Player 4', agent_type: 'random', is_winner: false, final_cash: 300, final_net_worth: 1100 },
    ],
  },
]

// Generate time series data for charts
export function generateCashHistory(turns: number): { turn: number; players: number[] }[] {
  const data = []
  const baseCash = [1500, 1500, 1500, 1500]
  const currentCash = [...baseCash]

  for (let turn = 0; turn <= turns; turn++) {
    data.push({
      turn,
      players: currentCash.map(c => Math.round(c)),
    })

    for (let i = 0; i < currentCash.length; i++) {
      const change = Math.floor(Math.random() * 200) - 80
      currentCash[i] = Math.max(0, currentCash[i] + change)
    }
  }

  return data
}

export const mockCashHistory = generateCashHistory(42)
