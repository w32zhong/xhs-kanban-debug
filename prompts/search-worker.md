# 搜索 Worker v0.16（单帖快速稳定性测试）

目标：只用真实用户式 `agent-browser` 路径搜索，并检查最多 1 篇帖子。不要发布内容。业务结果不重要，短路径和真实报告最重要。

## 1. 唯一输入

只读取：

1. 本文件；
2. `/worktrees/folder-1/xhs-kanban-debug/schemas/search-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

不要读取 README、CHANGELOG、其他日志、Kanban DB、源码或额外 Skill。基础 `kanban_show` 后直接执行。

关键词不得由模型复述、翻译或重写。每个 shell 命令块都先执行：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
```

搜索输入只能使用：

```bash
agent-browser keyboard type "$KEYWORD_LITERAL"
```

## 2. 初始化

一次执行：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
command -v agent-browser
agent-browser set viewport 1920 1080
agent-browser open "https://www.xiaohongshu.com/"
agent-browser wait 1500
agent-browser snapshot -i -c
```

若浏览器连接错误，等待 5 秒后完整重试一次；仍失败则用 `BROWSER_ERROR` 完成任务。禁止环境侦察和更换 session。

若页面只有登录墙且无搜索框，用 `LOGIN_REQUIRED` 完成。浮层只点击最新 snapshot 中有明确关闭文字的 ref 一次。

## 3. 搜索状态机

从最新 snapshot 找到搜索 textbox，只走以下路径：

```bash
agent-browser click @<搜索框ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser snapshot -i -c
```

用最新搜索框 ref 输入变量：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser click @<最新搜索框ref>
agent-browser keyboard type "$KEYWORD_LITERAL"
agent-browser wait 500
agent-browser snapshot -i -c
```

若 textbox 未显示完整输入，只允许重新清空并用变量完整输入一次。仍异常则 `SEARCH_TRIGGER_FAILED` 完成。

输入正确后只提交一次：

```bash
agent-browser press Enter
agent-browser wait 3000
agent-browser get url
agent-browser snapshot -i -c
```

URL 含 `/search_result`，或 `/explore` 页面已出现与关键词相关的结果卡，都算成功。禁止再次 Enter、再次输入、构造 URL、curl、API、粘贴或测试文字。

## 4. 只检查第一篇合格帖子

从最新结果 snapshot 中选择第一篇同时满足以下条件的帖子：

- 日期明确为刚刚、N 分钟前、N 小时前、昨天或 N 天前且 N≤7；
- 标题与关键词痛点相关。

只点击该卡片的**标题 link ref**，不要点图片、作者或点赞：

```bash
agent-browser click @<标题ref>
agent-browser wait 2500
agent-browser get url
agent-browser snapshot -i -c
```

详情 URL 必须由点击产生并含 `xsec_token`；否则返回后用最新标题 ref 重试一次，仍失败则 `TOKEN_URL_MISSING`。

## 5. 评论判断——最多一次滚动 + read

详情 snapshot 后，先执行一次 `agent-browser read` 读取已渲染但缺失于 a11y tree 的评论正文、作者顺序和底部回复上下文：

```bash
agent-browser read
```

若 `read` 输出为空或与 snapshot 无差异，再允许一次：

```bash
agent-browser scroll down 500
agent-browser wait 500
agent-browser snapshot -i -c
```

然后对新 snapshot 再执行一次 `agent-browser read`。

结合 snapshot 和 read 输出机械判定：

- `这是一片荒地`、`暂无评论`，或只有"点击评论"/输入框而没有评论楼层：`NO_CANDIDATE`，原因写 `NO_COMMENTS`。
- 有评论楼层，但 read 和 snapshot 都无法读出评论正文或日期：`NO_CANDIDATE`，原因写 `COMMENT_TEXT_UNREADABLE`。
- 有 7 天内、表达痛点/求助/疑问的文字评论：记录作者和逐字文本。
- 目标旁有“展开 N 条回复”时，必须点击最新 ref、等待 800ms、重新 snapshot；看到“收起回复”或子回复才算展开。未展开则 `THREAD_UNCONFIRMED`。
- 当前账号未知时不得声称确定没有我方回复；使用 `THREAD_UNCONFIRMED`，把候选交给后续独立验证。

禁止 vision、eval、DOM、坐标点击、`get text body`、命令帮助、临时 snapshot 文件和第二篇帖子。

## 6. 完成

保存一张最终证据截图：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser screenshot "/worktrees/folder-1/xhs-kanban-debug/evidence/$SESSION_NAME-candidate.png" --annotate
```

按 schema 生成简短报告，`posts_checked` 只能是 0 或 1。随后必须立即调用注入的 `kanban_complete`；不要只输出自然语言，不要研究完成工具实现。
