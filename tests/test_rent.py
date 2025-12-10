"""
Tests for rent calculation on all property types.
"""

import pytest
from monopoly.game import create_game
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.cards import Card, CardType
from monopoly.rules import get_legal_actions, apply_action, Action, ActionType


def test_basic_property_rent():
    """
    Test basic rent on unimproved property.
    Rule: 'The amount payable is shown on the Title Deed' [cite: 81]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice buys Mediterranean (position 1)
    game.buy_property(0, 1)

    # Calculate rent
    rent = game.calculate_rent(1)

    # Mediterranean base rent is 2
    assert rent == 2


def test_monopoly_doubles_rent():
    """
    Test that owning a complete color set doubles rent on unimproved sites.
    Rule: 'If all Sites within a colour-group are owned by a player, the rent payable is doubled on any Site of that group not yet built on.' [cite: 82]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice buys both brown properties (positions 1 and 3)
    game.buy_property(0, 1)  # Mediterranean
    game.buy_property(0, 3)  # Baltic

    # Calculate rent for Mediterranean
    rent = game.calculate_rent(1)

    # Base rent is 2, should be doubled to 4
    assert rent == 4


def test_monopoly_no_double_rent_if_group_mortgaged():
    """
    Test that monopoly doubling is suppressed if ANY property in the group is mortgaged.
    Rule: 'an owner who owns a whole colour-group may not collect double rent if any one Site there is mortgaged.' 
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Alice buys both brown properties
    game.buy_property(0, 1)
    game.buy_property(0, 3)

    # Alice mortgages ONE of them (e.g., Baltic/3)
    game.property_ownership[3].is_mortgaged = True

    # Calculate rent for the UNMORTGAGED property (Mediterranean/1)
    rent = game.calculate_rent(1)

    # Should be base rent (2), NOT doubled (4), because the group is incomplete due to mortgage
    assert rent == 2


def test_rent_with_houses():
    """
    Test rent calculation with houses.
    Rule: 'Where Houses or Hotels have been built on a Site, the rent will increase' [cite: 84]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give Alice the light blue monopoly
    game.buy_property(0, 6)   # Oriental
    game.buy_property(0, 8)   # Vermont
    game.buy_property(0, 9)   # Connecticut

    # Add houses
    game.property_ownership[6].houses = 1

    rent = game.calculate_rent(6)

    # Oriental with 1 house has rent of 30
    assert rent == 30


def test_rent_with_hotel():
    """Test rent calculation with hotel."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Give Alice a monopoly
    game.buy_property(0, 6)
    game.buy_property(0, 8)
    game.buy_property(0, 9)

    # Add hotel (represented as 5 houses)
    game.property_ownership[6].houses = 5

    rent = game.calculate_rent(6)

    # Oriental with hotel has rent of 550
    assert rent == 550


def test_railroad_rent_scaling():
    """
    Test railroad rent scales with number owned.
    Rule: 'The amount payable will vary according to the number of other Stations owned by that player.' [cite: 99]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy railroads one by one
    railroads = game.board.get_all_railroads()

    # 1 railroad: 25
    game.buy_property(0, railroads[0])
    assert game.calculate_rent(railroads[0]) == 25

    # 2 railroads: 50
    game.buy_property(0, railroads[1])
    assert game.calculate_rent(railroads[0]) == 50
    assert game.calculate_rent(railroads[1]) == 50

    # 3 railroads: 100
    game.buy_property(0, railroads[2])
    assert game.calculate_rent(railroads[0]) == 100

    # 4 railroads: 200
    game.buy_property(0, railroads[3])
    assert game.calculate_rent(railroads[0]) == 200


def test_utility_rent_with_dice():
    """
    Test utility rent calculation based on dice roll.
    Rule: 'rent will be four times your dice roll' (1 owned) [cite: 90]
    Rule: 'must pay ten times the amount of your dice roll' (2 owned) [cite: 91]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    utilities = game.board.get_all_utilities()

    # 1 utility: 4x dice
    game.buy_property(0, utilities[0])
    # The rule says 'according to the dice you rolled to get there' [cite: 89]
    dice_roll = 7 
    
    rent = game.calculate_rent(utilities[0], dice_roll=dice_roll)
    assert rent == 28  # 7 * 4

    # 2 utilities: 10x dice
    game.buy_property(0, utilities[1])
    rent = game.calculate_rent(utilities[0], dice_roll=dice_roll)
    assert rent == 70  # 7 * 10


def test_no_rent_on_mortgaged_property():
    """
    Test that mortgaged properties don't collect rent.
    Rule: 'Rent is not payable on mortgaged Properties.' [cite: 85]
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    # Buy and mortgage property
    game.buy_property(0, 1)
    game.property_ownership[1].is_mortgaged = True

    rent = game.calculate_rent(1)
    assert rent == 0


