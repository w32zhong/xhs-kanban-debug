#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run


class ConfigTests(unittest.TestCase):
    def test_cli_overrides_profile_workspace_and_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "runner-config.json"
            config_path.write_text(json.dumps({"profile": "from-file", "workspace": ".", "board_slug": "xhs-run", "account_name": "from-file-account"}))
            cfg = run.load_config(root, config_path, profile="from-cli", workspace=str(root / "project"), account_name="from-cli-account")
            self.assertEqual(cfg.profile, "from-cli")
            self.assertEqual(cfg.workspace, (root / "project").resolve())
            self.assertEqual(cfg.board_slug, "xhs-run")
            self.assertEqual(cfg.account_name, "from-cli-account")

    def test_relative_workspace_is_resolved_from_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "config"
            config_dir.mkdir()
            config_path = config_dir / "runner.json"
            config_path.write_text(json.dumps({"profile": "worker", "workspace": "../project", "account_name": "me"}))
            cfg = run.load_config(root, config_path)
            self.assertEqual(cfg.workspace, (root / "project").resolve())

    def test_default_poll_interval_is_fast(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "runner.json"
            config_path.write_text(json.dumps({"profile": "worker", "workspace": ".", "account_name": "me"}))
            self.assertEqual(run.load_config(root, config_path).poll_seconds, 3)
    def test_default_profile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "runner.json"
            config_path.write_text(json.dumps({"profile": "default", "workspace": ".", "account_name": "me"}))
            with self.assertRaisesRegex(ValueError, "default profile is not allowed"):
                run.load_config(root, config_path)

    def test_missing_account_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "runner.json"
            config_path.write_text(json.dumps({"profile": "worker", "workspace": "."}))
            with self.assertRaisesRegex(ValueError, "account name is required"):
                run.load_config(root, config_path)

    def test_scout_only_flag_uses_isolated_pipeline_and_board(self) -> None:
        with patch("sys.argv", ["run.py", "--scout-only"]):
            args = run.parse_args()
        self.assertTrue(args.scout_only)
        self.assertIsNone(args.pipeline_config)


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
    def test_terminal_when_all_current_tasks_done(self) -> None:
        tasks = [{"id": "a", "status": "done"}, {"id": "b", "status": "done"}]
        self.assertTrue(run.board_is_terminal(tasks, {"a", "b"}))

    def test_not_terminal_while_current_task_waits(self) -> None:
        tasks = [{"id": "a", "status": "done"}, {"id": "b", "status": "todo"}]
        self.assertFalse(run.board_is_terminal(tasks, {"a", "b"}))

    def test_not_terminal_while_current_task_is_blocked(self) -> None:
        self.assertFalse(run.board_is_terminal([{"id": "a", "status": "blocked"}], {"a"}))

    def test_historical_active_task_does_not_block_current_run(self) -> None:
        tasks = [{"id": "old", "status": "running"}, {"id": "current", "status": "done"}]
        self.assertTrue(run.board_is_terminal(tasks, {"current"}))

    def test_missing_current_task_is_not_terminal(self) -> None:
        self.assertFalse(run.board_is_terminal([{"id": "old", "status": "done"}], {"current"}))

    def test_prepare_existing_board_reuses_it_and_preserves_other_boards(self) -> None:
        calls: list[tuple[str, ...]] = []
        proc = type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(run, "list_boards", return_value={"default", "xhs-old", "xhs-run"}), patch.object(
            run, "command", side_effect=lambda args, **_: calls.append(tuple(args)) or proc
        ):
            run.prepare_board("xhs-run", Path("/tmp/project"))
        self.assertEqual(calls, [
            ("hermes", "kanban", "boards", "set-default-workdir", "xhs-run", "/tmp/project"),
            ("hermes", "kanban", "boards", "switch", "xhs-run"),
        ])

    def test_prepare_missing_board_creates_it(self) -> None:
        calls: list[tuple[str, ...]] = []
        proc = type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(run, "list_boards", return_value={"default", "xhs-old"}), patch.object(
            run, "command", side_effect=lambda args, **_: calls.append(tuple(args)) or proc
        ):
            run.prepare_board("xhs-run", Path("/tmp/project"))
        self.assertEqual(calls, [(
            "hermes", "kanban", "boards", "create", "xhs-run", "--name", "小红书流程测试 · 未定稿",
            "--default-workdir", "/tmp/project", "--switch",
        )])

    def test_archive_visible_tasks_archives_every_status(self) -> None:
        tasks = [
            {"id": "triage-1", "status": "triage"},
            {"id": "active-1", "status": "running"},
            {"id": "blocked-1", "status": "blocked"},
            {"id": "done-1", "status": "done"},
            {"id": "failed-1", "status": "failed"},
        ]
        calls: list[tuple[str, ...]] = []
        proc = type("P", (), {"returncode": 0, "stdout": "", "stderr": ""})()
        with patch.object(run, "list_tasks", return_value=tasks), patch.object(
            run, "command", side_effect=lambda args, **_: calls.append(tuple(args)) or proc
        ):
            run.archive_visible_tasks("xhs-run")
        self.assertEqual(calls, [(
            "hermes", "kanban", "--board", "xhs-run", "archive",
            "triage-1", "active-1", "blocked-1", "done-1", "failed-1",
        )])

    def test_archive_visible_tasks_does_not_call_archive_for_empty_board(self) -> None:
        with patch.object(run, "list_tasks", return_value=[]), patch.object(run, "command") as command:
            run.archive_visible_tasks("xhs-run")
        command.assert_not_called()

    def test_wait_for_board_ignores_historical_running_tasks(self) -> None:
        cfg = run.RunnerConfig(profile="worker", workspace=Path("/tmp/project"), account_name="me", poll_seconds=1, timeout_minutes=1)
        state = {"created": [{"key": "scout", "id": "current"}]}
        tasks = [{"id": "old", "status": "running"}, {"id": "current", "status": "done"}]
        with patch.object(run, "list_tasks", return_value=tasks), patch.object(
            run, "apply_semantic_gates", return_value=False
        ), patch.object(run.time, "sleep") as sleep:
            self.assertEqual(run.wait_for_board("xhs-run", state, cfg), tasks)
        sleep.assert_not_called()

    def test_timeout_reports_only_current_nonterminal_tasks(self) -> None:
        cfg = run.RunnerConfig(profile="worker", workspace=Path("/tmp/project"), account_name="me", poll_seconds=1, timeout_minutes=1)
        state = {"created": [
            {"key": "scout", "id": "current-running", "title": "Scout"},
            {"key": "chair", "id": "current-done", "title": "Chair"},
        ]}
        tasks = [
            {"id": "old", "status": "ready", "assignee": "other"},
            {"id": "current-running", "status": "running", "assignee": "worker"},
            {"id": "current-done", "status": "done", "assignee": "worker"},
        ]
        with patch.object(run, "list_tasks", return_value=tasks), patch.object(
            run, "apply_semantic_gates", return_value=False
        ), patch.object(run.time, "monotonic", side_effect=[0, 61]):
            with self.assertRaises(TimeoutError) as caught:
                run.wait_for_board("xhs-run", state, cfg)
        message = str(caught.exception)
        self.assertIn("scout", message)
        self.assertIn("current-running", message)
        self.assertIn("running", message)
        self.assertNotIn("old", message)
        self.assertNotIn("current-done", message)


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

    def test_cleaned_duplicates_with_one_reply_remaining_is_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "APPROVE"},
            {"key": "publish-send", "result_status": "SEND_SUCCESS"},
            {"key": "publish-verify", "result_status": "DUPLICATES_DELETED", "metadata": {
                "exact_draft_count_in_target_thread": "1",
                "deletions_performed": 1,
            }},
        ]
        self.assertTrue(run.is_published_and_verified(stages))

    def test_mismatched_reply_deleted_is_not_published(self) -> None:
        stages = [
            {"key": "chair", "result_status": "APPROVE"},
            {"key": "publish-send", "result_status": "SEND_SUCCESS"},
            {"key": "publish-verify", "result_status": "MISMATCH_DELETED", "metadata": {
                "exact_draft_count_in_target_thread": "0",
                "deletions_performed": 1,
            }},
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
                {"key": "review-a", "id": "review-a"},
                {"key": "review-b", "id": "review-b"},
                {"key": "chair", "id": "chair"},
                {"key": "publish-send", "id": "publish-send"},
                {"key": "publish-verify", "id": "publish-verify"},
            ],
        }

    def test_found_candidate_activates_both_reviewers(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "review-a", "status": "ready", "assignee": None},
            {"id": "review-b", "status": "ready", "assignee": None},
            {"id": "chair", "status": "todo", "assignee": None},
            {"id": "publish-send", "status": "todo", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        activated: list[str] = []
        with patch.object(run, "latest_run", return_value={"metadata": {"status": "FOUND"}}), patch.object(
            run, "activate_waiting_task", side_effect=lambda _board, task_id, _profile: activated.append(task_id)
        ), patch.object(run, "dispatch_board") as dispatch, patch.object(run, "finish_without_worker"):
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(activated, ["review-a", "review-b"])
        dispatch.assert_called_once_with("xhs-run", max_tasks=2)

    def test_semantic_gate_without_new_assignments_does_not_dispatch(self) -> None:
        tasks = [{"id": "scout", "status": "running", "assignee": "worker"}]
        with patch.object(run, "dispatch_board") as dispatch:
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertFalse(changed)
        dispatch.assert_not_called()

    def test_reviews_complete_activate_chair_even_when_they_request_revision(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "review-a", "status": "done", "assignee": "worker"},
            {"id": "review-b", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "ready", "assignee": None},
            {"id": "publish-send", "status": "todo", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        runs = {
            "scout": {"metadata": {"status": "FOUND"}},
            "review-a": {"metadata": {"recommendation": "REVISE"}},
            "review-b": {"metadata": {"recommendation": "PASS"}},
        }
        activated: list[str] = []
        with patch.object(run, "latest_run", side_effect=lambda _board, task_id: runs[task_id]), patch.object(
            run, "activate_waiting_task", side_effect=lambda _board, task_id, _profile: activated.append(task_id)
        ), patch.object(run, "dispatch_board"), patch.object(run, "finish_without_worker"):
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(activated, ["chair"])

    def test_no_candidate_finishes_all_downstream_without_workers(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "review-a", "status": "ready", "assignee": None},
            {"id": "review-b", "status": "ready", "assignee": None},
            {"id": "chair", "status": "todo", "assignee": None},
            {"id": "publish-send", "status": "todo", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        skipped: list[str] = []
        with patch.object(run, "latest_run", return_value={"metadata": {"status": "NO_CANDIDATE"}}), patch.object(
            run, "finish_without_worker", side_effect=lambda _board, task_id, _reason: skipped.append(task_id)
        ), patch.object(run, "activate_waiting_task") as activate:
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(skipped, ["review-a", "review-b", "chair", "publish-send", "publish-verify"])
        activate.assert_not_called()

    def test_chair_reject_skips_publish_and_verifier(self) -> None:
        tasks = [
            {"id": "scout", "status": "done", "assignee": "worker"},
            {"id": "review-a", "status": "done", "assignee": "worker"},
            {"id": "review-b", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "done", "assignee": "worker"},
            {"id": "publish-send", "status": "ready", "assignee": None},
            {"id": "publish-verify", "status": "todo", "assignee": None},
        ]
        runs = {
            "scout": {"metadata": {"status": "FOUND"}},
            "review-a": {"metadata": {"recommendation": "PASS"}},
            "review-b": {"metadata": {"recommendation": "PASS"}},
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
            {"id": "review-a", "status": "done", "assignee": "worker"},
            {"id": "review-b", "status": "done", "assignee": "worker"},
            {"id": "chair", "status": "done", "assignee": "worker"},
            {"id": "publish-send", "status": "done", "assignee": "worker"},
            {"id": "publish-verify", "status": "ready", "assignee": None},
        ]
        runs = {
            "scout": {"metadata": {"status": "FOUND"}},
            "review-a": {"metadata": {"recommendation": "REVISE"}},
            "review-b": {"metadata": {"recommendation": "PASS"}},
            "chair": {"metadata": {"decision": "APPROVE"}},
            "publish-send": {"metadata": {"status": "SEND_SUCCESS"}},
        }
        activated: list[str] = []
        with patch.object(run, "latest_run", side_effect=lambda _board, task_id: runs[task_id]), patch.object(
            run, "activate_waiting_task", side_effect=lambda _board, task_id, _profile: activated.append(task_id)
        ), patch.object(run, "dispatch_board"), patch.object(run, "finish_without_worker"):
            changed = run.apply_semantic_gates("xhs-run", self.state(), tasks)
        self.assertTrue(changed)
        self.assertEqual(activated, ["publish-verify"])


class RunnerFinallyTests(unittest.TestCase):
    def test_campaign_prepares_then_archives_before_starting_iteration(self) -> None:
        cfg = run.RunnerConfig(profile="worker", workspace=Path("/tmp/workspace"), account_name="test-account")
        calls: list[str] = []
        with patch.object(run, "prepare_board", side_effect=lambda *_: calls.append("prepare")), patch.object(
            run, "archive_visible_tasks", side_effect=lambda *_: calls.append("archive")
        ), patch.object(
            run, "start_iteration", side_effect=lambda *_args, **_kwargs: calls.append("start") or {"board": "xhs-run", "created": []}
        ), patch.object(run, "wait_for_board", return_value=[]), patch.object(
            run, "compact_result", return_value={"status": "COMPLETED"}
        ), patch.object(run, "cleanup_browser_tabs", return_value={}), patch.object(
            run, "cleanup_new_runtime_files", return_value={}
        ), patch.object(run, "snapshot_runtime_files", return_value=set()), patch.object(run, "runner_lock"):
            run.execute_campaign(Path("/tmp/project"), cfg)
        self.assertEqual(calls, ["prepare", "archive", "start"])

    def test_cleanup_runs_when_iteration_raises(self) -> None:
        cfg = run.RunnerConfig(profile="worker", workspace=Path("/tmp/workspace"), account_name="test-account", poll_seconds=1, timeout_minutes=1)
        calls: list[str] = []
        with patch.object(run, "prepare_board"), patch.object(run, "archive_visible_tasks"), patch.object(run, "start_iteration", side_effect=RuntimeError("boom")), patch.object(
            run, "cleanup_browser_tabs", side_effect=lambda *_: calls.append("tabs") or {}
        ), patch.object(run, "cleanup_new_runtime_files", side_effect=lambda *_: calls.append("files") or {}), patch.object(
            run, "snapshot_runtime_files", return_value=set()
        ), patch.object(run, "runner_lock"):
            result = run.execute_campaign(Path("/tmp/project"), cfg)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(calls, ["tabs", "files"])


if __name__ == "__main__":
    unittest.main()
