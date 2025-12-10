"""
Tests for the trading system.
"""

import pytest
from monopoly.game import create_game
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.trade import TradeOffer, Trade
from monopoly.rules import get_legal_actions, apply_action, Action, ActionType
from monopoly.money import EventType


@pytest.fixture
def basic_game():
    """Create a basic 2-player game for testing."""
    players = [Player(0, "Alice"), Player(1, "Bob")]
    config = GameConfig(seed=42, starting_cash=1500)
    game = create_game(config, players)
    return game


@pytest.fixture
def game_with_properties():
    """Create a game where players own some properties."""
    players = [Player(0, "Alice"), Player(1, "Bob")]
    config = GameConfig(seed=42, starting_cash=2000)
    game = create_game(config, players)

    # Give Alice Mediterranean (1) and Baltic (3)
    game.players[0].properties.add(1)
    game.players[0].properties.add(3)
    game.property_ownership[1].owner_id = 0
    game.property_ownership[3].owner_id = 0

    # Give Bob Oriental (6) and Vermont (8)
    game.players[1].properties.add(6)
    game.players[1].properties.add(8)
    game.property_ownership[6].owner_id = 1
    game.property_ownership[8].owner_id = 1

    return game


class TestTradeOfferValidation:
    """Tests for TradeOffer validation."""

    def test_empty_offer(self):
        """Test that empty offers are recognized."""
        offer = TradeOffer()
        assert offer.is_empty()

        offer_with_cash = TradeOffer(cash=100)
        assert not offer_with_cash.is_empty()

    def test_offer_representation(self):
        """Test string representation of offers."""
        offer = TradeOffer(cash=100, properties={1, 3}, jail_cards=1)
        repr_str = str(offer)
        assert "$100" in repr_str
        assert "2 properties" in repr_str
        assert "1 GOOJF" in repr_str

    def test_validate_sufficient_cash(self, basic_game):
        """Test validation accepts sufficient cash."""
        offer = TradeOffer(cash=500)
        valid, error = basic_game.validate_trade_offer(0, offer)
        assert valid
        assert error == ""

    def test_validate_insufficient_cash(self, basic_game):
        """Test validation rejects insufficient cash."""
        offer = TradeOffer(cash=2000)  # Player has 1500
        valid, error = basic_game.validate_trade_offer(0, offer)
        assert not valid
        assert "Insufficient cash" in error

    def test_validate_property_ownership(self, game_with_properties):
        """Test validation checks property ownership."""
        # Alice owns property 1
        offer = TradeOffer(properties={1})
        valid, error = game_with_properties.validate_trade_offer(0, offer)
        assert valid

        # Alice doesn't own property 6
        offer = TradeOffer(properties={6})
        valid, error = game_with_properties.validate_trade_offer(0, offer)
        assert not valid
        assert "doesn't own" in error

    def test_validate_jail_cards(self, basic_game):
        """Test validation checks jail card availability."""
        # Give player a jail card
        basic_game.players[0].get_out_of_jail_cards = 1

        offer = TradeOffer(jail_cards=1)
        valid, error = basic_game.validate_trade_offer(0, offer)
        assert valid

        offer = TradeOffer(jail_cards=2)
        valid, error = basic_game.validate_trade_offer(0, offer)
        assert not valid
        assert "Insufficient jail cards" in error


class TestPropertyTradability:
    """Tests for property trade restrictions."""

    def test_can_trade_property_basic(self, game_with_properties):
        """Test basic property tradability."""
        # Alice owns property 1 with no buildings
        assert game_with_properties.can_trade_property(0, 1)

    def test_cannot_trade_with_buildings(self, game_with_properties):
        """Test cannot trade property with buildings."""
        # Add a house to Mediterranean
        game_with_properties.property_ownership[1].houses = 1

        assert not game_with_properties.can_trade_property(0, 1)

    def test_cannot_trade_when_group_has_buildings(self, game_with_properties):
        """Test cannot trade if any property in group has buildings."""
        # Mediterranean (1) and Baltic (3) are both brown
        # Add house to Baltic
        game_with_properties.property_ownership[3].houses = 1

        # Should not be able to trade Mediterranean either
        assert not game_with_properties.can_trade_property(0, 1)

    def test_cannot_trade_not_owned(self, game_with_properties):
        """Test cannot trade property player doesn't own."""
        assert not game_with_properties.can_trade_property(0, 6)  # Bob owns this


