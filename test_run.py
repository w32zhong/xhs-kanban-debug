#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run


class ConfigTests(unittest.TestCase):
    def test_cli_overrides_profile_and_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "runner-config.json"
            config_path.write_text(json.dumps({
                "profile": "from-file",
                "workspace": ".",
                "poll_seconds": 20,
                "timeout_minutes": 40,
            }))

            cfg = run.load_config(
                root,
                config_path,
                profile="from-cli",
                workspace=str(root / "project"),
            )

            self.assertEqual(cfg.profile, "from-cli")
            self.assertEqual(cfg.workspace, (root / "project").resolve())

    def test_relative_workspace_is_resolved_from_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            config_path = config_dir / "runner.json"
            config_path.write_text(json.dumps({"profile": "worker", "workspace": "../project"}))

            cfg = run.load_config(root, config_path)

            self.assertEqual(cfg.workspace, (root / "project").resolve())


class CleanupTests(unittest.TestCase):
    def test_cleanup_removes_all_allowlisted_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in run.RUNTIME_DIRS:
                (root / name).mkdir(parents=True)
            old = root / "runtime-params" / "old.sh"
            old.write_text("keep")
            before = run.snapshot_runtime_files(root)
            new_param = root / "runtime-params" / "new.sh"
            new_log = root / "logs" / "new.log"
            new_param.write_text("delete")
            new_log.write_text("delete")

            result = run.cleanup_new_runtime_files(root, before)

            self.assertFalse(old.exists())
            self.assertFalse(new_param.exists())
            self.assertFalse(new_log.exists())
            self.assertEqual(result["removed_count"], 3)

    def test_cleanup_removes_current_run_created_during_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = run.snapshot_runtime_files(root)
            current = root / "current-run.json"
            current.write_text("{}")

            run.cleanup_new_runtime_files(root, before)

            self.assertFalse(current.exists())


class BoardStateTests(unittest.TestCase):
    def test_terminal_when_all_tasks_done(self) -> None:
        self.assertTrue(run.board_is_terminal([{"status": "done"}, {"status": "done"}]))

    def test_not_terminal_while_task_waits(self) -> None:
        self.assertFalse(run.board_is_terminal([{"status": "done"}, {"status": "todo"}]))


class RunnerFinallyTests(unittest.TestCase):
    def test_cleanup_runs_when_iteration_raises(self) -> None:
        cfg = run.RunnerConfig(
            profile="worker",
            workspace=Path("/tmp/workspace"),
            poll_seconds=1,
            timeout_minutes=1,
            keep_board=False,
            max_output_chars=2000,
        )
        calls: list[str] = []

        state = {"board": "test-board", "created": []}
        with patch.object(run, "start_iteration", return_value=state), \
             patch.object(run, "wait_for_board", side_effect=RuntimeError("boom")), \
             patch.object(run, "list_boards", return_value=set()), \
             patch.object(run, "remove_board", side_effect=lambda *_: calls.append("board") or {}), \
             patch.object(run, "cleanup_browser_tabs", side_effect=lambda *_: calls.append("tabs") or {}), \
             patch.object(run, "cleanup_new_runtime_files", side_effect=lambda *_: calls.append("files") or {}), \
             patch.object(run, "snapshot_runtime_files", return_value=set()), \
             patch.object(run, "runner_lock"):
            result = run.execute_campaign(Path("/tmp/project"), cfg)

        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(calls, ["board", "tabs", "files"])

    def test_cleanup_runs_when_start_creates_board_then_raises(self) -> None:
        cfg = run.RunnerConfig(
            profile="worker",
            workspace=Path("/tmp/workspace"),
            poll_seconds=1,
            timeout_minutes=1,
            keep_board=False,
            max_output_chars=2000,
        )
        calls: list[str] = []
        board_snapshots = iter([{"existing"}, {"existing", "new-board"}])

        with patch.object(run, "start_iteration", side_effect=RuntimeError("partial start")), \
             patch.object(run, "list_boards", side_effect=lambda: next(board_snapshots)), \
             patch.object(run, "remove_board", side_effect=lambda board: calls.append(board) or {}), \
             patch.object(run, "cleanup_browser_tabs", return_value={}), \
             patch.object(run, "cleanup_new_runtime_files", return_value={}), \
             patch.object(run, "snapshot_runtime_files", return_value=set()), \
             patch.object(run, "runner_lock"):
            result = run.execute_campaign(Path("/tmp/project"), cfg)

        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(calls, ["new-board"])


if __name__ == "__main__":
    unittest.main()
