#!/bin/bash

# Start League - Opens each service in a separate terminal window
# Works on macOS without requiring accessibility permissions

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Store window IDs for later cleanup
WINDOW_IDS_FILE="$DIR/.league_window_ids"
rm -f "$WINDOW_IDS_FILE"

echo "Starting Even/Odd League in separate terminal windows..."

# Open League Manager and capture window ID
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'League Manager' && python league_manager.py\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 3

# Open Referee Alpha
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'Referee Alpha' && python referee_agent.py --name 'Referee Alpha' --port 8001\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 1

# Open Referee Beta
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'Referee Beta' && python referee_agent.py --name 'Referee Beta' --port 8002\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 1

# Open Alice
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'Player Alice' && python player_agent.py --name 'Alice' --port 8101 --strategy random\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 1

# Open Bob
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'Player Bob' && python player_agent.py --name 'Bob' --port 8102 --strategy alternating\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 1

# Open Charlie
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'Player Charlie' && python player_agent.py --name 'Charlie' --port 8103 --strategy history\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 1

# Open Diana
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && source .venv/bin/activate && echo 'Player Diana' && python player_agent.py --name 'Diana' --port 8104 --strategy random\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"
sleep 5

# Open control window to start league
WINDOW_ID=$(osascript -e "tell app \"Terminal\" to do script \"cd '$DIR' && echo 'League Control' && sleep 3 && echo 'Starting league...' && curl -X POST http://localhost:8000/start_league && echo '' && echo 'League started! Check other windows for activity.' && echo 'Press Ctrl+C to close.'\"" | sed 's/.*window id //;s/.*tab 1 of //')
echo "$WINDOW_ID" >> "$WINDOW_IDS_FILE"

echo "All services started in separate terminal windows!"
