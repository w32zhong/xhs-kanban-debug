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
            config_path.write_text(json.dumps({"profile": "from-file", "workspace": ".", "board_slug": "xhs-run"}))
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
            config_path.write_text(json.dumps({"profile": "worker", "workspace": "../project"}))
            cfg = run.load_config(root, config_path)
            self.assertEqual(cfg.workspace, (root / "project").resolve())

    def test_default_poll_interval_is_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "runner.json"
            config_path.write_text(json.dumps({"profile": "worker", "workspace": "."}))
            self.assertEqual(run.load_config(root, config_path).poll_seconds, 3)


class CleanupTests(unittest.TestCase):
    def test_cleanup_removes_runtime_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in run.RUNTIME_DIRS:
                (root / name).mkdir(parents=True)
            files = [root / "runtime" / "result.json", root / "runtime-params" / "p.sh", root / "logs" / "x.log"]
            for path in files:
                path.write_text("delete")
            result = run.cleanup_new_runtime_files(root, set())
            self.assertTrue(all(not path.exists() for path in files))
            self.assertEqual(result["removed_count"], 3)


class BoardTests(unittest.TestCase):
    def test_terminal_when_all_tasks_done(self) -> None:
        self.assertTrue(run.board_is_terminal([{"status": "done"}, {"status": "done"}]))

    def test_not_terminal_while_task_waits(self) -> None:
        self.assertFalse(run.board_is_terminal([{"status": "done"}, {"status": "todo"}]))

    def test_prepare_board_keeps_one_fixed_test_board(self) -> None:
        calls: list[tuple[str, ...]] = []
        proc = type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(run, "list_boards", return_value={"default", "xhs-old", "xhs-run"}), patch.object(
            run, "command", side_effect=lambda args, **_: calls.append(tuple(args)) or proc
        ):
            run.prepare_board("xhs-run", Path("/tmp/project"))
        self.assertIn(("hermes", "kanban", "boards", "rm", "xhs-old", "--delete"), calls)
        self.assertIn(("hermes", "kanban", "boards", "create", "xhs-run", "--name", "小红书流程测试 · 未定稿", "--default-workdir", "/tmp/project", "--switch"), calls)


class ResultTests(unittest.TestCase):
    def test_verified_without_send_success_is_not_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "REJECT"},
            {"key": "publish-send", "result_status": None},
            {"key": "publish-verify", "result_status": "VERIFIED"},
        ]
        self.assertFalse(run.is_published_and_verified(stages))

    def test_send_success_and_one_target_match_is_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "APPROVE"},
            {"key": "publish-send", "result_status": "SEND_SUCCESS"},
            {"key": "publish-verify", "result_status": "VERIFIED", "metadata": {"exact_draft_count_in_target_thread": "1"}},
        ]
        self.assertTrue(run.is_published_and_verified(stages))

    def test_duplicate_in_target_thread_is_not_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "APPROVE"},
            {"key": "publish-send", "result_status": "SEND_SUCCESS"},
            {"key": "publish-verify", "result_status": "VERIFIED", "metadata": {"exact_draft_count_in_target_thread": "2"}},
        ]
        self.assertFalse(run.is_published_and_verified(stages))


class SemanticGateTests(unittest.TestCase):
    def test_finish_without_worker_promotes_before_completing(self) -> None:
        calls: list[tuple[str, ...]] = []
        proc = type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(run, "command", side_effect=lambda args, **_: calls.append(tuple(args)) or proc):
            run.finish_without_worker("xhs-run", "task-1", "no candidate")
        self.assertEqual(calls[0], (
            "hermes", "kanban", "--board", "xhs-run", "promote", "task-1", "semantic gate skip", "--force"
        ))
        self.assertEqual(calls[1][:7], (
            "hermes", "kanban", "--board", "xhs-run", "complete", "task-1", "--summary"
        ))

    def state(self) -> dict:
        return {
            "profile": "worker",
            "created": [
                {"key": "scout", "id": "scout"},
                {"key": "chair", "id": "chair"},
                {"key": "publish-send", "id": "publish-send"},
                {"key": "publish-verify", "id": "publish-verify"},
            ],
        }

    def test_no_candidate_finishes_all_downstream_without_workers(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "ready", "assignee": None},
            {"id": "publish-send", "status": "todo", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        skipped: list[str] = []
        with patch.object(run, "latest_run", return_value={"metadata": {"status": "NO_CANDIDATE"}}), patch.object(
            run, "finish_without_worker", side_effect=lambda _board, task_id, _reason: skipped.append(task_id)
        ), patch.object(run, "activate_waiting_task") as activate:
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(skipped, ["chair", "publish-send", "publish-verify"])
        activate.assert_not_called()

    def test_found_candidate_activates_only_chair(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "ready", "assignee": None},
            {"id": "publish-send", "status": "todo", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        activated: list[tuple[str, str]] = []
        with patch.object(run, "latest_run", return_value={"metadata": {"status": "FOUND"}}), patch.object(
            run, "activate_waiting_task", side_effect=lambda _board, task_id, profile: activated.append((task_id, profile))
        ), patch.object(run, "finish_without_worker") as skip:
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(activated, [("chair", "worker")])
        skip.assert_not_called()

    def test_chair_reject_skips_publish_and_verifier(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "done", "assignee": "worker"},
            {"id": "publish-send", "status": "ready", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        runs = {
            "scout": {"metadata": {"status": "FOUND"}},
            "chair": {"metadata": {"decision": "REJECT"}},
        }
        skipped: list[str] = []
        with patch.object(run, "latest_run", side_effect=lambda _board, task_id: runs[task_id]), patch.object(
            run, "finish_without_worker", side_effect=lambda _board, task_id, _reason: skipped.append(task_id)
        ), patch.object(run, "activate_waiting_task"):
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(skipped, ["publish-send", "publish-verify"])

    def test_send_success_activates_only_post_verifier(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "done", "assignee": "worker"},
            {"id": "publish-send", "status": "done", "assignee": "worker"},
            {"id": "publish-verify", "status": "ready", "assignee": None},
        ]
        runs = {
            "scout": {"metadata": {"status": "FOUND"}},
            "chair": {"metadata": {"decision": "APPROVE"}},
            "publish-send": {"metadata": {"status": "SEND_SUCCESS"}},
        }
        activated: list[str] = []
        with patch.object(run, "latest_run", side_effect=lambda _board, task_id: runs[task_id]), patch.object(
            run, "activate_waiting_task", side_effect=lambda _board, task_id, _profile: activated.append(task_id)
        ), patch.object(run, "finish_without_worker"):
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(activated, ["publish-verify"])


class RunnerFinallyTests(unittest.TestCase):
    def test_cleanup_runs_when_iteration_raises(self) -> None:
        cfg = run.RunnerConfig(profile="worker", workspace=Path("/tmp/workspace"), poll_seconds=1, timeout_minutes=1)
        calls: list[str] = []
        with patch.object(run, "prepare_board"), patch.object(run, "start_iteration", side_effect=RuntimeError("boom")), patch.object(
            run, "cleanup_browser_tabs", side_effect=lambda *_: calls.append("tabs") or {}
        ), patch.object(run, "cleanup_new_runtime_files", side_effect=lambda *_: calls.append("files") or {}), patch.object(
            run, "snapshot_runtime_files", return_value=set()
        ), patch.object(run, "runner_lock"):
            result = run.execute_campaign(Path("/tmp/project"), cfg)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(calls, ["tabs", "files"])


if __name__ == "__main__":
    unittest.main()
