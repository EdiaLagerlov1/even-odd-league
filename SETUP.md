# Even/Odd League Setup Guide

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer

## Installation

### 1. Install uv (if not already installed)

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Create Virtual Environment

```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Install all required packages
uv pip install -r requirements.txt
```

## Running the League

### Start all services

```bash
# macOS/Linux
./start_league.sh

# Windows
./start_league_windows.sh
```

### Start a league tournament

```bash
# Start a league with 3 rounds
curl -X POST "http://localhost:8000/start_league?rounds=3"
```

### Stop all services

```bash
./stop_league.sh
```

## Project Structure

- `league_manager.py` - Main league coordinator
- `referee_agent.py` - Game referee service
- `player_agent.py` - Player agent service
- `game/` - Game logic and player interaction
- `utils/` - Utility functions and message handlers
- `models/` - Data models for league, referee, and players
- `jsonl/` - Message logs (automatically created)

## Development

### Running individual components

```bash
# Activate virtual environment first
source .venv/bin/activate

# Start league manager
python league_manager.py

# Start referee (in another terminal)
python referee_agent.py --name "Referee Alpha" --port 8001

# Start player (in another terminal)
python player_agent.py --name Alice --port 8101 --strategy random
```

## Environment Information

- Python Version: 3.13.5
- Package Manager: uv
- Virtual Environment: `.venv/`
