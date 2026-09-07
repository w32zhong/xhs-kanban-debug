# 小红书 agent-browser 执行规范 v2

## 0. 总章程：Snapshot & Ref，不用 Eval 探针

小红书等重 SPA 站点频繁混淆 class、动态生成 DOM 树。连续 `eval` / `querySelector` 探测又慢又脆。

**必须采用原生 Snapshot & Ref 的类人操作范式：**

1. **`snapshot -i -c`** 感知页面 — 返回可读 UI 元素、语义 ref (`@e1`, `@e211`)、按钮文本和状态 (`[disabled]`)。
2. **`click @ref`** 点击目标；**`keyboard type "text"`** 拟人输入（触发框架响应式更新，自动点亮"发送"按钮）。
3. 效果：1 snapshot + 1 click + 1 keyboard type = 3 条命令完成交互，替代 6-8 轮 eval 探针。

---

## 1. 环境准备

```bash
export AGENT_BROWSER_SESSION="<task-id>-xhs"
export AGENT_BROWSER_PIN_TAB=1
agent-browser set viewport 1920 1080   # 必须！小视口会导致浮层布局挤压，评论框不可交互
```

- Kanban 已注入任务正文和父任务结果，不要运行 `hermes kanban show` 或寻找 venv。
- 只操作本 session 标签，每次交互后 ref 会变，必须重新 snapshot。

## 2. 搜索页流程

```bash
agent-browser open "https://www.xiaohongshu.com/search_result?keyword=<编码关键词>&type=51"
agent-browser wait 2500
agent-browser snapshot -i -c
```

- 标题以 `link "标题" [ref=eN]` 出现 → 直接 `click @eN`。
- 保存链接：`agent-browser get attr @eN href`（selector 在前，属性名在后）。
- 小红书详情 URL 依赖 `xsec_token`。必须通过点击 ref 或保存带 token 的完整 href。**禁止构造裸 `/explore/<id>`。**

## 3. 详情页与评论阅读

```bash
agent-browser wait 2000
agent-browser get url
agent-browser snapshot -c
```

Accessibility tree 通常直接包含：标题、正文、作者、日期、评论、`展开 N 条回复`、评论编辑框、发送按钮。

- **展开回复**：找 `展开 N 条回复 [ref=eN]` → `click @eN` → `wait 800` → `snapshot -c` 或 `diff snapshot`。
- **关闭浮层**：从最新 snapshot 找关闭/遮罩 ref → `click @eN`。
- **记录候选**：作者、逐字评论、日期/地区、帖子标题、完整 URL。
- **候选准入硬检查**：先识别当前登录账号昵称/UID；目标评论作者若等于当前账号，立即淘汰，绝不把自己的评论作为外展对象。然后只展开并检查**目标评论本身的子回复线程**：该目标楼层及其子回复内若有当前账号的历史回复，立即淘汰。**同一帖子里、其他独立评论楼层的我方回复不构成淘汰理由**，不可误伤。搜索员的“无我方既有回复”结论必须明确限定为“目标线程内”。
- 输出过长时用 `screenshot <path> --annotate`。不要猜 CSS 类名。

## 4. 发布流程

> **发布员必须先完整阅读** [`xhs-publisher-flow.md`](./xhs-publisher-flow.md)。该文件是发布任务的逐步执行清单；本节仅保留共用浏览器规范。核心原则：确认目标楼层后只提交一次；点击发送≠发布成功；发布员只交证据，独立复核员判定最终正确性。

### 4a. 打开帖子确认上下文

```bash
agent-browser set viewport 1920 1080    # 每次打开帖子前确认
agent-browser open "<完整带tokenURL>"
agent-browser wait 3000
agent-browser snapshot -c
```

确认帖子标题、目标评论作者和文本。展开回复确认无我方既有回复。

### 4b. 处理弹窗（如有）

`snapshot -i -c` 若看到 `温馨提示`、`广告屏蔽`、`活动`、`我要申诉` 等文本：
- 找关闭/确认按钮 ref → `click @关闭ref` → `wait 500` → `snapshot -i -c` 确认消失
- **Escape 仅用于关闭弹窗，绝不能在输入文字后按**

### 4c. 激活回复上下文并输入

**关键：不要直接点通用评论框，先点目标评论的"回复"按钮激活上下文。**

```bash
# 从 snapshot 中找目标评论旁的 "回复" 按钮 ref
agent-browser click @回复按钮ref
agent-browser wait 300
agent-browser snapshot -i -c
# 确认评论编辑框 (paragraph [contenteditable] [ref=eN]) 可见
agent-browser click @评论编辑框ref
agent-browser keyboard type "逐字定稿"
agent-browser wait 300
agent-browser snapshot -i -c
```

确认：编辑框有终稿文本，"发送"按钮不再 `[disabled]`，且回复上下文仍明确属于目标作者。若文字重复、不完整或上下文不明，**不要发送**，按 `xhs-publisher-flow.md` 回到定位步骤。

### 4d. 发送与证据交接

```bash
agent-browser click @发送ref
agent-browser wait 3000
agent-browser snapshot -i -c
agent-browser get url
```

- **仅点击一次发送。** 页面跳转不代表成功或失败；不得补发。
- 回到原始完整带 token URL，展开目标线程，用 snapshot 定位终稿的唯一前缀。
- 发布员找到时只能报告“已提交、初步可见”，找不到时报告“待独立复核”；**最终成功只能由独立复核 Agent 确认。**
- 一次发送后不得重复提交，除非协调员依据发布日志给出精确反馈并创建新的重发任务。

## 5. eval 红线

- **默认禁止。** 仅当 snapshot/read/refs 无法取得必要信息时使用，每个候选最多 2 次。
- 只读提取，禁止 eval 批量点击、修改 DOM、填写表单或触发提交。

## 6. 失败上报（验证 Agent）

验证 Agent 发现发布失败时：

1. `hermes kanban log <发布任务id>` 读取完整 log
2. 分析根因：浮层遮挡？viewport 太小？Escape 清空？点错元素？
3. 完成摘要输出结构化报告：
   ```
   fail_type: 未发布 | 错发
   root_cause: <具体原因>
   log_evidence: <日志关键证据>
   suggested_fix: <对重发 agent 的精确建议>
   ```
4. 标 blocked，交给委员长，不要自行重发

## 7. 标签与文件清理

- 只有最终清理任务可跨 session
- `session list` + `tab list --json` 识别本轮标签，只关闭本轮的
- 禁止 `close --all`
- 清理 workspace 内 `kanban-t_*` 临时目录和散落截图
- 保护：`highclaws-features.md`、`xhs-browser-flow.md`、`hermes-kanban-ui/`
