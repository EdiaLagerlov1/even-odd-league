"""
Message handlers for Player Agent
"""
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


def handle_round_announcement(player_agent, message: Dict):
    """Handle round announcement from league manager"""
    logger.info("Received ROUND_ANNOUNCEMENT")
    round_number = message.get("round_number")
    schedule = message.get("schedule", [])
    player_agent.upcoming_matches = schedule
    logger.info(f"Round {round_number}: {len(schedule)} matches scheduled")
    for match in schedule:
        logger.info(f"  Match {match.get('match_id')}: "
                   f"{match.get('player1_id')} vs {match.get('player2_id')}")


def handle_game_invitation(player_agent, message: Dict) -> Dict:
    """Handle game invitation from referee"""
    logger.info("Received GAME_INVITATION")
    match_id = message.get("match_id")
    opponent_id = message.get("opponent_id")
    league_id = message.get("league_id")
    round_id = message.get("round_id")
    game_type = message.get("game_type")
    role_in_match = message.get("role_in_match")
    player_agent.current_match = {
        "match_id": match_id,
        "opponent_id": opponent_id,
        "league_id": league_id,
        "round_id": round_id,
        "game_type": game_type,
        "role_in_match": role_in_match
    }

    logger.info(f"Invited to match {match_id} as {role_in_match} vs {opponent_id}")

    arrival_timestamp = player_agent.generate_timestamp()
    return {
        "protocol": "league.v2",
        "message_type": "GAME_JOIN_ACK",
        "sender": f"player:{player_agent.player_id}",
        "timestamp": arrival_timestamp,
        "conversation_id": message.get("conversation_id"),
        "auth_token": player_agent.auth_token,
        "match_id": match_id,
        "player_id": player_agent.player_id,
        "arrival_timestamp": arrival_timestamp,
        "accept": True
    }


def handle_choose_parity_call(player_agent, message: Dict) -> Dict:
    """Handle choose parity request from referee"""
    logger.info("Received CHOOSE_PARITY_CALL")
    match_id = message.get("match_id")
    timeout_seconds = message.get("timeout_seconds", 30)
    choice = player_agent.choose_parity()
    response = {
        "protocol": "league.v2",
        "message_type": "CHOOSE_PARITY_RESPONSE",
        "sender": f"player:{player_agent.player_id}",
        "timestamp": player_agent.generate_timestamp(),
        "conversation_id": message.get("conversation_id"),
        "auth_token": player_agent.auth_token,
        "match_id": match_id,
        "choice": choice
    }

    logger.info(f"Responding with choice: {choice}")
    return response


def handle_game_over(player_agent, message: Dict) -> Dict:
    """
    Process GAME_OVER message from referee and update player statistics.

    Extracts game result from message, updates player's win/loss/draw counts,
    records the game in history, and sends acknowledgment back to referee.

    Args:
        player_agent: PlayerAgent instance
        message: GAME_OVER message containing game_result object

    Returns:
        ACK message confirming receipt
    """
    logger.info("Received GAME_OVER")
    match_id = message.get("match_id")
    game_result = message.get("game_result", {})

    # Extract game result details
    winner_id = game_result.get("winner_player_id")
    final_number = game_result.get("drawn_number")
    choices = game_result.get("choices", {})
    status = game_result.get("status")

    # Determine outcome from player's perspective and update stats
    if status == "DRAW" or winner_id is None:
        # Draw - no winner
        result = "draw"
        player_agent.stats["draws"] += 1
    elif winner_id == player_agent.player_id:
        # Player won the match
        result = "win"
        player_agent.stats["wins"] += 1
    else:
        # Player lost the match
        result = "loss"
        player_agent.stats["losses"] += 1

    # Increment total games played
    player_agent.stats["total_games"] += 1

    # Extract opponent's choice from choices dictionary
    opponent_id = player_agent.current_match.get("opponent_id") if player_agent.current_match else None
    opponent_choice = choices.get(opponent_id) if opponent_id else None

    # Create game record for player's history
    game_record = {
        "match_id": match_id,
        "opponent": opponent_id,
        "my_choice": player_agent.last_choice,
        "opponent_choice": opponent_choice,
        "number": final_number,
        "result": result,
        "timestamp": player_agent.generate_timestamp()
    }
    player_agent.game_history.append(game_record)

    # Log game result and current statistics
    logger.info(f"Game result: {result.upper()} - Number: {final_number}")
    logger.info(f"Stats: W:{player_agent.stats['wins']} L:{player_agent.stats['losses']} "
                f"D:{player_agent.stats['draws']} Total:{player_agent.stats['total_games']}")

    # Clear current match state
    player_agent.current_match = None

    # Send acknowledgment back to referee
    return {
        "protocol": "league.v2",
        "message_type": "ACK",
        "sender": f"player:{player_agent.player_id}",
        "timestamp": player_agent.generate_timestamp(),
        "conversation_id": message.get("conversation_id"),
        "status": "received"
    }


def handle_league_standings_update(player_agent, message: Dict):
    """
    Process LEAGUE_STANDINGS_UPDATE message and log player's current position.

    Searches for this player's entry in the standings and logs their rank
    and statistics.

    Args:
        player_agent: PlayerAgent instance
        message: LEAGUE_STANDINGS_UPDATE message containing standings array
    """
    logger.info("Received LEAGUE_STANDINGS_UPDATE")
    standings = message.get("standings", [])

    # Find this player in the standings and log their position
    for player in standings:
        if player.get("player_id") == player_agent.player_id:
            logger.info(f"Current standing: #{player.get('rank')} - "
                       f"W:{player.get('wins')} L:{player.get('losses')} "
                       f"D:{player.get('draws')} Pts:{player.get('points')}")
            break


def handle_league_completed(player_agent, message: Dict):
    """Handle league completion notification"""
    logger.info("Received LEAGUE_COMPLETED")
    final_standings = message.get("final_standings", [])
    for player in final_standings:
        if player.get("player_id") == player_agent.player_id:
            logger.info(f"Final position: #{player.get('rank')}")
            logger.info(f"Final stats: W:{player.get('wins')} "
                       f"L:{player.get('losses')} D:{player.get('draws')} "
                       f"Points:{player.get('points')}")
            break

    logger.info("League completed!")
