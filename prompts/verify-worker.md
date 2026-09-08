# 独立验证 Worker v0.3（零 Vision、零常规截图）

目标：从小红书首页按真实用户路径重新搜索并独立验证 1 篇指定帖子。不要发布内容，不依赖上一张任务、旧评论或旧浏览器 session。

## 输入与上下文上限

只读取：

1. 本文件；
2. `./schemas/verify-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

不要读取搜索任务日志、旧证据、README、CHANGELOG、Kanban DB、源码或额外 Skill。基础 `kanban_show` 后直接执行。

每个 shell 命令块先执行：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
```

禁止在推理中翻译或重写 `$KEYWORD_LITERAL`、`$TARGET_TITLE_LITERAL`。输入搜索框只能使用 shell 变量。

## 状态 V0：初始化

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

浏览器连接错误只允许等待 5 秒后完整重试一次；仍失败则 `BROWSER_ERROR`。禁止环境侦察和换 session。

## 状态 V1：真实用户搜索

从最新 snapshot 找搜索 textbox：

```bash
agent-browser click @<搜索框ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser snapshot -i -c
```

用最新 ref 输入变量并提交一次：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser click @<最新搜索框ref>
agent-browser keyboard type "$KEYWORD_LITERAL"
agent-browser wait 500
agent-browser snapshot -i -c
agent-browser press Enter
agent-browser wait 3000
agent-browser get url
agent-browser snapshot -i -c
```

输入异常只允许完整清空并用变量重输一次。禁止构造 URL、curl、API、粘贴、测试文字、重复 Enter。

## 状态 V2：定位指定标题

在结果 snapshot 中查找标题逐字等于 `$TARGET_TITLE_LITERAL` 的标题 link。禁止凭相似语义选择别的帖子。

- 当前 snapshot 找到：点击该标题 link。
- 没找到：只允许 `agent-browser scroll down 600` 一次并重新 snapshot。
- 仍找不到：以 `TARGET_NOT_FOUND` 完成。

点击后：

```bash
agent-browser click @<目标标题ref>
agent-browser wait 2500
agent-browser get url
agent-browser snapshot -i -c
```

必须由点击产生含 `xsec_token` 的详情 URL。否则返回结果页，用最新 ref 重试一次；仍失败则 `TOKEN_URL_MISSING`。

## 状态 V3：独立核验上下文与评论区

只允许最多两次 `scroll down 500`，每次重新 snapshot。不得把 snapshot 写入 `/tmp`，不得用 grep/awk/sed 二次解析，直接阅读工具输出。

**使用 `agent-browser read` 获取页面可读文本。** 当 snapshot 只暴露作者和 action row、没有评论正文时，执行一次 `agent-browser read`。它能读取已渲染但缺失于 a11y tree 的评论正文、作者顺序和底部回复上下文。本阶段 Vision 配额固定为 0。

依次记录：帖子标题、作者、可见发布日期，以及评论区状态：

1. 明确看到“这是一片荒地”或“暂无评论”：`NO_COMMENTS_CONFIRMED`。
2. 只有“点击评论”/输入框且没有任何评论作者+回复楼层：`NO_COMMENTS_UNCONFIRMED`，不得断言确实无评论。
3. 有评论楼层，但 snapshot 与 read 均无法逐字读出正文或日期：`COMMENT_TEXT_UNREADABLE`，不得用截图或 Vision 猜测。
4. 有目标文字评论：记录作者、逐字文本和日期。
5. 任意评论旁有“展开 N 条回复”：必须用最新 ref 展开，等待 800ms 后重新 snapshot；看到“收起回复”或子回复作者才算成功。
6. 页面任意已展开楼层若明确出现当前账号的历史评论/回复，整帖 `REJECT_OUR_HISTORY`。当前账号无法确认时写 `ACCOUNT_UNKNOWN`，不得声称已排除我方历史回复。

禁止 Vision、截图、eval、DOM、坐标点击、`get text body`、临时文件、查看命令帮助和访问第二篇帖子。证据不足时必须 fail-closed，不得降低验证门槛。

## 状态 V4：分享 URL 与完成

`get url` 得到由点击产生、含 `xsec_token` 的当前详情 URL，作为 share URL。`evidence_file` 固定写 `NONE`，`vision_calls` 固定写 `0`。按 schema 输出，随后立即调用注入的 `kanban_complete`。任何状态都必须完成任务，不要研究完成工具。
