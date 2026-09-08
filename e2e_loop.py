#!/usr/bin/env python3
"""Orchestrate full E2E runs with automatic retry until publish-verify succeeds.

Usage:
    python3 e2e_loop.py              # retry up to 5 times
    python3 e2e_loop.py --max 3      # retry up to 3 times
    python3 e2e_loop.py --poll 30    # poll every 30s (default 20s)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_ATTEMPTS = 5
POLL_INTERVAL = 20  # seconds


def run_iteration() -> dict:
    """Run run_iteration.py and return the state_out dict."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_iteration.py")],
        text=True, capture_output=True, cwd=str(ROOT),
    )
    if proc.returncode:
        print(f"[e2e-loop] run_iteration failed:\n{proc.stdout}\n{proc.stderr}", flush=True)
        return {}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print(f"[e2e-loop] bad JSON from run_iteration:\n{proc.stdout}", flush=True)
        return {}


def poll_board(board: str, poll: int) -> dict:
    """Poll board until all tasks are done. Return final task statuses."""
    print(f"[e2e-loop] monitoring board: {board}", flush=True)
    tasks = {}
    while True:
        proc = subprocess.run(
            ["hermes", "kanban", "--board", board, "list", "--json"],
            text=True, capture_output=True,
        )
        if proc.returncode:
            print(f"[e2e-loop] kanban list failed: {proc.stderr}", flush=True)
            time.sleep(poll)
            continue

        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            time.sleep(poll)
            continue

        tasks = {t["id"]: t for t in data}
        statuses = [t["status"] for t in data]
        running = statuses.count("running")
        done = statuses.count("done")
        failed = statuses.count("failed")
        total = len(statuses)

        # Count by title for readable output
        summary = []
        for t in data:
            icon = {"done": "✅", "running": "⏳", "failed": "❌", "todo": "⏸"}.get(t["status"], "❓")
            summary.append(f"  {icon} {t['title']}")

        print(f"[e2e-loop] [{time.strftime('%H:%M:%S')}] "
              f"done={done} running={running} failed={failed} total={total}", flush=True)
        for s in summary:
            print(s, flush=True)

        # All finished when no running or todo tasks remain
        if running == 0 and "todo" not in statuses:
            break

        time.sleep(poll)

    return tasks


def check_result(tasks: dict) -> tuple[str, str]:
    """Return (publish_send_status, publish_verify_status) from task results."""
    send_status = "UNKNOWN"
    verify_status = "UNKNOWN"

    for t in tasks.values():
        title = t.get("title", "")
        # Try to extract result status from task output
        if "发布" in title and "复核" not in title:
            send_status = _extract_status(t)
        elif "复核" in title:
            verify_status = _extract_status(t)

    return send_status, verify_status


def _extract_status(task: dict) -> str:
    """Try to extract the completion status from a kanban task."""
    # The task result is in the kanban log; check the completion message
    tid = task.get("id", "")
    proc = subprocess.run(
        ["hermes", "kanban", "log", tid],
        text=True, capture_output=True, cwd=str(ROOT),
    )
    output = proc.stdout
    # Look for common status patterns
    for pattern in ["SEND_SUCCESS", "VERIFIED", "REPLY_NOT_FOUND",
                    "DUPLICATE_REPLY", "WRONG_THREAD", "THREAD_UNCONFIRMED",
                    "SETUP_ERROR", "BROWSER_ERROR", "LOGIN_REQUIRED",
                    "NEEDS_VERIFIER", "WRONG_REPLY_TARGET", "TEXT_MISMATCH",
                    "REJECT", "NO_CANDIDATE", "NO_COMMENTS",
                    "ACCOUNT_UNKNOWN", "TARGET_NOT_FOUND"]:
        if pattern in output:
            return pattern
    return "UNKNOWN"


def main() -> None:
    parser = argparse.ArgumentParser(description="E2E loop until publish-verify succeeds")
    parser.add_argument("--max", type=int, default=MAX_ATTEMPTS, help="Max attempts")
    parser.add_argument("--poll", type=int, default=POLL_INTERVAL, help="Poll interval in seconds")
    cli = parser.parse_args()

    for attempt in range(1, cli.max + 1):
        print(f"\n{'='*60}", flush=True)
        print(f"[e2e-loop] ATTEMPT {attempt}/{cli.max}", flush=True)
        print(f"{'='*60}\n", flush=True)

        state = run_iteration()
        if not state:
            print(f"[e2e-loop] attempt {attempt} failed to start, retrying...", flush=True)
            time.sleep(5)
            continue

        board = state.get("board", "")
        if not board:
            print(f"[e2e-loop] no board name returned, retrying...", flush=True)
            time.sleep(5)
            continue

        tasks = poll_board(board, cli.poll)
        send_status, verify_status = check_result(tasks)

        print(f"\n[e2e-loop] RESULT: publish={send_status} verify={verify_status}", flush=True)

        if verify_status == "VERIFIED":
            print(f"[e2e-loop] ✅ SUCCESS on attempt {attempt}!", flush=True)
            print(json.dumps({
                "status": "SUCCESS",
                "attempt": attempt,
                "board": board,
                "publish_status": send_status,
                "verify_status": verify_status,
            }, ensure_ascii=False, indent=2))
            sys.exit(0)

        print(f"[e2e-loop] ❌ Not verified (publish={send_status}, verify={verify_status}), "
              f"retrying with new board...", flush=True)
        time.sleep(3)

    print(f"\n[e2e-loop] ❌ FAILED after {cli.max} attempts", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
