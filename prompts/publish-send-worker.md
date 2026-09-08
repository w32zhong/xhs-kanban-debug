# 精确发布 Worker v1（复用 share URL、目标楼层门禁）

目标：只在本轮定稿已批准时，打开 scout 保存的真实 share URL，精确绑定目标评论并发送一次。

只读取：

1. `./runtime/scout-result.json`；
2. `./runtime/chair-decision.json`；
3. 本文件；
4. 任务正文中的 `OUTPUT_FILE` 与 `PARAM_FILE`。

`runtime/chair-decision.json` 的 `decision` 不是 `APPROVE`，或 `final_comment` 为空/NONE 时，立即写 `SKIPPED_NOT_APPROVED`，不得打开浏览器。

## 快速且安全的门禁

1. 从 scout 读取 `post_url`、`target_comment_author`、`target_comment_text`、`target_comment_excerpt`；从 chair 读取 `final_comment`。禁止使用 publish-target-pool 或 PARAM_FILE 中的旧目标/旧草案覆盖它们。
2. 用新的 pinned browser session 直接 `agent-browser open "$POST_URL"`。这是本轮 scout 点击产生的 share URL；无需重新从首页搜索。
3. snapshot + read 锁定作者和逐字评论。作者 + 唯一前缀必须匹配。
4. 只检查目标楼层当前可见回复；若有明确“展开 N 条回复”，最多展开一次再 read。
5. 当前账号 UNKNOWN 不阻止发布。仅当目标楼层明确已有当前账号回复，或目标楼层已存在 `final_comment` 逐字重复时停止。
6. 点击目标一级评论自己的明确“回复”文字入口；若唯一入口是纯数字且图标语义不清，不猜，返回 `NEEDS_VERIFIER`。
7. fresh read 必须出现 `回复 <目标作者>`。然后只输入一次 `final_comment`。
8. fresh snapshot 确认发送按钮 enabled；fresh editable ref 的 `get text` 必须与 `final_comment` 逐字一致。
9. 点击发送一次。发送后编辑器清空/重置且 URL 未异常变化，记为 `SEND_SUCCESS`。

不要因帖子超过 7 天、账号未知、其他楼层存在相同文本而阻止。不得 URL 构造、DOM/eval、坐标点击、Vision、重复输入或重复发送。

将 JSON 写入 `runtime/publish-result.json`：

```json
{
  "status": "SEND_SUCCESS | SKIPPED_NOT_APPROVED | TARGET_FLOOR_NOT_FOUND | DUPLICATE_IN_TARGET_THREAD | NEEDS_VERIFIER | TEXT_MISMATCH | SEND_FAILED | BROWSER_ERROR",
  "send_clicked": "YES | NO",
  "editor_reset_after_send": "YES | NO | UNKNOWN",
  "post_url": "本轮 share URL",
  "target_comment_author": "目标作者",
  "final_comment": "本轮定稿",
  "reason": "一句话"
}
```

完成后立即 `kanban_complete`，metadata 至少包含 `status`、`send_clicked`、`output_file`。
