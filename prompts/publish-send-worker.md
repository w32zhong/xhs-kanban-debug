# 发布员 Worker v0.1（真实发送）

目标：走真实用户路径绑定指定评论楼层，把参数文件中的逐字定稿输入一次，验证回复对象、文本完整性和发送按钮状态，然后**点击发送**。发送后截图取证，按 schema 输出结果。

只读取：

1. 本文件；
2. `/worktrees/folder-1/xhs-kanban-debug/schemas/publish-send-result.md`；
3. 任务正文指定的 `PARAM_FILE`。

不要读取 README、CHANGELOG、旧日志、Kanban DB、源码、圆桌文件或额外 Skill。基础 `kanban_show` 后直接执行。

每个命令块先：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
```

禁止在推理中复述、翻译或重写 `$KEYWORD_LITERAL`、`$TARGET_TITLE_LITERAL`、`$TARGET_COMMENT_AUTHOR_LITERAL`、`$TARGET_COMMENT_EXCERPT_LITERAL`、`$APPROVED_DRAFT_LITERAL`。

## I0-I3：定位并绑定目标楼层

（与输入演练完全相同，直接复用以下规则）

### I0 初始化：命令必须逐字使用，不准发明别名

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser open "https://www.xiaohongshu.com/"
agent-browser wait 1500
agent-browser snapshot -i -c
```

本流程不调整 viewport。禁止 `set viewport`、`resize`、`viewport`、`set-viewport`、fallback 和 `--help`。

### I1 真实用户搜索：必须先清空和验空

从最新 snapshot 找搜索 textbox，然后严格执行：

```bash
agent-browser click @<搜索框ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser snapshot -i -c
```

必须从新 snapshot 确认 textbox value 为空。再用新 ref：

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

搜索用的 `keyboard type` 不计入"定稿正文只能输入一次"；二者变量和状态不同。搜索关键词只能输入一次，Enter 只能一次。输入不完整时停止为 `BROWSER_ERROR`，禁止补字、重输、测试文字或改用 URL。

### I2-I3 目标帖与目标楼层

- 只点击标题逐字等于 `$TARGET_TITLE_LITERAL` 的 link；找不到时只滚动一次 600。
- 点击后必须以 `get url` 确认详情 URL 含 `xsec_token`，并重新 snapshot。
- 详情浮层有独立的内部滚动区域。窗口级 `scroll down 500` 可能只滚动背景 body，对右侧详情无效。
- 当 a11y 已找到目标作者但评论区不在 viewport 时，先对目标作者 ref 执行一次 `agent-browser scrollintoview @<目标作者ref>`，wait 500，再 fresh snapshot。`scrollintoview` 是此状态的唯一首选动作。正常 read 路径不截图；只有确实需要最后兜底 Vision 或发送后取证时才截图，且始终使用绝对路径。
- 只有 `scrollintoview` 失败或 ref stale 时，才 fresh snapshot 取得新作者 ref 后原样重试一次。禁止先截图/vision，也禁止用窗口级 scroll 消耗视觉预算。
- 评论作者找不到时最多滚动两次 500，每次必须重新 snapshot。
- 最终验收必须同时匹配作者 `$TARGET_COMMENT_AUTHOR_LITERAL` 与评论唯一前缀 `$TARGET_COMMENT_EXCERPT_LITERAL`。只匹配作者通常不够，因为同一作者可能有多个楼层。
- **优先使用 `agent-browser read` 获取页面可读文本，不使用 Vision。** 当 snapshot 只暴露作者和 action row、没有评论正文时，执行一次 `agent-browser read`。它能读取已渲染但缺失于 a11y tree 的评论正文、作者顺序和底部回复上下文。
- 从 `read` 输出中按页面顺序锁定结构：目标作者 → 下一段评论正文必须以 `$TARGET_COMMENT_EXCERPT_LITERAL` 开头 → 该楼层对应 snapshot 中同顺序的作者 ref/action row。不得只用作者名定位。
- 多个同作者楼层时，使用 `read` 中“作者 + 紧随其后的正文前缀”确定目标是从上到下第几个同作者楼层，再按 snapshot 中同作者 ref 的页面顺序选择对应 action row。无需 Vision。
- 点击回复入口后，执行一次 fresh `agent-browser read`。只有输出中明确出现 `回复 $TARGET_COMMENT_AUTHOR_LITERAL`，并且其附近/随后显示目标评论前缀，才视为回复对象绑定成功。编辑器空状态使用 fresh snapshot 中 editable 无正文 + 发送 disabled 确认。
- `read` 输出若不包含目标正文或点击后不包含 `回复 <目标作者>`，才允许进入严格受限 Vision 兜底；不得在 `read` 可确认时调用 Vision。
- **action row 不需要 Vision。** 当 `read` 已确认目标楼层是从上到下第 N 个同作者一级评论后，按 snapshot 中同作者一级楼层的同一顺序绑定 action row。若该行明确是两个连续 generic 数字，顺序固定解释为“点赞数 → 回复气泡数”，点击第二个；若是数字后跟 `generic "回复"`，点击文字回复。不得再用 Vision 确认图标语义。
- 不要把同名子回复误算为一级楼层：`read` 中缩进/位于目标一级评论正文、日期和 action row 之后且在下一条顶级评论之前的同名作者属于子回复；snapshot 中靠近 `展开 N 条回复` 的同名 link 也应视作子回复候选。只有页面顺序和楼层边界都不清楚时才 `NEEDS_VERIFIER`。
- **唯一作者的受限例外**：若 `read` 失败或没有正文、当前详情页 a11y 中目标作者只出现一个一级楼层，才可使用一次点击后 Vision 同时核验正文前缀和回复对象。若作者出现多个一级楼层且 `read` 也无法区分，则返回 `NEEDS_VERIFIER`，不点击，不为此常规调用 Vision。
- **禁止 hover。** `hover` 不属于本状态机，任何作者 link、评论正文或 action ref 都不得 hover。
- 一级评论 action row 有两种已实测的**直接回复入口**：
  1. `generic "回复"`：无回复数时的文字入口；
  2. 同一一级楼层 action row 中，紧随点赞控件之后的第二个纯数字 `generic "N"`：这是带数字的回复气泡，点击它会绑定回复到该一级评论。
