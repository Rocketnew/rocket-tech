#!/bin/bash
# Watchdog for 24/7 traffic bot — restart if dead
PID_FILE="/tmp/traffic_bot_247.pid"
BOT_DIR="/home/ubuntu/rocket-tech"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        # Check if child bot process exists
        CHILD=$(ps --ppid "$PID" -o pid= 2>/dev/null | head -1)
        if [ -n "$CHILD" ]; then
            exit 0  # All good
        fi
    fi
fi

# Daemon is dead — restart it
echo "[$(date)] ⚠️ Daemon not running, restarting..." >> "$BOT_DIR/traffic_247_watchdog.log"
killall -9 chrome chromedriver 2>/dev/null || true
rm -rf /tmp/cr_* /tmp/.com.google.Chrome* 2>/dev/null || true
cd "$BOT_DIR" || exit 1
nohup ./run_247.sh > traffic_247_daemon.log 2>&1 &
echo "[$(date)] ✅ Restarted 24/7 daemon (PID: $!)" >> "$BOT_DIR/traffic_247_watchdog.log"
