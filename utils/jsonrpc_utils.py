"""
JSON-RPC 2.0 message wrapper utilities
"""
from typing import Dict, Any, Optional


# Message type to JSON-RPC method mapping
# Maps league.v2 protocol message types to JSON-RPC 2.0 method names
# This enables standard JSON-RPC routing while maintaining semantic message types
MESSAGE_TYPE_TO_METHOD = {
    # Registration messages
    "REFEREE_REGISTER_REQUEST": "register_referee",      # Referee joining league
    "REFEREE_REGISTER_RESPONSE": "register_referee",     # League manager response
    "LEAGUE_REGISTER_REQUEST": "register_player",        # Player joining league
    "LEAGUE_REGISTER_RESPONSE": "register_player",       # League manager response

    # Match assignment
    "MATCH_ASSIGNMENT": "assign_match",                  # League → Referee: run this match
    "MATCH_ASSIGNMENT_ACK": "assign_match",              # Referee acknowledgment

    # Game flow
    "GAME_INVITATION": "handle_game_invitation",         # Referee → Player: join game
    "GAME_JOIN_ACK": "handle_game_invitation",           # Player acknowledgment
    "CHOOSE_PARITY_CALL": "choose_parity",               # Referee → Player: make choice
    "CHOOSE_PARITY_RESPONSE": "choose_parity",           # Player's choice response
    "GAME_OVER": "notify_match_result",                  # Referee → Players: game result
    "MATCH_RESULT_REPORT": "report_match_result",        # Referee → League: match outcome
    "MATCH_RESULT_ACKNOWLEDGED": "report_match_result",  # League acknowledgment

    # League progression
    "ROUND_ANNOUNCEMENT": "announce_round",              # League → All: round starting
    "ROUND_COMPLETED": "notify_round_completed",         # League → All: round finished
    "LEAGUE_STANDINGS_UPDATE": "update_standings",       # League → All: current standings
    "LEAGUE_COMPLETED": "notify_league_completed",       # League → All: tournament finished

    # Queries and acknowledgments
    "LEAGUE_QUERY": "query_league",                      # Query league information
    "LEAGUE_QUERY_RESPONSE": "query_league",             # Query response
    "ACK": "acknowledge",                                # Generic acknowledgment
    "ERROR": "error"                                     # Error notification
}


def wrap_request(params: Dict[str, Any], request_id: Optional[int] = 1) -> Dict[str, Any]:
    """
    Wrap a message in JSON-RPC 2.0 request format.

    Args:
        params: The message parameters (protocol, message_type, sender, etc.)
        request_id: The JSON-RPC request ID

    Returns:
        JSON-RPC 2.0 formatted request
    """
    message_type = params.get("message_type", "")
    method = MESSAGE_TYPE_TO_METHOD.get(message_type, "unknown")

    return {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id
    }


def wrap_response(result: Dict[str, Any], request_id: Optional[int] = 1,
                  error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Wrap a message in JSON-RPC 2.0 response format.

    Args:
        result: The response result
        request_id: The JSON-RPC request ID to match
        error: Optional error object

    Returns:
        JSON-RPC 2.0 formatted response
    """
    response = {
        "jsonrpc": "2.0",
        "id": request_id
    }

    if error:
        response["error"] = error
    else:
        response["result"] = result

    return response


def unwrap_message(jsonrpc_message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Unwrap a JSON-RPC 2.0 message to get the params/result.

    Args:
        jsonrpc_message: The JSON-RPC 2.0 formatted message

    Returns:
        The params (for requests) or result (for responses)
    """
    if "params" in jsonrpc_message:
        # This is a request
        return jsonrpc_message["params"]
    elif "result" in jsonrpc_message:
        # This is a successful response
        return jsonrpc_message["result"]
    elif "error" in jsonrpc_message:
        # This is an error response
        return jsonrpc_message["error"]
    else:
        # Fallback to the whole message
        return jsonrpc_message


def get_request_id(jsonrpc_message: Dict[str, Any]) -> Optional[int]:
    """Extract the request ID from a JSON-RPC message"""
    return jsonrpc_message.get("id")


def is_jsonrpc_message(message: Dict[str, Any]) -> bool:
    """Check if a message is in JSON-RPC 2.0 format"""
    return message.get("jsonrpc") == "2.0"
