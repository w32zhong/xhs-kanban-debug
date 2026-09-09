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
        self.assertIn("推荐流", prompt)

    def test_scout_uses_human_like_browser_operations(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("禁止使用", prompt)
        self.assertIn("evaluate", prompt)
        self.assertIn("拟人化", prompt)
        self.assertIn("agent-browser scroll down", prompt)

    def test_scout_browses_recommendation_feed(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("推荐流", prompt)
        self.assertIn("scroll down", prompt)
        self.assertIn("重新加载首页", prompt)

    def test_scout_refreshes_feed_before_selecting_candidates(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("先刷新推荐流", prompt)
        self.assertIn("agent-browser reload", prompt)
        self.assertIn("刷新完成前禁止进入帖子", prompt)

    def test_scout_uses_passed_account_name_and_sidebar_login_signal(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("ACCOUNT_NAME_LITERAL", prompt)
        self.assertIn("左侧栏", prompt)
        self.assertIn("“我”", prompt)
        self.assertIn("用户所说的“你”", prompt)
        self.assertIn("禁止进入个人主页", prompt)

    def test_scout_stops_at_first_reply_free_candidate(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("第一个通过内容门槛", prompt)
        self.assertIn("立即 FOUND", prompt)
        self.assertIn("禁止继续读取其他评论", prompt)
        self.assertIn("禁止比较是否还有更优目标", prompt)

    def test_scout_forbids_visual_and_exploratory_detours(self) -> None:
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertIn("禁止 screenshot", prompt)
        self.assertIn("禁止 vision", prompt)
        self.assertIn("禁止 agent-browser --help", prompt)
        self.assertIn("最多打开 2 篇帖子", prompt)

    def test_scout_only_pipeline_isolated_for_refinement(self) -> None:
        scout_pipeline = json.loads((ROOT / "scout-pipeline.json").read_text(encoding="utf-8"))
        self.assertEqual([task["key"] for task in scout_pipeline["tasks"]], ["scout"])
        self.assertEqual(scout_pipeline["tasks"][0]["prompt"], "prompts/scout-worker.md")
        self.assertNotIn("param_vars", scout_pipeline["tasks"][0])
        self.assertLessEqual(int(scout_pipeline["tasks"][0]["max_runtime"].removesuffix("m")), 6)

    def test_scout_account_name_is_external_runtime_input(self) -> None:
        pipeline_text = (ROOT / "pipeline.json").read_text(encoding="utf-8")
        scout_pipeline_text = (ROOT / "scout-pipeline.json").read_text(encoding="utf-8")
        prompt = (ROOT / "prompts/scout-worker.md").read_text(encoding="utf-8")
        self.assertNotIn("打钳的小虾", pipeline_text)
        self.assertNotIn("打钳的小虾", scout_pipeline_text)
        self.assertNotIn("打钳的小虾", prompt)
        self.assertIn("ACCOUNT_NAME_LITERAL", prompt)

    def test_worker_profile_setup_is_reproducible_from_repo(self) -> None:
        setup = (ROOT / "scripts/configure-worker-profile.py").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("disabled_toolsets", setup)
        self.assertIn('"kanban"', setup)
        self.assertIn('"vision"', setup)
        self.assertIn("terminal", setup)
        self.assertIn("configure-worker-profile.py", readme)
        self.assertIn("--account-name", readme)
        self.assertIn("不要使用 default profile", readme)

    def test_review_enforces_length_necessity_not_formula(self) -> None:
        prompt = (ROOT / "prompts/review-worker.md").read_text(encoding="utf-8")
        self.assertIn("默认一两句", prompt)
        self.assertIn("问句不是必选项", prompt)
        self.assertIn("承接句不是必选项", prompt)
        self.assertIn("拟人的懒惰", prompt)
        self.assertNotIn("20–100 个中文字符", prompt)

    def test_chair_runs_compression_and_anti_template_pass(self) -> None:
        prompt = (ROOT / "prompts/chair-worker.md").read_text(encoding="utf-8")
        self.assertIn("先删到不能再删", prompt)
        self.assertIn("一句话能完成，就不要写两句", prompt)
        self.assertIn("不得为了结构完整补问句", prompt)
        self.assertIn("事实问题确实需要解释", prompt)
        self.assertIn("像随手回的", prompt)

    def test_roundtable_focus_does_not_force_empathy_or_questions(self) -> None:
        tasks = {task["key"]: task for task in self.pipeline["tasks"]}
        self.assertNotIn("接住具体焦虑", tasks["review-a"]["body_vars"]["REVIEWER_FOCUS"])
        self.assertNotIn("好奇心与互动意愿", tasks["review-b"]["body_vars"]["REVIEWER_FOCUS"])

    def test_numbered_reply_bubble_is_allowed_when_row_order_is_clear(self) -> None:
        publish = (ROOT / "prompts/publish-send-worker.md").read_text(encoding="utf-8")
        self.assertIn("点赞数 → 回复气泡数", publish)
        self.assertIn("第二个纯数字", publish)
        self.assertNotIn("唯一入口是纯数字且图标语义不清，不猜", publish)

    def test_local_xhs_reply_style_guide_is_self_contained(self) -> None:
        guide = (ROOT / "prompts/xhs-reply-style.md").read_text(encoding="utf-8")
        self.assertIn("默认 1–2 句话", guide)
        self.assertIn("最多 3 句话", guide)
        self.assertIn("最多 1 个关键点", guide)
        self.assertIn("打钳", guide)
        self.assertIn("小范围内测", guide)
        self.assertNotIn("old-xhs-docs", guide)

    def test_original_reply_playbook_is_preserved_verbatim(self) -> None:
        import hashlib

        playbook = ROOT / "prompts/xhs-reply-话术-原典.md"
        self.assertTrue(playbook.is_file())
        digest = hashlib.sha256(playbook.read_bytes()).hexdigest()
        self.assertEqual(digest, "4eea6f67076c3966d9c182e7ca506e24fa8a9d9d614c09f4f0daf3e8b3f30a8d")

    def test_writing_workers_read_original_playbook_before_interpretation(self) -> None:
        for name in ("review-worker.md", "chair-worker.md"):
            prompt = (ROOT / "prompts" / name).read_text(encoding="utf-8")
            self.assertIn("./prompts/xhs-reply-话术-原典.md", prompt)
            self.assertIn("原典", prompt)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("xhs-reply-话术-原典.md", readme)
        self.assertIn("逐字", readme)

    def test_reviewers_must_follow_short_reply_guide(self) -> None:
        prompt = (ROOT / "prompts/review-worker.md").read_text(encoding="utf-8")
        self.assertIn("./prompts/xhs-reply-style.md", prompt)
        self.assertIn("最多 3 句话", prompt)
        self.assertIn("最多 1 个关键点", prompt)
        self.assertIn("不得输出小作文", prompt)

    def test_chair_hard_limits_final_comment(self) -> None:
        prompt = (ROOT / "prompts/chair-worker.md").read_text(encoding="utf-8")
        self.assertIn("./prompts/xhs-reply-style.md", prompt)
        self.assertIn("默认 1–2 句话", prompt)
        self.assertIn("最多 3 句话", prompt)
        self.assertIn("最多 4 行", prompt)
        self.assertIn("先删到不能再删", prompt)

    def test_publisher_rejects_overlong_or_tutorial_style_comment(self) -> None:
        prompt = (ROOT / "prompts/publish-send-worker.md").read_text(encoding="utf-8")
        self.assertIn("./prompts/xhs-reply-style.md", prompt)
        self.assertIn("TEXT_TOO_LONG", prompt)
        self.assertIn("超过 3 句话", prompt)
        self.assertIn("超过 4 行", prompt)
        self.assertIn("教程式", prompt)

    def test_browser_safety_gates_are_still_present(self) -> None:
        publish = (ROOT / "prompts/publish-send-worker.md").read_text(encoding="utf-8")
        self.assertIn("作者 + 唯一前缀必须匹配", publish)
        self.assertIn("逐字一致", publish)
        self.assertIn("点击发送一次", publish)


if __name__ == "__main__":
    unittest.main()
