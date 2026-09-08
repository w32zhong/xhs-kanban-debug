# 发布后独立复核 Worker v0.1

目标：使用全新的浏览器 session，从小红书首页重新搜索指定帖子，独立确认参数文件中的定稿回复是否发布在正确的目标评论楼层下，且页面中没有重复的同文回复。**禁止发布、删除、点赞或修改任何内容。**

只读取：

1. 本文件；
2. `./schemas/publish-verify-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

不要读取 publisher 日志、旧证据、README、CHANGELOG、Kanban DB、源码或额外 Skill。基础 `kanban_show` 后直接执行。

每个命令块先执行：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
```

禁止在推理、命令或报告中翻译、润色或重写 `$KEYWORD_LITERAL`、`$TARGET_TITLE_LITERAL`、`$TARGET_COMMENT_AUTHOR_LITERAL`、`$TARGET_COMMENT_EXCERPT_LITERAL`、`$APPROVED_DRAFT_LITERAL`。

## V0：初始化

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser open "https://www.xiaohongshu.com/"
agent-browser wait 1500
agent-browser snapshot -i -c
```

保持默认 viewport。禁止 help、环境侦察、换 session、URL 构造、curl/API、eval、DOM 和坐标点击。

## V1：真实用户搜索

从最新 snapshot 找搜索 textbox，严格执行：

```bash
agent-browser click @<搜索框ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser snapshot -i -c
```

确认 textbox 为空后，用 fresh ref：

```bash
source "<PARAM_FILE>"
agent-browser click @<fresh 搜索框ref>
agent-browser keyboard type "$KEYWORD_LITERAL"
agent-browser wait 500
agent-browser snapshot -i -c
agent-browser press Enter
agent-browser wait 3000
agent-browser get url
agent-browser snapshot -i -c
```

关键词只输入一次，Enter 只按一次。禁止补字、重输、粘贴或直达 URL。

## V2：进入指定帖子

- 只点击标题逐字等于 `$TARGET_TITLE_LITERAL` 的 link。
- 当前 snapshot 找不到时只允许滚动 600 一次并 fresh snapshot。
- 仍找不到：`TARGET_NOT_FOUND`。
- 点击后 wait 2500，`get url` 必须含 `xsec_token`，否则 `TOKEN_URL_MISSING`。

## V3：锁定目标一级评论

1. fresh snapshot 找目标作者 ref；如果评论区域未进入 viewport，对目标作者 ref `scrollintoview` 一次，wait 500，再 fresh snapshot。
2. 执行一次 `agent-browser read`。这是读取 snapshot 缺失评论正文的正常路径，不是 Vision。
3. 必须在 read 输出中锁定：作者 `$TARGET_COMMENT_AUTHOR_LITERAL`，以及紧随其后的一级评论正文以 `$TARGET_COMMENT_EXCERPT_LITERAL` 开头。
4. 同作者有多个楼层时，按“作者 + 紧随正文前缀”定位正确一级楼层；禁止只凭作者名判断。
5. `read` 找不到作者或前缀：`TARGET_FLOOR_NOT_FOUND`。

## V4：展开并核验发布回复

目标是在**正确一级评论的回复线程范围内**找到逐字等于 `$APPROVED_DRAFT_LITERAL` 的回复。

### 先读取当前可见线程

- V3 的第一次 `agent-browser read` 成功后，必须继续 V4/V5 并在本轮完成；**禁止重新执行 V0、V1、V2 或 V3，禁止第二次搜索或重新打开首页**。
- 在 V3 的 read 输出中，从目标一级评论开始，检查其后直到下一条明确一级评论之前的子回复区域。
- 若目标楼层后出现纯数字回复计数（例如 `1`），随后紧接另一作者及正文，则将这些随后条目视为该目标楼层已展开/已可见的回复线程；数字计数不是可点击 ref。
- 若逐字定稿已在上述范围出现，记录 `THREAD_ALREADY_VISIBLE`，立即做三项验收，不要点击、不再 read。
- 若目标楼层附近有 `展开 N 条回复` 且定稿尚不可见，只点击该目标楼层对应的明确文字 `generic "展开 N 条回复"` ref 一次；禁止点击数字气泡代替展开。
- 点击后 wait 800，fresh snapshot 必须出现 `收起回复` 或更多子回复；再执行一次 fresh `agent-browser read`。
- 如果该目标线程仍显示明确文字 `展开更多回复`，说明线程尚未穷尽。只允许点击**该目标线程内**的 `展开更多回复`，每次最多点击一次，然后 wait 800、fresh snapshot。重复这一小循环，直到：
  1. `展开更多回复` 消失，线程已穷尽；或
  2. 累计展开点击达到 100 次。
- 每次点击必须使用该次 fresh snapshot 里的新 ref。若用 shell 提取 ref，只能提取纯 `e<数字>`（例如 `e154`），传给 click 时写作 `@e154`，禁止把 `ref=e154` 整段传入。
- 不要在每次展开后执行 read；每累计 10 次展开或 `展开更多回复` 消失时执行一次 read，从目标一级评论开始重新确认线程边界并累计统计逐字定稿。
- 不得点击其他楼层的展开控件。若 fresh snapshot 中无法唯一确认目标线程的 `展开更多回复`，或 fresh ref 点击失败，立即返回 `THREAD_UNCONFIRMED`；禁止可见输出重试、grep/awk 调试、尝试旧 ref、从头重跑或重新绑定 tab。
- 若达到 100 次后仍有 `展开更多回复`，返回 `THREAD_UNCONFIRMED`；**不得返回 `REPLY_NOT_FOUND`，因为仍有未检查回复**。
- `REPLY_NOT_FOUND` 仅可在线程已经穷尽、全部可读回复均检查完成且定稿计数为 0 时使用。
- 找不到明确的目标楼层展开 ref 时，返回 `THREAD_UNCONFIRMED`，禁止猜 ref、Vision、坐标、重新搜索或重跑前序步骤。
- V0-V3 每步最多执行一次；V4 只允许上述目标线程展开小循环。禁止调用 `date`、建立自行估算的时间预算、创建 todo、编写临时诊断脚本。任何一步结果不明确都必须按 schema 安全结束，禁止通过从 V0 重启来重试。

### 三项验收

在目标楼层线程范围内必须同时确认：

1. `target_context_match`: 作者 + 评论前缀匹配；
2. `thread_exhausted`: 目标线程已穷尽，不再存在 `展开更多回复`；
3. `draft_exact_match`: 至少一条子回复正文逐字等于 `$APPROVED_DRAFT_LITERAL`；
4. `duplicate_count`: 在已穷尽的目标线程内，逐字等于定稿的回复恰好出现 1 次。

只允许用 read 输出做定稿逐字判断。禁止用 Vision 抄写或比较定稿。

- 线程已穷尽且恰好 1 次：`VERIFIED`
- 线程已穷尽且 0 次：`REPLY_NOT_FOUND`
- 大于 1 次：`DUPLICATE_REPLY`
- 定稿出现在页面其他评论楼层、但不在目标线程：`WRONG_THREAD`
- 线程未穷尽、看见疑似回复但无法确定线程边界、或达到展开上限：`THREAD_UNCONFIRMED`

## V5：完成

不保存像素截图；`evidence_file` 固定写 `NONE`。按 schema 输出并调用注入的 `kanban_complete`。

安全红线：

- 禁止点击任何发送、回复、取消、删除、点赞；
- 唯一允许的评论交互是点击目标楼层明确文字的 `展开 N 条回复` 一次；
- 禁止输入任何正文；
- 禁止读取 publisher 日志或旧截图；
- 禁止 Vision，正常验证全部使用 snapshot + read；
- 页面变化后必须 fresh snapshot，禁止旧 ref。
