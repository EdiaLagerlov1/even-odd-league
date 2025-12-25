"""
Data Models for League Manager
"""
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
from enum import Enum


class MatchStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class RefereeMetadata(BaseModel):
    display_name: str
    version: Optional[str] = None
    endpoint: Optional[str] = None


class PlayerMetadata(BaseModel):
    display_name: str
    agent_endpoint: str
    strategy: Optional[str] = None


class Referee:
    def __init__(self, referee_id: str, auth_token: str, metadata: RefereeMetadata):
        self.referee_id = referee_id
        self.auth_token = auth_token
        self.metadata = metadata


class Player:
    def __init__(self, player_id: str, auth_token: str, metadata: PlayerMetadata):
        self.player_id = player_id
        self.auth_token = auth_token
        self.metadata = metadata
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.total_points_earned = 0
        self.total_points_lost = 0


class Match:
    def __init__(self, match_id: str, round_id: int, player1_id: str, player2_id: str, referee_id: str):
        self.match_id = match_id
        self.round_id = round_id
        self.player1_id = player1_id
        self.player2_id = player2_id
        self.referee_id = referee_id
        self.status = MatchStatus.PENDING
        self.result = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
