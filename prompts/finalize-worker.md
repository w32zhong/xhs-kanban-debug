# 协调与清理 Worker v0.2

目标：在发布后独立复核完成后，用**同一个 worker**完成两件事：

1. 根据发布员与复核员的结构化状态，做出唯一、保守的恢复裁定；
2. 清理本轮运行时文件与浏览器标签页。

禁止发布、重发、删除回复、点赞或修改小红书内容。清理只针对本地临时产物与浏览器标签页。

## 1. 唯一输入

只读取：

1. 本文件；
2. `./schemas/finalize-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

基础 `kanban_show` 后直接执行。禁止读取 README、CHANGELOG、旧日志、旧证据、Kanban DB、源码或额外 Skill；禁止 Vision、git、网络 API、SQLite 和自行查询上游任务。

`PARAM_FILE` 必须包含：

- `PUBLISH_STATUS_LITERAL`
- `VERIFY_STATUS_LITERAL`
- `SEND_CLICKED_LITERAL`
- `EDITOR_RESET_AFTER_SEND_LITERAL`
- `TARGET_CONTEXT_MATCH_LITERAL`
- `THREAD_EXHAUSTED_LITERAL`
- `EXACT_DRAFT_COUNT_LITERAL`
- `EXACT_DRAFT_OUTSIDE_TARGET_LITERAL`
- `CONTENT_MODIFIED_LITERAL`

可选：

- `RUN_PREFIX_LITERAL`：本轮运行时文件前缀，例如 `xhs-023203-`；缺失时禁止广泛删除文件。
- `ARCHIVE_BOARD_LITERAL`：`YES|NO`。本 worker **不归档自己的当前看板**，只在结果中记录请求；外部调度者须在本卡完成后归档。

字段缺失、枚举非法或彼此矛盾时，协调裁定为 `ESCALATE_MANUAL / INVALID_OR_CONTRADICTORY_INPUT`，但仍继续执行安全的标签页清理；文件清理仅在 `RUN_PREFIX_LITERAL` 合法时执行。

## 2. 协调决策表

按顺序匹配，命中第一条即停止：

1. 复核为 `VERIFIED`，且目标上下文匹配、线程穷尽、目标线程内逐字定稿恰好 1 次、目标线程外没有同文：
   - decision: `NO_ACTION`
   - reason_code: `VERIFIED_SINGLE_CORRECT_REPLY`
   - retry_allowed: `NO`

2. 复核为 `WRONG_THREAD`，或目标线程外发现定稿且目标线程内计数为 0：
   - decision: `MANUAL_DELETE_REQUIRED`
   - reason_code: `WRONG_THREAD_PUBLISHED`
   - retry_allowed: `NO`

3. 复核为 `DUPLICATE_REPLY`，或目标线程内逐字定稿计数大于 1：
   - decision: `MANUAL_DELETE_REQUIRED`
   - reason_code: `DUPLICATE_PUBLISHED`
   - retry_allowed: `NO`

4. 复核为 `REPLY_NOT_FOUND` 且线程已穷尽：
   - 未点击发送：`SAFE_RETRY_ALLOWED / NOT_SENT_AND_VERIFIED_ABSENT / YES_ONCE_WITH_FRESH_SESSION`
   - 曾点击发送：`ESCALATE_MANUAL / SEND_CLAIMED_BUT_VERIFIED_ABSENT / NO`

5. 复核为 `THREAD_UNCONFIRMED`，或线程未穷尽：
   - `ESCALATE_MANUAL / VERIFICATION_INCOMPLETE / NO`

6. 发布员在发送前安全退出，复核已确认不存在回复：
   - `SAFE_RETRY_ALLOWED / PRE_SEND_SAFE_EXIT / YES_ONCE_WITH_FRESH_SESSION`

7. 发布结果不明确，且发送可能已点击：
   - `ESCALATE_MANUAL / AMBIGUOUS_SEND_OUTCOME / NO`

8. 其他组合：
   - `ESCALATE_MANUAL / UNCLASSIFIED_STATE / NO`

安全不变量：协调员永远不自动重发、不自动删除公开内容；任何“可能已发送”的不确定状态都禁止自动重试。

## 3. 清理本轮文件

先读取并验证 `RUN_PREFIX_LITERAL`：

- 必须以 `xhs-` 开头；
- 只允许字母、数字、连字符和下划线；
- 不得为空、不得包含 `/`、`.`、空格或 shell 元字符。

合法时，只删除与本轮前缀匹配的文件，不使用无前缀 `*`：

```bash
rm -f ./evidence/${RUN_PREFIX_LITERAL}*.png
rm -f ./logs/${RUN_PREFIX_LITERAL}*-watch.log
rm -f ./runtime-params/${RUN_PREFIX_LITERAL}*.sh
rm -f ./runtime-params/${RUN_PREFIX_LITERAL}*.txt
rm -f ./roundtable/${RUN_PREFIX_LITERAL}*.md
```

允许删除通用状态指针：

```bash
rm -f ./current-run.json ./full-e2e-current.json
```

禁止删除：

- `prompts/`、`schemas/`、`pipeline.json`、`publish-target-pool.json`；
- canonical `roundtable/reviewer-a.md`、`reviewer-b.md`、`chair-final.md`；
- 不属于本轮前缀的 evidence、日志或参数文件；
- `.git/` 及任何源码。

若前缀缺失或非法，文件清理状态记为 `SKIPPED_UNSAFE_PREFIX`，不得扩大删除范围。

## 4. 清理浏览器标签页

执行一次：

```bash
agent-browser tab list --json
```

关闭除 Kanban UI 以外的全部普通页面标签。Kanban UI 判定：标题为 `Hermes Kanban`，或 URL 明确为当前 Kanban UI。每次关闭使用返回的 `tabId`：

```bash
agent-browser tab close <tabId>
```

然后再次 `tab list --json` 验证。禁止关闭 Kanban UI；禁止导航、点击页面内容或打开新标签。

## 5. 看板归档边界

本 worker 不执行 `hermes kanban boards rm`，因为归档当前看板后可能导致本卡无法 `kanban_complete`。若 `ARCHIVE_BOARD_LITERAL=YES`，只在结果中输出 `board_archive_requested: YES`；外部调度者在看到本卡完成后再归档。

## 6. 完成

严格按 `./schemas/finalize-result.md` 输出一个 `FINALIZE_RESULT`，随后调用注入的 `kanban_complete`。metadata 至少包含：

- `decision`
- `reason_code`
- `retry_allowed`
- `manual_action_required`
- `content_modified_by_coordinator: NO`
- `files_cleanup_status`
- `files_deleted_count`
- `tabs_closed_count`
- `remaining_tabs`
- `board_archive_requested`
