"""
FastAPI endpoint handlers for League Manager
"""
from fastapi import HTTPException, Request
from typing import Dict, Any
from models.league_models import RefereeMetadata, PlayerMetadata, MatchStatus
from utils.league_utils import (
    create_referee_register_response, create_league_register_response,
    create_league_query_response, create_error_response, create_base_message
)
from utils.jsonrpc_utils import wrap_request, wrap_response, unwrap_message, get_request_id, is_jsonrpc_message
import uuid
import logging

logger = logging.getLogger(__name__)


async def handle_mcp_request(request: Request, league_manager):
    """Handle JSON-RPC 2.0 requests"""
    try:
        body = await request.json()
        league_manager.log_message({"type": "incoming_request", "body": body})

        # Unwrap JSON-RPC if needed
        request_id = get_request_id(body) if is_jsonrpc_message(body) else 1
        if is_jsonrpc_message(body):
            body = unwrap_message(body)

        conversation_id = body.get("conversation_id", str(uuid.uuid4()))
        message_type = body.get("message_type")

        if message_type == "REFEREE_REGISTER_REQUEST":
            metadata_dict = body.get("referee_meta", body.get("metadata", {}))
            metadata = RefereeMetadata(
                display_name=metadata_dict.get("display_name", "Unknown Referee"),
                version=metadata_dict.get("version"),
                endpoint=metadata_dict.get("contact_endpoint", metadata_dict.get("endpoint"))
            )
            referee_id, auth_token = league_manager.register_referee(metadata)
            response = create_referee_register_response(referee_id, auth_token, conversation_id)
            league_manager.log_message({"type": "outgoing_response", "body": response})
            return wrap_response(response, request_id)

        elif message_type == "LEAGUE_REGISTER_REQUEST":
            metadata_dict = body.get("player_meta", body.get("metadata", {}))
            metadata = PlayerMetadata(
                display_name=metadata_dict.get("display_name", "Unknown Player"),
                agent_endpoint=metadata_dict.get("contact_endpoint", metadata_dict.get("agent_endpoint", "")),
                strategy=metadata_dict.get("strategy")
            )
            player_id, auth_token = league_manager.register_player(metadata)
            response = create_league_register_response(player_id, auth_token, conversation_id)
            league_manager.log_message({"type": "outgoing_response", "body": response})
            return wrap_response(response, request_id)

        elif message_type == "MATCH_RESULT_REPORT":
            # Extract auth from sender field
            sender = body.get("sender", "")
            if sender.startswith("referee:"):
                referee_id = sender.split(":")[1]
            else:
                referee_id = body.get("referee_id")

            auth_token = body.get("auth_token")
            if not league_manager.validate_auth(referee_id, auth_token, "referee"):
                error_response = create_error_response("AUTH_FAILED", "Invalid auth token", conversation_id)
                league_manager.log_message({"type": "outgoing_response", "body": error_response})
                return wrap_response(error_response, request_id)

            match_id = body.get("match_id")
            result = body.get("result", {})
            league_manager.update_match_result(match_id, result)

            response = create_base_message("MATCH_RESULT_ACKNOWLEDGED", conversation_id)
            response["match_id"] = match_id
            league_manager.log_message({"type": "outgoing_response", "body": response})
            return wrap_response(response, request_id)

        elif message_type == "LEAGUE_QUERY":
            player_id, auth_token = body.get("player_id"), body.get("auth_token")
            if not league_manager.validate_auth(player_id, auth_token, "player"):
                error_response = create_error_response("AUTH_FAILED", "Invalid auth token", conversation_id)
                league_manager.log_message({"type": "outgoing_response", "body": error_response})
                return wrap_response(error_response, request_id)
            query_type = body.get("query_type")
            if query_type == "GET_STANDINGS":
                data = league_manager.get_standings()
                response = create_league_query_response("GET_STANDINGS", data, conversation_id)
            elif query_type == "GET_SCHEDULE":
                data = league_manager.get_schedule_data()
                response = create_league_query_response("GET_SCHEDULE", data, conversation_id)
            elif query_type == "GET_NEXT_MATCH":
                data = league_manager.get_next_match(player_id)
                response = create_league_query_response("GET_NEXT_MATCH", data, conversation_id)
            elif query_type == "GET_PLAYER_STATS":
                target_player_id = body.get("target_player_id", player_id)
                data = league_manager.get_player_stats(target_player_id)
                response = create_league_query_response("GET_PLAYER_STATS", data, conversation_id)
            else:
                error_response = create_error_response("UNKNOWN_QUERY", f"Unknown query type: {query_type}", conversation_id)
                league_manager.log_message({"type": "outgoing_response", "body": error_response})
                return wrap_response(error_response, request_id)
            league_manager.log_message({"type": "outgoing_response", "body": response})
            return wrap_response(response, request_id)
        else:
            error_response = create_error_response("UNKNOWN_MESSAGE_TYPE", f"Unknown message type: {message_type}", conversation_id)
            league_manager.log_message({"type": "outgoing_response", "body": error_response})
            return wrap_response(error_response, request_id)
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        error_response = create_error_response("INTERNAL_ERROR", str(e), str(uuid.uuid4()))
        league_manager.log_message({"type": "outgoing_response", "body": error_response})
        wrapped_error = wrap_response(error_response, 1)
        raise HTTPException(status_code=500, detail=str(e))


async def start_league(rounds: int, league_manager):
    """Create schedule and start the league"""
    try:
        league_manager.create_schedule(rounds=rounds)
        import httpx
        import asyncio
        assigned_count = 0
        for match in league_manager.schedule:
            referee = league_manager.referees.get(match.referee_id)
            player1 = league_manager.players.get(match.player1_id)
            player2 = league_manager.players.get(match.player2_id)

            if not referee or not player1 or not player2:
                continue

            assignment_message = create_base_message("MATCH_ASSIGNMENT", str(uuid.uuid4()))
            assignment_message.update({
                "match_id": match.match_id,
                "league_id": "league_2025_even_odd",
                "round_id": match.round_id,
                "player1_id": match.player1_id,
                "player2_id": match.player2_id,
                "player1_endpoint": player1.metadata.agent_endpoint,
                "player2_endpoint": player2.metadata.agent_endpoint
            })

            # Wrap in JSON-RPC 2.0 format
            jsonrpc_message = wrap_request(assignment_message, request_id=assigned_count + 1)

            ref_port = 8001 if assigned_count % 2 == 0 else 8002
            referee_url = f"http://localhost:{ref_port}/mcp"

            try:
                async with httpx.AsyncClient() as client:
                    await client.post(referee_url, json=jsonrpc_message, timeout=10)
                match.status = MatchStatus.IN_PROGRESS
                assigned_count += 1
                # Add delay between assignments to respect max_concurrent_matches
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Failed to assign match {match.match_id} to referee: {e}")

        return {
            "status": "success",
            "message": f"League started, {assigned_count} matches assigned",
            "matches": len(league_manager.matches)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
