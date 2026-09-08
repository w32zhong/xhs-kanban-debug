#!/usr/bin/env python3
"""Deterministic post-run coordination and cleanup.

No LLM is involved. Public XHS content is never modified. The script only:
1. validates structured publish/verify state;
2. applies a fixed ordered decision table;
3. deletes files that match a validated run prefix;
4. closes stale browser tabs while preserving Kanban UI and one XHS login tab.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SAFE_PREFIX = re.compile(r"^xhs-[A-Za-z0-9_-]+-$")
PRE_SEND_SAFE = {
    "EDITOR_REF_INVALID",
    "TEXT_MISMATCH",
    "WRONG_REPLY_TARGET",
    "REPLY_CONTEXT_UNCONFIRMED",
    "COMMENT_CONTEXT_UNCONFIRMED",
    "COMMENT_TARGET_NOT_FOUND",
    "TARGET_NOT_FOUND",
    "TOKEN_URL_MISSING",
    "LOGIN_REQUIRED",
    "BROWSER_ERROR",
    "SETUP_ERROR",
    "WRONG_ELEMENT_CLICKED",
}


def normalize(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "publish_status": "PUBLISH_STATUS_LITERAL",
        "verify_status": "VERIFY_STATUS_LITERAL",
        "send_clicked": "SEND_CLICKED_LITERAL",
        "editor_reset_after_send": "EDITOR_RESET_AFTER_SEND_LITERAL",
        "target_context_match": "TARGET_CONTEXT_MATCH_LITERAL",
        "thread_exhausted": "THREAD_EXHAUSTED_LITERAL",
        "exact_draft_count": "EXACT_DRAFT_COUNT_LITERAL",
        "exact_draft_count_in_target_thread": "EXACT_DRAFT_COUNT_LITERAL",
        "exact_draft_outside_target": "EXACT_DRAFT_OUTSIDE_TARGET_LITERAL",
        "exact_draft_found_outside_target_thread": "EXACT_DRAFT_OUTSIDE_TARGET_LITERAL",
        "content_modified": "CONTENT_MODIFIED_LITERAL",
        "run_prefix": "RUN_PREFIX_LITERAL",
        "archive_board": "ARCHIVE_BOARD_LITERAL",
    }
    out = dict(data)
    for short, literal in aliases.items():
        if literal not in out and short in out:
            out[literal] = out[short]
    return out


def parse_count(raw: Any) -> int | None:
    if raw == "UNKNOWN" or raw is None:
        return None
    if isinstance(raw, int) and raw >= 0:
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    raise ValueError("EXACT_DRAFT_COUNT_LITERAL must be a non-negative integer or UNKNOWN")


def validate(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    d = normalize(data)
    required = [
        "PUBLISH_STATUS_LITERAL", "VERIFY_STATUS_LITERAL", "SEND_CLICKED_LITERAL",
        "EDITOR_RESET_AFTER_SEND_LITERAL", "TARGET_CONTEXT_MATCH_LITERAL",
        "THREAD_EXHAUSTED_LITERAL", "EXACT_DRAFT_COUNT_LITERAL",
        "EXACT_DRAFT_OUTSIDE_TARGET_LITERAL", "CONTENT_MODIFIED_LITERAL",
    ]
    errors = [f"missing {key}" for key in required if key not in d]
    for key in ["SEND_CLICKED_LITERAL", "EDITOR_RESET_AFTER_SEND_LITERAL",
                "TARGET_CONTEXT_MATCH_LITERAL", "THREAD_EXHAUSTED_LITERAL",
                "EXACT_DRAFT_OUTSIDE_TARGET_LITERAL"]:
        if key in d and d[key] not in {"YES", "NO", "UNKNOWN"}:
            errors.append(f"invalid {key}={d[key]!r}")
    if d.get("CONTENT_MODIFIED_LITERAL") != "NO":
        errors.append("CONTENT_MODIFIED_LITERAL must be NO")
    try:
        d["_count"] = parse_count(d.get("EXACT_DRAFT_COUNT_LITERAL"))
    except ValueError as exc:
        errors.append(str(exc))
        d["_count"] = None
    if d.get("VERIFY_STATUS_LITERAL") == "VERIFIED":
        expected = {
            "TARGET_CONTEXT_MATCH_LITERAL": "YES",
            "THREAD_EXHAUSTED_LITERAL": "YES",
            "EXACT_DRAFT_OUTSIDE_TARGET_LITERAL": "NO",
        }
        for key, value in expected.items():
            if d.get(key) != value:
                errors.append(f"VERIFIED contradicts {key}={d.get(key)!r}")
        if d.get("_count") != 1:
            errors.append("VERIFIED requires exact draft count 1")
    return d, errors


def decide(d: dict[str, Any], errors: list[str]) -> dict[str, str]:
    if errors:
        return result("ESCALATE_MANUAL", "INVALID_OR_CONTRADICTORY_INPUT", "NO", "REVIEW_INVALID_INPUT")
    publish = d["PUBLISH_STATUS_LITERAL"]
    verify = d["VERIFY_STATUS_LITERAL"]
    clicked = d["SEND_CLICKED_LITERAL"]
    exhausted = d["THREAD_EXHAUSTED_LITERAL"]
    count = d["_count"]
    outside = d["EXACT_DRAFT_OUTSIDE_TARGET_LITERAL"]
    context = d["TARGET_CONTEXT_MATCH_LITERAL"]

    if verify == "VERIFIED" and context == "YES" and exhausted == "YES" and count == 1 and outside == "NO":
        return result("NO_ACTION", "VERIFIED_SINGLE_CORRECT_REPLY", "NO", "NONE")
    if verify == "WRONG_THREAD" or (outside == "YES" and count == 0):
        return result("MANUAL_DELETE_REQUIRED", "WRONG_THREAD_PUBLISHED", "NO", "REVIEW_AND_DELETE_WRONG_THREAD")
    if verify == "DUPLICATE_REPLY" or (count is not None and count > 1):
        return result("MANUAL_DELETE_REQUIRED", "DUPLICATE_PUBLISHED", "NO", "REVIEW_AND_REMOVE_DUPLICATES")
    if verify == "REPLY_NOT_FOUND" and exhausted == "YES":
        if clicked == "NO":
            return result("SAFE_RETRY_ALLOWED", "NOT_SENT_AND_VERIFIED_ABSENT", "YES_ONCE_WITH_FRESH_SESSION", "NONE")
        return result("ESCALATE_MANUAL", "SEND_CLAIMED_BUT_VERIFIED_ABSENT", "NO", "REVIEW_AMBIGUOUS_SEND")
    if verify == "THREAD_UNCONFIRMED" or exhausted != "YES":
        return result("ESCALATE_MANUAL", "VERIFICATION_INCOMPLETE", "NO", "COMPLETE_VERIFICATION")
    if publish in PRE_SEND_SAFE and clicked == "NO" and verify == "REPLY_NOT_FOUND" and exhausted == "YES" and count == 0:
        return result("SAFE_RETRY_ALLOWED", "PRE_SEND_SAFE_EXIT", "YES_ONCE_WITH_FRESH_SESSION", "NONE")
    if publish in {"SEND_FAILED", "NEEDS_VERIFIER"} and (clicked == "YES" or d["EDITOR_RESET_AFTER_SEND_LITERAL"] == "UNKNOWN"):
        return result("ESCALATE_MANUAL", "AMBIGUOUS_SEND_OUTCOME", "NO", "REVIEW_AMBIGUOUS_SEND")
    return result("ESCALATE_MANUAL", "UNCLASSIFIED_STATE", "NO", "REVIEW_AMBIGUOUS_SEND")


def result(decision: str, reason: str, retry: str, manual: str) -> dict[str, str]:
    return {"decision": decision, "reason_code": reason, "retry_allowed": retry, "manual_action_required": manual}


def cleanup_files(prefix: str | None, dry_run: bool) -> dict[str, Any]:
    if not prefix or not SAFE_PREFIX.fullmatch(prefix):
        return {"status": "SKIPPED_UNSAFE_PREFIX", "deleted": [], "errors": []}
    specs = [
        ("evidence", f"{prefix}*.png"),
        ("logs", f"{prefix}*-watch.log"),
        ("runtime-params", f"{prefix}*.sh"),
        ("runtime-params", f"{prefix}*.txt"),
        ("roundtable", f"{prefix}*.md"),
    ]
    deleted: list[str] = []
    errors: list[str] = []
    for dirname, pattern in specs:
        base = (ROOT / dirname).resolve()
        for path in base.glob(pattern):
            resolved = path.resolve()
            if base not in resolved.parents:
                errors.append(f"outside allowlist: {resolved}")
                continue
            try:
                if not dry_run:
                    resolved.unlink(missing_ok=True)
                deleted.append(str(resolved))
            except OSError as exc:
                errors.append(f"{resolved}: {exc}")
    for name in ["current-run.json", "full-e2e-current.json"]:
        path = ROOT / name
        if path.exists():
            try:
                if not dry_run:
                    path.unlink()
                deleted.append(str(path))
            except OSError as exc:
                errors.append(f"{path}: {exc}")
    return {"status": "PARTIAL" if errors else "COMPLETED", "deleted": deleted, "errors": errors}


def browser(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["agent-browser", *args], text=True, capture_output=True)


def cleanup_tabs(dry_run: bool) -> dict[str, Any]:
    listed = browser("tab", "list", "--json")
    if listed.returncode:
        return {"status": "PARTIAL", "closed": [], "errors": [listed.stderr or listed.stdout], "remaining": []}
    tabs = json.loads(listed.stdout).get("data", {}).get("tabs", [])
    preserve: set[str] = set()
    for tab in tabs:
        url = tab.get("url", "")
        title = tab.get("title", "")
        if title == "Hermes Kanban" or "sandbox_env:8002" in url or ":10012/" in url:
            preserve.add(tab["targetId"])
    xhs = [tab for tab in tabs if "xiaohongshu.com" in tab.get("url", "")]
    chosen = next((tab for tab in xhs if tab.get("active")), xhs[0] if xhs else None)
    if chosen:
        preserve.add(chosen["targetId"])
    closed: list[dict[str, Any]] = []
    errors: list[str] = []
    for tab in tabs:
        if tab["targetId"] in preserve:
            continue
        ok = True
        detail = "dry-run"
        if not dry_run:
            proc = browser("tab", "close", tab["tabId"])
            ok = proc.returncode == 0
            detail = proc.stderr or proc.stdout
            if not ok:
                errors.append(f"{tab['tabId']}: {detail}")
        closed.append({"tabId": tab["tabId"], "title": tab.get("title", ""), "ok": ok})
    final = tabs
    if not dry_run:
        relisted = browser("tab", "list", "--json")
        if relisted.returncode == 0:
            final = json.loads(relisted.stdout).get("data", {}).get("tabs", [])
        else:
            errors.append(relisted.stderr or relisted.stdout)
    return {"status": "PARTIAL" if errors else "COMPLETED", "closed": closed, "errors": errors, "remaining": final}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON file containing structured publish/verify state")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-tabs", action="store_true")
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    d, errors = validate(data)
    coordination = decide(d, errors)
    files = cleanup_files(d.get("RUN_PREFIX_LITERAL"), args.dry_run)
    tabs = {"status": "SKIPPED", "closed": [], "errors": [], "remaining": []} if args.skip_tabs else cleanup_tabs(args.dry_run)
    output = {
        "coordination": coordination,
        "validation_errors": errors,
        "files_cleanup_status": files["status"],
        "files_deleted_count": len(files["deleted"]),
        "files_deleted": files["deleted"],
        "file_errors": files["errors"],
        "tabs_cleanup_status": tabs["status"],
        "tabs_closed_count": len(tabs["closed"]),
        "tabs_closed": tabs["closed"],
        "tab_errors": tabs["errors"],
        "remaining_tabs": tabs["remaining"],
        "board_archive_requested": d.get("ARCHIVE_BOARD_LITERAL", "NO"),
        "content_modified_by_coordinator": "NO",
        "vision_calls": 0,
        "dry_run": args.dry_run,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
