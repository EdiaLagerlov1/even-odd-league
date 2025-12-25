"""
Game execution logic for Referee
"""
import asyncio
import random
from models.referee_models import GameState
from game.player_interaction import request_player_choice, send_game_over, send_match_result


async def determine_winner(game):
    """Determine game winner based on drawn number and choices"""
    game.state = GameState.DETERMINING_WINNER

    game.drawn_number = random.randint(1, 100)
    parity = "even" if game.drawn_number % 2 == 0 else "odd"

    print(f"Drew number: {game.drawn_number} ({parity})")
    print(f"Player1 chose: {game.player1_choice}, Player2 chose: {game.player2_choice}")

    if game.player1_choice == parity and game.player2_choice != parity:
        game.winner_id = game.player1_id
    elif game.player2_choice == parity and game.player1_choice != parity:
        game.winner_id = game.player2_id
    else:
        game.winner_id = None


async def run_game(referee_server, game):
    """Execute complete game flow"""
    try:
        print(f"\n=== Starting Game {game.match_id} ===")

        # Send invitations in parallel
        results = await asyncio.gather(
            asyncio.to_thread(
                referee_server.send_message,
                game.player1_endpoint,
                referee_server.create_message(
                    "GAME_INVITATION",
                    conversation_id=game.conversation_id,
                    league_id=game.league_id,
                    round_id=game.round_id,
                    match_id=game.match_id,
                    game_type="even_odd",
                    role_in_match="PLAYER_A",
                    opponent_id=game.player2_id
                )
            ),
            asyncio.to_thread(
                referee_server.send_message,
                game.player2_endpoint,
                referee_server.create_message(
                    "GAME_INVITATION",
                    conversation_id=game.conversation_id,
                    league_id=game.league_id,
                    round_id=game.round_id,
                    match_id=game.match_id,
                    game_type="even_odd",
                    role_in_match="PLAYER_B",
                    opponent_id=game.player1_id
                )
            ),
            return_exceptions=True
        )

        p1_result, p2_result = results

        p1_joined = (
            not isinstance(p1_result, Exception) and
            p1_result and
            p1_result.get("message_type") == "GAME_JOIN_ACK"
        )
        p2_joined = (
            not isinstance(p2_result, Exception) and
            p2_result and
            p2_result.get("message_type") == "GAME_JOIN_ACK"
        )

        if not p1_joined or not p2_joined:
            print(f"Players failed to join: P1={p1_joined}, P2={p2_joined}")
            return

        game.player1_joined = True
        game.player2_joined = True
        print("Both players joined!")

        # Collect choices
        game.state = GameState.COLLECTING_CHOICES
        print("Collecting player choices...")

        results = await asyncio.gather(
            request_player_choice(referee_server, game, game.player1_id, game.player1_endpoint),
            request_player_choice(referee_server, game, game.player2_id, game.player2_endpoint),
            return_exceptions=True
        )

        game.player1_choice = results[0] if not isinstance(results[0], Exception) else None
        game.player2_choice = results[1] if not isinstance(results[1], Exception) else None

        if game.player1_choice is None:
            game.winner_id = game.player2_id
            print(f"Technical loss: {game.player1_id} failed to respond")
        elif game.player2_choice is None:
            game.winner_id = game.player1_id
            print(f"Technical loss: {game.player2_id} failed to respond")
        else:
            await determine_winner(game)

        await send_game_over(referee_server, game)
        await send_match_result(referee_server, game)

        game.state = GameState.COMPLETED
        print(f"=== Game {game.match_id} Completed ===\n")

    except Exception as e:
        print(f"Error running game {game.match_id}: {e}")
        for player_endpoint in [game.player1_endpoint, game.player2_endpoint]:
            error_msg = referee_server.create_message(
                "GAME_ERROR",
                conversation_id=game.conversation_id,
                match_id=game.match_id,
                error_code="GAME_ERROR",
                error_message=str(e)
            )
            referee_server.send_message(player_endpoint, error_msg)
