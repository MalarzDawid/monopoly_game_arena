"""
Tests for property auctions.
"""

import pytest
from core import GameConfig, Player, create_game
from core.game.auction import Auction
from core.game.money import EventLog


def test_auction_creation():
    """Test creating an auction with initiator placing 10% starting bid."""
    event_log = EventLog()
    # Property price = 60 (Mediterranean Ave), 10% = 6
    auction = Auction(
        property_position=1,
        property_name="Mediterranean Avenue",
        eligible_player_ids=[0, 1, 2],
        event_log=event_log,
        initiator_id=0,
        property_price=60,
    )

    assert auction.property_position == 1
    # Initiator automatically places 10% bid
    assert auction.high_bidder == 0
    assert auction.current_bid == 6  # 10% of 60
    assert not auction.is_complete
    assert len(auction.active_bidders) == 3
    assert auction.initiator_id == 0


def test_auction_bidding_mechanics():
    """
    Test placing bids in auction.
    Rule: 'starting at any price that another player is willing to pay'
    """
    event_log = EventLog()
    # Property price = 60, starting bid = 6
    auction = Auction(
        property_position=1,
        property_name="Mediterranean Avenue",
        eligible_player_ids=[0, 1],
        event_log=event_log,
        initiator_id=0,
        property_price=60,
    )

    # Player 0 (initiator) already has bid of 6
    assert auction.current_bid == 6
    assert auction.high_bidder == 0

    # Player 1 bids 10 (higher than 6)
    assert auction.place_bid(1, 10)
    assert auction.current_bid == 10
    assert auction.high_bidder == 1

    # Player 0 tries to bid 5 (lower than current)
    assert not auction.place_bid(0, 5)
    assert auction.current_bid == 10


def test_auction_participation_includes_decliner():
    """
    Test that the player who declined the purchase is included in the auction.
    Rule: 'Even though you declined the option of buying... you may join in the bidding, too.'
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Alice lands on property and declines (simulated by starting auction)
    game.players[0].position = 1

    # Alice (player 0) is the initiator
    auction = game.start_auction(1, initiator_id=0)

    # Both Alice (0) and Bob (1) must be eligible
    assert 0 in auction.active_bidders
    assert 1 in auction.active_bidders

    # Alice already has automatic 10% bid
    assert auction.high_bidder == 0
    assert auction.current_bid == 6  # 10% of 60

    # Bob outbids Alice
    success = auction.place_bid(1, 20)
    assert success
    assert auction.high_bidder == 1


def test_auction_passing_leads_to_win():
    """Test players passing in auction results in win for remaining bidder."""
    event_log = EventLog()
    auction = Auction(
        property_position=1,
        property_name="Mediterranean Avenue",
        eligible_player_ids=[0, 1],
        event_log=event_log,
        initiator_id=0,
        property_price=60,
    )

    # Player 0 already has starting bid of 6
    assert auction.current_bid == 6

    # Player 1 passes
    auction.pass_turn(1)

    # Auction should complete with player 0 winning (initiator's starting bid)
    assert auction.is_complete
    assert auction.get_winner() == 0
    assert auction.get_winning_bid() == 6


def test_auction_all_others_pass_initiator_wins():
    """
    Test that when all other players pass, the initiator wins with their 10% bid.
    This is the key fix: initiator always gets property for at least 10% if no one else bids.
    """
    event_log = EventLog()
    auction = Auction(
        property_position=1,
        property_name="Mediterranean Avenue",
        eligible_player_ids=[0, 1, 2, 3],
        event_log=event_log,
        initiator_id=0,
        property_price=200,  # 10% = 20
    )

    # Initiator has starting bid of 20
    assert auction.current_bid == 20
    assert auction.high_bidder == 0

    # All other players pass
    auction.pass_turn(1)
    auction.pass_turn(2)
    auction.pass_turn(3)

    # Auction completes with initiator winning
    assert auction.is_complete
    assert auction.get_winner() == 0
    assert auction.get_winning_bid() == 20


def test_auction_initiator_passes_others_bid():
    """Test that if initiator passes, other players can still bid and win."""
    event_log = EventLog()
    auction = Auction(
        property_position=1,
        property_name="Mediterranean Avenue",
        eligible_player_ids=[0, 1, 2],
        event_log=event_log,
        initiator_id=0,
        property_price=100,  # 10% = 10
    )

    # Initiator has starting bid of 10
    assert auction.current_bid == 10

    # Player 1 outbids
    auction.place_bid(1, 50)
    assert auction.high_bidder == 1

    # Initiator passes
    auction.pass_turn(0)

    # Player 2 passes
    auction.pass_turn(2)

    # Auction completes with player 1 winning
    assert auction.is_complete
    assert auction.get_winner() == 1
    assert auction.get_winning_bid() == 50


def test_auction_result_transfer():
    """
    Test that winning an auction transfers property and cash correctly.
    Crucial: Winner pays BID price, not BOARD price.
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Mediterranean Avenue: Board Price is 60.
    # Auction it off with Alice as initiator
    auction = game.start_auction(1, initiator_id=0)

    # Alice's starting bid is 6 (10% of 60)
    assert auction.current_bid == 6

    # Bob outbids
    auction.place_bid(1, 20)
    auction.pass_turn(0)  # Alice gives up

    # Bob wins with 20
    assert auction.get_winner() == 1
    assert auction.get_winning_bid() == 20

    # Execute settlement (game logic to finalize auction)
    bob_cash_before = game.players[1].cash
    game.resolve_auction(auction)

    # Check ownership
    assert game.property_ownership[1].owner_id == 1

    # Check cash: Bob pays 20 (bid), NOT 60 (price)
    expected_cash = bob_cash_before - 20
    assert game.players[1].cash == expected_cash


def test_declined_purchase_flow():
    """Test that declining purchase properly sets up the auction state."""
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    game.players[0].position = 1

    # Simulate logic where player lands but chooses NOT to buy
    # Alice is the initiator
    auction = game.start_auction(1, initiator_id=0)

    assert auction is not None
    assert auction.property_position == 1
    assert auction.initiator_id == 0
    # Alice has starting bid (10% of 60 = 6)
    assert auction.current_bid == 6
    assert auction.high_bidder == 0
    # Check that it's stored in game state
    assert game.active_auction == auction


def test_auction_minimum_bid_is_one():
    """Test that even for very cheap properties, minimum starting bid is 1."""
    event_log = EventLog()
    # Property price = 5, 10% = 0.5, but minimum should be 1
    auction = Auction(
        property_position=1,
        property_name="Cheap Property",
        eligible_player_ids=[0, 1],
        event_log=event_log,
        initiator_id=0,
        property_price=5,
    )

    assert auction.current_bid == 1  # Minimum $1
    assert auction.high_bidder == 0