def test_rent_transaction_safety_on_own_property():
    """
    Test that no money is lost if owner 'pays' themselves.
    Rule implied: You don't pay rent to yourself.
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice")]
    game = create_game(config, players)

    game.buy_property(0, 1)
    initial_cash = game.players[0].cash
    
    rent = game.calculate_rent(1)
    assert rent > 0 

    # Attempt to execute payment from Alice (0) to Alice (0)
    game.pay_rent(0, 0, rent)

    # Cash should remain identical
    assert game.players[0].cash == initial_cash


def test_rent_payment_transfer():
    """Test that rent payment transfers money correctly between players."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice buys property
    game.buy_property(0, 1)

    alice_cash = game.players[0].cash
    bob_cash = game.players[1].cash

    # Bob pays rent
    rent = game.calculate_rent(1)
    # pay_rent(payer_id, recipient_id, amount)
    game.pay_rent(1, 0, rent)

    assert game.players[0].cash == alice_cash + rent
    assert game.players[1].cash == bob_cash - rent


@pytest.fixture
def game_with_railroads():
    """Create a game where Bob owns railroads."""
    players = [Player(0, "Alice"), Player(1, "Bob")]
    config = GameConfig(seed=42, starting_cash=2000)
    game = create_game(config, players)

    # Bob owns Reading Railroad (5) and Pennsylvania Railroad (15)
    game.players[1].properties.add(5)
    game.players[1].properties.add(15)
    game.property_ownership[5].owner_id = 1
    game.property_ownership[15].owner_id = 1

    return game


@pytest.fixture
def game_with_utilities():
    """Create a game where Bob owns utilities."""
    players = [Player(0, "Alice"), Player(1, "Bob")]
    config = GameConfig(seed=42, starting_cash=2000)
    game = create_game(config, players)

    # Bob owns Electric Company (12)
    game.players[1].properties.add(12)
    game.property_ownership[12].owner_id = 1

    return game


class TestNearestRailroadCard:
    """Tests for 'Advance to nearest Railroad' Chance card."""

    def test_card_has_special_multiplier(self):
        """Test that nearest railroad cards have 2.0 multiplier."""
        players = [Player(0, "Alice"), Player(1, "Bob")]
        game = create_game(GameConfig(seed=42), players)

        # Find all nearest railroad cards
        nearest_rr_cards = [
            card for card in game.chance_deck.cards + game.chance_deck.discard_pile
            if card.card_type == CardType.MOVE_TO_NEAREST and card.target_type == "railroad"
        ]

        # Should have 2 such cards in standard deck
        assert len(nearest_rr_cards) == 2

        # Both should have 2.0 multiplier
        for card in nearest_rr_cards:
            assert card.special_rent_multiplier == 2.0

    def test_moves_to_nearest_railroad(self, game_with_railroads):
        """Test that card moves player to nearest railroad."""
        # Alice at position 7 (Chance space)
        game_with_railroads.players[0].position = 7

        # Create and execute nearest railroad card
        card = Card(
            "Advance to nearest Railroad",
            CardType.MOVE_TO_NEAREST,
            target_type="railroad",
            special_rent_multiplier=2.0
        )

        game_with_railroads.execute_card(card, 0, game_with_railroads.chance_deck)

        # Nearest railroad from 7 is Pennsylvania Railroad (15)
        assert game_with_railroads.players[0].position == 15

    def test_sets_rent_multiplier(self, game_with_railroads):
        """Test that card sets the special rent multiplier."""
        game_with_railroads.players[0].position = 3

        card = Card(
            "Advance to nearest Railroad",
            CardType.MOVE_TO_NEAREST,
            target_type="railroad",
            special_rent_multiplier=2.0
        )

        # Execute card
        game_with_railroads.execute_card(card, 0, game_with_railroads.chance_deck)

        # Multiplier should be set
        assert game_with_railroads.next_rent_multiplier == 2.0

    def test_double_rent_one_railroad(self, game_with_railroads):
        """Test double rent when owner has 1 railroad."""
        # Bob owns only Reading Railroad (5)
        game_with_railroads.players[1].properties.remove(15)
        game_with_railroads.property_ownership[15].owner_id = None

        # Set multiplier as if card was played
        game_with_railroads.next_rent_multiplier = 2.0

        # Normal rent for 1 railroad = $25
        # Double rent = $50
        rent = game_with_railroads.calculate_rent(5)
        assert rent == 50

    def test_double_rent_two_railroads(self, game_with_railroads):
        """Test double rent when owner has 2 railroads."""
        # Bob owns 2 railroads (5 and 15)
        game_with_railroads.next_rent_multiplier = 2.0

        # Normal rent for 2 railroads = $50
        # Double rent = $100
        rent = game_with_railroads.calculate_rent(5)
        assert rent == 100

    def test_double_rent_four_railroads(self, game_with_railroads):
        """Test double rent when owner has all 4 railroads."""
        # Give Bob all 4 railroads
        game_with_railroads.players[1].properties.add(25)  # B&O
        game_with_railroads.players[1].properties.add(35)  # Short Line
        game_with_railroads.property_ownership[25].owner_id = 1
        game_with_railroads.property_ownership[35].owner_id = 1

        game_with_railroads.next_rent_multiplier = 2.0

        # Normal rent for 4 railroads = $200
        # Double rent = $400
        rent = game_with_railroads.calculate_rent(5)
        assert rent == 400

    def test_multiplier_cleared_after_rent_payment(self, game_with_railroads):
        """Test that multiplier is cleared after rent is paid."""
        game_with_railroads.next_rent_multiplier = 2.0

        initial_alice_cash = game_with_railroads.players[0].cash

        # Calculate and pay rent
        rent = game_with_railroads.calculate_rent(5)  # $100 (double of $50)
        game_with_railroads.pay_rent(0, 1, rent)

        # Multiplier should be cleared
        assert game_with_railroads.next_rent_multiplier is None

        # Cash should be reduced by rent
        assert game_with_railroads.players[0].cash == initial_alice_cash - 100

    def test_no_rent_on_mortgaged_railroad(self, game_with_railroads):
        """Test that mortgaged railroad pays no rent even with multiplier."""
        # Mortgage Reading Railroad
        game_with_railroads.property_ownership[5].is_mortgaged = True
        game_with_railroads.next_rent_multiplier = 2.0

        rent = game_with_railroads.calculate_rent(5)
        assert rent == 0


