"""
Player interaction functions for game logic
"""
import asyncio
from typing import Optional


async def request_player_choice(referee_server, game, player_id: str, player_endpoint: str) -> Optional[str]:
    """
    Request parity choice from player with timeout and retries.

    Sends CHOOSE_PARITY_CALL message to player and waits for their response.
    Will retry up to max_retries times if player doesn't respond or sends invalid choice.

    Args:
        referee_server: RefereeServer instance managing the game
        game: GameSession instance containing game state
        player_id: ID of the player to request choice from
        player_endpoint: HTTP endpoint URL of the player agent

    Returns:
        str: Player's choice ("even" or "odd"), or None if player failed to respond
    """
    max_retries = 3
    timeout_seconds = 30

    # Initialize retry counter for this player if not exists
    if player_id not in game.retry_counts:
        game.retry_counts[player_id] = 0

    # Retry loop - give player multiple chances to respond
    while game.retry_counts[player_id] < max_retries:
        # Determine who the opponent is (the other player in the match)
        opponent_id = game.player2_id if player_id == game.player1_id else game.player1_id

        # Calculate deadline timestamp (current time + timeout seconds)
        from datetime import datetime, timezone, timedelta
        deadline = (datetime.now(timezone.utc) + timedelta(seconds=timeout_seconds)).isoformat()

        # Create CHOOSE_PARITY_CALL message with game context
        message = referee_server.create_message(
            "CHOOSE_PARITY_CALL",
            conversation_id=game.conversation_id,
            match_id=game.match_id,
            player_id=player_id,
            game_type="even_odd",
            context={
                "opponent_id": opponent_id,
                "round_id": game.round_id,
                "your_standings": {  # Current player stats (placeholder for now)
                    "wins": 0,
                    "losses": 0,
                    "draws": 0
                }
            },
            deadline=deadline
        )

        try:
            # Send message and wait for response with timeout
            response = await asyncio.wait_for(
                asyncio.to_thread(referee_server.send_message, player_endpoint, message),
                timeout=timeout_seconds
            )

            # Validate response
            if response and response.get("message_type") == "CHOOSE_PARITY_RESPONSE":
                choice = response.get("choice")
                # Check if choice is valid ("even" or "odd")
                if choice in ["even", "odd"]:
                    return choice
                else:
                    print(f"Invalid choice from {player_id}: {choice}")

            # Invalid response - increment retry counter
            game.retry_counts[player_id] += 1

        except asyncio.TimeoutError:
            # Player didn't respond in time
            print(f"Timeout waiting for {player_id} choice (attempt {game.retry_counts[player_id] + 1})")
            game.retry_counts[player_id] += 1

            # Send error notification to player
            error_msg = referee_server.create_message(
                "GAME_ERROR",
                conversation_id=game.conversation_id,
                match_id=game.match_id,
                error_code="TIMEOUT",
                error_message=f"Player {player_id} did not respond in time"
            )
            referee_server.send_message(player_endpoint, error_msg)

    # Player failed after all retries
    return None


async def send_game_over(referee_server, game):
    """
    Send GAME_OVER message to both players with complete game results.

    Constructs a game result object containing the outcome, drawn number,
    player choices, and explanation. Sends identical message to both players.

    Args:
        referee_server: RefereeServer instance managing the game
        game: GameSession instance with final game state
    """
    # Determine if the drawn number is even or odd
    number_parity = "even" if game.drawn_number % 2 == 0 else "odd"

    # Determine game status: DRAW if no winner, WIN if there's a winner
    if game.winner_id is None:
        status = "DRAW"
    else:
        status = "WIN"

    # Create choices dictionary mapping player IDs to their choices
    choices = {
        game.player1_id: game.player1_choice,
        game.player2_id: game.player2_choice
    }

    # Create human-readable reason string explaining the outcome
    if game.winner_id is None:
        # Draw scenario - both players chose the same or both were wrong
        reason = f"Both players chose {game.player1_choice}, number was {game.drawn_number} ({number_parity})"
    else:
        # Win scenario - one player chose correctly
        winner_choice = game.player1_choice if game.winner_id == game.player1_id else game.player2_choice
        reason = f"{game.winner_id} chose {winner_choice}, number was {game.drawn_number} ({number_parity})"

    # Send GAME_OVER message to both players
    for player_id, player_endpoint in [
        (game.player1_id, game.player1_endpoint),
        (game.player2_id, game.player2_endpoint)
    ]:
        message = referee_server.create_message(
            "GAME_OVER",
            conversation_id=game.conversation_id,
            match_id=game.match_id,
            game_type="even_odd",
            game_result={
                "status": status,                    # "WIN" or "DRAW"
                "winner_player_id": game.winner_id,  # Winner ID or None
                "drawn_number": game.drawn_number,   # Random number that was drawn
                "number_parity": number_parity,      # "even" or "odd"
                "choices": choices,                  # Dict of player choices
                "reason": reason                     # Human-readable explanation
            }
        )
        referee_server.send_message(player_endpoint, message)


async def send_match_result(referee_server, game):
    """
    Send MATCH_RESULT_REPORT to league manager with game outcome and scores.

    Calculates points for each player (3 for win, 1 for draw, 0 for loss)
    and reports the result to the league manager for standings updates.

    Args:
        referee_server: RefereeServer instance managing the game
        game: GameSession instance with final game state
    """
    # Calculate scores using standard league scoring: 3 points for win, 1 for draw, 0 for loss
    if game.winner_id is None:
        # Draw - both players get 1 point
        score = {
            game.player1_id: 1,
            game.player2_id: 1
        }
        winner = None
    elif game.winner_id == game.player1_id:
        # Player 1 wins - gets 3 points, player 2 gets 0
        score = {
            game.player1_id: 3,
            game.player2_id: 0
        }
        winner = game.player1_id
    else:
        # Player 2 wins - gets 3 points, player 1 gets 0
        score = {
            game.player1_id: 0,
            game.player2_id: 3
        }
        winner = game.player2_id

    # Create choices dictionary mapping player IDs to their choices
    choices = {
        game.player1_id: game.player1_choice,
        game.player2_id: game.player2_choice
    }

    # Create and send MATCH_RESULT_REPORT to league manager
    message = referee_server.create_message(
        "MATCH_RESULT_REPORT",
        conversation_id=game.conversation_id,
        league_id=game.league_id,
        round_id=game.round_id,
        match_id=game.match_id,
        game_type="even_odd",
        result={
            "winner": winner,              # Winner player ID or None for draw
            "score": score,                # Points awarded to each player
            "details": {                   # Additional game details
                "drawn_number": game.drawn_number,
                "choices": choices
            }
        }
    )
    referee_server.send_message(referee_server.league_manager_url, message)
