# 搜索与核验 Worker v1（动态候选、单次浏览）

目标：在一个浏览器 session 内完成搜索、候选选择、目标评论核验和轻量去重，最多检查 3 篇帖子。不要发布。

## 输入

只读取：

1. 本文件；
2. `./pipeline.json` 中的 `search_keywords` 与 `policy`；
3. `./highclaws-features.md`；
4. 任务正文中的 `OUTPUT_FILE` 与 `PARAM_FILE`。

基础 `kanban_show` 后直接执行。每个命令块先 source PARAM_FILE，并设置固定 browser session。

## 快速路径

1. 打开小红书首页，snapshot 一次。
2. 依次使用 `search_keywords`。每个关键词最多搜索一次；若结果明显无关，切换下一个关键词。
3. 每个关键词按页面顺序检查结果，整轮最多打开 3 篇帖子。
4. 候选帖子允许最近 30 天。日期不精确但明确显示“本月/若干周前”也可保留为 WARN，不因超过 7 天自动拒绝。
5. 在详情页使用 `agent-browser read`。选择一条明确表达以下任一需求的一级评论：
   - 任务中断、续跑、进度保存；
   - 不会写代码、不会配置；
   - 电脑常开、远程操作或维护麻烦。
6. 必须确认目标评论作者和逐字正文。评论日期未知是 WARN，不是自动失败。
7. 账号昵称无法从页面确认时写 `UNKNOWN`，但不自动拒绝。只检查目标楼层当前可见回复，并最多点击一次明确的“展开 N 条回复”。
8. 若目标楼层中明确出现当前账号昵称的历史回复，或已存在拟定回复的逐字重复，拒绝该候选并继续下一篇。
9. 不要求穷尽整篇帖子的所有楼层，也不因相同文本出现在其他楼层自动拒绝；发布只绑定当前目标楼层。

## 输出

将以下 JSON 原子写入任务指定的 `OUTPUT_FILE`：

```json
{
  "status": "FOUND | NO_CANDIDATE | LOGIN_REQUIRED | BROWSER_ERROR",
  "keyword": "逐字搜索词",
  "post_title": "页面原文",
  "post_url": "点击产生且含 xsec_token 的 URL",
  "post_date": "页面原文或 UNKNOWN",
  "target_comment_author": "页面原文",
  "target_comment_text": "逐字全文",
  "target_comment_excerpt": "足以唯一定位的逐字前缀",
  "target_comment_date": "页面原文或 UNKNOWN",
  "current_account": "页面昵称或 UNKNOWN",
  "target_thread_duplicate": "YES | NO | UNKNOWN",
  "account_history_in_target_thread": "YES | NO | UNKNOWN",
  "pain_point": "一句话",
  "posts_checked": 0,
  "warnings": []
}
```

`FOUND` 的硬门槛只有：精确帖子、含 token URL、精确目标作者、可读目标评论、明确痛点。账号未知和评论日期未知只进入 warnings。

完成后立即 `kanban_complete`，metadata 至少包含 `status`、`output_file`、`post_title`、`target_comment_author`。禁止创建新卡。
