"""
PlayerAgent class implementation
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

import requests

from strategies.player_strategies import choose_parity_random, choose_parity_alternating, choose_parity_history
from utils import player_handlers
from utils.jsonrpc_utils import wrap_request, wrap_response, unwrap_message, get_request_id, is_jsonrpc_message


class PlayerAgent:
    """Player Agent for Even/Odd League"""

    def __init__(self, display_name: str, port: int, strategy: str):
        self.display_name = display_name
        self.port = port
        self.strategy = strategy
        self.agent_endpoint = f"http://localhost:{port}/mcp"
        self.league_manager_url = "http://localhost:8000/mcp"

        self.player_id: Optional[str] = None
        self.auth_token: Optional[str] = None
        self.last_choice: Optional[str] = None

        self.upcoming_matches: List[Dict] = []
        self.game_history: List[Dict] = []
        self.current_match: Optional[Dict] = None

        self.stats = {"wins": 0, "losses": 0, "draws": 0, "total_games": 0}

        Path("jsonl").mkdir(exist_ok=True)
        self.log_file = Path(f"jsonl/player_{port}.jsonl")
        self.setup_logging()

    def setup_logging(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(f"PlayerAgent:{self.port}")

    def log_message(self, message: Dict, direction: str):
        log_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "direction": direction, "message": message}
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    def generate_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def generate_conversation_id(self) -> str:
        return str(uuid4())

    def send_message(self, url: str, message: Dict, request_id: int = 1) -> Optional[Dict]:
        # Wrap in JSON-RPC 2.0 format
        jsonrpc_message = wrap_request(message, request_id)
        self.log_message(jsonrpc_message, "outgoing")
        self.logger.info(f"Sending {message['message_type']} to {url}")

        try:
            response = requests.post(url, json=jsonrpc_message, timeout=10)
            response.raise_for_status()
            result = response.json()
            self.log_message(result, "incoming")

            # Unwrap JSON-RPC response
            if is_jsonrpc_message(result):
                return unwrap_message(result)
            return result
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return None

    def choose_parity(self) -> str:
        """Choose parity based on configured strategy"""
        if self.strategy == "random":
            choice = choose_parity_random()
        elif self.strategy == "alternating":
            choice = choose_parity_alternating(self.last_choice)
        elif self.strategy == "history":
            choice = choose_parity_history(self.game_history, self.last_choice)
        else:
            self.logger.warning(f"Unknown strategy '{self.strategy}', using random")
            choice = choose_parity_random()

        self.last_choice = choice
        self.logger.info(f"Chose parity: {choice} (strategy: {self.strategy})")
        return choice

    def register_with_league(self):
        """Register with league manager"""
        self.logger.info("Registering with league manager...")

        message = {
            "protocol": "league.v2",
            "message_type": "LEAGUE_REGISTER_REQUEST",
            "sender": f"player:{self.display_name}",
            "timestamp": self.generate_timestamp(),
            "conversation_id": self.generate_conversation_id(),
            "player_meta": {
                "display_name": self.display_name,
                "version": "1.0.0",
                "game_types": ["even_odd"],
                "contact_endpoint": self.agent_endpoint
            }
        }

        response = self.send_message(self.league_manager_url, message, request_id=1)

        if response and response.get("message_type") == "LEAGUE_REGISTER_RESPONSE":
            self.player_id = response.get("player_id")
            self.auth_token = response.get("auth_token")
            self.logger.info(f"Successfully registered as {self.player_id}")
            return True
        else:
            self.logger.error("Failed to register with league manager")
            return False

    def handle_message(self, message: Dict) -> Optional[Dict]:
        """Route incoming message to appropriate handler"""
        self.log_message(message, "incoming")

        # Unwrap JSON-RPC if needed
        request_id = get_request_id(message) if is_jsonrpc_message(message) else 1
        if is_jsonrpc_message(message):
            message = unwrap_message(message)

        message_type = message.get("message_type")
        self.logger.info(f"Handling message: {message_type}")

        if message_type == "ROUND_ANNOUNCEMENT":
            player_handlers.handle_round_announcement(self, message)
            result = {"status": "received"}
        elif message_type == "GAME_INVITATION":
            result = player_handlers.handle_game_invitation(self, message)
        elif message_type == "CHOOSE_PARITY_CALL":
            result = player_handlers.handle_choose_parity_call(self, message)
        elif message_type == "GAME_OVER":
            result = player_handlers.handle_game_over(self, message)
        elif message_type == "LEAGUE_STANDINGS_UPDATE":
            player_handlers.handle_league_standings_update(self, message)
            result = {"status": "received"}
        elif message_type == "LEAGUE_COMPLETED":
            player_handlers.handle_league_completed(self, message)
            result = {"status": "received"}
        else:
            self.logger.warning(f"Unknown message type: {message_type}")
            result = {"status": "unknown_message_type"}

        # Wrap result in JSON-RPC response
        return wrap_response(result, request_id)
