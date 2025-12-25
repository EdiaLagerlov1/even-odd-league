"""
Utility functions for League Manager
"""
from typing import Dict, Any
import uuid
from datetime import datetime


def get_timestamp() -> str:
    """Get ISO 8601 UTC timestamp"""
    return datetime.utcnow().isoformat() + "Z"


def create_base_message(message_type: str, conversation_id: str = None) -> Dict[str, Any]:
    """Create base message structure"""
    return {
        "protocol": "league.v2",
        "message_type": message_type,
        "sender": "league_manager",
        "timestamp": get_timestamp(),
        "conversation_id": conversation_id or str(uuid.uuid4())
    }


def create_referee_register_response(referee_id: str, auth_token: str, conversation_id: str) -> Dict[str, Any]:
    """Create REFEREE_REGISTER_RESPONSE"""
    msg = create_base_message("REFEREE_REGISTER_RESPONSE", conversation_id)
    msg.update({
        "status": "ACCEPTED",
        "referee_id": referee_id,
        "auth_token": auth_token,
        "league_id": "league_2025_even_odd",
        "reason": None
    })
    return msg


def create_league_register_response(player_id: str, auth_token: str, conversation_id: str) -> Dict[str, Any]:
    """Create LEAGUE_REGISTER_RESPONSE"""
    msg = create_base_message("LEAGUE_REGISTER_RESPONSE", conversation_id)
    msg.update({
        "status": "ACCEPTED",
        "player_id": player_id,
        "auth_token": auth_token,
        "league_id": "league_2025_even_odd",
        "reason": None
    })
    return msg


def create_league_query_response(query_type: str, data: Any, conversation_id: str) -> Dict[str, Any]:
    """Create LEAGUE_QUERY_RESPONSE"""
    msg = create_base_message("LEAGUE_QUERY_RESPONSE", conversation_id)
    msg.update({
        "query_type": query_type,
        "data": data
    })
    return msg


def create_error_response(error_code: str, error_message: str, conversation_id: str) -> Dict[str, Any]:
    """Create error response"""
    msg = create_base_message("ERROR", conversation_id)
    msg.update({
        "error_code": error_code,
        "error_message": error_message
    })
    return msg
