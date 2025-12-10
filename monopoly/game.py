"""
Main game engine and state management.
"""

import random
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from monopoly.board import Board
from monopoly.player import Player, PlayerState, PropertyOwnership
from monopoly.config import GameConfig
from monopoly.spaces import (
    PropertySpace,
    RailroadSpace,
    UtilitySpace,
    TaxSpace,
    SpaceType,
)
from monopoly.cards import Card, CardType, create_chance_deck, create_community_chest_deck, Deck
from monopoly.money import Bank, EventLog, EventType
from monopoly.auction import Auction
from monopoly.trade import TradeManager, TradeOffer, Trade

class ActionType(Enum):
    """Types of actions a player can take."""

    ROLL_DICE = "roll_dice"
    BUY_PROPERTY = "buy_property"
    DECLINE_PURCHASE = "decline_purchase"
    BID = "bid"
    PASS_AUCTION = "pass_auction"
    BUILD_HOUSE = "build_house"
    BUILD_HOTEL = "build_hotel"
    SELL_BUILDING = "sell_building"
    MORTGAGE_PROPERTY = "mortgage_property"
    UNMORTGAGE_PROPERTY = "unmortgage_property"
    PAY_JAIL_FINE = "pay_jail_fine"
    USE_JAIL_CARD = "use_jail_card"
    END_TURN = "end_turn"
    DECLARE_BANKRUPTCY = "declare_bankruptcy"
    PROPOSE_TRADE = "propose_trade"
    ACCEPT_TRADE = "accept_trade"
    REJECT_TRADE = "reject_trade"
    CANCEL_TRADE = "cancel_trade"


