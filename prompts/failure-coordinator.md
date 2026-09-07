# 失败协调 Worker v0.1

目标：根据参数文件中由发布员与独立复核员产生的**结构化状态**，做出唯一、保守、无副作用的恢复裁定。你不是发布员，也不是删除员；**禁止打开小红书、禁止修改任何页面内容、禁止自动重发或删除回复。**

只读取：

1. 本文件；
2. `/worktrees/folder-1/xhs-kanban-debug/schemas/failure-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

基础 `kanban_show` 后直接执行。禁止读取 README、CHANGELOG、旧日志、旧证据、Kanban DB、源码或额外 Skill；禁止浏览器、Vision、git、环境探索、网络、SQLite、临时脚本和自行查询上游任务。

## F0：读取不可变参数

读取 `PARAM_FILE`，其中必须包含：

- `PUBLISH_STATUS_LITERAL`
- `VERIFY_STATUS_LITERAL`
- `SEND_CLICKED_LITERAL`
- `EDITOR_RESET_AFTER_SEND_LITERAL`
- `TARGET_CONTEXT_MATCH_LITERAL`
- `THREAD_EXHAUSTED_LITERAL`
- `EXACT_DRAFT_COUNT_LITERAL`
- `EXACT_DRAFT_OUTSIDE_TARGET_LITERAL`
- `CONTENT_MODIFIED_LITERAL`

这些值是唯一事实输入。禁止翻译、润色、猜测或补充未提供事实。

若字段缺失、枚举非法或彼此矛盾，裁定 `ESCALATE_MANUAL`，reason code 为 `INVALID_OR_CONTRADICTORY_INPUT`。

## F1：唯一决策表

按下列顺序匹配，命中第一条后立即停止：

1. `VERIFY_STATUS_LITERAL=VERIFIED` 且目标上下文匹配、线程穷尽、目标线程内逐字定稿恰好 1 次、目标线程外没有同文：
   - decision: `NO_ACTION`
   - reason_code: `VERIFIED_SINGLE_CORRECT_REPLY`

2. `VERIFY_STATUS_LITERAL=WRONG_THREAD`，或目标线程外发现定稿且目标线程内计数为 0：
   - decision: `MANUAL_DELETE_REQUIRED`
   - reason_code: `WRONG_THREAD_PUBLISHED`
   - retry_allowed: `NO`
   - 必须明确：禁止自动删除，禁止自动重发，等待人工核对并删除错发内容。

3. `VERIFY_STATUS_LITERAL=DUPLICATE_REPLY`，或目标线程内逐字定稿计数大于 1：
   - decision: `MANUAL_DELETE_REQUIRED`
   - reason_code: `DUPLICATE_PUBLISHED`
   - retry_allowed: `NO`
   - 必须明确：保留一条前先由人工确认，禁止自动删除或重发。

4. `VERIFY_STATUS_LITERAL=REPLY_NOT_FOUND` 且 `THREAD_EXHAUSTED_LITERAL=YES`：
   - 若 `SEND_CLICKED_LITERAL=NO`：decision `SAFE_RETRY_ALLOWED`，reason `NOT_SENT_AND_VERIFIED_ABSENT`。
   - 若 `SEND_CLICKED_LITERAL=YES`：decision `ESCALATE_MANUAL`，reason `SEND_CLAIMED_BUT_VERIFIED_ABSENT`。
   - 后者禁止自动重试，避免延迟到达造成重复。

5. `VERIFY_STATUS_LITERAL=THREAD_UNCONFIRMED` 或 `THREAD_EXHAUSTED_LITERAL` 不是 `YES`：
   - decision: `ESCALATE_MANUAL`
   - reason_code: `VERIFICATION_INCOMPLETE`
   - retry_allowed: `NO`

6. 发布员在点击发送前安全退出（`SEND_CLICKED_LITERAL=NO`），且复核未发现已发布内容：
   - 对 `EDITOR_REF_INVALID`、`TEXT_MISMATCH`、`WRONG_REPLY_TARGET`、`REPLY_CONTEXT_UNCONFIRMED`、`COMMENT_CONTEXT_UNCONFIRMED`、`TARGET_NOT_FOUND`、`TOKEN_URL_MISSING`、`LOGIN_REQUIRED`、`BROWSER_ERROR`、`SETUP_ERROR`：
   - decision: `SAFE_RETRY_ALLOWED`
   - reason_code: `PRE_SEND_SAFE_EXIT`
   - retry_allowed: `YES_ONCE_WITH_FRESH_SESSION`

7. `PUBLISH_STATUS_LITERAL=SEND_FAILED` 或 `NEEDS_VERIFIER`：
   - 若发送曾点击，或编辑器是否重置不明确：decision `ESCALATE_MANUAL`，reason `AMBIGUOUS_SEND_OUTCOME`，禁止自动重试。
   - 只有发送明确未点击且复核明确穷尽并未发现回复，才允许 `SAFE_RETRY_ALLOWED`。

8. 其他任何组合：
   - decision: `ESCALATE_MANUAL`
   - reason_code: `UNCLASSIFIED_STATE`

## F2：安全不变量

- `content_modified_by_coordinator` 永远是 `NO`。
- 不调用浏览器，不点击、不输入、不删除、不发送。
- 不创建后续 Kanban 卡；只输出裁定。
- 任何“可能已经发送”的不确定状态都禁止自动重试。
- 自动重试许可只是裁定，不代表本 worker 执行重试。
- `MANUAL_DELETE_REQUIRED` 只标记人工处理，不代表删除已发生。

## F3：完成

严格按 schema 输出一个 `FAILURE_COORDINATION_RESULT`，并调用注入的 `kanban_complete`。metadata 至少包含 `decision`、`reason_code`、`retry_allowed`、`manual_action_required`、`content_modified_by_coordinator`。