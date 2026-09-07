# 发布员 Worker v1.1（输入但绝不发送演练）

目标：走真实用户路径绑定指定评论楼层，把参数文件中的逐字定稿输入一次，验证回复对象、文本完整性和发送按钮状态，然后彻底清空并停止。**任何情况下禁止点击发送。**

只读取：

1. 本文件；
2. `/worktrees/folder-1/xhs-kanban-debug/schemas/publish-input-rehearsal-result.md`；
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

### I0 初始化：命令必须逐字使用，不准发明别名

```bash
source "<PARAM_FILE>"
export AGENT_BROWSER_SOCKET_DIR=/tmp
export AGENT_BROWSER_SESSION="$SESSION_NAME"
export AGENT_BROWSER_PIN_TAB=1
# viewport 调整不是前置条件；保持浏览器当前默认视口
agent-browser open "https://www.xiaohongshu.com/"
agent-browser wait 1500
agent-browser snapshot -i -c
```

本流程不调整 viewport。板外调试者已在默认 1280×720 独立复现：目标楼层回复可绑定、编辑器可输入、发送可 enabled，并能清空恢复 disabled。禁止 `set viewport`、`resize`、`viewport`、`set-viewport`、fallback 和 `--help`；真正关键的是点击**同一楼层明确文字为“回复”的 generic ref**，不是图片、头像或通用输入框。

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

搜索用的 `keyboard type` 不计入“定稿正文只能输入一次”；二者变量和状态不同。搜索关键词只能输入一次，Enter 只能一次。输入不完整时停止为 `BROWSER_ERROR`，禁止补字、重输、测试文字或改用 URL。

### I2-I3 目标帖与目标楼层

- 只点击标题逐字等于 `$TARGET_TITLE_LITERAL` 的 link；找不到时只滚动一次 600。
- 点击后必须以 `get url` 确认详情 URL 含 `xsec_token`，并重新 snapshot。
- 详情浮层有独立的内部滚动区域。窗口级 `scroll down 500` 可能只滚动背景 body，对右侧详情无效。
- 当 a11y 已找到目标作者但截图中评论区不在 viewport 时，先对目标作者 ref 执行一次 `agent-browser scrollintoview @<目标作者ref>`，wait 500，再 fresh snapshot 和截图。`scrollintoview` 是此状态的唯一首选动作。
- 只有 `scrollintoview` 失败或 ref stale 时，才 fresh snapshot 取得新作者 ref 后原样重试一次。禁止先截图/vision，也禁止用窗口级 scroll 消耗视觉预算。
- 评论作者找不到时最多滚动两次 500，每次必须重新 snapshot。
- 最终验收必须同时匹配作者 `$TARGET_COMMENT_AUTHOR_LITERAL` 与评论唯一前缀 `$TARGET_COMMENT_EXCERPT_LITERAL`。优先使用 snapshot/a11y。只匹配作者通常不够，因为同一作者可能有多个楼层。
- **唯一作者的受限例外**：若当前详情页 a11y 中目标作者只出现一个一级楼层、该楼层已 `scrollintoview` 并且唯一缺失字段只是评论正文，则可把它记为 `PROVISIONAL_UNIQUE_AUTHOR_FLOOR`。此时允许按下方严格 action-row 规则点击一次直接回复入口，再用全任务唯一一次 vision 在同一张点击后截图中同时核验：(a) 该楼层正文的前 10 个可见字符内包含 `$TARGET_COMMENT_EXCERPT_LITERAL`；(b) 底部显示 `回复 <目标作者>`。任一项不符或读不清，立即 `WRONG_REPLY_TARGET`/`NEEDS_VERIFIER`，不输入。若作者出现多个一级楼层，则此例外禁用，必须在点击前确认正文前缀。
- **禁止 hover。小红书回复按钮不是通过 hover 作者或楼层才出现。** `hover` 不属于本状态机，任何作者 link、评论正文或 action ref 都不得 hover。
- 一级评论 action row 有两种已实测的**直接回复入口**：
  1. `generic "回复"`：无回复数时的文字入口；
  2. 同一一级楼层 action row 中，紧随点赞控件之后的第二个纯数字 `generic "N"`：这是带数字的回复气泡，点击它会绑定回复到该一级评论。**此前把所有纯数字一律禁止点击是错误规则。**