class TestNearestUtilityCard:
    """Tests for 'Advance to nearest Utility' Chance card."""

    def test_card_has_special_multiplier(self):
        """Test that nearest utility card has 10.0 multiplier."""
        players = [Player(0, "Alice"), Player(1, "Bob")]
        game = create_game(GameConfig(seed=42), players)

        # Find nearest utility card
        nearest_util_cards = [
            card for card in game.chance_deck.cards + game.chance_deck.discard_pile
            if card.card_type == CardType.MOVE_TO_NEAREST and card.target_type == "utility"
        ]

        # Should have 1 such card
        assert len(nearest_util_cards) == 1
        assert nearest_util_cards[0].special_rent_multiplier == 10.0

    def test_moves_to_nearest_utility(self, game_with_utilities):
        """Test that card moves player to nearest utility."""
        # Alice at position 7 (between Electric Company at 12 and Water Works at 28)
        game_with_utilities.players[0].position = 7

        card = Card(
            "Advance to nearest Utility",
            CardType.MOVE_TO_NEAREST,
            target_type="utility",
            special_rent_multiplier=10.0
        )

        game_with_utilities.execute_card(card, 0, game_with_utilities.chance_deck)

        # Nearest utility from 7 is Electric Company (12)
        assert game_with_utilities.players[0].position == 12

    def test_ten_times_dice_roll(self, game_with_utilities):
        """Test rent is 10x dice roll (not 4x for one utility)."""
        # Set last dice roll
        game_with_utilities.last_dice_roll = (3, 5)  # Total 8

        # Set special multiplier as if card was played
        game_with_utilities.next_rent_multiplier = 10.0

        # Rent should be 8 * 10 = 80
        # (Normal rent for 1 utility would be 8 * 4 = 32)
        rent = game_with_utilities.calculate_rent(12, dice_roll=8)
        assert rent == 80

    def test_ten_times_dice_various_rolls(self, game_with_utilities):
        """Test with different dice rolls."""
        game_with_utilities.next_rent_multiplier = 10.0

        test_cases = [
            (2, 20),  # Snake eyes
            (7, 70),  # Average roll
            (12, 120),  # Boxcars
        ]

        for dice_total, expected_rent in test_cases:
            rent = game_with_utilities.calculate_rent(12, dice_roll=dice_total)
            assert rent == expected_rent, f"Failed for dice roll {dice_total}"

    def test_special_rent_overrides_two_utilities(self, game_with_utilities):
        """Test that special rent applies even if owner has both utilities."""
        # Give Bob Water Works too
        game_with_utilities.players[1].properties.add(28)
        game_with_utilities.property_ownership[28].owner_id = 1

        game_with_utilities.next_rent_multiplier = 10.0

        # With special multiplier: 7 * 10 = 70
        # Normal rent for 2 utilities would be: 7 * 10 = 70 (same by coincidence)
        # But the code path is different - special multiplier takes precedence
        rent = game_with_utilities.calculate_rent(12, dice_roll=7)
        assert rent == 70

    def test_multiplier_cleared_after_utility_rent(self, game_with_utilities):
        """Test multiplier is cleared after utility rent payment."""
        game_with_utilities.next_rent_multiplier = 10.0
        game_with_utilities.last_dice_roll = (4, 3)

        rent = game_with_utilities.calculate_rent(12, dice_roll=7)
        game_with_utilities.pay_rent(0, 1, rent)

        assert game_with_utilities.next_rent_multiplier is None

    def test_no_rent_on_mortgaged_utility(self, game_with_utilities):
        """Test mortgaged utility pays no rent with multiplier."""
        game_with_utilities.property_ownership[12].is_mortgaged = True
        game_with_utilities.next_rent_multiplier = 10.0

        rent = game_with_utilities.calculate_rent(12, dice_roll=7)
        assert rent == 0