class GameState:
    """
    Represents the complete state of a Monopoly game.
    This is the main interface for the game engine.
    """

    def __init__(self, config: GameConfig, players: List[Player]):
        self.config = config
        self.board = Board()
        self.bank = Bank(config.house_limit, config.hotel_limit)
        self.event_log = EventLog()

        # Initialize RNG
        self.rng = random.Random(config.seed)

        # Initialize players
        self.players: Dict[int, PlayerState] = {}
        for player in players:
            self.players[player.player_id] = PlayerState(
                player.player_id, player.name, config.starting_cash
            )

        # Property ownership tracking
        self.property_ownership: Dict[int, PropertyOwnership] = {}
        for space in self.board.spaces:
            if isinstance(space, (PropertySpace, RailroadSpace, UtilitySpace)):
                self.property_ownership[space.position] = PropertyOwnership()

        # Card decks
        self.chance_deck = create_chance_deck(self.rng)
        self.community_chest_deck = create_community_chest_deck(self.rng)

        self.trade_manager = TradeManager(self.event_log)

        # Game state
        self.current_player_index = 0
        self.turn_number = 0
        self.active_auction: Optional[Auction] = None
        self.pending_rent_payment: Optional[Tuple[int, int, int]] = None  # (payer_id, owner_id, amount)
        self.pending_tax_payment: Optional[Tuple[int, int]] = None  # (payer_id, amount)
        self.game_over = False
        self.winner: Optional[int] = None

        # Dice state
        self.last_dice_roll: Optional[Tuple[int, int]] = None
        self.pending_dice_roll = True

        self.next_rent_multiplier: Optional[float] = None

        self.event_log.log(
            EventType.GAME_START,
            details={
                "players": [p.name for p in players],
                "starting_cash": config.starting_cash,
                "seed": config.seed,
            },
        )


    @property
    def chance_cards(self):
        """Access to chance deck cards for testing."""
        return self.chance_deck.cards + self.chance_deck.discard_pile

    @property
    def community_chest_cards(self):
        """Access to community chest deck cards for testing."""
        return self.community_chest_deck.cards + self.community_chest_deck.discard_pile

    def get_current_player(self) -> PlayerState:
        """Get the current active player."""
        player_ids = sorted(self.players.keys())
        current_id = player_ids[self.current_player_index % len(player_ids)]
        return self.players[current_id]

    def get_active_players(self) -> List[PlayerState]:
        """Get all non-bankrupt players."""
        return [p for p in self.players.values() if not p.is_bankrupt]

    def roll_dice(self) -> Tuple[int, int]:
        """
        Roll two dice and return the result.
        Updates game state with the roll.
        """
        die1 = self.rng.randint(1, 6)
        die2 = self.rng.randint(1, 6)
        self.last_dice_roll = (die1, die2)
        self.pending_dice_roll = False

        current_player = self.get_current_player()
        is_doubles = die1 == die2

        self.event_log.log(
            EventType.DICE_ROLL,
            player_id=current_player.player_id,
            details={"die1": die1, "die2": die2, "total": die1 + die2, "doubles": is_doubles},
        )

        return (die1, die2)

    def move_player(self, player_id: int, spaces: int, collect_go: bool = True) -> int:
        """
        Move a player forward by the specified number of spaces.
        Returns the new position.
        """
        player = self.players[player_id]
        old_position = player.position
        new_position = (old_position + spaces) % 40

        # Check if passed GO
        if collect_go and new_position < old_position and spaces > 0:
            self._collect_go(player_id)

        player.position = new_position

        self.event_log.log(
            EventType.MOVE,
            player_id=player_id,
            details={
                "from": old_position,
                "to": new_position,
                "spaces": spaces,
            },
        )

        return new_position

    def move_player_to(self, player_id: int, position: int, collect_go: bool = True) -> None:
        """Move a player to a specific position."""
        player = self.players[player_id]
        old_position = player.position

        # Check if passed GO
        if collect_go and position < old_position:
            self._collect_go(player_id)

        player.position = position

        self.event_log.log(
            EventType.MOVE,
            player_id=player_id,
            details={
                "from": old_position,
                "to": position,
                "direct": True,
            },
        )

    def _collect_go(self, player_id: int) -> None:
        """Player collects GO salary."""
        player = self.players[player_id]
        player.cash += self.config.go_salary

        self.event_log.log(
            EventType.PASS_GO,
            player_id=player_id,
            details={"amount": self.config.go_salary, "new_balance": player.cash},
        )

    def send_to_jail(self, player_id: int) -> None:
        """Send a player to jail."""
        player = self.players[player_id]
        player.position = 10  # Jail position
        player.in_jail = True
        player.jail_turns = 0
        player.consecutive_doubles = 0

        self.event_log.log(EventType.GO_TO_JAIL, player_id=player_id)

    def attempt_jail_release(self, player_id: int) -> bool:
        """
        Player attempts to roll doubles to get out of jail.
        If successful, releases player AND moves them by the dice roll.
        Returns True if successful (rolled doubles).
        Rule: 'move out of Jail using this dice roll.'
        """
        player = self.players[player_id]
        if not player.in_jail:
            return False

        die1, die2 = self.roll_dice()
        is_doubles = die1 == die2

        player.jail_turns += 1

        self.event_log.log(
            EventType.JAIL_ATTEMPT,
            player_id=player_id,
            details={
                "attempt": player.jail_turns,
                "doubles": is_doubles,
            },
        )

        if is_doubles:
            self._release_from_jail(player_id)
            # Move by the dice roll
            total = die1 + die2
            self.move_player(player_id, total)
            return True

        # Must pay after 3 failed attempts
        if player.jail_turns >= self.config.max_jail_turns:
            if player.cash >= self.config.jail_fine:
                self.pay_jail_fine(player_id)
            else:
                # Player must raise funds or declare bankruptcy
                pass

        return False

    def process_jail_turn(self, player_id: int) -> None:
        """
        Process a complete jail turn including forced payment/release after 3 turns.
        Rule: 'After you have waited three turns, you must move out of Jail and pay £50
        before moving your token according to your dice roll.'
        """
        player = self.players[player_id]
        if not player.in_jail:
            return

        die1, die2 = self.roll_dice()
        is_doubles = die1 == die2
        player.jail_turns += 1

        if is_doubles:
            # Released and move
            self._release_from_jail(player_id)
            total = die1 + die2
            self.move_player(player_id, total)
        elif player.jail_turns >= self.config.max_jail_turns:
            # Forced release: pay fine and move
            player.cash -= self.config.jail_fine
            self._release_from_jail(player_id)
            total = die1 + die2
            self.move_player(player_id, total)
        # else: stay in jail

    def pay_jail_fine(self, player_id: int) -> bool:
        """
        Player pays fine to get out of jail.
        Returns True if successful, False if insufficient funds.
        """
        player = self.players[player_id]
        if player.cash < self.config.jail_fine:
            return False

        player.cash -= self.config.jail_fine
        self._release_from_jail(player_id)

        self.event_log.log(
            EventType.JAIL_RELEASE,
            player_id=player_id,
            details={"method": "fine", "amount": self.config.jail_fine},
        )

        return True

    def use_jail_card(self, player_id: int) -> bool:
        """
        Use a Get Out of Jail Free card.
        Returns True if successful, False if player has no card.
        """
        player = self.players[player_id]
        if player.get_out_of_jail_cards == 0:
            return False

        player.get_out_of_jail_cards -= 1
        self._release_from_jail(player_id)

        # Return card to appropriate deck (simplified: return to chance)
        # In full implementation, track which deck the card came from
        from monopoly.cards import Card, CardType

        card = Card("Get Out of Jail Free", CardType.GET_OUT_OF_JAIL)
        self.chance_deck.return_held_card(card)

        self.event_log.log(
            EventType.JAIL_RELEASE,
            player_id=player_id,
            details={"method": "card"},
        )

        return True

    def _release_from_jail(self, player_id: int) -> None:
        """Release a player from jail."""
        player = self.players[player_id]
        player.in_jail = False
        player.jail_turns = 0

    def buy_property(self, player_id: int, position: int) -> bool:
        """
        Player buys a property at the specified position.
        Returns True if successful, False otherwise.
        """
        player = self.players[player_id]
        space = self.board.get_space(position)

        # Determine price
        price = 0
        if isinstance(space, PropertySpace):
            price = space.price
        elif isinstance(space, RailroadSpace):
            price = space.price
        elif isinstance(space, UtilitySpace):
            price = space.price
        else:
            return False

        # Check ownership and funds
        ownership = self.property_ownership.get(position)
        if ownership is None or ownership.is_owned():
            return False

        if player.cash < price:
            return False

        # Execute purchase
        player.cash -= price
        player.properties.add(position)
        ownership.owner_id = player_id

        self.event_log.log(
            EventType.PURCHASE,
            player_id=player_id,
            details={
                "property": space.name,
                "position": position,
                "price": price,
                "new_balance": player.cash,
            },
        )

        return True

    def start_auction(self, position: int) -> Auction:
        """Start an auction for a property."""
        space = self.board.get_space(position)
        eligible_players = [p.player_id for p in self.get_active_players()]

        auction = Auction(position, space.name, eligible_players, self.event_log)
        self.active_auction = auction
        return auction

    def resolve_auction(self, auction: Auction) -> None:
        """
        Finalize an auction by transferring property and money.
        Winner pays the bid amount (not the board price).
        """
        if not auction.is_complete:
            return

        winner_id = auction.get_winner()
        if winner_id is None:
            # No bids - property remains unowned
            return

        winning_bid = auction.get_winning_bid()
        position = auction.property_position

        # Transfer cash and property
        winner = self.players[winner_id]
        winner.cash -= winning_bid
        winner.properties.add(position)
        self.property_ownership[position].owner_id = winner_id

        # Clear active auction
        if self.active_auction == auction:
            self.active_auction = None

    def calculate_rent(self, property_position: int, dice_roll: Optional[int] = None) -> int:
        """
        Calculate the rent owed for landing on a property.

        Args:
            property_position: Position of the property
            dice_roll: Optional dice roll (needed for utilities)

        Returns:
            Rent amount
        """
        ownership = self.property_ownership[property_position]
        if not ownership.is_owned() or ownership.is_mortgaged:
            return 0

        space = self.board.get_space(property_position)
        owner_id = ownership.owner_id
        owner = self.players[owner_id]

        rent = 0

        if isinstance(space, PropertySpace):
            has_monopoly = self._has_monopoly(owner_id, space.color_group)
            rent = space.get_rent(ownership.houses, has_monopoly)

        elif isinstance(space, RailroadSpace):
            railroads_owned = sum(
                1
                for pos in self.board.get_all_railroads()
                if self.property_ownership[pos].owner_id == owner_id
            )
            rent = space.get_rent(railroads_owned)

            # Apply special multiplier if set (from "nearest railroad" card)
            if self.next_rent_multiplier is not None:
                rent = int(rent * self.next_rent_multiplier)

        elif isinstance(space, UtilitySpace):
            if dice_roll is None:
                dice_roll = sum(self.last_dice_roll) if self.last_dice_roll else 0

            # Check for special multiplier (from "nearest utility" card)
            if self.next_rent_multiplier is not None:
                # Special case: multiply dice by the specified value (e.g., 10)
                rent = int(dice_roll * self.next_rent_multiplier)
            else:
                # Normal utility rent
                utilities_owned = sum(
                    1
                    for pos in self.board.get_all_utilities()
                    if self.property_ownership[pos].owner_id == owner_id
                )
                rent = space.get_rent(dice_roll, utilities_owned)

        return rent

    def pay_rent(self, payer_id: int, owner_id: int, amount: int) -> bool:
        """
        Player pays rent to property owner.
        Returns True if successful, False if insufficient funds.
        """
        payer = self.players[payer_id]
        owner = self.players[owner_id]

        if payer.cash < amount:
            # Player needs to raise funds or declare bankruptcy
            self.pending_rent_payment = (payer_id, owner_id, amount)
            return False

        payer.cash -= amount
        owner.cash += amount
        self.pending_rent_payment = None  # Clear any pending payment

        self.next_rent_multiplier = None

        self.event_log.log(
            EventType.RENT_PAYMENT,
            player_id=payer_id,
            details={
                "owner": owner_id,
                "amount": amount,
                "payer_balance": payer.cash,
                "owner_balance": owner.cash,
            },
        )

        return True

    def pay_tax(self, player_id: int, amount: int) -> bool:
        """
        Player pays tax to the bank.
        Returns True if successful, False if insufficient funds.
        """
        player = self.players[player_id]

        if player.cash < amount:
            # Player needs to raise funds or declare bankruptcy
            self.pending_tax_payment = (player_id, amount)
            return False

        player.cash -= amount
        self.pending_tax_payment = None  # Clear any pending payment

        self.event_log.log(
            EventType.TAX_PAYMENT,
            player_id=player_id,
            details={"amount": amount, "new_balance": player.cash},
        )

        return True

    def _has_monopoly(self, player_id: int, color_group: str) -> bool:
        """
        Check if a player owns all properties in a color group.
        Returns False if any property in the group is mortgaged.
        Rule: 'an owner who owns a whole colour-group may not collect double rent if any one Site there is mortgaged.'
        """
        group_positions = self.board.get_color_group(color_group)
        # Must own all and none can be mortgaged
        for pos in group_positions:
            ownership = self.property_ownership[pos]
            if ownership.owner_id != player_id:
                return False
            if ownership.is_mortgaged:
                return False
        return True

    def can_build_house(self, player_id: int, property_position: int) -> bool:
        """
        Check if a player can build a house on a property.

        Requirements:
        - Player owns the property
        - Player has monopoly on color group (none mortgaged)
        - Property is not mortgaged
        - NO property in the color group is mortgaged
        - Property has less than 4 houses
        - Even build rule is satisfied
        - Houses are available in bank
        - Player can afford it
        Rule: 'no building on ANY property in that colour-group... until the mortgage has been repaid'
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        if ownership.is_mortgaged or ownership.houses >= 4:
            return False

        space = self.board.get_property_space(property_position)
        if not space:
            return False

        # This already checks that no property in group is mortgaged
        if not self._has_monopoly(player_id, space.color_group):
            return False

        # Check even build rule
        if not self._can_build_evenly(property_position, space.color_group):
            return False

        # Check bank supply and player funds
        if not self.bank.can_buy_houses(1):
            return False

        player = self.players[player_id]
        if player.cash < space.house_cost:
            return False

        return True

    def can_build_hotel(self, player_id: int, property_position: int) -> bool:
        """
        Check if a player can build a hotel on a property.

        Requirements:
        - Same as house, plus:
        - Property has exactly 4 houses
        - ALL properties in the color group have 4 houses (even build rule for hotel)
        - Hotel is available in bank
        Rule: 'You must have four Houses on each Site... before you can buy a Hotel'
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        if ownership.is_mortgaged or ownership.houses != 4:
            return False

        space = self.board.get_property_space(property_position)
        if not space:
            return False

        if not self._has_monopoly(player_id, space.color_group):
            return False

        # Check that ALL properties in group have 4 houses
        group_positions = self.board.get_color_group(space.color_group)
        for pos in group_positions:
            if self.property_ownership[pos].houses != 4:
                return False

        if not self.bank.can_buy_hotel():
            return False

        player = self.players[player_id]
        if player.cash < space.house_cost:
            return False

        return True

    def _can_build_evenly(self, property_position: int, color_group: str) -> bool:
        """
        Check if building on this property satisfies the even build rule.
        The property to build on must not already have more houses than any other in the group.
        """
        group_positions = self.board.get_color_group(color_group)
        current_houses = self.property_ownership[property_position].houses

        for pos in group_positions:
            if pos != property_position:
                other_houses = self.property_ownership[pos].houses
                if current_houses > other_houses:
                    # This property already has more than another - can't build here
                    return False

        return True

    def _can_sell_evenly(self, property_position: int, color_group: str) -> bool:
        """
        Check if selling from this property satisfies the even build rule.
        The property to sell from must not have fewer houses than any other in the group.
        """
        group_positions = self.board.get_color_group(color_group)
        current_houses = self.property_ownership[property_position].houses

        for pos in group_positions:
            if pos != property_position:
                other_houses = self.property_ownership[pos].houses
                if current_houses < other_houses:
                    # This property already has fewer - can't sell from it
                    return False

        return True

    def build_house(self, player_id: int, property_position: int) -> bool:
        """
        Build a house on a property.
        Returns True if successful, False otherwise.
        """
        if not self.can_build_house(player_id, property_position):
            return False

        space = self.board.get_property_space(property_position)
        player = self.players[player_id]
        ownership = self.property_ownership[property_position]

        # Execute build
        player.cash -= space.house_cost
        self.bank.buy_houses(1)
        ownership.houses += 1

        self.event_log.log(
            EventType.BUILD_HOUSE,
            player_id=player_id,
            details={
                "property": space.name,
                "position": property_position,
                "cost": space.house_cost,
                "houses": ownership.houses,
                "new_balance": player.cash,
            },
        )

        return True

    def build_hotel(self, player_id: int, property_position: int) -> bool:
        """
        Build a hotel on a property (requires 4 houses).
        Returns True if successful, False otherwise.
        """
        if not self.can_build_hotel(player_id, property_position):
            return False

        space = self.board.get_property_space(property_position)
        player = self.players[player_id]
        ownership = self.property_ownership[property_position]

        # Execute build
        player.cash -= space.house_cost
        self.bank.buy_hotel(return_houses=4)
        ownership.houses = 5  # 5 represents a hotel

        self.event_log.log(
            EventType.BUILD_HOTEL,
            player_id=player_id,
            details={
                "property": space.name,
                "position": property_position,
                "cost": space.house_cost,
                "new_balance": player.cash,
            },
        )

        return True

    def sell_building(self, player_id: int, property_position: int) -> bool:
        """
        Sell a building (house or hotel) back to the bank for half cost.
        Returns True if successful, False otherwise.
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        if ownership.houses == 0:
            return False

        space = self.board.get_property_space(property_position)
        if not space:
            return False

        # Check even sell rule
        if not self._can_sell_evenly(property_position, space.color_group):
            return False

        player = self.players[player_id]
        sale_price = space.house_cost // 2

        # Execute sale
        if ownership.houses == 5:  # Hotel
            self.bank.sell_hotel()
            ownership.houses = 4  # Back to 4 houses
            building_type = "hotel"
        else:  # House
            self.bank.sell_houses(1)
            ownership.houses -= 1
            building_type = "house"

        player.cash += sale_price

        self.event_log.log(
            EventType.SELL_BUILDING,
            player_id=player_id,
            details={
                "property": space.name,
                "position": property_position,
                "type": building_type,
                "sale_price": sale_price,
                "houses": ownership.houses,
                "new_balance": player.cash,
            },
        )

        return True

    def downgrade_hotel(self, player_id: int, property_position: int) -> bool:
        """
        Downgrade a hotel to 4 houses, receiving half the hotel cost.
        Rule: 'receive in exchange four Houses as well as money for the Hotel (i.e. half its cost)'
        Rule: 'when selling Hotels you cannot replace them with Houses if there are none left.'
        Returns True if successful, False otherwise.
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        if ownership.houses != 5:  # Must be a hotel
            return False

        # Check if bank has 4 houses available
        if not self.bank.can_sell_houses(4):
            return False

        space = self.board.get_property_space(property_position)
        if not space:
            return False

        player = self.players[player_id]
        sale_price = space.house_cost // 2  # Half the hotel cost

        # Execute downgrade
        self.bank.sell_hotel()  # Return hotel to bank
        self.bank.buy_houses(4)  # Take 4 houses from bank
        ownership.houses = 4
        player.cash += sale_price

        self.event_log.log(
            EventType.SELL_BUILDING,
            player_id=player_id,
            details={
                "property": space.name,
                "position": property_position,
                "type": "hotel_downgrade",
                "sale_price": sale_price,
                "houses": 4,
                "new_balance": player.cash,
            },
        )

        return True

    def mortgage_property(self, player_id: int, property_position: int) -> bool:
        """
        Mortgage a property to raise funds.
        Cannot mortgage if property has buildings.
        Returns True if successful, False otherwise.
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        if ownership.is_mortgaged or ownership.houses > 0:
            return False

        space = self.board.get_space(property_position)
        mortgage_value = 0

        if isinstance(space, PropertySpace):
            mortgage_value = space.mortgage_value
        elif isinstance(space, (RailroadSpace, UtilitySpace)):
            mortgage_value = space.mortgage_value
        else:
            return False

        # Execute mortgage
        player = self.players[player_id]
        player.cash += mortgage_value
        ownership.is_mortgaged = True

        self.event_log.log(
            EventType.MORTGAGE,
            player_id=player_id,
            details={
                "property": space.name,
                "position": property_position,
                "value": mortgage_value,
                "new_balance": player.cash,
            },
        )

        return True

    def unmortgage_property(self, player_id: int, property_position: int) -> bool:
        """
        Unmortgage a property by paying mortgage value + interest.
        Returns True if successful, False otherwise.
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        if not ownership.is_mortgaged:
            return False

        space = self.board.get_space(property_position)
        mortgage_value = 0

        if isinstance(space, PropertySpace):
            mortgage_value = space.mortgage_value
        elif isinstance(space, (RailroadSpace, UtilitySpace)):
            mortgage_value = space.mortgage_value
        else:
            return False

        cost = int(mortgage_value * (1 + self.config.mortgage_interest_rate))
        player = self.players[player_id]

        if player.cash < cost:
            return False

        # Execute unmortgage
        player.cash -= cost
        ownership.is_mortgaged = False

        self.event_log.log(
            EventType.UNMORTGAGE,
            player_id=player_id,
            details={
                "property": space.name,
                "position": property_position,
                "cost": cost,
                "new_balance": player.cash,
            },
        )

        return True

    def draw_card(self, deck_type: str) -> Card:
        """Draw a card from the specified deck ('chance' or 'community_chest')."""
        if deck_type == "chance":
            card = self.chance_deck.draw()
            deck = self.chance_deck
        else:
            card = self.community_chest_deck.draw()
            deck = self.community_chest_deck

        current_player = self.get_current_player()
        self.event_log.log(
            EventType.CARD_DRAW,
            player_id=current_player.player_id,
            details={"deck": deck_type, "card": card.description},
        )

        # Execute immediately and discard
        self.execute_card(card, current_player.player_id, deck)

        return card

    def execute_card(self, card: Card, player_id: int, deck=None) -> None:
        """Execute the effect of a drawn card."""
        if deck is None:
            # Default to chance deck for backwards compatibility with tests
            deck = self.chance_deck
        player = self.players[player_id]

        self.event_log.log(
            EventType.CARD_EFFECT,
            player_id=player_id,
            details={"card": card.description, "type": card.card_type.value},
        )

        if card.card_type == CardType.MOVE_TO:
            self.move_player_to(player_id, card.target_position, card.collect_go)

        elif card.card_type == CardType.MOVE_SPACES:
            self.move_player(player_id, card.value, card.collect_go)


        elif card.card_type == CardType.MOVE_TO_NEAREST:

            if card.target_type == "railroad":

                target = self.board.find_nearest_railroad(player.position)

            else:  # utility

                target = self.board.find_nearest_utility(player.position)

            # Set special rent multiplier if specified

            if card.special_rent_multiplier is not None:
                self.next_rent_multiplier = card.special_rent_multiplier

            self.move_player_to(player_id, target, card.collect_go)

        elif card.card_type == CardType.COLLECT:
            player.cash += card.value

        elif card.card_type == CardType.PAY:
            player.cash -= card.value

        elif card.card_type == CardType.PAY_PER_HOUSE:
            total = 0
            for pos in player.properties:
                ownership = self.property_ownership[pos]
                if ownership.houses == 5:  # Hotel
                    total += card.value * 4  # Hotel cost is 4x house cost
                else:
                    total += card.value * ownership.houses
            player.cash -= total

        elif card.card_type == CardType.PAY_PER_BUILDING:
            # Different costs for houses vs hotels
            total = 0
            for pos in player.properties:
                ownership = self.property_ownership[pos]
                if ownership.houses == 5:  # Hotel
                    total += card.value2  # Per-hotel cost
                else:
                    total += card.value * ownership.houses  # Per-house cost
            player.cash -= total

        elif card.card_type == CardType.COLLECT_FROM_PLAYERS:
            for other_id, other_player in self.players.items():
                if other_id != player_id and not other_player.is_bankrupt:
                    transfer = min(card.value, other_player.cash)
                    other_player.cash -= transfer
                    player.cash += transfer

        elif card.card_type == CardType.PAY_TO_PLAYERS:
            for other_id, other_player in self.players.items():
                if other_id != player_id and not other_player.is_bankrupt:
                    transfer = min(card.value, player.cash)
                    player.cash -= transfer
                    other_player.cash += transfer

        elif card.card_type == CardType.GO_TO_JAIL:
            self.send_to_jail(player_id)

        elif card.card_type == CardType.GET_OUT_OF_JAIL:
            player.get_out_of_jail_cards += 1
            deck.hold_card(card)
            # Don't discard - card is held
            return

        # Return card to discard pile
        deck.discard(card)

    def declare_bankruptcy(self, player_id: int, creditor_id: Optional[int] = None) -> None:
        """
        Player declares bankruptcy.
        Rule: 'Houses and Hotels are sold to the Bank at half their original cost and that player receives any cash'
        Rule: 'he must immediately pay 10% and then choose whether to retain the mortgage or pay it off'
        Rule: 'You must return "Get Out Of Jail Free" cards to the bottom of the relevant pile.'
        If creditor is specified, transfer assets to them.
        Otherwise, assets go to bank and are auctioned.
        """
        player = self.players[player_id]
        player.is_bankrupt = True

        # First, sell all buildings to the bank at half cost
        properties = list(player.properties)
        building_cash = 0
        for pos in properties:
            ownership = self.property_ownership[pos]
            if ownership.houses > 0:
                space = self.board.get_property_space(pos)
                if space:
                    # Sell all houses/hotels
                    if ownership.houses == 5:  # Hotel
                        building_cash += space.house_cost // 2
                        self.bank.sell_hotel()
                    else:
                        building_cash += (ownership.houses * space.house_cost) // 2
                        self.bank.sell_houses(ownership.houses)
                    ownership.houses = 0

        # Add building sale proceeds to player's cash
        player.cash += building_cash

        # Transfer properties
        mortgage_transfer_fee = 0
        for pos in properties:
            ownership = self.property_ownership[pos]

            if creditor_id is not None:
                # Transfer to creditor
                creditor = self.players[creditor_id]
                creditor.properties.add(pos)
                ownership.owner_id = creditor_id

                # Creditor must pay 10% fee on mortgaged properties
                if ownership.is_mortgaged:
                    space = self.board.get_space(pos)
                    if hasattr(space, 'mortgage_value'):
                        fee = int(space.mortgage_value * 0.10)
                        mortgage_transfer_fee += fee
            else:
                # Return to bank (will be auctioned)
                ownership.owner_id = None
                ownership.houses = 0
                ownership.is_mortgaged = False

            player.properties.remove(pos)

        # Transfer cash to creditor (minus mortgage fees)
        if creditor_id is not None:
            self.players[creditor_id].cash += player.cash
            self.players[creditor_id].cash -= mortgage_transfer_fee

        # Handle Get Out of Jail cards
        if creditor_id is not None:
            # Transfer to creditor
            self.players[creditor_id].get_out_of_jail_cards += player.get_out_of_jail_cards
        else:
            # Return to deck bottom
            from monopoly.cards import Card, CardType
            for _ in range(player.get_out_of_jail_cards):
                card = Card("Get Out of Jail Free", CardType.GET_OUT_OF_JAIL)
                # Return to chance deck (simplified - in real game would track which deck)
                self.chance_deck.discard(card)

        player.cash = 0
        player.get_out_of_jail_cards = 0

        self.event_log.log(
            EventType.BANKRUPTCY,
            player_id=player_id,
            details={"creditor": creditor_id, "properties": properties, "building_cash": building_cash},
        )

        # Check for game end
        active_players = self.get_active_players()
        if len(active_players) == 1:
            self.game_over = True
            self.winner = active_players[0].player_id
            self.event_log.log(
                EventType.GAME_END,
                player_id=self.winner,
                details={"winner": active_players[0].name},
            )

    def end_turn(self) -> None:
        """End the current player's turn and advance to next player."""
        current = self.get_current_player()
        current.consecutive_doubles = 0
        self.pending_dice_roll = True
        self.last_dice_roll = None

        # Advance to next non-bankrupt player
        player_ids = sorted(self.players.keys())
        for _ in range(len(player_ids)):
            self.current_player_index = (self.current_player_index + 1) % len(player_ids)
            next_player = self.get_current_player()
            if not next_player.is_bankrupt:
                break

        self.turn_number += 1

        # Check time limit
        if self.config.time_limit_turns and self.turn_number >= self.config.time_limit_turns:
            self._end_game_by_time_limit()

        self.event_log.log(
            EventType.TURN_START,
            player_id=self.get_current_player().player_id,
            details={"turn": self.turn_number},
        )

    def _end_game_by_time_limit(self) -> None:
        """End game due to time limit and determine winner by net worth."""
        max_worth = -1
        winner_id = None

        for player in self.get_active_players():
            worth = self._calculate_net_worth(player.player_id)
            if worth > max_worth:
                max_worth = worth
                winner_id = player.player_id

        self.game_over = True
        self.winner = winner_id
        self.event_log.log(
            EventType.GAME_END,
            player_id=winner_id,
            details={"reason": "time_limit", "net_worth": max_worth},
        )

    def _calculate_net_worth(self, player_id: int) -> int:
        """Calculate a player's total net worth (cash + property values)."""
        player = self.players[player_id]
        worth = player.cash

        for pos in player.properties:
            space = self.board.get_space(pos)
            ownership = self.property_ownership[pos]

            # Add property value
            if isinstance(space, PropertySpace):
                worth += space.price
                worth += ownership.houses * space.house_cost
            elif isinstance(space, (RailroadSpace, UtilitySpace)):
                worth += space.price

            # Subtract mortgage if mortgaged
            if ownership.is_mortgaged:
                if isinstance(space, PropertySpace):
                    worth -= space.mortgage_value
                elif isinstance(space, (RailroadSpace, UtilitySpace)):
                    worth -= space.mortgage_value

        return worth

    # === TRADING METHODS === (dodaj to przed def create_game)

    def can_trade_property(self, player_id: int, property_position: int) -> bool:
        """
        Check if a property can be traded.

        Rules:
        - Player must own it
        - Cannot have buildings on it
        - Cannot trade if ANY property in color group has buildings
        """
        ownership = self.property_ownership.get(property_position)
        if not ownership or ownership.owner_id != player_id:
            return False

        # Cannot trade property with buildings
        if ownership.houses > 0:
            return False

        # Check if it's a property space (has color group)
        space = self.board.get_property_space(property_position)
        if space:
            # Cannot trade if any property in group has buildings
            group_positions = self.board.get_color_group(space.color_group)
            for pos in group_positions:
                if self.property_ownership[pos].houses > 0:
                    return False

        return True

    def validate_trade_offer(self, player_id: int, offer: TradeOffer) -> tuple[bool, str]:
        """
        Validate that a player can offer the specified items.

        Returns:
            (valid, error_message) tuple
        """
        player = self.players[player_id]

        # Check cash
        if offer.cash > player.cash:
            return False, f"Insufficient cash: has ${player.cash}, offering ${offer.cash}"

        # Check jail cards
        if offer.jail_cards > player.get_out_of_jail_cards:
            return False, f"Insufficient jail cards: has {player.get_out_of_jail_cards}, offering {offer.jail_cards}"

        # Check properties
        for pos in offer.properties:
            if pos not in player.properties:
                return False, f"Player doesn't own property at position {pos}"

            if not self.can_trade_property(player_id, pos):
                space = self.board.get_space(pos)
                return False, f"Cannot trade {space.name}: has buildings or group has buildings"

        return True, ""

    def execute_trade(self, trade: Trade) -> bool:
        """
        Execute an accepted trade, transferring all items atomically.

        Returns:
            True if successful, False if validation failed
        """
        if not trade.is_accepted:
            return False

        proposer = self.players[trade.proposer_id]
        recipient = self.players[trade.recipient_id]

        # Final validation (state might have changed)
        valid, error = self.validate_trade_offer(trade.proposer_id, trade.proposer_offer)
        if not valid:
            self.event_log.log(
                EventType.TRADE_EXECUTED,
                player_id=None,
                trade_id=trade.trade_id,
                success=False,
                error=f"Proposer validation failed: {error}",
            )
            return False

        valid, error = self.validate_trade_offer(trade.recipient_id, trade.recipient_offer)
        if not valid:
            self.event_log.log(
                EventType.TRADE_EXECUTED,
                player_id=None,
                trade_id=trade.trade_id,
                success=False,
                error=f"Recipient validation failed: {error}",
            )
            return False

        # Calculate mortgage transfer fees
        proposer_mortgage_fee = 0
        recipient_mortgage_fee = 0

        # Transfer from proposer to recipient
        proposer.cash -= trade.proposer_offer.cash
        recipient.cash += trade.proposer_offer.cash

        for pos in trade.proposer_offer.properties:
            proposer.properties.remove(pos)
            recipient.properties.add(pos)
            ownership = self.property_ownership[pos]
            ownership.owner_id = trade.recipient_id

            # Recipient pays 10% fee for mortgaged properties
            if ownership.is_mortgaged:
                space = self.board.get_space(pos)
                if hasattr(space, 'mortgage_value'):
                    fee = int(space.mortgage_value * 0.10)
                    recipient_mortgage_fee += fee

        proposer.get_out_of_jail_cards -= trade.proposer_offer.jail_cards
        recipient.get_out_of_jail_cards += trade.proposer_offer.jail_cards

        # Transfer from recipient to proposer
        recipient.cash -= trade.recipient_offer.cash
        proposer.cash += trade.recipient_offer.cash

        for pos in trade.recipient_offer.properties:
            recipient.properties.remove(pos)
            proposer.properties.add(pos)
            ownership = self.property_ownership[pos]
            ownership.owner_id = trade.proposer_id

            # Proposer pays 10% fee for mortgaged properties
            if ownership.is_mortgaged:
                space = self.board.get_space(pos)
                if hasattr(space, 'mortgage_value'):
                    fee = int(space.mortgage_value * 0.10)
                    proposer_mortgage_fee += fee

        recipient.get_out_of_jail_cards -= trade.recipient_offer.jail_cards
        proposer.get_out_of_jail_cards += trade.recipient_offer.jail_cards

        # Apply mortgage fees
        proposer.cash -= proposer_mortgage_fee
        recipient.cash -= recipient_mortgage_fee

        self.event_log.log(
            EventType.TRADE_EXECUTED,
            player_id=None,
            trade_id=trade.trade_id,
            success=True,
            proposer=trade.proposer_id,
            recipient=trade.recipient_id,
            proposer_gave=str(trade.proposer_offer),
            recipient_gave=str(trade.recipient_offer),
            proposer_mortgage_fee=proposer_mortgage_fee,
            recipient_mortgage_fee=recipient_mortgage_fee,
        )

        return True


