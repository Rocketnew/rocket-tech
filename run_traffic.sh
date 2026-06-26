#!/bin/bash
# Traffic bot runner — stdout goes to cron, stderr+stdout logged
cd /home/ubuntu/rocket-tech || exit 1
export PATH="/home/ubuntu/.hermes/hermes-agent/venv/bin:/usr/local/bin:/usr/bin:/bin"
python3 -u traffic_bot.py --visits 3 2>&1 | tee -a /home/ubuntu/rocket-tech/traffic_bot.log
