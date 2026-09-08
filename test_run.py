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
                "profile": "from-file", "workspace": ".", "board_slug": "xhs-run"
            }))
            cfg = run.load_config(root, config_path, profile="from-cli", workspace=str(root / "project"))
            self.assertEqual(cfg.profile, "from-cli")
            self.assertEqual(cfg.workspace, (root / "project").resolve())
            self.assertEqual(cfg.board_slug, "xhs-run")

    def test_relative_workspace_is_resolved_from_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            config_path = config_dir / "runner.json"
            config_path.write_text(json.dumps({
                "profile": "worker", "workspace": "../project", "board_slug": "xhs-run"
            }))
            cfg = run.load_config(root, config_path)
            self.assertEqual(cfg.workspace, (root / "project").resolve())


class CleanupTests(unittest.TestCase):
    def test_cleanup_removes_all_allowlisted_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in run.RUNTIME_DIRS:
                (root / name).mkdir(parents=True)
            old = root / "runtime-params" / "old.sh"
            old.write_text("delete")
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


class BoardTests(unittest.TestCase):
    def test_terminal_when_all_tasks_done(self) -> None:
        self.assertTrue(run.board_is_terminal([{"status": "done"}, {"status": "done"}]))

    def test_not_terminal_while_task_waits(self) -> None:
        self.assertFalse(run.board_is_terminal([{"status": "done"}, {"status": "todo"}]))

    def test_prepare_board_deletes_old_managed_boards_and_creates_fixed_slug(self) -> None:
        calls: list[tuple[str, ...]] = []
        with patch.object(run, "list_boards", return_value={"default", "xhs-debug", "xhs-e2e-full-old", "xhs-run"}), \
             patch.object(run, "command", side_effect=lambda args, **_: calls.append(tuple(args)) or type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()):
            run.prepare_board("xhs-run", Path("/tmp/project"))
        removed = [c for c in calls if c[:4] == ("hermes", "kanban", "boards", "rm")]
        self.assertIn(("hermes", "kanban", "boards", "rm", "xhs-e2e-full-old", "--delete"), removed)
        self.assertIn(("hermes", "kanban", "boards", "rm", "xhs-run", "--delete"), removed)
        self.assertIn(("hermes", "kanban", "boards", "rm", "xhs-debug", "--delete"), removed)
        self.assertIn(("hermes", "kanban", "boards", "create", "xhs-run", "--name", "小红书定时工作流", "--default-workdir", "/tmp/project", "--switch"), calls)


class ResultTests(unittest.TestCase):
    def test_verified_without_send_success_is_not_reported_as_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "REJECT"},
            {"key": "publish-send", "result_status": None},
            {"key": "publish-verify", "result_status": "VERIFIED"},
        ]
        self.assertFalse(run.is_published_and_verified(stages))

    def test_send_success_and_verified_is_reported_as_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "APPROVE"},
            {"key": "publish-send", "result_status": "SEND_SUCCESS"},
            {"key": "publish-verify", "result_status": "VERIFIED"},
        ]
        self.assertTrue(run.is_published_and_verified(stages))


class RunnerFinallyTests(unittest.TestCase):
    def config(self) -> run.RunnerConfig:
        return run.RunnerConfig(
            profile="worker", workspace=Path("/tmp/workspace"), board_slug="xhs-run",
            poll_seconds=1, timeout_minutes=1, keep_board=True, max_output_chars=2000,
        )

    def test_cleanup_runs_when_iteration_raises(self) -> None:
        calls: list[str] = []
        with patch.object(run, "prepare_board"), \
             patch.object(run, "start_iteration", side_effect=RuntimeError("boom")), \
             patch.object(run, "cleanup_browser_tabs", side_effect=lambda *_: calls.append("tabs") or {}), \
             patch.object(run, "cleanup_new_runtime_files", side_effect=lambda *_: calls.append("files") or {}), \
             patch.object(run, "snapshot_runtime_files", return_value=set()), \
             patch.object(run, "runner_lock"):
            result = run.execute_campaign(Path("/tmp/project"), self.config())
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(calls, ["tabs", "files"])


if __name__ == "__main__":
    unittest.main()
