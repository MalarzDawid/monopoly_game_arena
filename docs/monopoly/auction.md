## Auction

Auctions are started when a player declines to purchase an unowned property. The auction system ensures that properties always find an owner.

### Auction Rules

When a player lands on an unowned property and declines to buy it:

1. **Auction starts** - The declining player (initiator) automatically places a starting bid of **10% of the property's price**
2. **All active players participate** - Including the initiator (per official Monopoly rules)
3. **Bidding continues** - Players can bid higher or pass
4. **Auction ends** when only one bidder remains (all others have passed)
5. **Winner pays their bid amount** - Not the original property price

### Key Feature: Guaranteed Owner

The initiator's automatic 10% bid ensures that:
- **Properties always have an owner** after auction
- If all other players pass, initiator wins at 10% price
- No "stuck" auctions where nobody bids

### Example Flow

```
1. Alice lands on Boardwalk ($400) and declines to buy
2. Auction starts:
   - Alice automatically bids $40 (10% of $400)
3. Bob bids $50
4. Charlie passes
5. Alice bids $60
6. Bob passes
7. Auction ends: Alice wins Boardwalk for $60
```

### Auction Class

```python
from monopoly.auction import Auction
from monopoly.money import EventLog

event_log = EventLog()
auction = Auction(
    property_position=39,          # Boardwalk
    property_name="Boardwalk",
    eligible_player_ids=[0, 1, 2],
    event_log=event_log,
    initiator_id=0,               # Alice started the auction
    property_price=400,           # For calculating 10% starting bid
)

# Alice already has $40 bid
print(auction.current_bid)      # 40
print(auction.high_bidder)      # 0 (Alice)

# Bob outbids
auction.place_bid(1, 50)        # True

# Charlie passes
auction.pass_turn(2)

# Alice outbids
auction.place_bid(0, 60)        # True

# Bob passes
auction.pass_turn(1)

# Auction complete
print(auction.is_complete)      # True
print(auction.get_winner())     # 0 (Alice)
print(auction.get_winning_bid()) # 60
```

### Starting an Auction

Auctions are typically started via `GameState.start_auction()`:

```python
# Player 0 declines to buy property at position 1
auction = game_state.start_auction(
    position=1,
    initiator_id=0  # Player who declined
)
```

Or via the rules API when handling `DECLINE_PURCHASE`:

```python
from monopoly.rules import apply_action
from monopoly.game import ActionType

action = Action(ActionType.DECLINE_PURCHASE, position=1)
apply_action(game_state, action)  # Starts auction with current player as initiator
```

### Bidding and Passing

Players interact with the auction using `BID` and `PASS_AUCTION` actions:

```python
# Place a bid
bid_action = Action(ActionType.BID, amount=100)
apply_action(game_state, bid_action)

# Pass on the auction
pass_action = Action(ActionType.PASS_AUCTION)
apply_action(game_state, pass_action)
```

### Bid Limits

Each player has a maximum number of bids (default: 3) to prevent infinite bidding wars:

```python
auction = Auction(
    ...,
    max_bids_per_player=3,  # Default
)
```

When a player exhausts their bids, they are automatically passed.

### Minimum Bid Rules

- **Starting bid**: 10% of property price (minimum $1)
- **Subsequent bids**: Must be higher than current bid
- **Invalid bids** (too low): Player is automatically passed

### Events Logged

The auction system logs the following events:

| Event | Description |
|-------|-------------|
| `AUCTION_START` | Auction begins, includes initiator and starting bid |
| `AUCTION_BID` | Player places a bid |
| `AUCTION_PASS` | Player passes |
| `AUCTION_END` | Auction complete, winner determined |

### Resolving the Auction

After the auction completes, call `resolve_auction()` to transfer property and deduct payment:

```python
if auction.is_complete:
    game_state.resolve_auction(auction)
    # Winner now owns the property
    # Winner's cash reduced by winning bid
```

### Edge Cases

| Scenario | Result |
|----------|--------|
| All others pass immediately | Initiator wins at 10% price |
| Initiator passes, others bid | Highest bidder wins |
| Only one eligible player | Wins at 10% price automatically |
| Player can't afford their bid | Handled by game rules (bankruptcy) |

### Reference

::: monopoly.auction.Auction