class TestTradeProposal:
    """Tests for creating and managing trade proposals."""

    def test_create_trade_proposal(self, game_with_properties):
        """Test creating a basic trade proposal."""
        proposer_offer = TradeOffer(cash=100, properties={1})
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(
            proposer_id=0,
            recipient_id=1,
            proposer_offer=proposer_offer,
            recipient_offer=recipient_offer
        )

        assert trade.trade_id == 1
        assert trade.proposer_id == 0
        assert trade.recipient_id == 1
        assert not trade.is_complete()

    def test_trade_logged(self, game_with_properties):
        """Test that trade proposal is logged."""
        proposer_offer = TradeOffer(cash=100, properties={1})
        recipient_offer = TradeOffer(properties={6})

        game_with_properties.trade_manager.create_trade(
            proposer_id=0,
            recipient_id=1,
            proposer_offer=proposer_offer,
            recipient_offer=recipient_offer
        )

        events = game_with_properties.event_log.get_events()
        trade_events = [e for e in events if e.event_type == EventType.TRADE_PROPOSED]
        assert len(trade_events) == 1
        assert trade_events[0].player_id == 0

    def test_get_active_trade_for_player(self, game_with_properties):
        """Test retrieving active trade for a player."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        game_with_properties.trade_manager.create_trade(
            proposer_id=0,
            recipient_id=1,
            proposer_offer=proposer_offer,
            recipient_offer=recipient_offer
        )

        # Both players should see the active trade
        trade_p0 = game_with_properties.trade_manager.get_active_trade_for_player(0)
        trade_p1 = game_with_properties.trade_manager.get_active_trade_for_player(1)

        assert trade_p0 is not None
        assert trade_p1 is not None
        assert trade_p0.trade_id == trade_p1.trade_id


class TestTradeExecution:
    """Tests for accepting and executing trades."""

    def test_accept_trade_cash_only(self, basic_game):
        """Test accepting a cash-only trade."""
        initial_alice_cash = basic_game.players[0].cash
        initial_bob_cash = basic_game.players[1].cash

        # Alice offers $100 for $200 from Bob
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(cash=200)

        trade = basic_game.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        basic_game.execute_trade(trade)

        # Alice: loses 100, gains 200 = +100
        # Bob: loses 200, gains 100 = -100
        assert basic_game.players[0].cash == initial_alice_cash + 100
        assert basic_game.players[1].cash == initial_bob_cash - 100

    def test_accept_trade_properties(self, game_with_properties):
        """Test accepting a property trade."""
        # Alice trades Mediterranean (1) for Oriental (6)
        proposer_offer = TradeOffer(properties={1})
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        game_with_properties.execute_trade(trade)

        # Check ownership changed
        assert 6 in game_with_properties.players[0].properties
        assert 1 not in game_with_properties.players[0].properties
        assert 1 in game_with_properties.players[1].properties
        assert 6 not in game_with_properties.players[1].properties

        assert game_with_properties.property_ownership[1].owner_id == 1
        assert game_with_properties.property_ownership[6].owner_id == 0

    def test_accept_trade_mixed(self, game_with_properties):
        """Test accepting a mixed trade (cash + property)."""
        initial_alice_cash = game_with_properties.players[0].cash
        initial_bob_cash = game_with_properties.players[1].cash

        # Alice offers Mediterranean + $100 for Oriental
        proposer_offer = TradeOffer(cash=100, properties={1})
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        game_with_properties.execute_trade(trade)

        # Check cash
        assert game_with_properties.players[0].cash == initial_alice_cash - 100
        assert game_with_properties.players[1].cash == initial_bob_cash + 100

        # Check properties
        assert 6 in game_with_properties.players[0].properties
        assert 1 not in game_with_properties.players[0].properties
        assert 1 in game_with_properties.players[1].properties

    def test_trade_with_jail_cards(self, basic_game):
        """Test trading Get Out of Jail Free cards."""
        # Give Alice a jail card
        basic_game.players[0].get_out_of_jail_cards = 1

        proposer_offer = TradeOffer(jail_cards=1)
        recipient_offer = TradeOffer(cash=50)

        trade = basic_game.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        basic_game.execute_trade(trade)

        assert basic_game.players[0].get_out_of_jail_cards == 0
        assert basic_game.players[1].get_out_of_jail_cards == 1
        assert basic_game.players[0].cash == 1500 + 50
        assert basic_game.players[1].cash == 1500 - 50

    def test_trade_mortgage_fee(self, game_with_properties):
        """Test 10% mortgage fee on mortgaged property transfer."""
        # Mortgage Mediterranean (mortgage value = 30)
        game_with_properties.property_ownership[1].is_mortgaged = True

        initial_bob_cash = game_with_properties.players[1].cash

        # Alice trades mortgaged Mediterranean to Bob
        proposer_offer = TradeOffer(properties={1})
        recipient_offer = TradeOffer(cash=20)

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        game_with_properties.execute_trade(trade)

        # Bob pays 20 for property + 3 (10% of 30) mortgage fee = 23 total
        assert game_with_properties.players[1].cash == initial_bob_cash - 23
        assert game_with_properties.property_ownership[1].owner_id == 1
        assert game_with_properties.property_ownership[1].is_mortgaged


class TestTradeRejection:
    """Tests for rejecting and cancelling trades."""

    def test_reject_trade(self, game_with_properties):
        """Test rejecting a trade."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.reject()

        assert trade.is_rejected
        assert trade.is_complete()
        assert trade.get_result() == "rejected"

        # Check nothing changed
        assert game_with_properties.players[0].cash == 2000
        assert 6 in game_with_properties.players[1].properties

    def test_cancel_trade(self, game_with_properties):
        """Test proposer cancelling their trade."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.cancel()

        assert trade.is_cancelled
        assert trade.is_complete()
        assert trade.get_result() == "cancelled"

    def test_trade_rejection_logged(self, game_with_properties):
        """Test that rejection is logged."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.reject()

        events = game_with_properties.event_log.get_events()
        reject_events = [e for e in events if e.event_type == EventType.TRADE_REJECTED]
        assert len(reject_events) == 1
        assert reject_events[0].player_id == 1  # Recipient rejected


