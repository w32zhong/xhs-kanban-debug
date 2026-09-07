# 发布员 Worker v0.2（无发送演练）

目标：用真实用户式浏览器路径重新找到指定帖子和指定评论楼层，激活该楼层的“回复”上下文，验证编辑器确实绑定目标；**不得输入或发送任何文字**。

这是一张发布机械路径演练卡，不发布业务结果。只读取：

1. 本文件；
2. `/worktrees/folder-1/xhs-kanban-debug/schemas/publish-rehearsal-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

不要读取 README、CHANGELOG、旧任务日志、Kanban DB、源码、圆桌意见或额外 Skill。基础 `kanban_show` 后直接执行。

每个 shell 命令块先执行：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
```

不得在推理中翻译或重写 `$KEYWORD_LITERAL`、`$TARGET_TITLE_LITERAL`、`$TARGET_COMMENT_AUTHOR_LITERAL`。

## P0 初始化

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

连接错误只允许等待 5 秒后完整重试一次；仍失败则 `BROWSER_ERROR` 完成。禁止环境侦察和更换 session。

## P1 真实用户搜索

从最新 snapshot 找搜索 textbox：

```bash
agent-browser click @<搜索框ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser snapshot -i -c
```

用最新 ref 输入变量，只提交一次：

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

禁止构造 URL、curl、API、粘贴、测试文字、重复 Enter。

## P2 定位指定帖子

只点击标题逐字等于 `$TARGET_TITLE_LITERAL` 的标题 link。当前 snapshot 未找到时，只允许滚动结果页一次 `scroll down 600` 后重新 snapshot；仍没有则 `TARGET_NOT_FOUND`。

```bash
agent-browser click @<目标标题ref>
agent-browser wait 2500
agent-browser get url
agent-browser snapshot -i -c
```

详情 URL 必须由点击产生并含 `xsec_token`；否则返回并用最新标题 ref 重试一次，仍失败则 `TOKEN_URL_MISSING`。

## P3 定位目标评论楼层

只允许最多两次 `scroll down 500`，每次重新 snapshot。寻找作者逐字等于 `$TARGET_COMMENT_AUTHOR_LITERAL` 的评论楼层。

- 找不到作者：`COMMENT_TARGET_NOT_FOUND`。
- 找到作者但无法把“回复”按钮绑定到该楼层：`COMMENT_CONTEXT_UNCONFIRMED`。
- 找到时，在推理中只复述“目标作者已匹配”，不要重写作者字面值。

禁止 eval、DOM、坐标点击、`get text body`、临时 snapshot 文件和连续猜 ref。普通定位阶段禁止 vision。

## P4 激活回复上下文

从**同一个最新 snapshot**中确认目标作者与相邻“回复”按钮属于同一楼层，然后只点击该“回复”ref：

```bash
agent-browser click @<目标楼层回复ref>
agent-browser wait 500
agent-browser snapshot -i -c
```

激活成功必须满足以下任一条：

- 编辑器/placeholder 显示“回复 <目标作者>”或等价目标绑定文字；
- snapshot 中出现明确的目标回复上下文；
- **受限视觉证据**明确看到编辑器顶部/内部显示“回复 <目标作者>”。

重要：小红书的回复编辑器通常一直固定在详情面板底部；点击楼层“回复”后不一定新建或移动 editable。**不要再把“editable 预先存在”或“位置未移动”当作绑定失败。** `取消` 按钮只能证明进入回复模式，单独不能证明回复对象。

若 snapshot 没暴露“回复 <目标作者>”，不要重复点击同一个“回复”按钮。立即保存一张带标注截图，并且只允许做一次受限 vision：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser screenshot "/worktrees/folder-1/xhs-kanban-debug/evidence/$SESSION_NAME-reply-context.png" --annotate
```

Vision 只回答：底部编辑器是否逐字显示“回复 <目标作者>”，编辑器是否为空，发送按钮是否 disabled，是否有“取消”。禁止读取或推断其他业务信息，禁止第二张截图和 vision 重试。

- 视觉明确显示“回复 <目标作者>”且编辑器为空：绑定成功，进入 P5。
- 视觉显示其他作者：`WRONG_REPLY_TARGET`，不得再点击。
- 视觉读不清或服务不可用：`REPLY_CONTEXT_UNCONFIRMED`。

## P5 安全停止和清空

红线：**本演练禁止 `keyboard type`、禁止输入任何评论、禁止点击发送。**

如果编辑器意外已有文本，立即：

```bash
agent-browser click @<编辑器ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser snapshot -i -c
```

确认编辑器为空。若 P4 已保存 `$SESSION_NAME-reply-context.png`，直接复用，不要再截图；否则保存一张证据截图：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser screenshot "/worktrees/folder-1/xhs-kanban-debug/evidence/$SESSION_NAME-publish-rehearsal.png" --annotate
```

按 schema 输出并立即调用 `kanban_complete`。不得把“找到通用评论框”当成目标楼层绑定成功。
