#!/usr/bin/env python3
"""Create and dispatch one XHS workflow iteration.

Dynamic discovery is the default. Static target rotation is fixture-only.
"""
from __future__ import annotations

import json
import argparse
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "pipeline.json").read_text(encoding="utf-8"))
POOL = json.loads((ROOT / "publish-target-pool.json").read_text(encoding="utf-8"))
STATE_FILE = ROOT / "target-rotation-state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"used_indices": [], "run_count": 0}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def pick_next_target(state: dict) -> dict:
    targets = POOL["targets"]
    used = set(state.get("used_indices", []))
    # Find next unused target
    for i, t in enumerate(targets):
        if i not in used:
            return t
    # All used — reset and start over
    state["used_indices"] = []
    save_state(state)
    return targets[0]


def run(*args: str, json_output: bool = False) -> str | dict | list:
    cmd = ["hermes", "kanban", *args]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode:
        raise SystemExit(f"command failed: {' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    if json_output:
        return json.loads(proc.stdout)
    return proc.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-id", help="Override publish rehearsal literals from publish-target-pool.json")
    parser.add_argument("--finalize-input", help="Run deterministic finalize_run.py with this JSON input instead of creating a Kanban board")
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to deterministic finalizer")
    parser.add_argument("--profile", help="Override pipeline.json default_assignee")
    parser.add_argument("--workspace", help="Override pipeline.json workspace")
    parser.add_argument("--board-slug", help="Use a board already prepared by run.py")
    cli = parser.parse_args()

    config = json.loads(json.dumps(CONFIG))
    if cli.profile:
        config["default_assignee"] = cli.profile
    if cli.workspace:
        config["workspace"] = cli.workspace
    # Resolve workspace path relative to project root
    ws = config.get("workspace", ".")
    if not os.path.isabs(ws):
        ws = str((ROOT / ws).resolve())
    config["workspace"] = ws
    finalizer = config.get("finalizer")
    if finalizer and finalizer.get("agent_required") is False:
        if not cli.finalize_input:
            raise SystemExit("pipeline.json uses a deterministic finalizer; pass --finalize-input <result.json>")
        command = [sys.executable, str(ROOT / finalizer.get("script", "finalize_run.py")), "--input", cli.finalize_input]
        if cli.dry_run:
            command.append("--dry-run")
        raise SystemExit(subprocess.run(command).returncode)
    selected_target = None
    if cli.target_id:
        pool = json.loads((ROOT / "publish-target-pool.json").read_text(encoding="utf-8"))
        selected_target = next((item for item in pool["targets"] if item["id"] == cli.target_id), None)
        if selected_target is None:
            raise SystemExit(f"unknown target id: {cli.target_id}")
        if len(config["tasks"]) != 1:
            raise SystemExit("--target-id requires exactly one task in pipeline.json")
        task = config["tasks"][0]
        for key in ("keyword", "target_title", "target_comment_author", "target_comment_excerpt"):
            task[key] = selected_target[key]

    guard = subprocess.run(
        [sys.executable, str(ROOT / "resource_guard.py")],
        text=True, capture_output=True,
    )
    if guard.returncode:
        raise SystemExit("browser resource guard failed; refusing to start another iteration")
    if guard.stdout:
        print(guard.stdout, file=sys.stderr)

    # Dynamic mode lets the scout choose the candidate. Fixture rotation is opt-in.
    state = load_state()
    dynamic_mode = config.get("target_source", "dynamic_search") == "dynamic_search"
    target = None if dynamic_mode and selected_target is None else (
        selected_target if selected_target is not None else pick_next_target(state)
    )
    target_idx = POOL["targets"].index(target) if target else None

    suffix = time.strftime("%Y%m%d-%H%M%S")
    board = cli.board_slug or f"{config['board_prefix']}-{suffix}"
    if not cli.board_slug:
        run("boards", "create", board, "--name", f"小红书流程调试 · {suffix}")
    run("boards", "set-default-workdir", board, config["workspace"])
    run("boards", "switch", board)

    params_dir = ROOT / "runtime-params"
    params_dir.mkdir(exist_ok=True)
    runtime_dir = ROOT / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    for stale in runtime_dir.glob("*.json"):
        stale.unlink(missing_ok=True)
    created: list[dict] = []
    ids_by_key: dict[str, str] = {}

    # Create tasks sequentially so parent IDs are available at creation time.
    for index, task in enumerate(config["tasks"], start=1):
        session_name = f"xhs-{suffix[-6:]}-{index}"
        prompt_path = str(ROOT / task["prompt"])
        param_path = params_dir / f"{session_name}.sh"

        target_data = target or {}
        keyword = target_data.get("keyword") or task.get("keyword", "")
        target_title = target_data.get("target_title") or task.get("target_title", "")
        target_author = target_data.get("target_comment_author") or task.get("target_comment_author", "")
        target_excerpt = target_data.get("target_comment_excerpt") or task.get("target_comment_excerpt", "")
        approved_draft = target_data.get("approved_draft") or task.get("approved_draft", "")

        param_content = f"SESSION_NAME={shlex.quote(session_name)}\n"
        if keyword:
            param_content += f"KEYWORD_LITERAL={shlex.quote(keyword)}\n"
        if target_title:
            param_content += f"TARGET_TITLE_LITERAL={shlex.quote(target_title)}\n"
        if target_author:
            param_content += f"TARGET_COMMENT_AUTHOR_LITERAL={shlex.quote(target_author)}\n"
        if target_excerpt:
            param_content += f"TARGET_COMMENT_EXCERPT_LITERAL={shlex.quote(target_excerpt)}\n"
        if approved_draft:
            param_content += f"APPROVED_DRAFT_LITERAL={shlex.quote(approved_draft)}\n"
        # Stage-specific immutable inputs (for example failure-coordination
        # statuses) belong in pipeline.json rather than the worker prompt.
        for key, value in task.get("param_vars", {}).items():
            if not key or not key.replace("_", "").isalnum() or not key[0].isalpha():
                raise SystemExit(f"invalid param_vars key: {key!r}")
            param_content += f"{key}={shlex.quote(str(value))}\n"
        param_path.write_text(param_content, encoding="utf-8")

        body_lines = [
            "不要执行任何 Kanban/项目环境探索；任务参数已完整给出。",
            f"第一步读取并严格逐步执行：{prompt_path}",
            f"PARAM_FILE: {param_path}",
        ]
        for key, value in task.get("body_vars", {}).items():
            body_lines.append(f"{key}: {value}")
        body_lines.append("禁止 git/pwd/env/目录搜索/hermes kanban CLI/SQLite/额外 skill；严格遵守所引用 prompt 的副作用边界。")

        configured_assignee = task.get("assignee") or config.get("default_assignee", "")
        args = [
            "--board", board, "create", task["name"],
            "--body", "\n".join(body_lines),
            "--workspace", f"dir:{config['workspace']}",
            "--max-runtime", task.get("max_runtime", "12m"),
            "--max-retries", "1",
            "--priority", str(100 - index),
        ]
        if index == 1:
            args.extend(["--assignee", configured_assignee])
        for parent_key in task.get("parents", []):
            if parent_key not in ids_by_key:
                raise SystemExit(f"unknown/uncreated parent key {parent_key!r} for task {task['key']!r}")
            args.extend(["--parent", ids_by_key[parent_key]])
        args.append("--json")

        item = run(*args, json_output=True)
        if not isinstance(item, dict) or "id" not in item:
            raise SystemExit(f"unexpected create response: {item!r}")
        ids_by_key[task["key"]] = item["id"]
        created.append({
            "key": task["key"],
            "id": item["id"],
            "title": task["name"],
            "session_name": session_name,
            "target_id": target_data.get("id", "dynamic"),
            "target_title": target_title,
        })

    dispatched = run(
        "--board", board, "dispatch", "--max", str(config["max_parallel"]), "--json",
        json_output=True,
    )

    # Update rotation state
    if target_idx is not None and target_idx not in state["used_indices"]:
        state["used_indices"].append(target_idx)
    state["run_count"] = state.get("run_count", 0) + 1
    state["last_target_id"] = (target or {}).get("id", "dynamic")
    state["last_target_title"] = (target or {}).get("target_title", "")
    save_state(state)

    state_out = {
        "board": board,
        "profile": config.get("default_assignee", ""),
        "stage": config.get("stage"),
        "created": created,
        "dispatch": dispatched,
        "started_at": int(time.time()),
        "target_rotated_from_pool": target_idx is not None,
        "target_id": (target or {}).get("id", "dynamic"),
        "target_layout": (target or {}).get("layout_goal", "dynamic discovery"),
        "run_number": state["run_count"],
    }
    (ROOT / "current-run.json").write_text(
        json.dumps(state_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(state_out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
