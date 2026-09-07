#!/usr/bin/env python3
"""Persistently capture the current debug board's statuses and worker logs.

This collector is intentionally non-reasoning: it creates an audit stream for the
coordinator to inspect. It stops when replaced/killed before a full-board rerun.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
state = json.loads((ROOT / "current-run.json").read_text(encoding="utf-8"))
board = state["board"]
tasks = state["created"]
out = ROOT / "logs" / f"{board}-watch.log"

with out.open("a", encoding="utf-8") as stream:
    stream.write(f"WATCH START board={board}\n")
    while True:
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        listing = subprocess.run(
            ["hermes", "kanban", "--board", board, "list", "--json"],
            capture_output=True, text=True,
        )
        stream.write(f"\n[{stamp}] LIST rc={listing.returncode}\n{listing.stdout}{listing.stderr}\n")
        if listing.returncode != 0 and "does not exist" in (listing.stdout + listing.stderr):
            stream.write("BOARD REMOVED; WATCH STOP\n")
            stream.flush()
            break
        for task in tasks:
            log = subprocess.run(
                ["hermes", "kanban", "--board", board, "log", task["id"]],
                capture_output=True, text=True,
            )
            stream.write(f"[{stamp}] LOG {task['id']} rc={log.returncode}\n{log.stdout[-16000:]}{log.stderr[-2000:]}\n")
        stream.flush()
        time.sleep(20)
