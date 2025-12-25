"""
Data Models for Referee Agent
"""
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel


class GameState(Enum):
    """Game state machine"""
    WAITING_FOR_PLAYERS = "WAITING_FOR_PLAYERS"
    COLLECTING_CHOICES = "COLLECTING_CHOICES"
    DETERMINING_WINNER = "DETERMINING_WINNER"
    COMPLETED = "COMPLETED"


class Message(BaseModel):
    """JSON-RPC 2.0 message structure"""
    protocol: str = "league.v2"
    message_type: str
    sender: str
    timestamp: str
    conversation_id: str
    match_id: Optional[str] = None

    class Config:
        extra = "allow"


class GameSession:
    """Manages a single game session"""
    def __init__(self, match_id: str, player1_id: str, player2_id: str,
                 player1_endpoint: str, player2_endpoint: str,
                 league_id: str = "league_2025_even_odd", round_id: int = 1):
        import uuid
        self.match_id = match_id
        self.league_id = league_id
        self.round_id = round_id
        self.conversation_id = str(uuid.uuid4())
        self.state = GameState.WAITING_FOR_PLAYERS

        self.player1_id = player1_id
        self.player2_id = player2_id
        self.player1_endpoint = player1_endpoint
        self.player2_endpoint = player2_endpoint

        self.player1_joined = False
        self.player2_joined = False
        self.player1_choice: Optional[str] = None
        self.player2_choice: Optional[str] = None

        self.drawn_number: Optional[int] = None
        self.winner_id: Optional[str] = None

        self.retry_counts: Dict[str, int] = {player1_id: 0, player2_id: 0}
