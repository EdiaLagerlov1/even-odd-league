#!/usr/bin/env python3
"""
Referee HTTP Server for Even/Odd League Games
Manages game sessions, enforces rules, and determines winners
"""
import argparse
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
import uvicorn

from utils.referee_server_class import RefereeServer


# Global referee instance
referee = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print("Starting Referee Server...")
    await referee.register_with_league()
    yield
    print("Shutting down Referee Server...")


# FastAPI app
app = FastAPI(title="Referee Server", lifespan=lifespan)


@app.post("/mcp")
async def mcp_endpoint(message: Dict[str, Any]):
    """Main JSON-RPC 2.0 endpoint"""
    try:
        response = await referee.handle_message(message)
        return response
    except Exception as e:
        print(f"Error handling message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "referee_id": referee.referee_id,
        "active_games": len(referee.games)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Referee Server for Even/Odd League")
    parser.add_argument("--name", default="Referee Alpha", help="Referee display name")
    parser.add_argument("--port", type=int, default=8001, help="Port to run server on")
    args = parser.parse_args()

    referee = RefereeServer(name=args.name, port=args.port)

    uvicorn.run(app, host="localhost", port=args.port)
