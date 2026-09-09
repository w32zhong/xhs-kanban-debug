#!/bin/bash
# Continuous XHS Kanban workflow runner
cd /worktrees/folder-1/xhs-kanban-workflow
PROFILE="${XHS_AGENT_PROFILE:?set XHS_AGENT_PROFILE to a dedicated non-default profile}"
ACCOUNT_NAME="${XHS_ACCOUNT_NAME:?set XHS_ACCOUNT_NAME to the current Xiaohongshu nickname}"

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting new run..."
    python3 run.py --profile "$PROFILE" --account-name "$ACCOUNT_NAME"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Run finished, starting next..."
    sleep 5
done
