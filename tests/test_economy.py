import pytest
from monopoly.game import create_game, ActionType
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.rules import get_legal_actions, apply_action, Action, _resolve_landing
from monopoly.spaces import SpaceType


@pytest.fixture
def basic_game():
    """Create a basic game."""
    players = [Player(0, "Alice"), Player(1, "Bob")]
    config = GameConfig(seed=42, starting_cash=1500)
    return create_game(config, players)


@pytest.fixture
def rich_game():
    """Create a game with wealthy players."""
    players = [Player(0, "Alice"), Player(1, "Bob")]
    config = GameConfig(seed=42, starting_cash=5000)
    game = create_game(config, players)

    # Give Alice expensive properties
    game.players[0].properties.add(37)  # Park Place - $350
    game.players[0].properties.add(39)  # Boardwalk - $400
    game.property_ownership[37].owner_id = 0
    game.property_ownership[39].owner_id = 0

    return game


class TestIncomeTaxSpace:
    """Tests for Income Tax space configuration."""

    def test_income_tax_has_choice_flag(self, basic_game):
        """Test that Income Tax space has choice=True."""
        income_tax = basic_game.board.get_space(4)

        assert income_tax.name == "Income Tax"
        assert income_tax.space_type == SpaceType.TAX
        assert income_tax.has_choice == True
        assert income_tax.amount == 200  # Default flat amount

    def test_luxury_tax_no_choice(self, basic_game):
        """Test that Luxury Tax has no choice."""
        luxury_tax = basic_game.board.get_space(38)

        assert luxury_tax.name == "Luxury Tax"
        assert luxury_tax.space_type == SpaceType.TAX
        assert luxury_tax.has_choice == False
        assert luxury_tax.amount == 100

    def test_luxury_tax_auto_pays(self, basic_game):
        """Test that Luxury Tax is paid automatically."""
        initial_cash = basic_game.players[0].cash

        # Land on Luxury Tax
        basic_game.players[0].position = 38
        _resolve_landing(basic_game, 0, 38)

        # Should auto-pay $100
        assert basic_game.players[0].cash == initial_cash - 100
        assert basic_game.pending_income_tax_choice == False


class TestIncomeTaxPayment:
    """Tests for income tax payment mechanics."""

    def test_pay_flat_200(self, basic_game):
        """Test paying flat $200."""
        initial_cash = basic_game.players[0].cash

        success = basic_game.pay_income_tax_choice(0, pay_flat=True)

        assert success
        assert basic_game.players[0].cash == initial_cash - 200
        assert basic_game.pending_income_tax_choice == False

    def test_pay_10_percent_cash_only(self, basic_game):
        """Test paying 10% when player has only cash."""
        # Alice has $1500, 10% = $150
        initial_cash = basic_game.players[0].cash

        success = basic_game.pay_income_tax_choice(0, pay_flat=False)

        assert success
        assert basic_game.players[0].cash == initial_cash - 150

    def test_pay_10_percent_with_properties(self, rich_game):
        """Test 10% calculation includes property values."""
        # Alice has:
        # - $5000 cash
        # - Park Place ($350)
        # - Boardwalk ($400)
        # Total net worth = $5750
        # 10% = $575

        initial_cash = rich_game.players[0].cash

        success = rich_game.pay_income_tax_choice(0, pay_flat=False)

        assert success
        assert rich_game.players[0].cash == initial_cash - 575

    def test_pay_10_percent_with_buildings(self, basic_game):
        """Test 10% includes building values."""
        # Give Alice properties and buildings
        basic_game.players[0].properties.add(1)  # Mediterranean - $60
        basic_game.players[0].properties.add(3)  # Baltic - $60
        basic_game.property_ownership[1].owner_id = 0
        basic_game.property_ownership[3].owner_id = 0
        basic_game.property_ownership[1].houses = 2  # 2 houses @ $50 each

        # Net worth = $1500 cash + $60 + $60 + (2 * $50) = $1720
        # 10% = $172 (not $167 - that was a calculation error)

        initial_cash = basic_game.players[0].cash
        success = basic_game.pay_income_tax_choice(0, pay_flat=False)

        assert success
        assert basic_game.players[0].cash == initial_cash - 172

    def test_pay_10_percent_with_hotel(self, basic_game):
        """Test 10% includes hotel value."""
        # Give Alice a hotel
        basic_game.players[0].properties.add(1)
        basic_game.property_ownership[1].owner_id = 0
        basic_game.property_ownership[1].houses = 5  # Hotel

        # Net worth = $1500 + $60 + (5 * $50) = $1810
        # 10% = $181

        initial_cash = basic_game.players[0].cash
        success = basic_game.pay_income_tax_choice(0, pay_flat=False)

        assert success
        assert basic_game.players[0].cash == initial_cash - 181

    def test_mortgaged_property_reduces_net_worth(self, basic_game):
        """Test that mortgaged properties reduce net worth."""
        # Give Alice property and mortgage it
        basic_game.players[0].properties.add(1)  # Mediterranean
        basic_game.property_ownership[1].owner_id = 0
        basic_game.property_ownership[1].is_mortgaged = True

        # Property value $60, but mortgaged so worth -$30 (mortgage value)
        # Net worth = $1500 + $60 - $30 = $1530
        # 10% = $153

        initial_cash = basic_game.players[0].cash
        success = basic_game.pay_income_tax_choice(0, pay_flat=False)

        assert success
        assert basic_game.players[0].cash == initial_cash - 153

    def test_insufficient_cash_sets_pending_payment(self, basic_game):
        """Test that insufficient cash creates pending payment."""
        # Set cash to $50 (less than $200)
        basic_game.players[0].cash = 50

        success = basic_game.pay_income_tax_choice(0, pay_flat=True)

        assert not success
        assert basic_game.pending_tax_payment == (0, 200)

    def test_choice_logged_flat(self, basic_game):
        """Test that flat choice is logged."""
        basic_game.pay_income_tax_choice(0, pay_flat=True)

        events = basic_game.event_log.get_events()
        tax_events = [e for e in events if e.event_type.value == "tax_payment"]

        assert len(tax_events) > 0
        last_tax = tax_events[-1]
        assert "choice" in last_tax.details
        assert last_tax.details["choice"] == "flat_200"

    def test_choice_logged_percent(self, basic_game):
        """Test that percent choice is logged."""
        basic_game.pay_income_tax_choice(0, pay_flat=False)

        events = basic_game.event_log.get_events()
        tax_events = [e for e in events if e.event_type.value == "tax_payment"]

        last_tax = tax_events[-1]
        assert last_tax.details["choice"] == "percent_10"


