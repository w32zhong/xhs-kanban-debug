# 发布复核 Worker v2（复核 + 就地清理）

目标：仅在本轮 publisher 确认点击发送后，用 fresh session 复核目标楼层中的回复。发现重复或语义不匹配的回复时就地删除。

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
5. 如果目标楼层中语义相同的回复出现 2 次以上，保留最早的一条，**删除多余的重复回复**。
6. 展开入口消失且目标楼层仍无语义匹配的回复，记 `REPLY_NOT_FOUND`；达到 5 次仍未穷尽，记 `THREAD_UNCONFIRMED`。
7. 相同回复出现在其他楼层不改变目标楼层结果，但可作为 warning 记录。
8. 如果目标楼层中找到的回复与 `final_comment` 语义不一致（核心意思偏差、关键信息错误、语气方向不对），**删除该回复**并记 `MISMATCH_DELETED`。

## 删除操作

删除回复的步骤：
1. 找到要删除的回复
2. 点击该回复旁边的「···」或长按该回复，弹出操作菜单
3. 选择「删除」选项
4. 确认删除弹窗
5. 验证该回复已从楼层中消失

删除前不需要犹豫——只有 DUPLICATE_REPLY 和 MISMATCH 两种情况会触发删除，其他情况不动。

安全红线：不输入、不发送、不点赞；不用 Vision、DOM/eval 或坐标。

结果 metadata 至少包含：

```json
{
  "status": "VERIFIED | SKIPPED_NO_SEND | TARGET_FLOOR_NOT_FOUND | REPLY_NOT_FOUND | DUPLICATE_REPLY | MISMATCH_DELETED | THREAD_UNCONFIRMED | BROWSER_ERROR",
  "target_context_match": "YES | NO | UNKNOWN",
  "exact_draft_count_in_target_thread": "整数或 UNKNOWN",
  "exact_draft_found_outside_target_thread": "YES | NO | UNKNOWN",
  "expansion_clicks": 0
}
```

完成后立即 `kanban_complete`。