- 纯数字只有在同时满足下列全部条件时才可作为 `REPLY_REF`：
  1. 目标楼层已由作者 + 评论唯一前缀确认；
  2. 该数字位于目标一级楼层自己的 action row；
  3. 同一 action row 有两个连续动作控件，顺序是"点赞数 → 回复气泡数"；
  4. 它是第二个数字控件，而不是已缩进子回复的点赞数，也不是帖子底部总评论数；
  5. snapshot 或受限 vision 已确认该行确实为爱心数字 + 气泡数字。
- 一级楼层只有一个纯数字、无法区分图标语义、或楼层归属不清时，返回 `NEEDS_VERIFIER`，禁止猜。
- `展开 N 条回复` 是**线程展开入口**，不是直接回复入口。
- 在最新 snapshot 中锁定结构：`link "<目标作者>"` → 该楼层正文/唯一前缀 → 一级 action row → 可选的已露出子回复 → 可选 `展开 N 条回复`。
- 禁止点击作者 link、头像/image、赞或三点菜单。
- 点击前记录：`TARGET_AUTHOR_REF=<ref>; REPLY_REF=<ref>; REPLY_ROLE=generic; REPLY_KIND=TEXT_REPLY|NUMBERED_REPLY_BUBBLE; REPLY_TEXT_OR_COUNT=<回复|N>`。
- **点击前必须用最新 ref。** 从 `scrollintoview` 到 `click` 之间不要有多余命令。
- 点击后 wait 500，然后 `get url` 检查是否发生页面导航。若 URL 变化，说明点错：`WRONG_ELEMENT_CLICKED`，不恢复不重试。
- URL 未变则重新 snapshot。
- 若点击后出现图片 lightbox、头像预览或页面导航，说明点错：**不要恢复重试**，立即 `WRONG_ELEMENT_CLICKED` 完成。
- 若 a11y 不显示回复对象，先执行 fresh `agent-browser read`，检查是否明确出现 `回复 <目标作者>` 与目标评论前缀。read 可确认就继续 I4，禁止 Vision；read 无法确认时才允许按下方配额保存原始截图并做一次受限 Vision。对象错误则 `WRONG_REPLY_TARGET`，仍不清楚则 `NEEDS_VERIFIER`。
- 页面变化后重新 snapshot，禁止旧 ref。
- 禁止 URL 构造、curl/API、eval、DOM、坐标、help、`get text body`、临时 snapshot 文本文件。`agent-browser read` 是允许且优先的页面可读文本接口，不属于 `get text body`。
- **Vision 不是常规步骤，只是 read 路径失败后的最后兜底。** 在 snapshot/read 已经明确作者、评论前缀、直接回复入口、回复对象、editable 和发送状态时，禁止截图和 vision，直接继续。
- 所有场景最多 1 次有效兜底 Vision。若该调用完全没有回答指定字段，允许对**同一截图、同一问题逐字不变**重试一次，记为 `VISION_FORMAT_RETRY`。
- **Vision 是最后兜底，不是多楼层的默认步骤。** `agent-browser read` 已实测能读取 snapshot 缺失的评论正文和点击后的 `回复 <作者>`；因此普通、唯一作者、多同作者楼层都必须先走 read 路径。
- 只有 `read` 命令失败、目标正文确实不在 read 输出、或点击后 `回复 <作者>` 确实不在 read 输出时，才允许一次受限 Vision。多楼层不因“多个作者 ref”自动获得 Vision；read 无法区分时安全退出 `NEEDS_VERIFIER`。
- 兜底 Vision 提示必须直接引用变量代表的目标作者与评论前缀，要求只看**右侧评论栏和底部编辑器**：

