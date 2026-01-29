#!/bin/bash
# Internship discovery workflow trigger for cron

LOG="/var/log/ai-agent/cron.log"

echo "[$(date)] Starting workflow" >> $LOG

# Check if API is up
if ! curl -sf http://localhost:8000/ >/dev/null 2>&1; then
    echo "[$(date)] ERROR: API not running" >> $LOG
    exit 1
fi

# Trigger workflow
curl -s -X POST http://localhost:8000/run-workflow >> $LOG 2>&1

echo "[$(date)] Done" >> $LOG