# Funkcja create_game powinna być tutaj (bez zmian)
def create_game(config: GameConfig, players: List[Player]) -> GameState:
    """Create a new game with the specified configuration and players."""
    # ... existing code ...
def create_game(config: GameConfig, players: List[Player]) -> GameState:
    """
    Create a new game with the specified configuration and players.

    Args:
        config: Game configuration
        players: List of players (1-8 players, 2+ recommended)

    Returns:
        Initialized GameState
    """
    if len(players) < 1:
        raise ValueError("Game requires at least 1 player")

    return GameState(config, players)

def can_trade_property(self, player_id: int, property_position: int) -> bool:
    """
    Check if a property can be traded.

    Rules:
    - Player must own it
    - Cannot have buildings on it
    - Cannot trade if ANY property in color group has buildings
    """
    ownership = self.property_ownership.get(property_position)
    if not ownership or ownership.owner_id != player_id:
        return False

    # Cannot trade property with buildings
    if ownership.houses > 0:
        return False

    # Check if it's a property space (has color group)
    space = self.board.get_property_space(property_position)
    if space:
        # Cannot trade if any property in group has buildings
        group_positions = self.board.get_color_group(space.color_group)
        for pos in group_positions:
            if self.property_ownership[pos].houses > 0:
                return False

    return True

