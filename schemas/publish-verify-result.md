# 发布后独立复核结果固定格式

```text
PUBLISH_VERIFY_RESULT
status: VERIFIED | TARGET_NOT_FOUND | TOKEN_URL_MISSING | TARGET_FLOOR_NOT_FOUND | THREAD_UNCONFIRMED | REPLY_NOT_FOUND | WRONG_THREAD | DUPLICATE_REPLY | LOGIN_REQUIRED | BROWSER_ERROR | SETUP_ERROR
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
content_modified: NO
vision_calls: 0
evidence_file: <绝对路径或 NONE>
obstacles:
  - <无则 NONE>
```

规则：

- `VERIFIED` 仅用于：作者与目标评论前缀匹配，逐字定稿位于该目标一级评论的线程内，且该线程中的逐字定稿恰好出现一次。
- 状态机单向执行：V0→V1→V2→V3→V4→V5；V0-V3 每步最多一次。第一次 `read` 后禁止回到 V0-V3。任务最多执行 1 次搜索、打开 1 篇帖子。V4 可为穷尽目标线程而循环点击其明确文字 `展开更多回复`，累计展开点击最多 100 次；每次点击后 fresh snapshot，每 10 次或线程穷尽时 fresh read。
- 如果页面结构无法按规则确认，必须返回最接近的安全失败状态；禁止从头重跑来消除不确定性。
- `REPLY_NOT_FOUND`：目标楼层明确、目标线程已穷尽，且目标线程内逐字定稿出现 0 次。
- `DUPLICATE_REPLY`：目标线程内逐字定稿出现超过 1 次。
- `WRONG_THREAD`：逐字定稿在页面其他楼层出现，但目标线程内没有。
- `THREAD_UNCONFIRMED`：无法可靠确定子回复归属/展开状态，或目标线程仍有未展开回复。线程未穷尽时不得用 `REPLY_NOT_FOUND`。
- 复核必须完全独立，`publisher_claim_used` 永远为 `NO`。
- 禁止修改页面内容，`content_modified` 永远为 `NO`，`vision_calls` 永远为 `0`。
- 完成后调用注入的 `kanban_complete`。