```bash
source "<PARAM_FILE>"
printf -v VISION_QUESTION '忽略左侧图片/视频、笔记正文、搜索背景和 AI 面板。只检查右侧详情栏下半部的评论区和最底部编辑器。逐项回答：1) 是否能看到作者「%s」的一级评论；2) 正文是否以「%s」开头；3) 编辑器是否逐字显示「回复 %s」；4) 编辑器是否为空。每项只答 YES/NO；若评论区不在图内，明确写 NOT_IN_VIEW。' "$TARGET_COMMENT_AUTHOR_LITERAL" "$TARGET_COMMENT_EXCERPT_LITERAL" "$TARGET_COMMENT_AUTHOR_LITERAL"
```

- 若 vision 仍无法确认评论前缀或回复对象，返回 `NEEDS_VERIFIER`，不输入文字。

## I4：输入一次并验证

只有回复对象已明确等于目标作者且编辑器为空时才可输入。必须使用参数变量，且 `keyboard type`（定稿）全任务只能出现一次：

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
agent-browser click @<当前 editable ref>
agent-browser keyboard type "$APPROVED_DRAFT_LITERAL"
agent-browser wait 500
agent-browser snapshot -i -c
```

输入后必须验证：

1. editable 的文本逐字等于变量内容；
2. `发送`按钮从 disabled 变为 enabled；
3. 若 a11y 明确显示回复对象，则必须仍是目标作者；若 a11y 不暴露，但输入前已通过 vision 确认且没有点击其他楼层，则记录 `PRECHECK_CARRIED_FORWARD`。

### 输入后 ref 更新与逐字验收（必须机械执行）

小红书在输入后会重渲染详情区域，**输入前的 editable ref 立即视为失效**。禁止对输入前 ref 执行 `get text`。

输入完成并 wait 500 后，只执行一次 fresh `snapshot -i -c`。从该 snapshot 中获取：

- 唯一的 `paragraph ... editable [contenteditable]` 的**新 ref**；
- 最新的 `button "发送"` ref，并确认它不带 `[disabled]`。

然后仅对这个 fresh editable ref 进行一次只读逐字比对：

```bash
source "<PARAM_FILE>"
text=$(agent-browser get text @<输入后 fresh snapshot 中的 editable ref>)
if [ "$text" = "$APPROVED_DRAFT_LITERAL" ]; then printf 'TEXT_EXACT=YES\n'; else printf 'TEXT_EXACT=NO\n'; fi
```

若 `get text` 返回值明显包含页面其他区域，或长度大于定稿长度，则这是 `STALE_OR_WRONG_REF`，不是 `TEXT_MISMATCH`。此时禁止字符数/codepoint、grep/sed/awk、枚举 contenteditable、tail snapshot、额外 snapshot、脚本诊断或等待页面重渲染；立即安全退出，不发送，并报告 `EDITOR_REF_INVALID`。调试者会修正文档并整轮重跑。

禁止解析 snapshot 文本来提取 editable name；禁止自行比较字符码。逐字验收只有上面一条 `get text @fresh_ref` 路径。

只有 fresh ref 的 `get text` 成功取得编辑器正文但与变量不等时，才报告 `TEXT_MISMATCH`。出现重复文本、缺字、改字或错误作者时，**绝不发送**，进入 I6 安全退出。

## I5：点击发送

**只有** I4 全部验证通过（TEXT_EXACT=YES 且 SEND_ENABLED=YES 且回复对象正确）才可发送。

```bash
agent-browser click @<最新发送按钮ref>
agent-browser wait 3000
agent-browser snapshot -i -c
```

发送后验证：

1. 重新 snapshot，检查编辑器是否已被清空或重置（发送成功的强信号）；
2. `get url` 确认页面未发生导航；
3. 保存发送后截图到绝对路径 `/worktrees/folder-1/xhs-kanban-debug/evidence/$SESSION_NAME-after-send.png`。`agent-browser screenshot` 成功返回即视为写入成功；禁止再用 `stat`、`ls`、`file`、哈希或图片处理命令验证截图文件。

发送后**禁止**：
- 再次输入任何文字；
- 刷新页面重做；
- 点击取消或返回；
- 自行检查评论是否已发布（由独立 verifier 负责）。

## I6：输出结果

按 schema 输出结果后调用注入的 `kanban_complete`。

截图都必须写入 `evidence/`，不得散落在 workspace 根目录。