- 纯数字只有在同时满足下列全部条件时才可作为 `REPLY_REF`：
  1. 目标楼层已由作者 + 评论唯一前缀确认；
  2. 该数字位于目标一级楼层自己的 action row；
  3. 同一 action row 有两个连续动作控件，顺序是“点赞数 → 回复气泡数”；
  4. 它是第二个数字控件，而不是已缩进子回复的点赞数，也不是帖子底部总评论数；
  5. snapshot 或受限 vision 已确认该行确实为爱心数字 + 气泡数字。
- 一级楼层只有一个纯数字、无法区分图标语义、或楼层归属不清时，返回 `NEEDS_VERIFIER`，禁止猜。
- `展开 N 条回复` 是**线程展开入口**，不是直接回复入口。它通常位于已露出的第一条子回复下方；仅在任务需要审查折叠子回复/历史回复时点击。当前“输入但不发送”演练若已确认目标一级楼层，不必先展开线程。
- 如果确实需要展开，只点击 a11y 明确提供的 `generic "展开 N 条回复" [ref=...]`；点击后必须看到 `收起回复` 或更多子回复。绝不使用气泡数字来代替“展开”。
- 在最新 snapshot 中锁定结构：`link "<目标作者>"` → 该楼层正文/唯一前缀 → 一级 action row（点赞动作 → 回复动作）→ 可选的已露出子回复 → 可选 `展开 N 条回复`。不要把子回复的 `generic "回复"` 错当成一级楼层入口。
- 禁止点击作者 link、头像/image、赞或三点菜单；ref 数字相邻不等于元素相邻，必须以语义、动作顺序和楼层结构判定。
- 点击前记录：`TARGET_AUTHOR_REF=<ref>; REPLY_REF=<ref>; REPLY_ROLE=generic; REPLY_KIND=TEXT_REPLY|NUMBERED_REPLY_BUBBLE; REPLY_TEXT_OR_COUNT=<回复|N>`。数字入口还必须记录 `LIKE_REF=<同楼层前一个点赞控件ref>`。
- **点击前必须用最新 ref。** 从 `scrollintoview` 到 `click` 之间不要有多余命令（不要中间插入 mkdir、截图等），以免 ref stale 导致点击偏移。
- 点击后 wait 500，然后 `get url` 检查是否发生页面导航。若 URL 变化，说明点错：`WRONG_ELEMENT_CLICKED`，不恢复不重试。
- URL 未变则重新 snapshot；不要仅凭"DOM/ref 没变化"判断失败。底部 editable 可能一直存在，回复对象通常只在像素层显示。
- 若点击后出现图片 lightbox、头像预览或页面导航，说明点错：**不要恢复重试**，立即 `WRONG_ELEMENT_CLICKED` 完成；调试模式由板外调试者修文档并整板重跑。
- 若 a11y 不显示回复对象，按下方 Vision 配额保存原始截图并受限核验底部 `回复 <作者>`、是否为空、发送是否 disabled、是否有取消。视觉对象正确即继续 I4；错误则 `WRONG_REPLY_TARGET`；仍不清楚才 `NEEDS_VERIFIER`。
- 页面变化后重新 snapshot，禁止旧 ref。
- 禁止 URL 构造、curl/API、eval、DOM、坐标、help、`get text body`、临时 snapshot 文本文件。
   - **Vision 不是常规步骤，只是卡住时的一次兜底。** 在 snapshot 已经明确作者、评论前缀、直接回复入口、editable 和发送状态时，禁止截图和 vision，直接继续。
   - **普通或唯一作者楼层正常最多 1 次有效 Vision。** 只有 `scrollintoview` 已把目标作者放进视觉 viewport，并在一次额外 wait+snapshot 后仍有关键字段不可见，才保存原始截图并调用。
- 若该调用完全没有回答指定字段（例如只描述全页/笔记头部、输出被截断在评论区之前），允许对**同一截图、同一问题逐字不变**重试一次，记为 `VISION_FORMAT_RETRY`。只有这种格式失败允许重试；回答了字段但结论不确定时不得重试。重试仍不回答即 `NEEDS_VERIFIER`。
   - **同一作者有多个一级楼层时，严格允许最多 2 次 Vision**，因为安全闭环需要两个不同事实：
     1. 点击前 Vision：在 `scrollintoview` 后的截图中逐字区分多个同作者楼层，指出哪个楼层以前缀变量开头，并报告该楼层 action row 是 `点赞数 + 回复气泡数` 还是 `点赞数 + 文字回复`。按 a11y 中同作者楼层的页面顺序绑定对应 ref；读不清即 `NEEDS_VERIFIER`，不点击。
     2. 点击后 Vision：只核验底部是否显示 `回复 <目标作者>`、编辑器是否为空。对象不符即 `WRONG_REPLY_TARGET`；读不清即 `NEEDS_VERIFIER`，不输入。
   - 多楼层的两次有效 Vision 必须各自只回答该阶段缺失事实。任一阶段若发生纯格式失败，也仅允许对同一截图和同一问题原样重试一次；schema 另记 `vision_format_retries`。禁止因业务结论不确定而重复问、截图加工或扩大到其他评论。