class TestTradeValidation:
    """Tests for trade validation edge cases."""

    def test_cannot_execute_unaccepted_trade(self, game_with_properties):
        """Test that unaccepted trades cannot be executed."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        result = game_with_properties.execute_trade(trade)

        assert not result  # Should fail
        # Nothing should have changed
        assert game_with_properties.players[0].cash == 2000

    def test_validation_fails_if_state_changed(self, game_with_properties):
        """Test that validation fails if game state changed after proposal."""
        proposer_offer = TradeOffer(cash=500)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)

        # Alice spends money before trade is accepted
        game_with_properties.players[0].cash = 100

        trade.accept()
        result = game_with_properties.execute_trade(trade)

        assert not result  # Should fail validation

        # Check execution was logged as failed
        events = game_with_properties.event_log.get_events()
        exec_events = [e for e in events if e.event_type == EventType.TRADE_EXECUTED]
        assert len(exec_events) == 1
        assert exec_events[0].details["success"] == False

    def test_cannot_trade_property_with_buildings_validation(self, game_with_properties):
        """Test validation catches buildings added after proposal."""
        proposer_offer = TradeOffer(properties={1})
        recipient_offer = TradeOffer(cash=50)

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)

        # Add building before acceptance
        game_with_properties.property_ownership[1].houses = 1

        trade.accept()
        result = game_with_properties.execute_trade(trade)

        assert not result


class TestTradeIntegrationWithRules:
    """Integration tests with rules.py API."""

    def test_propose_trade_action(self, game_with_properties):
        """Test proposing trade through rules API."""
        proposer_offer = TradeOffer(cash=100, properties={1})
        recipient_offer = TradeOffer(properties={6})

        action = Action(
            ActionType.PROPOSE_TRADE,
            recipient_id=1,
            proposer_offer=proposer_offer,
            recipient_offer=recipient_offer
        )

        result = apply_action(game_with_properties, action)
        assert result

        # Check trade was created
        trade = game_with_properties.trade_manager.get_active_trade_for_player(0)
        assert trade is not None
        assert trade.proposer_id == 0
        assert trade.recipient_id == 1

    def test_accept_trade_action(self, game_with_properties):
        """Test accepting trade through rules API."""
        proposer_offer = TradeOffer(properties={1})
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)

        action = Action(ActionType.ACCEPT_TRADE, trade_id=trade.trade_id)

        # Change current player to recipient (Bob)
        game_with_properties.current_player_index = 1

        result = apply_action(game_with_properties, action)
        assert result

        # Check trade was executed
        assert 6 in game_with_properties.players[0].properties
        assert 1 in game_with_properties.players[1].properties

    def test_reject_trade_action(self, game_with_properties):
        """Test rejecting trade through rules API."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)

        action = Action(ActionType.REJECT_TRADE, trade_id=trade.trade_id)

        # Change current player to recipient
        game_with_properties.current_player_index = 1

        result = apply_action(game_with_properties, action)
        assert result

        # Check trade was rejected
        assert trade.is_rejected
        # Nothing should have changed
        assert 6 in game_with_properties.players[1].properties
        assert game_with_properties.players[0].cash == 2000

    def test_legal_actions_include_trade_responses(self, game_with_properties):
        """Test that legal actions include trade responses."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)

        # Bob (recipient) should see accept/reject actions even if not his turn
        actions = get_legal_actions(game_with_properties, 1)

        action_types = [a.action_type for a in actions]
        assert ActionType.ACCEPT_TRADE in action_types
        assert ActionType.REJECT_TRADE in action_types


class TestTradeEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_trade_all_properties_for_cash(self, game_with_properties):
        """Test trading all properties for cash."""
        # Alice trades both her properties for cash
        proposer_offer = TradeOffer(properties={1, 3})
        recipient_offer = TradeOffer(cash=500)

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        game_with_properties.execute_trade(trade)

        assert len(game_with_properties.players[0].properties) == 0
        assert 1 in game_with_properties.players[1].properties
        assert 3 in game_with_properties.players[1].properties
        assert game_with_properties.players[0].cash == 2500

    def test_trade_completes_monopoly(self, game_with_properties):
        """Test that trade can create a monopoly."""
        # Give Bob Connecticut (9) so he has the full light blue set after trade
        game_with_properties.players[1].properties.add(9)
        game_with_properties.property_ownership[9].owner_id = 1

        # Alice trades Oriental to Bob (completes light blue: 6, 8, 9)
        # Already has Oriental, wait... let me fix this

        # Actually Alice needs to get Vermont from Bob to complete light blue
        # Let's give Alice Connecticut (9) and Oriental (6)
        game_with_properties.players[0].properties.add(9)
        game_with_properties.property_ownership[9].owner_id = 0
        game_with_properties.players[0].properties.add(6)
        game_with_properties.property_ownership[6].owner_id = 0

        # Bob has Vermont (8)
        # Alice trades Mediterranean (1) for Vermont (8) to complete light blue
        proposer_offer = TradeOffer(properties={1})
        recipient_offer = TradeOffer(properties={8})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        game_with_properties.execute_trade(trade)

        # Alice now has 6, 8, 9 (light blue monopoly)
        assert game_with_properties._has_monopoly(0, "light_blue")

    def test_empty_trade_not_allowed(self, basic_game):
        """Test that completely empty trades are not useful."""
        proposer_offer = TradeOffer()
        recipient_offer = TradeOffer()

        assert proposer_offer.is_empty()
        assert recipient_offer.is_empty()

        # System doesn't prevent it, but it's useless
        trade = basic_game.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        result = basic_game.execute_trade(trade)

        # Should succeed but change nothing
        assert result
        assert basic_game.players[0].cash == 1500
        assert basic_game.players[1].cash == 1500

    def test_bidirectional_trade(self, game_with_properties):
        """Test complex bidirectional trade."""
        # Both players trade properties and cash
        proposer_offer = TradeOffer(cash=200, properties={1, 3})
        recipient_offer = TradeOffer(cash=100, properties={6, 8})

        initial_alice_cash = game_with_properties.players[0].cash
        initial_bob_cash = game_with_properties.players[1].cash

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        trade.accept()
        game_with_properties.execute_trade(trade)

        # Alice gets 6, 8 and 100 cash, gives 1, 3 and 200 cash = net -100 cash
        assert game_with_properties.players[0].cash == initial_alice_cash - 100
        assert 6 in game_with_properties.players[0].properties
        assert 8 in game_with_properties.players[0].properties
        assert 1 not in game_with_properties.players[0].properties

        # Bob gets 1, 3 and 200 cash, gives 6, 8 and 100 cash = net +100 cash
        assert game_with_properties.players[1].cash == initial_bob_cash + 100
        assert 1 in game_with_properties.players[1].properties
        assert 3 in game_with_properties.players[1].properties


class TestTradeHistory:
    """Tests for trade history and management."""

    def test_trade_moved_to_history(self, game_with_properties):
        """Test that completed trades move to history."""
        proposer_offer = TradeOffer(cash=100)
        recipient_offer = TradeOffer(properties={6})

        trade = game_with_properties.trade_manager.create_trade(0, 1, proposer_offer, recipient_offer)
        assert len(game_with_properties.trade_manager.active_trades) == 1

        trade.reject()
        game_with_properties.trade_manager.complete_trade(trade.trade_id)

        assert len(game_with_properties.trade_manager.active_trades) == 0
        assert len(game_with_properties.trade_manager.trade_history) == 1

    def test_multiple_trades_sequential(self, game_with_properties):
        """Test multiple trades in sequence."""
        # First trade
        trade1 = game_with_properties.trade_manager.create_trade(
            0, 1,
            TradeOffer(cash=100),
            TradeOffer(properties={6})
        )
        trade1.reject()
        game_with_properties.trade_manager.complete_trade(trade1.trade_id)

        # Second trade
        trade2 = game_with_properties.trade_manager.create_trade(
            0, 1,
            TradeOffer(properties={1}),
            TradeOffer(properties={6})
        )
        trade2.accept()
        game_with_properties.execute_trade(trade2)
        game_with_properties.trade_manager.complete_trade(trade2.trade_id)

        assert len(game_with_properties.trade_manager.trade_history) == 2
        assert trade2.trade_id == 2