class TestIncomeTaxChoice:
    """Tests for optimal choice between flat and percent."""

    def test_flat_better_when_rich(self, rich_game):
        """Test flat $200 is better when net worth > $2000."""
        # Alice has $5750 net worth
        # 10% = $575 (worse than $200)

        initial_cash = rich_game.players[0].cash

        # Pay flat
        rich_game.pay_income_tax_choice(0, pay_flat=True)
        cash_after_flat = rich_game.players[0].cash

        # Reset
        rich_game.players[0].cash = initial_cash

        # Pay percent
        rich_game.pay_income_tax_choice(0, pay_flat=False)
        cash_after_percent = rich_game.players[0].cash

        # Flat should leave more money
        assert cash_after_flat > cash_after_percent
        assert initial_cash - cash_after_flat == 200
        assert initial_cash - cash_after_percent == 575

    def test_percent_better_when_poor(self, basic_game):
        """Test 10% is better when net worth < $2000."""
        # Set Alice to have only $1000
        basic_game.players[0].cash = 1000

        # 10% = $100 (better than $200)

        initial_cash = basic_game.players[0].cash

        # Pay percent
        basic_game.pay_income_tax_choice(0, pay_flat=False)
        assert basic_game.players[0].cash == initial_cash - 100

        # This is better than paying $200
        assert 100 < 200

    def test_breakeven_point_2000(self, basic_game):
        """Test that $2000 net worth is breakeven."""
        basic_game.players[0].cash = 2000

        # 10% of $2000 = $200 (same as flat)
        basic_game.pay_income_tax_choice(0, pay_flat=False)
        amount_paid = 2000 - basic_game.players[0].cash

        assert amount_paid == 200


