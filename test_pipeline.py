#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class FastPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = json.loads((ROOT / "pipeline.json").read_text(encoding="utf-8"))

    def test_pipeline_has_four_stages_not_seven(self) -> None:
        self.assertEqual(
            [task["key"] for task in self.pipeline["tasks"]],
            ["scout", "chair", "publish-send", "publish-verify"],
        )

    def test_pipeline_is_dynamic_not_rotated_fixture_mode(self) -> None:
        self.assertEqual(self.pipeline["target_source"], "dynamic_search")
        self.assertNotIn("publish-target-pool.json", json.dumps(self.pipeline, ensure_ascii=False))

    def test_review_consumes_scout_handoff_not_static_review_case(self) -> None:
        chair_prompt = (ROOT / "prompts/chair-worker.md").read_text(encoding="utf-8")
        self.assertIn("runtime/scout-result.json", chair_prompt)
        self.assertIn("候选事实以 `runtime/scout-result.json` 为唯一来源", chair_prompt)

    def test_publish_requires_current_run_chair_file(self) -> None:
        publish_prompt = (ROOT / "prompts/publish-send-worker.md").read_text(encoding="utf-8")
        self.assertIn("runtime/chair-decision.json", publish_prompt)
        self.assertIn("decision", publish_prompt)

    def test_post_verify_skips_when_current_run_did_not_send(self) -> None:
        verify_prompt = (ROOT / "prompts/publish-verify-worker.md").read_text(encoding="utf-8")
        self.assertIn("runtime/publish-result.json", verify_prompt)
        self.assertIn("SEND_SUCCESS", verify_prompt)

    def test_iteration_assigns_only_first_stage_at_creation(self) -> None:
        source = (ROOT / "run_iteration.py").read_text(encoding="utf-8")
        self.assertIn('if index == 1:', source)
        self.assertIn('args.extend(["--assignee", configured_assignee])', source)
        self.assertIn('"profile": config.get("default_assignee", "")', source)
        self.assertIn('"--priority", str(100 - index)', source)


if __name__ == "__main__":
    unittest.main()
