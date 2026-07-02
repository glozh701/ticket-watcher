#!/usr/bin/env bash
# Run the ticket watcher with environment from .env file
# Usage: ./run.sh
#   or via cron (see below)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load environment variables from .env if present
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "Warning: .env not found. Copy .env.example to .env and configure it."
    exit 1
fi

# Run the watcher
python3 watch_ticket.py

# --- CRON SETUP ---
# To run every 15 minutes, add this to your crontab (run: crontab -e):
#
#   */15 * * * * /local/home/glozh/ticket-watcher/run.sh >> /local/home/glozh/ticket-watcher/cron.log 2>&1
#
# Adjust the path and interval as needed.
# Every 5 minutes:  */5 * * * *
# Every 30 minutes: */30 * * * *
# Every hour:       0 * * * *
