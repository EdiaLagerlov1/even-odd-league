# Player Agent - Even/Odd League

HTTP server implementation for player agents that participate in the Even/Odd League game using strategic choices.

## Features

- **HTTP JSON-RPC 2.0 Server**: Handles incoming messages on `/mcp` endpoint
- **League Registration**: Automatically registers with League Manager on startup
- **Game Participation**: Joins games, makes strategic choices, tracks results
- **Multiple Strategies**: Random, Alternating, and History-based strategies
- **Statistics Tracking**: Tracks wins, losses, draws, and game history
- **JSON Logging**: All messages logged to JSON Lines file
- **Health Endpoints**: Health check and statistics endpoints

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Start a player agent with default settings:

```bash
python player_agent.py --name "Player 1"
```

This starts a player on port 8101 with random strategy.

### Custom Configuration

```bash
python player_agent.py --name "Alice" --port 8101 --strategy random
python player_agent.py --name "Bob" --port 8102 --strategy alternating
python player_agent.py --name "Charlie" --port 8103 --strategy history
python player_agent.py --name "Diana" --port 8104 --strategy random
```

### Command-Line Arguments

- `--name`: **Required**. Player display name (e.g., "Player 1", "Alice")
- `--port`: HTTP server port (default: 8101). Use 8101-8104 for multiple players.
- `--strategy`: Playing strategy. Options:
  - `random`: Randomly choose even or odd (default)
  - `alternating`: Alternate between even and odd choices
  - `history`: Choose based on past winning choices

## Strategies

### Random Strategy
Randomly selects "even" or "odd" for each game with equal probability.

```python
def choose_parity_random():
    return random.choice(["even", "odd"])
```

### Alternating Strategy
Alternates between "even" and "odd" on each turn. If last choice was "even", choose "odd", and vice versa.

```python
def choose_parity_alternating():
    return "odd" if last_choice == "even" else "even"
```

### History-Based Strategy
Analyzes the last 10 games and chooses the parity that won more often. Falls back to alternating strategy if no clear pattern exists.

```python
def choose_parity_history():
    # Count even vs odd wins in recent games
    # Choose the more successful parity
    return "even" if even_wins > odd_wins else "odd"
```

## API Endpoints

### POST /mcp
Main JSON-RPC 2.0 endpoint for receiving messages from League Manager and Referee agents.

**Handles**:
- `ROUND_ANNOUNCEMENT`: Round start notifications
- `GAME_INVITATION`: Invitations to join games
- `CHOOSE_PARITY_CALL`: Requests to make a choice
- `GAME_OVER`: Game result notifications
- `LEAGUE_STANDINGS_UPDATE`: Current standings
- `LEAGUE_COMPLETED`: Final league results

### GET /health
Health check endpoint.

**Response**:
```json
{
  "status": "healthy",
  "player_id": "P01",
  "registered": true
}
```

### GET /stats
Player statistics endpoint.

**Response**:
```json
{
  "player_id": "P01",
  "display_name": "Alice",
  "strategy": "random",
  "stats": {
    "wins": 3,
    "losses": 1,
    "draws": 1,
    "total_games": 5
  },
  "games_played": 5,
  "current_match": null
}
```

## Message Flow

### 1. Registration (Startup)
```
Player → League Manager: LEAGUE_REGISTER_REQUEST
League Manager → Player: LEAGUE_REGISTER_RESPONSE (with player_id, auth_token)
```

### 2. Game Participation
```
League Manager → Player: ROUND_ANNOUNCEMENT
Referee → Player: GAME_INVITATION
Player → Referee: GAME_JOIN_ACK
Referee → Player: CHOOSE_PARITY_CALL
Player → Referee: CHOOSE_PARITY_RESPONSE (with choice)
Referee → Player: GAME_OVER (with results)
```

### 3. League Updates
```
League Manager → Player: LEAGUE_STANDINGS_UPDATE
League Manager → Player: LEAGUE_COMPLETED
```

## Message Structure

All messages follow the league.v2 protocol:

