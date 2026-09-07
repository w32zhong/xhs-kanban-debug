#!/usr/bin/env python3
"""Keep shared browser tabs below the debug-stage memory ceiling.

Policy:
- soft cleanup threshold: 8 tabs
- hard ceiling: fewer than 10 tabs
- preserve the Kanban UI and at most one existing Xiaohongshu login-state tab
- optionally preserve sessions listed by the current run
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV = {**os.environ, "AGENT_BROWSER_SOCKET_DIR": "/tmp"}


def browser(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["agent-browser", *args], env=ENV, text=True, capture_output=True)


def list_tabs() -> list[dict]:
    result = browser("tab", "list", "--json")
    if result.returncode:
        raise SystemExit(result.stderr or result.stdout)
    return json.loads(result.stdout)["data"]["tabs"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="clean even below the soft threshold")
    args = parser.parse_args()

    tabs = list_tabs()
    if len(tabs) < 8 and not args.force:
        print(json.dumps({"before": len(tabs), "after": len(tabs), "closed": []}, ensure_ascii=False))
        return

    preserve: set[str] = set()
    # Preserve Kanban UI.
    for tab in tabs:
        if "sandbox_env:8002" in tab.get("url", ""):
            preserve.add(tab["targetId"])
    # Preserve one active/first Xiaohongshu tab to retain login continuity.
    xhs = [tab for tab in tabs if "xiaohongshu.com" in tab.get("url", "")]
    chosen = next((tab for tab in xhs if tab.get("active")), xhs[0] if xhs else None)
    if chosen:
        preserve.add(chosen["targetId"])

    closed = []
    for tab in tabs:
        if tab["targetId"] in preserve:
            continue
        result = browser("tab", "close", tab["targetId"])
        closed.append({"targetId": tab["targetId"], "title": tab.get("title", ""), "ok": result.returncode == 0})

    final = list_tabs()
    if len(final) >= 10:
        raise SystemExit(f"resource guard failed: {len(final)} tabs remain")
    print(json.dumps({"before": len(tabs), "after": len(final), "closed": closed}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
