#!/bin/bash

# Stop all league processes and close terminal windows

# Get the current directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WINDOW_IDS_FILE="$DIR/.league_window_ids"

echo "Stopping all league services..."

# Kill the processes FIRST
echo "Terminating Python processes..."
pkill -f "python league_manager.py"
pkill -f "python referee_agent.py"
pkill -f "python player_agent.py"

sleep 1

# Force kill if any processes are still running
if ps aux | grep -E "python (league_manager|referee_agent|player_agent)" | grep -v grep > /dev/null; then
    echo "Force killing remaining processes..."
    pkill -9 -f "python league_manager.py"
    pkill -9 -f "python referee_agent.py"
    pkill -9 -f "python player_agent.py"
    sleep 1
fi

# Now close Terminal windows (after processes are dead)
if [ -f "$WINDOW_IDS_FILE" ]; then
    echo "Closing terminal windows..."

    osascript <<EOF
tell application "Terminal"
    set windowIDs to paragraphs of (do shell script "cat '$WINDOW_IDS_FILE'")
    repeat with wid in windowIDs
        try
            close (first window whose id is (wid as integer))
        end try
    end repeat
end tell
EOF

    rm -f "$WINDOW_IDS_FILE"
fi

echo "All league services stopped and terminal windows closed."
