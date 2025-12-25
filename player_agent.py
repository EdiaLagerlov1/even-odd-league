#!/usr/bin/env python3
"""
Player Agent for Even/Odd League Game
HTTP server that participates in league games using strategic choices
"""
import argparse
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request

from utils.player_agent_class import PlayerAgent


# Global player agent instance
player_agent: Optional[PlayerAgent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown"""
    await asyncio.sleep(2)
    if player_agent:
        player_agent.register_with_league()
        player_agent.logger.info("Player agent ready and waiting for messages...")
    yield
    if player_agent:
        player_agent.logger.info("Shutting down player agent...")


app = FastAPI(title="Player Agent", version="1.0.0", lifespan=lifespan)


@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """Handle incoming JSON-RPC 2.0 requests"""
    try:
        message = await request.json()
        if player_agent is None:
            return {"error": "Player agent not initialized"}
        response = player_agent.handle_message(message)
        if response is None:
            response = {"status": "processed"}
        return response
    except Exception as e:
        player_agent.logger.error(f"Error handling request: {e}")
        return {"error": str(e)}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "player_id": player_agent.player_id if player_agent else None,
        "registered": player_agent.auth_token is not None if player_agent else False
    }


@app.get("/stats")
async def get_stats():
    """Get player statistics"""
    if player_agent is None:
        return {"error": "Player agent not initialized"}
    return {
        "player_id": player_agent.player_id,
        "display_name": player_agent.display_name,
        "strategy": player_agent.strategy,
        "stats": player_agent.stats,
        "games_played": len(player_agent.game_history),
        "current_match": player_agent.current_match
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Player Agent for Even/Odd League")
    parser.add_argument("--name", type=str, required=True, help="Player display name")
    parser.add_argument("--port", type=int, default=8101, help="HTTP server port (default: 8101)")
    parser.add_argument("--strategy", type=str, choices=["random", "alternating", "history"],
                       default="random", help="Playing strategy (default: random)")

    args = parser.parse_args()

    global player_agent
    player_agent = PlayerAgent(args.name, args.port, args.strategy)

    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
