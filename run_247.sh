#!/bin/bash
# ═══════════════════════════════════════════════════════════
# 🚀 ROCKET BOT 24/7 — Continuous Traffic Generator Daemon
# ═══════════════════════════════════════════════════════════
# Runs traffic_bot.py in an infinite loop with:
#   - Random visit counts per cycle (3-7)
#   - Random delays between cycles (30-180s)
#   - Auto restart on crash (any exit code)
#   - Memory / Chrome cleanup between runs
#   - Heartbeat logging every 10 cycles
#   - Graceful shutdown on SIGTERM/SIGINT
# ═══════════════════════════════════════════════════════════

set -Eeo pipefail

BOT_DIR="/home/ubuntu/rocket-tech"
BOT_SCRIPT="traffic_bot.py"
LOG_FILE="$BOT_DIR/traffic_247.log"
PID_FILE="/tmp/traffic_bot_247.pid"
HEARTBEAT_INTERVAL=10  # Log heartbeat every N cycles
MAX_CONSECUTIVE_FAILS=5  # Max fails before restarting harder

cd "$BOT_DIR" || exit 1
export PATH="/home/ubuntu/.hermes/hermes-agent/venv/bin:/usr/local/bin:/usr/bin:/bin"
export PYTHONUNBUFFERED=1

# ─── Write our PID ───
echo $$ > "$PID_FILE"

# ─── Cleanup function ───
cleanup() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⛔ Received shutdown signal, stopping 24/7 bot..." | tee -a "$LOG_FILE"
    # Kill any running chrome processes
    killall -q chrome 2>/dev/null || true
    killall -q chromedriver 2>/dev/null || true
    rm -f "$PID_FILE"
    exit 0
}
trap cleanup SIGTERM SIGINT

# ─── Banner ───
echo ""
echo "╔═══════════════════════════════════════════════════╗"
echo "║  🚀 ROCKET BOT 24/7 DAEMON                       ║"
echo "║  Started: $(date '+%Y-%m-%d %H:%M:%S')            ║"
echo "║  PID: $$                                          ║"
echo "╚═══════════════════════════════════════════════════╝"
echo "" | tee -a "$LOG_FILE"

CYCLE=0
FAILS=0

while true; do
    CYCLE=$((CYCLE + 1))
    
    # ─── Heartbeat ───
    if [ $((CYCLE % HEARTBEAT_INTERVAL)) -eq 1 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 💓 Heartbeat — Cycle #$CYCLE | Bot running 24/7 ✅" | tee -a "$LOG_FILE"
    fi

    # ─── Run stealth rotator (fresh anti-detection each cycle) ───
    python3 "$BOT_DIR/stealth_rotator.py" 2>&1 | tail -1 >> "$LOG_FILE"

    # ─── Random visit count (3-7) ───
    VISITS=$(( (RANDOM % 5) + 3 ))
    
    # ─── Randomly decide to use proxy (30% chance) ───
    PROXY_FLAG=""
    if [ $((RANDOM % 10)) -lt 3 ]; then
        PROXY_FLAG="--proxy"
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔄 Cycle #$CYCLE | Starting $VISITS visits $PROXY_FLAG" | tee -a "$LOG_FILE"
    
    # ─── Run traffic bot ───
    set +e  # Allow errors
    python3 -u "$BOT_SCRIPT" --visits "$VISITS" $PROXY_FLAG 2>&1 | tee -a "$LOG_FILE"
    EXIT_CODE=$?
    set -e
    
    if [ $EXIT_CODE -ne 0 ]; then
        FAILS=$((FAILS + 1))
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Bot exited with code $EXIT_CODE (fail #$FAILS)" | tee -a "$LOG_FILE"
        
        if [ $FAILS -ge $MAX_CONSECUTIVE_FAILS ]; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔴 $FAILS consecutive failures! Hard resetting..." | tee -a "$LOG_FILE"
            # Kill all Chrome processes aggressively
            killall -9 chrome 2>/dev/null || true
            killall -9 chromedriver 2>/dev/null || true
            sleep 5
            FAILS=0
        fi
    else
        FAILS=0  # Reset fail counter on successful run
    fi
    
    # ─── Cleanup Chrome junk ───
    killall -q chrome 2>/dev/null || true
    killall -q chromedriver 2>/dev/null || true
    rm -rf /tmp/cr_* /tmp/.com.google.Chrome* 2>/dev/null || true
    
    # ─── Random delay between cycles (30-180 seconds) ───
    DELAY=$(( (RANDOM % 151) + 30 ))
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 😴 Sleeping ${DELAY}s until next cycle..." | tee -a "$LOG_FILE"
    sleep "$DELAY"
done
