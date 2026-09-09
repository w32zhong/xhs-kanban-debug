# 发布后独立复核结果固定格式

```text
PUBLISH_VERIFY_RESULT
status: VERIFIED | DUPLICATES_DELETED | MISMATCH_DELETED | TARGET_NOT_FOUND | TOKEN_URL_MISSING | TARGET_FLOOR_NOT_FOUND | THREAD_UNCONFIRMED | REPLY_NOT_FOUND | WRONG_THREAD | DUPLICATE_REPLY | LOGIN_REQUIRED | BROWSER_ERROR | SETUP_ERROR
session_name: <session>
posts_opened: <0-1>
target_title: <参数指定标题>
share_url: <点击产生且含 xsec_token；无则 NONE>
target_comment_author: <参数指定作者>
target_comment_excerpt: <参数指定前缀>
target_context_match: YES | NO | UNKNOWN
thread_action: THREAD_ALREADY_VISIBLE | EXPANDED_ONCE | NONE
thread_expansion_confirmed: YES | NO | NOT_NEEDED
thread_exhausted: YES | NO | UNKNOWN
thread_expansion_clicks: <整数>
reply_text_source: READ_TEXT | NONE
draft_exact_match: YES | NO | UNKNOWN
exact_draft_count_in_target_thread: <整数或 UNKNOWN>
exact_draft_found_outside_target_thread: YES | NO | UNKNOWN
publisher_claim_used: NO
deletions_performed: <非负整数>
content_modified: YES | NO
vision_calls: 0
evidence_file: NONE
obstacles:
  - <无则 NONE>
```

规则：

- `VERIFIED` 仅用于：目标上下文匹配，语义与定稿一致的回复恰好出现一次，且没有执行删除。
- `DUPLICATES_DELETED`：只删除本轮发布造成的多余重复，删除至少 1 条，并确认目标线程最终只剩 1 条语义匹配回复。
- `MISMATCH_DELETED`：只删除可确认由本轮 publisher 新发、但与定稿语义不一致的回复，并确认它已经消失。
- 状态机单向执行：只打开 scout 保存的目标 URL，不重新搜索；累计最多点击 5 次明确文字的“展开回复/展开更多回复”，每次都使用 fresh ref，随后用 fresh read 判断目标线程是否穷尽。
- `REPLY_NOT_FOUND`：目标楼层明确、目标线程已穷尽，且目标线程内语义与定稿一致的回复出现 0 次。
- `DUPLICATE_REPLY`：目标线程内语义与定稿一致的回复超过 1 次，但删除失败或无法确认最终只剩 1 条。
- `WRONG_THREAD`：语义与定稿一致的回复出现在页面其他楼层，但目标线程内没有。
- `THREAD_UNCONFIRMED`：无法可靠确定子回复归属/展开状态，或目标线程仍有未展开回复。线程未穷尽时不得用 `REPLY_NOT_FOUND`。
- 复核必须完全独立，`publisher_claim_used` 永远为 `NO`。
- 页面修改仅限上述两种有界清理。`DUPLICATES_DELETED` 或 `MISMATCH_DELETED` 时 `content_modified: YES` 且 `deletions_performed >= 1`；其他状态必须为 `content_modified: NO`、`deletions_performed: 0`。禁止删除历史回复、其他账号回复或其他楼层内容。`vision_calls` 永远为 `0`，`evidence_file` 永远为 `NONE`。
- 完成后调用注入的 `kanban_complete`。
