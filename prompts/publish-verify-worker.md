# 发布复核 Worker v1（只复核本轮真实发送）

目标：仅在本轮 publisher 确认点击发送后，用 fresh session 复核目标楼层中的逐字回复。只读，不修改内容。

只读取：

1. `./runtime/scout-result.json`；
2. `./runtime/chair-decision.json`；
3. `./runtime/publish-result.json`；
4. 本文件；
5. 任务正文中的 `PARAM_FILE`。

若 `runtime/publish-result.json` 的 `status` 不是 `SEND_SUCCESS`，或 `send_clicked` 不是 `YES`，立即完成为 `SKIPPED_NO_SEND`。禁止打开浏览器，也不得把历史上已存在的同文回复当成本轮成功。

## 快速复核

1. 用 fresh pinned session 直接打开 scout 的 `post_url`，不重新搜索。
2. snapshot + read 精确锁定 `target_comment_author` + `target_comment_excerpt`。
3. 查看目标楼层当前可见子回复；若定稿未出现且存在明确"展开 N 条回复"或"展开更多回复"，累计最多点击 5 次，每次用 fresh ref。
4. 用肉眼判断目标楼层中是否有语义与 `final_comment` 一致的回复——不要求逐字相同，只要核心意思、关键信息、语气方向一致即可判定为 `VERIFIED`。
5. 如果目标楼层中语义相同的回复出现 2 次以上，记 `DUPLICATE_REPLY`。
6. 展开入口消失且目标楼层仍无语义匹配的回复，记 `REPLY_NOT_FOUND`；达到 5 次仍未穷尽，记 `THREAD_UNCONFIRMED`。
7. 相同回复出现在其他楼层不改变目标楼层结果，但可作为 warning 记录。

安全红线：不输入、不发送、不点赞、不删除；不用 Vision、DOM/eval 或坐标。

结果 metadata 至少包含：

```json
{
  "status": "VERIFIED | SKIPPED_NO_SEND | TARGET_FLOOR_NOT_FOUND | REPLY_NOT_FOUND | DUPLICATE_REPLY | THREAD_UNCONFIRMED | BROWSER_ERROR",
  "target_context_match": "YES | NO | UNKNOWN",
  "exact_draft_count_in_target_thread": "整数或 UNKNOWN",
  "exact_draft_found_outside_target_thread": "YES | NO | UNKNOWN",
  "expansion_clicks": 0
}
```

完成后立即 `kanban_complete`。