class TestSpecialRentIntegration:
    """Integration tests for special rent in full game flow."""

    def test_full_flow_railroad_card_to_payment(self, game_with_railroads):
        """Test complete flow from drawing card to paying rent."""
        initial_alice_cash = game_with_railroads.players[0].cash
        initial_bob_cash = game_with_railroads.players[1].cash

        # Alice at Chance space
        game_with_railroads.players[0].position = 7

        # Draw and execute nearest railroad card
        card = Card(
            "Advance to nearest Railroad",
            CardType.MOVE_TO_NEAREST,
            target_type="railroad",
            special_rent_multiplier=2.0
        )
        game_with_railroads.execute_card(card, 0, game_with_railroads.chance_deck)

        # Alice should be at Pennsylvania Railroad (15)
        assert game_with_railroads.players[0].position == 15

        # Calculate and pay rent (Bob owns 2 railroads: normal $50, double $100)
        rent = game_with_railroads.calculate_rent(15)
        assert rent == 100

        game_with_railroads.pay_rent(0, 1, rent)

        # Check cash transferred
        assert game_with_railroads.players[0].cash == initial_alice_cash - 100
        assert game_with_railroads.players[1].cash == initial_bob_cash + 100

        # Multiplier should be cleared
        assert game_with_railroads.next_rent_multiplier is None

    def test_full_flow_utility_card_to_payment(self, game_with_utilities):
        """Test complete flow for utility card."""
        initial_alice_cash = game_with_utilities.players[0].cash

        # Give Bob Water Works too (he already has Electric Company from fixture)
        game_with_utilities.players[1].properties.add(28)  # <-- ADD THIS
        game_with_utilities.property_ownership[28].owner_id = 1  # <-- ADD THIS

        game_with_utilities.players[0].position = 22
        game_with_utilities.last_dice_roll = (5, 4)  # Total 9

        # Draw utility card
        card = Card(
            "Advance to nearest Utility",
            CardType.MOVE_TO_NEAREST,
            target_type="utility",
            special_rent_multiplier=10.0
        )
        game_with_utilities.execute_card(card, 0, game_with_utilities.chance_deck)

        # Should move to Water Works (28)
        assert game_with_utilities.players[0].position == 28

        # Calculate rent: 9 * 10 = 90
        rent = game_with_utilities.calculate_rent(28, dice_roll=9)
        assert rent == 90

        game_with_utilities.pay_rent(0, 1, rent)
        assert game_with_utilities.players[0].cash == initial_alice_cash - 90

    def test_unowned_railroad_can_be_purchased(self, game_with_railroads):
        """Test that player can buy unowned railroad after landing via card."""
        # Make Pennsylvania Railroad unowned
        game_with_railroads.players[1].properties.remove(15)
        game_with_railroads.property_ownership[15].owner_id = None

        game_with_railroads.players[0].position = 7

        card = Card(
            "Advance to nearest Railroad",
            CardType.MOVE_TO_NEAREST,
            target_type="railroad",
            special_rent_multiplier=2.0
        )
        game_with_railroads.execute_card(card, 0, game_with_railroads.chance_deck)

        # Alice at position 15, should be able to buy
        initial_cash = game_with_railroads.players[0].cash
        success = game_with_railroads.buy_property(0, 15)

        assert success
        assert game_with_railroads.players[0].cash == initial_cash - 200
        assert 15 in game_with_railroads.players[0].properties

        # Multiplier should not affect purchase
        assert game_with_railroads.next_rent_multiplier == 2.0  # Still set but unused

    def test_normal_landing_has_no_multiplier(self, game_with_railroads):
        """Test that normal landing on railroad doesn't have special rent."""
        # Alice lands normally (not via card)
        game_with_railroads.players[0].position = 5

        # No multiplier set
        assert game_with_railroads.next_rent_multiplier is None

        # Normal rent for 2 railroads = $50
        rent = game_with_railroads.calculate_rent(5)
        assert rent == 50