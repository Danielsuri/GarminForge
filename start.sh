#!/usr/bin/env bash
# GarminForge – start / restart the web server
# Usage: ./start.sh [--port 8080] [--reload]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$SCRIPT_DIR/.venv/bin"
VENV="$VENV_BIN/python"
PIDFILE="$SCRIPT_DIR/.garminforge.pid"
PORT="${PORT:-8080}"

# Parse args
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port) PORT="$2"; shift 2 ;;
        *)      EXTRA_ARGS+=("$1"); shift ;;
    esac
done

# Kill existing instance if running
if [[ -f "$PIDFILE" ]]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Stopping existing server (PID $OLD_PID)..."
        kill "$OLD_PID"
        sleep 1
    fi
    rm -f "$PIDFILE"
fi

# Also free the port in case pidfile is stale
if lsof -ti:"$PORT" &>/dev/null; then
    echo "Freeing port $PORT..."
    lsof -ti:"$PORT" | xargs kill -9
    sleep 1
fi

cd "$SCRIPT_DIR"

# Run DB migrations before starting
echo "Running database migrations..."
"$VENV_BIN/alembic" upgrade head

echo "Starting GarminForge on port $PORT..."
nohup "$VENV" run.py --port "$PORT" "${EXTRA_ARGS[@]}" \
    >> "$SCRIPT_DIR/garminforge.log" 2>&1 &

echo $! > "$PIDFILE"
echo "Server started (PID $(cat "$PIDFILE")). Logs: $SCRIPT_DIR/garminforge.log"