```json
{
  "protocol": "league.v2",
  "message_type": "CHOOSE_PARITY_RESPONSE",
  "sender": "player:P01",
  "timestamp": "2025-12-20T10:30:00Z",
  "conversation_id": "uuid-1234",
  "auth_token": "token-xyz",
  "match_id": "M001",
  "choice": "even"
}
```

## Logging

Each player agent creates a JSON Lines log file: `player_{port}.jsonl`

**Log Format**:
```json
{
  "timestamp": "2025-12-20T10:30:00Z",
  "direction": "incoming",
  "message": { ... }
}
```

- `direction`: "incoming" or "outgoing"
- `message`: Full message object

## Game History

Each completed game is stored in memory:

```python
{
  "match_id": "M001",
  "opponent": "P02",
  "my_choice": "even",
  "opponent_choice": "odd",
  "number": 5,
  "result": "win",
  "timestamp": "2025-12-20T10:30:00Z"
}
```

## Statistics Tracking

Player agents track:
- **wins**: Number of games won
- **losses**: Number of games lost
- **draws**: Number of draws
- **total_games**: Total games played
- **game_history**: List of all completed games

## Running Multiple Players

Start multiple players for a complete league:

```bash
# Terminal 1
python player_agent.py --name "Alice" --port 8101 --strategy random

# Terminal 2
python player_agent.py --name "Bob" --port 8102 --strategy alternating

# Terminal 3
python player_agent.py --name "Charlie" --port 8103 --strategy history

# Terminal 4
python player_agent.py --name "Diana" --port 8104 --strategy random
```

## Testing

### Check Health
```bash
curl http://localhost:8101/health
```

### Check Statistics
```bash
curl http://localhost:8101/stats
```

### Send Test Message
```bash
curl -X POST http://localhost:8101/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "league.v2",
    "message_type": "ROUND_ANNOUNCEMENT",
    "sender": "league_manager",
    "timestamp": "2025-12-20T10:00:00Z",
    "conversation_id": "test-123",
    "round_number": 1,
    "schedule": []
  }'
```

## Architecture

```
┌─────────────────┐
│ League Manager  │
│  (port 8000)    │
└────────┬────────┘
         │
         │ LEAGUE_REGISTER_REQUEST/RESPONSE
         │ ROUND_ANNOUNCEMENT
         │ LEAGUE_STANDINGS_UPDATE
         │ LEAGUE_COMPLETED
         │
    ┌────┴─────┬──────────┬──────────┐
    │          │          │          │
┌───▼───┐  ┌──▼────┐  ┌──▼────┐  ┌──▼────┐
│Player │  │Player │  │Player │  │Player │
│ 8101  │  │ 8102  │  │ 8103  │  │ 8104  │
└───┬───┘  └───┬───┘  └───┬───┘  └───┬───┘
    │          │          │          │
    └──────────┴──────────┴──────────┘
         │
         │ GAME_INVITATION
         │ GAME_JOIN_ACK
         │ CHOOSE_PARITY_CALL
         │ CHOOSE_PARITY_RESPONSE
         │ GAME_OVER
         │
    ┌────▼────┐
    │ Referee │
    │ Agents  │
    └─────────┘
```

## Timeouts

- **CHOOSE_PARITY_CALL**: Must respond within 30 seconds (default)
- **HTTP Requests**: 10-second timeout for outgoing requests

## Error Handling

- Invalid messages: Returns error response
- Unknown message types: Logged and ignored
- Network errors: Logged, automatic retry not implemented
- Timeout: If no response within timeout, referee may forfeit the player

## Dependencies

- **FastAPI**: Web framework for HTTP server
- **Uvicorn**: ASGI server
- **Requests**: HTTP client for sending messages
- **Pydantic**: Data validation

## Troubleshooting

### Player not registering
- Ensure League Manager is running on port 8000
- Check network connectivity to localhost:8000
- Review logs in `player_{port}.jsonl`

### No games being played
- Ensure at least 2 players are registered
- Verify League Manager has started rounds
- Check player is receiving GAME_INVITATION messages

### Strategy not working
- Verify strategy name is correct: "random", "alternating", or "history"
- Check logs to see actual choices being made
- History strategy requires at least 1 game of history

## License

MIT