- Vision 提示必须直接引用变量代表的目标作者与评论前缀，要求只看**右侧评论栏和底部编辑器**；禁止使用“first top-level comment”这种依赖整页相对位置的描述。为避免在推理中重写字面值，固定通过 shell 生成提示：

```bash
source "<PARAM_FILE>"
printf -v VISION_QUESTION '忽略左侧图片/视频、笔记正文、搜索背景和 AI 面板。只检查右侧详情栏下半部的评论区和最底部编辑器。逐项回答：1) 是否能看到作者「%s」的一级评论；2) 正文是否以「%s」开头；3) 编辑器是否逐字显示「回复 %s」；4) 编辑器是否为空。每项只答 YES/NO；若评论区不在图内，明确写 NOT_IN_VIEW。' "$TARGET_COMMENT_AUTHOR_LITERAL" "$TARGET_COMMENT_EXCERPT_LITERAL" "$TARGET_COMMENT_AUTHOR_LITERAL"
```

普通/唯一作者场景把 `$VISION_QUESTION` 作为唯一 vision 问题；禁止自行改写为英文或相对位置描述。同作者多楼层场景分别生成 `PRECLICK_VISION_QUESTION` 与 `POSTCLICK_VISION_QUESTION`，不得把点击后的回复对象问题提前问在尚未绑定的截图中。
- 受限 Vision 只读取当前阶段缺失字段，不重复核验 a11y 已明确的字段。除“同作者多个一级楼层”的点击前/点击后两阶段外，禁止第二次 Vision；所有场景均禁止截图加工、execute_code、Python、PIL、ImageMagick、ffmpeg、安装包、裁切、画框或加横幅。
- 若 vision 仍无法确认评论前缀或回复对象，返回 `NEEDS_VERIFIER`，不输入文字；交由独立 verifier 用新 session 检查。回复对象明确为其他作者则 `WRONG_REPLY_TARGET`。

## I4：输入一次并验证，绝不发送

只有回复对象已明确等于目标作者且编辑器为空时才可输入。必须使用参数变量，且 `keyboard type` 全任务只能出现一次：

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
3. 若 a11y 明确显示回复对象，则必须仍是目标作者；若 a11y 不暴露，但输入前已通过 vision 确认且没有点击其他楼层，则记录 `PRECHECK_CARRIED_FORWARD`，不要为同一事实再次调用 vision。

逐字比对允许一次只读命令，不得在输出中打印定稿：

```bash
source "<PARAM_FILE>"
text=$(agent-browser get text @<最新 editable ref>)
if [ "$text" = "$APPROVED_DRAFT_LITERAL" ]; then printf 'TEXT_EXACT=YES\n'; else printf 'TEXT_EXACT=NO\n'; fi
```

输入后禁止再次调用 vision。文字正确性由只读变量比对确认；发送 enabled 由 a11y 中 `button "发送"` 不再带 `[disabled]` 确认。回复对象沿用输入前证据，因为中间没有任何楼层切换动作。

出现重复文本、缺字、改字或错误作者时，绝不发送，进入 I5 清空并报告 `TEXT_MISMATCH` 或 `WRONG_REPLY_TARGET`。

## I5：强制清空与安全停止

不论 I4 成功或失败，只要输入过文字，都必须清空：

```bash
agent-browser click @<最新 editable ref>
agent-browser press Control+a
agent-browser press Backspace
agent-browser wait 300
agent-browser snapshot -i -c
```

清空成功必须同时看到 editable 无正文且 `发送` disabled。若无法确认清空，状态为 `CLEAR_UNCONFIRMED`，**仍然禁止发送或点击取消**，保存 `/worktrees/folder-1/xhs-kanban-debug/evidence/$SESSION_NAME-clear-state.png` 后立即结束。

安全红线：

- 禁止点击任何“发送”；
- 输入后禁止 Escape；
- 禁止第二次 `keyboard type`；
- 禁止点击取消作为清空手段；
- 禁止因验证失败刷新后重新输入；
- 不能把“按钮 enabled”当作已发布。

截图都必须写入 `evidence/`，不得散落在 workspace 根目录。按 schema 输出并调用注入的 `kanban_complete`。
