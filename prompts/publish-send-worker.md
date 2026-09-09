# 精确发布 Worker v1（复用 share URL、目标楼层门禁）

目标：只在本轮定稿已批准时，打开 scout 保存的真实 share URL，精确绑定目标评论并发送一次。

只读取：

1. `./runtime/scout-result.json`；
2. `./runtime/chair-decision.json`；
3. `./prompts/xhs-reply-style.md`；
4. 本文件；
5. 任务正文中的 `OUTPUT_FILE` 与 `PARAM_FILE`。

`runtime/chair-decision.json` 的 `decision` 不是 `APPROVE`，或 `final_comment` 为空/NONE 时，立即写 `SKIPPED_NOT_APPROVED`，不得打开浏览器。

## 快速且安全的门禁

**严格走短路径：**禁止 `agent-browser --help`、`session_search`、技能/源码/HTML/DOM 探索、无关点击实验和从首页重新搜索。直接使用 scout 的 share URL。最多重新加载页面 1 次，目标回复入口最多尝试 2 次；仍无法绑定就立即写 `NEEDS_VERIFIER` 并完成，不得继续探索。

1. 从 scout 读取 `post_url`、`target_comment_author`、`target_comment_text`、`target_comment_excerpt`；从 chair 读取 `final_comment`。禁止使用 publish-target-pool 或 PARAM_FILE 中的旧目标/旧草案覆盖它们。
2. 打开浏览器前先执行本地短回复门禁：`final_comment` 超过 3 句话、超过 4 行、明显包含多个并列建议，或属于清单/步骤/教程式展开时，写 `TEXT_TOO_LONG` 并结束，不得发布。不要替委员长现场改稿。
3. 用新的 pinned browser session 直接 `agent-browser open "$POST_URL"`。这是本轮 scout 点击产生的 share URL；无需重新从首页搜索。
4. snapshot + read 锁定作者和逐字评论。作者 + 唯一前缀必须匹配。
5. 只检查目标楼层当前可见回复；若有明确“展开 N 条回复”，最多展开一次再 read。
6. **先做幂等检查：**如果目标楼层已经出现当前账号发布的 `final_comment`，视为本轮或前次尝试已经发送成功；不得再次输入或点击发送。立即写 `SEND_SUCCESS`，`send_clicked` 填 `YES`（表示本轮发送动作已发生，不表示本次重跑再次点击），reason 明确写“existing exact reply reconciled”，然后 `kanban_complete`，让最后的发布复核 task 独立确认。
7. 当前账号 UNKNOWN 不阻止首次发布。仅当目标楼层明确已有当前账号的其他回复，或存在无法判断归属的逐字重复时，写 `NEEDS_VERIFIER`，不得继续发送。
8. 点击目标一级评论自己的回复入口。优先使用明确“回复”文字；若 action row 明确按页面顺序显示两个连续动作数字，解释为“点赞数 → 回复气泡数”，可以点击第二个纯数字作为该楼层的回复入口。前提是作者 + 评论前缀已唯一锁定、该数字确属同一一级楼层，且不是子回复或帖子总评论数。每次点击后必须用 fresh read 确认出现 `回复 <目标作者>`；累计最多尝试 2 次。对象不对或仍未绑定时立即写 `NEEDS_VERIFIER` 并完成，不输入。
9. fresh read 必须出现 `回复 <目标作者>`。然后只输入一次 `final_comment`。
10. fresh snapshot 确认发送按钮 enabled；fresh editable ref 的 `get text` 必须与 `final_comment` 逐字一致。
11. 点击发送一次。**调用返回后立即**写 `runtime/publish-result.json` 并执行 `kanban_complete`：编辑器清空/重置且 URL 未异常变化时记 `SEND_SUCCESS`；点击结果不确定时记 `NEEDS_VERIFIER` 且 `send_clicked=YES`。不要继续做深度页面验证，目标楼层渲染、重复和内容一致性由最后的 `发布复核` task 负责。

不要因帖子超过 7 天、账号未知、其他楼层存在相同文本而阻止。不得 URL 构造、DOM/eval、坐标点击、Vision、重复输入或重复发送。

将 JSON 写入 `runtime/publish-result.json`：

```json
{
  "status": "SEND_SUCCESS | SKIPPED_NOT_APPROVED | TEXT_TOO_LONG | TARGET_FLOOR_NOT_FOUND | DUPLICATE_IN_TARGET_THREAD | NEEDS_VERIFIER | TEXT_MISMATCH | SEND_FAILED | BROWSER_ERROR",
  "send_clicked": "YES | NO",
  "editor_reset_after_send": "YES | NO | UNKNOWN",
  "post_url": "本轮 share URL",
  "target_comment_author": "目标作者",
  "final_comment": "本轮定稿",
  "reason": "一句话"
}
```

完成后立即 `kanban_complete`，metadata 至少包含 `status`、`send_clicked`、`output_file`。
