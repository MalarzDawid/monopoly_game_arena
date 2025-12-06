"""
Tests for property auctions.
"""

import pytest
from monopoly.game import create_game
from monopoly.player import Player
from monopoly.config import GameConfig
from monopoly.auction import Auction
from monopoly.money import EventLog


def test_auction_creation():
    """Test creating an auction."""
    event_log = EventLog()
    auction = Auction(1, "Mediterranean Avenue", [0, 1, 2], event_log)

    assert auction.property_position == 1
    assert auction.high_bidder is None
    assert auction.current_bid == 0
    assert not auction.is_complete
    assert len(auction.active_bidders) == 3


def test_auction_bidding_mechanics():
    """
    Test placing bids in auction.
    Rule: 'starting at any price that another player is willing to pay'
    """
    event_log = EventLog()
    auction = Auction(1, "Mediterranean Avenue", [0, 1], event_log)

    # Player 0 bids 1 (valid start price, low)
    assert auction.place_bid(0, 1)
    assert auction.current_bid == 1
    assert auction.high_bidder == 0

    # Player 1 bids 10
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
    
    auction = game.start_auction(1)

    # Both Alice (0) and Bob (1) must be eligible
    assert 0 in auction.active_bidders
    assert 1 in auction.active_bidders
    
    # Alice should be able to place a bid
    success = auction.place_bid(0, 10)
    assert success
    assert auction.high_bidder == 0


def test_auction_passing_leads_to_win():
    """Test players passing in auction results in win for remaining bidder."""
    event_log = EventLog()
    auction = Auction(1, "Mediterranean Avenue", [0, 1], event_log)

    auction.place_bid(0, 10)

    # Player 1 passes
    auction.pass_turn(1)

    # Auction should complete with player 0 winning
    assert auction.is_complete
    assert auction.get_winner() == 0
    assert auction.get_winning_bid() == 10


def test_auction_no_bids():
    """Test auction where all players pass without bidding."""
    event_log = EventLog()
    auction = Auction(1, "Mediterranean Avenue", [0, 1], event_log)

    # Both players pass immediately
    auction.pass_turn(0)
    auction.pass_turn(1)

    assert auction.is_complete
    assert auction.get_winner() is None
    # Property remains unowned


def test_auction_result_transfer():
    """
    Test that winning an auction transfers property and cash correctly.
    Crucial: Winner pays BID price, not BOARD price.
    """
    config = GameConfig(seed=42)
    players = [Player(0, "Alice"), Player(1, "Bob")]
    game = create_game(config, players)

    # Mediterranean Avenue: Board Price is 60.
    # Auction it off.
    auction = game.start_auction(1)

    # Bidding war
    auction.place_bid(0, 10)
    auction.place_bid(1, 20)
    auction.pass_turn(0) # Alice gives up

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
    # This usually triggers the auction immediately
    auction = game.start_auction(1)

    assert auction is not None
    assert auction.property_position == 1
    # Check that it's stored in game state if applicable
    assert game.active_auction == auction
