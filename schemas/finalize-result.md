# 协调与清理结果固定格式

```text
FINALIZE_RESULT
decision: NO_ACTION | SAFE_RETRY_ALLOWED | MANUAL_DELETE_REQUIRED | ESCALATE_MANUAL
reason_code: VERIFIED_SINGLE_CORRECT_REPLY | WRONG_THREAD_PUBLISHED | DUPLICATE_PUBLISHED | NOT_SENT_AND_VERIFIED_ABSENT | SEND_CLAIMED_BUT_VERIFIED_ABSENT | VERIFICATION_INCOMPLETE | PRE_SEND_SAFE_EXIT | AMBIGUOUS_SEND_OUTCOME | INVALID_OR_CONTRADICTORY_INPUT | UNCLASSIFIED_STATE
publish_status: <参数原值>
verify_status: <参数原值>
send_clicked: YES | NO | UNKNOWN
thread_exhausted: YES | NO | UNKNOWN
exact_draft_count_in_target_thread: <非负整数或 UNKNOWN>
exact_draft_found_outside_target_thread: YES | NO | UNKNOWN
retry_allowed: NO | YES_ONCE_WITH_FRESH_SESSION
manual_action_required: NONE | REVIEW_AND_DELETE_WRONG_THREAD | REVIEW_AND_REMOVE_DUPLICATES | REVIEW_AMBIGUOUS_SEND | COMPLETE_VERIFICATION | REVIEW_INVALID_INPUT
content_modified_by_coordinator: NO
browser_content_calls: 0
vision_calls: 0
files_cleanup_status: COMPLETED | SKIPPED_UNSAFE_PREFIX | PARTIAL
files_deleted_count: <非负整数>
tabs_closed_count: <非负整数>
remaining_tabs:
  - <tabId | title | url；无则 NONE>
board_archive_requested: YES | NO
notes:
  - <简洁说明；无则 NONE>
```

规则：

- 协调决策遵循 `prompts/finalize-worker.md` 的有序决策表。
- `NO_ACTION` 仅用于复核确认正确目标线程内恰好一条定稿、线程穷尽且无外部重复。
- 只要发送可能已发生但结果不确定，`retry_allowed` 必须为 `NO`。
- `MANUAL_DELETE_REQUIRED` 只标记人工处理，本 worker 禁止删除或修改公开内容。
- 本地文件只能按合法 `RUN_PREFIX_LITERAL` 删除；缺失或非法时必须 `SKIPPED_UNSAFE_PREFIX`。
- 浏览器仅允许关闭非 Kanban UI 标签；禁止页面内容交互。
- 本 worker 不归档自己的当前看板，只报告 `board_archive_requested`。
- 完成后调用注入的 `kanban_complete`。
