## Rules (Overview)

The engine implements the classic Monopoly rules with deterministic RNG and explicit validation. Highlights below map directly to code and tests.

### Turn Flow & Dice

- Roll two dice; move forward by their sum
- Doubles grant another roll in the same turn
- Three consecutive doubles: go to Jail immediately; turn ends
- Turn advances only when `END_TURN` or forced by rules (e.g., jail)

### Passing GO

- Passing or landing on `GO` pays `config.go_salary` (default 200)
- Salary is logged (`EventType.PASS_GO`)

### Purchases & Auctions

- Landing on an unowned purchasable space offers `BUY_PROPERTY` or `DECLINE_PURCHASE`
- Declining (or insufficient funds) triggers an auction including all active players (decliner included)
- Auctions accept any strictly higher bid; passing removes a bidder
- Auction ends when ≤1 active bidder remains; winner pays winning bid (not board price)

### Rent

- No rent for unowned or mortgaged properties
- Properties: base rent; if owner holds a full color group (and none are mortgaged), unimproved rents are doubled
- Houses/Hotels: rent by deed schedule (1–4 houses, hotel=5)
- Railroads: 25, 50, 100, 200 depending on number owned by the owner
- Utilities: 4× dice with 1 utility, 10× dice with both utilities

### Building (Houses/Hotels)

- Prerequisites to build a house:
  - Owner holds the full color group, and none in the group are mortgaged
  - Property not mortgaged and has < 4 houses
  - Even‑build rule across the color group
  - Bank has houses; player can afford the cost
- Hotels:
  - Property must have exactly 4 houses
  - All properties in the color group have 4 houses (even rule)
  - Bank has a hotel; cost is the house cost; 4 houses return to bank
- Selling buildings returns half the build cost; obey even‑sell rule
- Downgrading a hotel to 4 houses is allowed only if the bank has at least 4 houses; receive half the hotel cost

### Mortgages

- Cannot mortgage if property has buildings
- Mortgage value equals deed mortgage (typically half of price)
- Unmortgaging costs mortgage value plus `config.mortgage_interest_rate` (default 10%)

### Jail

- Sending to jail places the token at position 10; do not collect GO
- In Jail options each turn:
  - Attempt doubles: if successful, immediately move with that roll and exit jail
  - Pay fine if you have at least `config.jail_fine` (default 50)
  - Use “Get Out of Jail Free” card
- After 3 failed attempts, you must pay the fine and move by the rolled dice

### Cards (Chance & Community Chest)

- Move to a position; move relative; move to nearest railroad/utility (collect GO if passing, if card says so)
- Collect/Pay fixed amounts; pay per house vs. per hotel
- Collect from players or pay to players
- Go To Jail; Get Out of Jail Free (held until used, tracked by the deck)

### Trading

- Propose trade to another player: properties, cash, jail cards
- Validation:
  - Both players exist and are not bankrupt
  - Offerer owns offered properties; receiver owns requested properties
  - No buildings on properties being traded
  - Cash and jail card quantities must be available
  - Mortgaged properties can be traded; recipient immediately pays a 10% mortgage transfer fee
- Recipient can accept or reject; proposer can cancel pending offers

### Taxes

- Income Tax and Luxury Tax charge fixed amounts per the board
- If insufficient funds, a pending tax payment is set; player must raise cash or declare bankruptcy

### Bankruptcy & Endgame

- Declaring bankruptcy:
  - Sell all buildings at half cost; add proceeds to debtor’s cash
  - Transfer properties to creditor (player) with 10% fees for mortgaged properties
  - If to the bank (no creditor): properties revert to unowned (ready for future auctions)
  - Transfer jail cards to creditor, or return to the deck if no creditor
- Game ends when only one non‑bankrupt player remains
- Optional time limit (`config.time_limit_turns`): winner determined by net worth

### Events & Logging

- Every important action is logged in `EventLog` (purchases, rolls, moves, cards, auctions, trades, building, mortgage, jail events, endgame)
- `GameLogger` can flush internal events to JSONL and (optionally) a database
