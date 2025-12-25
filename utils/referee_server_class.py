"""
RefereeServer class implementation
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any

import requests

from models.referee_models import GameSession
from game import game_logic
from utils.jsonrpc_utils import wrap_request, wrap_response, unwrap_message, get_request_id, is_jsonrpc_message


class RefereeServer:
    """Referee server managing Even/Odd games"""

    def __init__(self, name: str = "Referee Alpha", port: int = 8001):
        self.referee_id: Optional[str] = None
        self.auth_token: Optional[str] = None
        self.league_manager_url = "http://localhost:8000/mcp"
        self.games: Dict[str, GameSession] = {}

        import os
        os.makedirs("jsonl", exist_ok=True)
        self.log_file = f"jsonl/referee_{port}.jsonl"

        self.name = name
        self.port = port

    def log_message(self, message: Dict[str, Any], direction: str = "sent"):
        """Log message to JSON Lines file"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "direction": direction,
            "message": message
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def create_message(self, message_type: str, **kwargs) -> Dict[str, Any]:
        """Create a message with standard fields"""
        message = {
            "protocol": "league.v2",
            "message_type": message_type,
            "sender": f"referee:{self.referee_id}" if self.referee_id else "referee:UNREGISTERED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
        return message

    def send_message(self, url: str, message: Dict[str, Any], request_id: int = 1) -> Optional[Dict[str, Any]]:
        """Send HTTP POST request with message in JSON-RPC 2.0 format"""
        # Add auth token if needed
        if self.auth_token and "auth_token" not in message:
            message["auth_token"] = self.auth_token

        # Wrap in JSON-RPC 2.0 format
        jsonrpc_message = wrap_request(message, request_id)
        self.log_message(jsonrpc_message, "sent")

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=jsonrpc_message, headers=headers, timeout=30)
            response.raise_for_status()
            response_data = response.json()
            self.log_message(response_data, "received")

            # Unwrap JSON-RPC response
            if is_jsonrpc_message(response_data):
                return unwrap_message(response_data)
            return response_data
        except Exception as e:
            print(f"Error sending message to {url}: {e}")
            return None

    async def register_with_league(self):
        """Register referee with league manager"""
        message = self.create_message(
            "REFEREE_REGISTER_REQUEST",
            conversation_id=str(uuid.uuid4()),
            referee_meta={
                "display_name": self.name,
                "version": "1.0.0",
                "game_types": ["even_odd"],
                "contact_endpoint": f"http://localhost:{self.port}/mcp",
                "max_concurrent_matches": 2
            }
        )

        response = self.send_message(self.league_manager_url, message, request_id=1)
        if response and response.get("message_type") == "REFEREE_REGISTER_RESPONSE":
            self.referee_id = response.get("referee_id")
            self.auth_token = response.get("auth_token")
            print(f"✓ Registered as {self.referee_id}")
            return True
        else:
            print("✗ Registration failed")
            return False

    async def handle_match_assignment(self, data: Dict[str, Any]):
        """Handle match assignment from league manager"""
        match_id = data.get("match_id")
        player1_id = data.get("player1_id")
        player2_id = data.get("player2_id")
        player1_endpoint = data.get("player1_endpoint")
        player2_endpoint = data.get("player2_endpoint")
        league_id = data.get("league_id", "league_2025_even_odd")
        round_id = data.get("round_id", 1)

        if not all([match_id, player1_id, player2_id, player1_endpoint, player2_endpoint]):
            print("Invalid match assignment - missing required fields")
            return

        game = GameSession(match_id, player1_id, player2_id, player1_endpoint, player2_endpoint,
                          league_id, round_id)
        self.games[match_id] = game

        asyncio.create_task(game_logic.run_game(self, game))

        return {
            "protocol": "league.v2",
            "message_type": "MATCH_ASSIGNMENT_ACK",
            "sender": f"referee:{self.referee_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "conversation_id": data.get("conversation_id"),
            "match_id": match_id,
            "status": "accepted"
        }

    async def handle_message(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC messages"""
        self.log_message(data, "received")

        # Unwrap JSON-RPC if needed
        request_id = get_request_id(data) if is_jsonrpc_message(data) else 1
        if is_jsonrpc_message(data):
            data = unwrap_message(data)

        message_type = data.get("message_type")

        if message_type == "MATCH_ASSIGNMENT":
            result = await self.handle_match_assignment(data)
            return wrap_response(result, request_id)

        elif message_type == "GAME_JOIN_ACK":
            match_id = data.get("match_id")
            player_id = data.get("player_id")

            if match_id in self.games:
                game = self.games[match_id]
                if player_id == game.player1_id:
                    game.player1_joined = True
                elif player_id == game.player2_id:
                    game.player2_joined = True
                print(f"Player {player_id} joined game {match_id}")

        result = {
            "protocol": "league.v2",
            "message_type": "ACK",
            "sender": f"referee:{self.referee_id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "conversation_id": data.get("conversation_id", str(uuid.uuid4()))
        }
        return wrap_response(result, request_id)
