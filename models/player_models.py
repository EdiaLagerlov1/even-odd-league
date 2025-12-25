"""
Data Models for Player Agent
"""
from pydantic import BaseModel
from typing import Optional


class Message(BaseModel):
    protocol: str = "league.v2"
    message_type: str
    sender: str
    timestamp: str
    conversation_id: str
    auth_token: Optional[str] = None
