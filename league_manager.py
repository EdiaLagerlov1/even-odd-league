"""
League Manager HTTP Server for Even/Odd Game League System
Handles referee and player registrations, match scheduling, and standings tracking
"""
from fastapi import FastAPI, Request
from utils.league_manager_class import LeagueManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize League Manager
league_manager = LeagueManager()

# FastAPI App
app = FastAPI(title="League Manager", version="1.0.0")


@app.post("/mcp")
async def handle_mcp(request: Request):
    """Handle JSON-RPC 2.0 requests"""
    from utils.league_endpoints import handle_mcp_request
    return await handle_mcp_request(request, league_manager)


@app.post("/start_league")
async def start_league_endpoint(rounds: int = 1):
    """Create schedule and start the league"""
    from utils.league_endpoints import start_league
    return await start_league(rounds, league_manager)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "referees": len(league_manager.referees),
        "players": len(league_manager.players),
        "matches": len(league_manager.matches)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