class TestIncomeTaxLegalActions:
    """Tests for legal actions when facing income tax choice."""

    def test_landing_on_income_tax_sets_flag(self, basic_game):
        """Test that landing on income tax sets pending choice flag."""
        basic_game.players[0].position = 4

        _resolve_landing(basic_game, 0, 4)

        assert basic_game.pending_income_tax_choice == True

    def test_legal_actions_include_both_choices(self, basic_game):
        """Test that both payment options are legal actions."""
        basic_game.pending_income_tax_choice = True

        actions = get_legal_actions(basic_game, 0)
        action_types = [a.action_type for a in actions]

        assert ActionType.PAY_INCOME_TAX_FLAT in action_types
        assert ActionType.PAY_INCOME_TAX_PERCENT in action_types

    def test_legal_actions_include_property_management(self, basic_game):
        """Test that property management is available during choice."""
        # Give Alice a mortgageable property
        basic_game.players[0].properties.add(1)
        basic_game.property_ownership[1].owner_id = 0
        basic_game.pending_income_tax_choice = True

        actions = get_legal_actions(basic_game, 0)
        action_types = [a.action_type for a in actions]

        # Should be able to mortgage to raise funds
        assert ActionType.MORTGAGE_PROPERTY in action_types

    def test_apply_action_flat_payment(self, basic_game):
        """Test applying flat payment action."""
        basic_game.pending_income_tax_choice = True
        initial_cash = basic_game.players[0].cash

        action = Action(ActionType.PAY_INCOME_TAX_FLAT)
        success = apply_action(basic_game, action)

        assert success
        assert basic_game.players[0].cash == initial_cash - 200
        assert basic_game.pending_income_tax_choice == False

    def test_apply_action_percent_payment(self, basic_game):
        """Test applying percent payment action."""
        basic_game.pending_income_tax_choice = True
        initial_cash = basic_game.players[0].cash

        action = Action(ActionType.PAY_INCOME_TAX_PERCENT)
        success = apply_action(basic_game, action)

        assert success
        assert basic_game.players[0].cash == initial_cash - 150  # 10% of 1500
        assert basic_game.pending_income_tax_choice == False


class TestIncomeTaxIntegration:
    """Integration tests for full income tax flow."""

    def test_full_flow_land_choose_pay(self, basic_game):
        """Test complete flow from landing to payment."""
        initial_cash = basic_game.players[0].cash

        # Move to Income Tax space
        basic_game.players[0].position = 4
        _resolve_landing(basic_game, 0, 4)

        # Should have choice pending
        assert basic_game.pending_income_tax_choice == True

        # Get legal actions
        actions = get_legal_actions(basic_game, 0)

        # Choose flat payment
        flat_action = next(a for a in actions if a.action_type == ActionType.PAY_INCOME_TAX_FLAT)
        apply_action(basic_game, flat_action)

        # Verify payment
        assert basic_game.players[0].cash == initial_cash - 200
        assert basic_game.pending_income_tax_choice == False

    def test_player_must_mortgage_to_pay(self, basic_game):
        """Test player mortgaging property to afford tax."""
        # Set Alice to have $100 cash (not enough for $200 tax)
        basic_game.players[0].cash = 100

        # Give her mortgageable property
        basic_game.players[0].properties.add(1)  # Mediterranean, mortgage = $30
        basic_game.property_ownership[1].owner_id = 0

        # Land on Income Tax
        basic_game.players[0].position = 4
        _resolve_landing(basic_game, 0, 4)

        # Try to pay flat - should fail
        action = Action(ActionType.PAY_INCOME_TAX_FLAT)
        success = apply_action(basic_game, action)
        assert not success

        # Mortgage property to raise funds
        mortgage_action = Action(ActionType.MORTGAGE_PROPERTY, position=1)
        apply_action(basic_game, mortgage_action)

        # Now has $130, still not enough
        # Choose 10% instead (10% of $130 + property = ~$19)
        percent_action = Action(ActionType.PAY_INCOME_TAX_PERCENT)
        success = apply_action(basic_game, percent_action)

        assert success

    def test_multiple_players_different_choices(self, basic_game):
        """Test different players making different choices."""
        # Alice (poor) chooses percent
        basic_game.players[0].cash = 1000
        basic_game.pending_income_tax_choice = True
        alice_action = Action(ActionType.PAY_INCOME_TAX_PERCENT)
        apply_action(basic_game, alice_action)
        alice_paid = 1000 - basic_game.players[0].cash

        # Bob (rich) chooses flat
        basic_game.players[1].cash = 3000
        basic_game.current_player_index = 1
        basic_game.pending_income_tax_choice = True
        bob_action = Action(ActionType.PAY_INCOME_TAX_FLAT)
        apply_action(basic_game, bob_action)
        bob_paid = 3000 - basic_game.players[1].cash

        # Alice paid less (10% of 1000 = 100)
        # Bob paid more ($200)
        assert alice_paid == 100
        assert bob_paid == 200
        assert alice_paid < bob_paid
