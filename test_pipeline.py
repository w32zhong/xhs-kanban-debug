#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class QualityRoundtablePipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = json.loads((ROOT / "pipeline.json").read_text(encoding="utf-8"))

    def test_pipeline_restores_parallel_two_member_roundtable(self) -> None:
        self.assertEqual(
            [task["key"] for task in self.pipeline["tasks"]],
            ["scout", "review-a", "review-b", "chair", "publish-send", "publish-verify"],
        )
        tasks = {task["key"]: task for task in self.pipeline["tasks"]}
        self.assertEqual(tasks["review-a"]["parents"], ["scout"])
        self.assertEqual(tasks["review-b"]["parents"], ["scout"])
        self.assertEqual(tasks["chair"]["parents"], ["review-a", "review-b"])
        self.assertEqual(self.pipeline["max_parallel"], 2)

    def test_roundtable_uses_dynamic_scout_candidate(self) -> None:
        prompt = (ROOT / "prompts/review-worker.md").read_text(encoding="utf-8")
        self.assertIn("runtime/scout-result.json", prompt)
        self.assertIn("提高回答", prompt)
        self.assertNotIn("命中角度库自动 REJECT", prompt)

    def test_review_rejection_is_reserved_for_severe_problems(self) -> None:
        prompt = (ROOT / "prompts/review-worker.md").read_text(encoding="utf-8")
        self.assertIn("特别严重", prompt)
        self.assertIn("默认 recommendation: PASS", prompt)
        self.assertIn("可以通过改写解决", prompt)

    def test_chair_synthesizes_both_reviews_and_defaults_to_approve(self) -> None:
        prompt = (ROOT / "prompts/chair-worker.md").read_text(encoding="utf-8")
        self.assertIn("runtime/reviewer-a.json", prompt)
        self.assertIn("runtime/reviewer-b.json", prompt)
        self.assertIn("默认 decision: APPROVE", prompt)
        self.assertIn("直接修好", prompt)

    def test_scout_accepts_relevant_conversation_not_only_explicit_pain(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("相关的疑问、追问、经验交流、赞同或兴趣表达", prompt)
        self.assertIn("不要求必须是强烈痛点", prompt)
        self.assertIn("换下一个关键词", prompt)

    def test_numbered_reply_bubble_is_allowed_when_row_order_is_clear(self) -> None:
        publish = (ROOT / "prompts/publish-send-worker.md").read_text(encoding="utf-8")
        self.assertIn("点赞数 → 回复气泡数", publish)
        self.assertIn("第二个纯数字", publish)
        self.assertNotIn("唯一入口是纯数字且图标语义不清，不猜", publish)

    def test_browser_safety_gates_are_still_present(self) -> None:
        publish = (ROOT / "prompts/publish-send-worker.md").read_text(encoding="utf-8")
        self.assertIn("作者 + 唯一前缀必须匹配", publish)
        self.assertIn("逐字一致", publish)
        self.assertIn("点击发送一次", publish)


if __name__ == "__main__":
    unittest.main()
