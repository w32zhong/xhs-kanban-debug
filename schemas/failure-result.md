# 失败协调结果固定格式

```text
FAILURE_COORDINATION_RESULT
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
browser_calls: 0
vision_calls: 0
notes:
  - <简洁说明；无则 NONE>
```

规则：

- `NO_ACTION` 仅用于独立复核确认正确目标线程内恰好一条定稿、线程穷尽且无外部重复。
- `SAFE_RETRY_ALLOWED` 仅用于明确未点击发送，或明确未发送且独立复核已穷尽并确认不存在回复；最多允许全新 session 重试一次。
- 只要发送可能已发生但结果不确定，`retry_allowed` 必须为 `NO`。
- `MANUAL_DELETE_REQUIRED` 只标记需要人工核对/删除，协调员本身禁止删除或修改内容。
- `REPLY_NOT_FOUND` 只有在线程穷尽时才可作为不存在证据；线程未穷尽必须视为 `VERIFICATION_INCOMPLETE`。
- 缺字段、非法枚举或矛盾输入必须 `ESCALATE_MANUAL / INVALID_OR_CONTRADICTORY_INPUT`。
- `content_modified_by_coordinator` 永远为 `NO`，`browser_calls` 与 `vision_calls` 永远为 `0`。
- 完成后调用注入的 `kanban_complete`。
