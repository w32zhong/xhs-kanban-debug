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
    rc=0
    python3 run.py --profile "$PROFILE" --account-name "$ACCOUNT_NAME" || rc=$?
    if [ "$rc" -eq 0 ]; then
        result="completed"
    else
        result="failed"
    fi
    if [ "$rc" -eq 3 ]; then
        printf '[%s] Xiaohongshu login required; the loop is stopping. Scan the QR code in the shared browser, then restart this service.\n' \
            "$(date '+%Y-%m-%d %H:%M:%S')"
        exit 0
    fi
    printf '[%s] Run %s; next run starts in %s seconds.\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" "$result" "$SLEEP_SECONDS"
    sleep "$SLEEP_SECONDS"
done
