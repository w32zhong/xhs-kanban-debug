#!/usr/bin/env python3
"""Run one bounded XHS Kanban workflow and always clean transient resources.

Designed for cron: one compact JSON result on stdout, no persistent watcher log,
and a process lock preventing overlapping runs.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parent
RUNTIME_DIRS = ("runtime-params", "logs", "evidence", "roundtable")
RUNTIME_ROOT_FILES = ("current-run.json", "full-e2e-current.json")
ACTIVE_STATUSES = {"triage", "todo", "scheduled", "ready", "running", "review"}


@dataclass(frozen=True)
class RunnerConfig:
    profile: str
    workspace: Path
    poll_seconds: int = 20
    timeout_minutes: int = 45
    keep_board: bool = False
    max_output_chars: int = 6000


def load_config(
    root: Path,
    config_path: Path,
    *,
    profile: str | None = None,
    workspace: str | None = None,
    poll_seconds: int | None = None,
    timeout_minutes: int | None = None,
    keep_board: bool | None = None,
) -> RunnerConfig:
    data: dict[str, Any] = {}
    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
    config_dir = config_path.resolve().parent
    raw_workspace = workspace or os.environ.get("XHS_WORKSPACE") or data.get("workspace") or str(root)
    workspace_path = Path(raw_workspace).expanduser()
    if not workspace_path.is_absolute():
        workspace_path = config_dir / workspace_path
    resolved_profile = profile or os.environ.get("XHS_AGENT_PROFILE") or data.get("profile")
    if not resolved_profile:
        raise ValueError("agent profile is required: set --profile, XHS_AGENT_PROFILE, or runner-config.json")
    return RunnerConfig(
        profile=str(resolved_profile),
        workspace=workspace_path.resolve(),
        poll_seconds=int(poll_seconds or data.get("poll_seconds", 20)),
        timeout_minutes=int(timeout_minutes or data.get("timeout_minutes", 45)),
        keep_board=bool(data.get("keep_board", False) if keep_board is None else keep_board),
        max_output_chars=int(data.get("max_output_chars", 6000)),
    )


def command(args: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(args, cwd=str(cwd), text=True, capture_output=True)
    if check and proc.returncode:
        detail = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}: {detail[-1200:]}")
    return proc


@contextlib.contextmanager
def runner_lock(root: Path = ROOT) -> Iterator[None]:
    lock_path = root / ".run.lock"
    with lock_path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another XHS workflow run is already active") from exc
        yield


def list_boards() -> set[str]:
    proc = command(["hermes", "kanban", "boards", "list", "--json"])
    return {item["slug"] for item in json.loads(proc.stdout)}


def start_iteration(root: Path, cfg: RunnerConfig) -> dict[str, Any]:
    proc = command([
        sys.executable,
        str(root / "run_iteration.py"),
        "--profile", cfg.profile,
        "--workspace", str(cfg.workspace),
    ], cwd=root)
    return json.loads(proc.stdout)


def list_tasks(board: str) -> list[dict[str, Any]]:
    proc = command(["hermes", "kanban", "--board", board, "list", "--json"])
    return json.loads(proc.stdout)


def board_is_terminal(tasks: list[dict[str, Any]]) -> bool:
    return bool(tasks) and not any(task.get("status") in ACTIVE_STATUSES for task in tasks)


def wait_for_board(board: str, cfg: RunnerConfig) -> list[dict[str, Any]]:
    deadline = time.monotonic() + cfg.timeout_minutes * 60
    while True:
        tasks = list_tasks(board)
        if board_is_terminal(tasks):
            return tasks
        if time.monotonic() >= deadline:
            raise TimeoutError(f"board {board} exceeded {cfg.timeout_minutes} minutes")
        time.sleep(cfg.poll_seconds)


def latest_run(board: str, task_id: str) -> dict[str, Any]:
    proc = command(["hermes", "kanban", "--board", board, "runs", task_id, "--json"])
    runs = json.loads(proc.stdout)
    return runs[-1] if runs else {}


def compact_result(board: str, state: dict[str, Any], tasks: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {task["id"]: task for task in tasks}
    stages: list[dict[str, Any]] = []
    for created in state.get("created", []):
        task = by_id.get(created["id"], {})
        run = latest_run(board, created["id"])
        metadata = run.get("metadata") or {}
        stages.append({
            "key": created.get("key"),
            "task_id": created.get("id"),
            "task_status": task.get("status"),
            "outcome": run.get("outcome"),
            "result_status": (
                metadata.get("status")
                or metadata.get("publish_status")
                or metadata.get("decision")
                or metadata.get("recommendation")
            ),
        })
    verify = next((stage for stage in stages if stage["key"] == "publish-verify"), {})
    publish = next((stage for stage in stages if stage["key"] == "publish-send"), {})
    return {
        "status": "COMPLETED",
        "board": board,
        "target_id": state.get("target_id"),
        "publish_status": publish.get("result_status"),
        "verify_status": verify.get("result_status"),
        "published_and_verified": verify.get("result_status") == "VERIFIED",
        "stages": stages,
    }


def snapshot_runtime_files(root: Path) -> set[Path]:
    files: set[Path] = set()
    for dirname in RUNTIME_DIRS:
        base = root / dirname
        if base.is_dir():
            files.update(path.resolve() for path in base.rglob("*") if path.is_file())
    for name in RUNTIME_ROOT_FILES:
        path = root / name
        if path.is_file():
            files.add(path.resolve())
    return files


def cleanup_new_runtime_files(root: Path, before: set[Path]) -> dict[str, Any]:
    """Remove bounded transient artifacts.

    ``before`` is retained in the API for testability and compatibility, but
    recurring runs intentionally clear stale artifacts too: every allowlisted
    path is generated runtime state and ignored by git.
    """
    after = snapshot_runtime_files(root)
    removed: list[str] = []
    errors: list[str] = []
    for path in sorted(after):
        try:
            path.unlink(missing_ok=True)
            removed.append(str(path))
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    for dirname in RUNTIME_DIRS:
        base = root / dirname
        if base.is_dir():
            for directory in sorted((p for p in base.rglob("*") if p.is_dir()), reverse=True):
                try:
                    directory.rmdir()
                except OSError:
                    pass
    return {"removed_count": len(removed), "errors": errors}


def cleanup_browser_tabs(root: Path = ROOT) -> dict[str, Any]:
    proc = command([sys.executable, str(root / "resource_guard.py"), "--force"], cwd=root, check=False)
    if proc.returncode:
        return {"ok": False, "error": (proc.stderr or proc.stdout).strip()[-1000:]}
    try:
        return {"ok": True, **json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"ok": True, "detail": proc.stdout.strip()[-1000:]}


def remove_board(board: str) -> dict[str, Any]:
    proc = command(["hermes", "kanban", "boards", "rm", board, "--delete"], check=False)
    return {"ok": proc.returncode == 0, "detail": (proc.stderr or proc.stdout).strip()[-1000:]}


def execute_campaign(root: Path, cfg: RunnerConfig) -> dict[str, Any]:
    started = time.time()
    runtime_before = snapshot_runtime_files(root)
    boards_before: set[str] = set()
    board: str | None = None
    result: dict[str, Any] = {"status": "ERROR", "error": "runner did not start"}
    cleanup: dict[str, Any] = {}
    try:
        with runner_lock(root):
            boards_before = list_boards()
            state = start_iteration(root, cfg)
            started_board = state.get("board")
            if not isinstance(started_board, str) or not started_board:
                raise RuntimeError("run_iteration.py did not return a board slug")
            board = started_board
            tasks = wait_for_board(started_board, cfg)
            result = compact_result(started_board, state, tasks)
    except Exception as exc:
        result = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
    finally:
        if board is None and boards_before:
            try:
                new_boards = list_boards() - boards_before
                board = sorted(new_boards)[-1] if len(new_boards) == 1 else None
            except Exception:
                board = None
        if board and (result.get("status") == "ERROR" or not cfg.keep_board):
            cleanup["board"] = remove_board(board)
        else:
            cleanup["board"] = {"ok": True, "kept": bool(board)}
        cleanup["tabs"] = cleanup_browser_tabs(root)
        cleanup["files"] = cleanup_new_runtime_files(root, runtime_before)
    result["cleanup"] = cleanup
    result["elapsed_seconds"] = round(time.time() - started, 1)
    if board and "board" not in result:
        result["board"] = board
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one bounded XHS Kanban workflow with guaranteed cleanup")
    parser.add_argument("--config", default=str(ROOT / "runner-config.json"))
    parser.add_argument("--profile")
    parser.add_argument("--workspace")
    parser.add_argument("--poll-seconds", type=int)
    parser.add_argument("--timeout-minutes", type=int)
    parser.add_argument("--keep-board", action="store_true", default=None)
    parser.add_argument("--inject-error", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg: RunnerConfig | None = None
    try:
        cfg = load_config(
            ROOT,
            Path(args.config),
            profile=args.profile,
            workspace=args.workspace,
            poll_seconds=args.poll_seconds,
            timeout_minutes=args.timeout_minutes,
            keep_board=args.keep_board,
        )
        if args.inject_error:
            raise RuntimeError("injected test error")
        result = execute_campaign(ROOT, cfg)
    except Exception as exc:
        result = {"status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    max_chars = cfg.max_output_chars if cfg is not None else 6000
    print(text if len(text) <= max_chars else text[:max_chars] + "\n...TRUNCATED")
    return 0 if result.get("status") == "COMPLETED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
