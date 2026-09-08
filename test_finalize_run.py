#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("finalize_run", ROOT / "finalize_run.py")
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def base(**changes):
    data = {
        "PUBLISH_STATUS_LITERAL": "SEND_SUCCESS",
        "VERIFY_STATUS_LITERAL": "VERIFIED",
        "SEND_CLICKED_LITERAL": "YES",
        "EDITOR_RESET_AFTER_SEND_LITERAL": "YES",
        "TARGET_CONTEXT_MATCH_LITERAL": "YES",
        "THREAD_EXHAUSTED_LITERAL": "YES",
        "EXACT_DRAFT_COUNT_LITERAL": "1",
        "EXACT_DRAFT_OUTSIDE_TARGET_LITERAL": "NO",
        "CONTENT_MODIFIED_LITERAL": "NO",
        "RUN_PREFIX_LITERAL": "xhs-test-",
        "ARCHIVE_BOARD_LITERAL": "NO",
    }
    data.update(changes)
    return data


class DecisionTests(unittest.TestCase):
    def decision(self, data):
        d, errors = mod.validate(data)
        return mod.decide(d, errors), errors

    def test_verified_single_reply(self):
        out, errors = self.decision(base())
        self.assertEqual(errors, [])
        self.assertEqual(out["decision"], "NO_ACTION")

    def test_wrong_thread(self):
        out, _ = self.decision(base(VERIFY_STATUS_LITERAL="WRONG_THREAD", EXACT_DRAFT_COUNT_LITERAL="0", EXACT_DRAFT_OUTSIDE_TARGET_LITERAL="YES"))
        self.assertEqual(out["reason_code"], "WRONG_THREAD_PUBLISHED")

    def test_duplicate(self):
        out, _ = self.decision(base(VERIFY_STATUS_LITERAL="DUPLICATE_REPLY", EXACT_DRAFT_COUNT_LITERAL="2"))
        self.assertEqual(out["reason_code"], "DUPLICATE_PUBLISHED")

    def test_clicked_but_absent_never_retries(self):
        out, _ = self.decision(base(VERIFY_STATUS_LITERAL="REPLY_NOT_FOUND", EXACT_DRAFT_COUNT_LITERAL="0"))
        self.assertEqual(out["decision"], "ESCALATE_MANUAL")
        self.assertEqual(out["retry_allowed"], "NO")

    def test_not_clicked_and_absent_allows_one_retry(self):
        out, _ = self.decision(base(PUBLISH_STATUS_LITERAL="SETUP_ERROR", VERIFY_STATUS_LITERAL="REPLY_NOT_FOUND", SEND_CLICKED_LITERAL="NO", EDITOR_RESET_AFTER_SEND_LITERAL="UNKNOWN", EXACT_DRAFT_COUNT_LITERAL="0"))
        self.assertEqual(out["decision"], "SAFE_RETRY_ALLOWED")
        self.assertEqual(out["retry_allowed"], "YES_ONCE_WITH_FRESH_SESSION")

    def test_unconfirmed_never_retries(self):
        out, _ = self.decision(base(VERIFY_STATUS_LITERAL="THREAD_UNCONFIRMED", THREAD_EXHAUSTED_LITERAL="NO", EXACT_DRAFT_COUNT_LITERAL="UNKNOWN"))
        self.assertEqual(out["reason_code"], "VERIFICATION_INCOMPLETE")
        self.assertEqual(out["retry_allowed"], "NO")

    def test_contradictory_verified_is_invalid(self):
        out, errors = self.decision(base(EXACT_DRAFT_COUNT_LITERAL="0"))
        self.assertTrue(errors)
        self.assertEqual(out["reason_code"], "INVALID_OR_CONTRADICTORY_INPUT")

    def test_unsafe_prefix_skips_cleanup(self):
        out = mod.cleanup_files("../", dry_run=True)
        self.assertEqual(out["status"], "SKIPPED_UNSAFE_PREFIX")
        self.assertEqual(out["deleted"], [])


if __name__ == "__main__":
    unittest.main()
