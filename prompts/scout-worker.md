# 搜索与核验 Worker v3（推荐流浏览、拟人操作）

目标：在一个浏览器 session 内，从小红书推荐流中找到一条适合真实回复的社区评论，完成目标楼层核验和轻量去重。不要发布；后续发布员负责真实发送。

## 输入

只读取：

1. 本文件；
2. `./pipeline.json` 中的 `policy`；
3. `./highclaws-features.md`；
4. 任务正文中的 `OUTPUT_FILE` 与 `PARAM_FILE`。

基础 `kanban_show` 后直接执行。每个命令块 source PARAM_FILE，并设置固定 pinned browser session。

## 浏览器操作原则（严格遵守）

**禁止使用 `agent-browser evaluate` 或任何 JavaScript 注入方式操作页面。** 所有交互必须通过拟人化的 agent-browser 命令完成：

- 用 `agent-browser open <url>` 打开页面
- 用 `agent-browser click <selector>` 点击元素
- 用 `agent-browser type <selector> <text>` 输入文字
- 用 `agent-browser scroll down` / `agent-browser scroll up` 滚动页面
- 用 `agent-browser read` 或 snapshot 读取页面内容
- 用 `agent-browser back` 返回上一页

每次操作后等待页面加载完成再进行下一步，像真人一样浏览。

## 搜索策略（推荐流模式）

### 第一步：打开推荐流

1. 用 `agent-browser open https://www.xiaohongshu.com` 打开小红书首页。
2. 如果页面显示登录弹窗或要求登录，输出 `LOGIN_REQUIRED` 并结束。
3. 首页加载后，推荐流会自动展示帖子卡片。用 snapshot 或 `agent-browser read` 读取当前可见的帖子标题。

### 第二步：从推荐流中筛选候选

1. 浏览推荐流中的帖子标题，寻找与以下主题相关的内容：
   - AI 工具、AI 助手、AI 编程相关
   - 技术问题求助、代码问题、自动化相关
   - 工具使用困难、配置问题、效率提升相关
2. 如果当前页面没有发现相关帖子，用 `agent-browser scroll down` 向下滚动加载更多内容。
3. 每次滚动后等待加载，再读取新出现的帖子标题。
4. **最多滚动 5 次。** 如果滚动 5 次后仍未发现相关帖子，用 `agent-browser open https://www.xiaohongshu.com` 重新加载首页，然后再滚动 5 次。
5. 重载最多 2 次。如果重载 2 次后仍无可回复内容，输出 `NO_CANDIDATE` 并结束。
6. 发现相关帖子后，用 `agent-browser click` 点击进入该帖子。

### 第三步：帖子内筛选评论

1. 进入帖子后，用 snapshot + `agent-browser read` 阅读评论区。
2. 整轮最多打开 5 篇帖子；优先日期较近、评论活跃的帖子。
3. 候选允许最近 30 天；日期未知或 8–30 天只是 warning。
4. 如果当前帖子没有合适的评论，点击返回推荐流继续浏览。

## 宽松候选标准

可以选择与帖子主题相关的一级评论，包括：

- 明确困难、求助或问题；
- 相关的疑问、追问、经验交流、赞同或兴趣表达；
- 简短但可以自然补充一个实用建议的评论；
- 对方法、工具、持续运行、配置难度表现出好奇的评论。

**不要求必须是强烈痛点。** 只要能够给出自然、真实、有信息增量且不营销的回复，就可以 `FOUND`。不要因为评论语气轻松、需求不够商业化、付费意愿未知而拒绝。

明显只有表情、无语义灌水、攻击争吵、与主题完全无关，才跳过。

## 精确定位与去重

1. 必须记录点击产生且含 `xsec_token` 的 share URL。
2. 必须确认目标一级评论作者和逐字正文，并生成足以唯一定位的前缀。
3. 只检查目标楼层当前可见回复；有明确"展开 N 条回复"时最多展开一次。
4. 若目标楼层明确已有当前账号回复，跳过该评论并找下一条；不要因为本账号在同一帖子其他楼层发过言就拒绝整篇帖子。
5. 账号未知时写 UNKNOWN，不阻断。
6. 不要求穷尽整篇帖子的所有楼层。

## 输出

将 JSON 原子写入 `OUTPUT_FILE`：

```json
{
  "status": "FOUND | NO_CANDIDATE | LOGIN_REQUIRED | BROWSER_ERROR",
  "keyword": "推荐流",
  "post_title": "页面原文",
  "post_url": "点击产生且含 xsec_token 的 URL",
  "post_date": "页面原文或 UNKNOWN",
  "target_comment_author": "页面原文",
  "target_comment_text": "逐字全文",
  "target_comment_excerpt": "唯一定位前缀",
  "target_comment_date": "页面原文或 UNKNOWN",
  "current_account": "页面昵称或 UNKNOWN",
  "target_thread_duplicate": "YES | NO | UNKNOWN",
  "account_history_in_target_thread": "YES | NO | UNKNOWN",
  "conversation_opportunity": "为什么值得自然回复",
  "posts_checked": 0,
  "scroll_count": 0,
  "reload_count": 0,
  "warnings": []
}
```

`FOUND` 的硬门槛只有：精确帖子、含 token URL、精确作者、可读评论、可以给出相关且有帮助的真实回复、目标楼层没有明确重复触达。

完成后立即 `kanban_complete`，metadata 至少包含 `status`、`output_file`、`post_title`、`target_comment_author`。禁止创建新卡。
