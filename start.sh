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

# Run DB migrations before starting.
# If a migration fails with "duplicate column" it means those columns were
# already applied outside of Alembic (e.g. by a manual ALTER TABLE or a
# previous run without tracking).  In that case we stamp Alembic to that
# revision — telling it "yes, this one is done" — and retry.  We loop so
# that multiple consecutive untracked migrations are all resolved in one go.
run_migrations() {
    local attempt=0
    local max_attempts=20   # safety valve against infinite loops

    while [[ $attempt -lt $max_attempts ]]; do
        attempt=$((attempt + 1))
        local output exit_code
        output=$("$VENV_BIN/alembic" upgrade head 2>&1)
        exit_code=$?

        if [[ $exit_code -eq 0 ]]; then
            echo "Migrations OK."
            return 0
        fi

        if echo "$output" | grep -q "duplicate column name"; then
            # Pull the 4-digit revision from the offending filename in the traceback
            # e.g. ".../0002_add_preferred_lang.py, line 21, in upgrade"
            local rev
            rev=$(echo "$output" | grep -oP '(?<=/)\d{4}(?=_[^/]+\.py.*in upgrade)' | head -1)
            if [[ -n "$rev" ]]; then
                echo "Migration $rev already applied without tracking — stamping and retrying..."
                "$VENV_BIN/alembic" stamp "$rev"
            else
                echo "ERROR: duplicate column but could not parse revision. Full output:" >&2
                echo "$output" >&2
                return 1
            fi
        else
            echo "ERROR: migration failed:" >&2
            echo "$output" >&2
            return 1
        fi
    done

    echo "ERROR: migration loop did not converge after $max_attempts attempts." >&2
    return 1
}

run_migrations

echo "Starting GarminForge on port $PORT..."
nohup "$VENV" run.py --port "$PORT" "${EXTRA_ARGS[@]}" \
    >> "$SCRIPT_DIR/garminforge.log" 2>&1 &

echo $! > "$PIDFILE"
echo "Server started (PID $(cat "$PIDFILE")). Logs: $SCRIPT_DIR/garminforge.log"