def validate_trade_offer(self, player_id: int, offer: 'TradeOffer') -> tuple[bool, str]:
    """
    Validate that a player can offer the specified items.

    Returns:
        (valid, error_message) tuple
    """
    player = self.players[player_id]

    # Check cash
    if offer.cash > player.cash:
        return False, f"Insufficient cash: has ${player.cash}, offering ${offer.cash}"

    # Check jail cards
    if offer.jail_cards > player.get_out_of_jail_cards:
        return False, f"Insufficient jail cards: has {player.get_out_of_jail_cards}, offering {offer.jail_cards}"

    # Check properties
    for pos in offer.properties:
        if pos not in player.properties:
            return False, f"Player doesn't own property at position {pos}"

        if not self.can_trade_property(player_id, pos):
            space = self.board.get_space(pos)
            return False, f"Cannot trade {space.name}: has buildings or group has buildings"

    return True, ""

def execute_trade(self, trade: 'Trade') -> bool:
    """
    Execute an accepted trade, transferring all items atomically.

    Returns:
        True if successful, False if validation failed
    """
    if not trade.is_accepted:
        return False

    proposer = self.players[trade.proposer_id]
    recipient = self.players[trade.recipient_id]

    # Final validation (state might have changed)
    valid, error = self.validate_trade_offer(trade.proposer_id, trade.proposer_offer)
    if not valid:
        self.event_log.log(
            EventType.TRADE_EXECUTED,
            details={
                "trade_id": trade.trade_id,
                "success": False,
                "error": f"Proposer validation failed: {error}",
            },
        )
        return False

    valid, error = self.validate_trade_offer(trade.recipient_id, trade.recipient_offer)
    if not valid:
        self.event_log.log(
            EventType.TRADE_EXECUTED,
            details={
                "trade_id": trade.trade_id,
                "success": False,
                "error": f"Recipient validation failed: {error}",
            },
        )
        return False

    # Calculate mortgage transfer fees
    proposer_mortgage_fee = 0
    recipient_mortgage_fee = 0

    # Transfer from proposer to recipient
    proposer.cash -= trade.proposer_offer.cash
    recipient.cash += trade.proposer_offer.cash

    for pos in trade.proposer_offer.properties:
        proposer.properties.remove(pos)
        recipient.properties.add(pos)
        ownership = self.property_ownership[pos]
        ownership.owner_id = trade.recipient_id

        # Recipient pays 10% fee for mortgaged properties
        if ownership.is_mortgaged:
            space = self.board.get_space(pos)
            if hasattr(space, 'mortgage_value'):
                fee = int(space.mortgage_value * 0.10)
                recipient_mortgage_fee += fee

    proposer.get_out_of_jail_cards -= trade.proposer_offer.jail_cards
    recipient.get_out_of_jail_cards += trade.proposer_offer.jail_cards

    # Transfer from recipient to proposer
    recipient.cash -= trade.recipient_offer.cash
    proposer.cash += trade.recipient_offer.cash

    for pos in trade.recipient_offer.properties:
        recipient.properties.remove(pos)
        proposer.properties.add(pos)
        ownership = self.property_ownership[pos]
        ownership.owner_id = trade.proposer_id

        # Proposer pays 10% fee for mortgaged properties
        if ownership.is_mortgaged:
            space = self.board.get_space(pos)
            if hasattr(space, 'mortgage_value'):
                fee = int(space.mortgage_value * 0.10)
                proposer_mortgage_fee += fee

    recipient.get_out_of_jail_cards -= trade.recipient_offer.jail_cards
    proposer.get_out_of_jail_cards += trade.recipient_offer.jail_cards

    # Apply mortgage fees
    proposer.cash -= proposer_mortgage_fee
    recipient.cash -= recipient_mortgage_fee

    self.event_log.log(
        EventType.TRADE_EXECUTED,
        details={
            "trade_id": trade.trade_id,
            "success": True,
            "proposer": trade.proposer_id,
            "recipient": trade.recipient_id,
            "proposer_gave": str(trade.proposer_offer),
            "recipient_gave": str(trade.recipient_offer),
            "proposer_mortgage_fee": proposer_mortgage_fee,
            "recipient_mortgage_fee": recipient_mortgage_fee,
        },
    )

    return True
