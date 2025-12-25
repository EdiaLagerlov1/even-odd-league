"""
LeagueManager class implementation
"""
from typing import Dict, List, Optional, Any
from models.league_models import MatchStatus, RefereeMetadata, PlayerMetadata, Referee, Player, Match
from utils.league_manager_core import LeagueManagerCore
from utils.jsonrpc_utils import wrap_request
import uuid
import secrets
import json
import itertools
import logging

logger = logging.getLogger(__name__)


class LeagueManager(LeagueManagerCore):
    def __init__(self):
        self.referees: Dict[str, Referee] = {}
        self.players: Dict[str, Player] = {}
        self.matches: Dict[str, Match] = {}
        self.schedule: List[Match] = []
        self.current_round = 0
        self.total_rounds = 0
        self.league_started = False
        self.league_completed = False

        import os
        os.makedirs("jsonl", exist_ok=True)
        self.log_file = "jsonl/league_manager.jsonl"

    def generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def generate_token(self) -> str:
        return secrets.token_urlsafe(32)

    def log_message(self, message: Dict[str, Any]):
        try:
            with open(self.log_file, 'a') as f:
                json.dump(message, f)
                f.write('\n')
        except Exception as e:
            logger.error(f"Failed to log message: {e}")

    def validate_auth(self, entity_id: str, auth_token: str, entity_type: str = "player") -> bool:
        if entity_type == "player":
            player = self.players.get(entity_id)
            return player and player.auth_token == auth_token
        elif entity_type == "referee":
            referee = self.referees.get(entity_id)
            return referee and referee.auth_token == auth_token
        return False

    def register_referee(self, metadata: RefereeMetadata) -> tuple[str, str]:
        referee_id = self.generate_id("ref")
        auth_token = self.generate_token()
        referee = Referee(referee_id, auth_token, metadata)
        self.referees[referee_id] = referee
        logger.info(f"Registered referee: {referee_id} - {metadata.display_name}")
        return referee_id, auth_token

    def register_player(self, metadata: PlayerMetadata) -> tuple[str, str]:
        player_id = self.generate_id("player")
        auth_token = self.generate_token()
        player = Player(player_id, auth_token, metadata)
        self.players[player_id] = player
        logger.info(f"Registered player: {player_id} - {metadata.display_name}")
        return player_id, auth_token

    def create_schedule(self, rounds: int = 1):
        if len(self.players) < 2:
            raise ValueError("Need at least 2 players to create schedule")
        if len(self.referees) == 0:
            raise ValueError("Need at least 1 referee to create schedule")

        player_ids = list(self.players.keys())
        referee_ids = list(self.referees.keys())

        self.schedule = []
        for round_num in range(rounds):
            round_id = round_num + 1
            pairings = list(itertools.combinations(player_ids, 2))

            for i, (player1_id, player2_id) in enumerate(pairings):
                match_id = self.generate_id("match")
                referee_id = referee_ids[i % len(referee_ids)]
                match = Match(match_id, round_id, player1_id, player2_id, referee_id)
                self.matches[match_id] = match
                self.schedule.append(match)

        self.total_rounds = rounds
        self.current_round = 1
        self.league_started = True
        logger.info(f"Created schedule with {len(self.schedule)} matches across {rounds} rounds")

    def broadcast_to_players(self, message: Dict[str, Any]):
        import requests
        # Wrap message in JSON-RPC 2.0 format
        jsonrpc_message = wrap_request(message, request_id=1)
        for player_id, player in self.players.items():
            try:
                endpoint = player.metadata.agent_endpoint
                response = requests.post(endpoint, json=jsonrpc_message, timeout=5)
                logger.info(f"Broadcasted {message['message_type']} to {player_id}")
            except Exception as e:
                logger.error(f"Failed to broadcast to {player_id}: {e}")

    def broadcast_to_referees(self, message: Dict[str, Any]):
        import requests
        # Wrap message in JSON-RPC 2.0 format
        jsonrpc_message = wrap_request(message, request_id=1)
        for referee_id, referee in self.referees.items():
            try:
                endpoint = referee.metadata.endpoint
                if endpoint:
                    response = requests.post(endpoint, json=jsonrpc_message, timeout=5)
                    logger.info(f"Broadcasted {message['message_type']} to {referee_id}")
            except Exception as e:
                logger.error(f"Failed to broadcast to {referee_id}: {e}")

    def broadcast_to_all(self, message: Dict[str, Any]):
        self.broadcast_to_players(message)
        self.broadcast_to_referees(message)

    def check_round_complete(self, round_id: int) -> bool:
        round_matches = [m for m in self.matches.values() if m.round_id == round_id]
        if not round_matches:
            return False
        return all(m.status == MatchStatus.COMPLETED for m in round_matches)

    def check_league_complete(self) -> bool:
        return all(m.status == MatchStatus.COMPLETED for m in self.matches.values())
