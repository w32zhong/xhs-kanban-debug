# 发布输入演练结果固定格式

```text
PUBLISH_INPUT_REHEARSAL_RESULT
status: INPUT_PATH_READY | NEEDS_VERIFIER | TARGET_NOT_FOUND | TOKEN_URL_MISSING | COMMENT_TARGET_NOT_FOUND | COMMENT_CONTEXT_UNCONFIRMED | WRONG_ELEMENT_CLICKED | REPLY_CONTEXT_UNCONFIRMED | WRONG_REPLY_TARGET | EDITOR_REF_INVALID | TEXT_MISMATCH | CLEAR_UNCONFIRMED | LOGIN_REQUIRED | BROWSER_ERROR | SETUP_ERROR
session_name: <session>
share_url: <点击产生且含 xsec_token；无则 NONE>
target_title: <指定标题>
target_comment_author: <指定作者>
target_comment_excerpt: <指定评论唯一前缀>
target_floor_match: AUTHOR_AND_EXCERPT | NO | UNKNOWN
reply_context_evidence_mode: A11Y | VISUAL_EVIDENCE | NONE
reply_entry_kind: TEXT_REPLY | NUMBERED_REPLY_BUBBLE | NONE
vision_calls: 0 | 1 | 2
vision_format_retries: 0 | 1 | 2
reply_target_after_type_check: A11Y | PRECHECK_CARRIED_FORWARD | UNKNOWN
draft_input_method: PARAM_FILE_VARIABLE
text_typed_once: YES | NO
text_exact_match: YES | NO | UNKNOWN
send_enabled_after_type: YES | NO | UNKNOWN
send_clicked: NO
escape_after_type: NO
editor_cleared: YES | NO | NOT_APPLICABLE
send_disabled_after_clear: YES | NO | UNKNOWN
evidence_files:
  - <绝对路径；无则 NONE>
obstacles:
  - <无则 NONE>
```

规则：

- `INPUT_PATH_READY` 只用于：目标楼层的作者和唯一评论前缀均匹配、回复对象已明确、定稿通过参数变量输入一次、文字逐字匹配、发送按钮已 enabled、随后完整清空且发送重新 disabled。
- `NUMBERED_REPLY_BUBBLE` 只允许用于一级楼层 action row 中已确认的第二个数字动作（前一个是点赞数），并且点击后视觉核验底部 `回复 <目标作者>` 成功；不能用于 `展开 N 条回复`。
- `vision_calls: 2` 仅允许同一作者存在多个一级楼层：第一次点击前区分正文前缀和对应 action row，第二次点击后核验回复对象。普通/唯一作者仍不得超过 1 次。
- `vision_format_retries` 只统计 Vision 完全未回答指定字段时，对同一截图、同一问题逐字不变的重试；不得用它重问不确定的业务结论。普通场景最多 1，双阶段场景每阶段最多 1。
- 所有状态 `send_clicked` 都必须为 `NO`，输入后 `escape_after_type` 必须为 `NO`。
- 输入后的任何失败都必须先尝试 Control+A + Backspace 清空一次；不得第二次输入，不得点击取消或刷新重做。
- 完成后调用注入的 `kanban_complete`。