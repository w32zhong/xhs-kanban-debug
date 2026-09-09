#!/usr/bin/env bash
# Continuously run complete XHS Kanban campaigns, one at a time.
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PROFILE="${XHS_AGENT_PROFILE:?set XHS_AGENT_PROFILE to a dedicated non-default profile}"
ACCOUNT_NAME="${XHS_ACCOUNT_NAME:?set XHS_ACCOUNT_NAME to the current Xiaohongshu nickname}"
SLEEP_SECONDS="${XHS_LOOP_SLEEP_SECONDS:-5}"

while true; do
    printf '[%s] Starting new run...\n' "$(date '+%Y-%m-%d %H:%M:%S')"
    if python3 run.py --profile "$PROFILE" --account-name "$ACCOUNT_NAME"; then
        result="completed"
    else
        result="failed"
    fi
    printf '[%s] Run %s; next run starts in %s seconds.\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$result" "$SLEEP_SECONDS"
    sleep "$SLEEP_SECONDS"
done
