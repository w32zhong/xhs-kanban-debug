# 小红书 Kanban 流程调试包

目标：把小红书线索发现、独立验证、圆桌起草、发布与复核流程调试成可由较小模型稳定执行的流程。

## 新环境配置

本项目不含硬编码路径。克隆到任意目录即可使用：

```bash
# 1. 克隆到你想要的位置
git clone <repo-url> /path/to/xhs-kanban-workflow
cd /path/to/xhs-kanban-workflow

# 2. 确保 Hermes profile 的 worker 模型已配置（默认 agent-26c319b9362c7cec）
hermes profile list

# 3. 运行单阶段调试（pipeline.json 中 workspace 会自动解析为当前目录）
python3 run_iteration.py

# 4. 或按 README 下方"全链路 E2E"章节手动创建看板
```

所有 prompt 文件使用相对路径（`./prompts/...`、`./schemas/...`），Kanban worker 的 cwd 自动设为 workspace 目录。


## 当前阶段

采用 bottom-up 调试。搜索、独立验证、综合圆桌/委员长、发布后独立复核和失败协调均已完成有界实跑。

当前按用户要求**只使用 Qwen 小虾**，暂不使用 Mimo。继续使用本地 prompt、schema 和参数文件机制，从全新 board/task/session/context 执行并观测流程；发现可泛化问题即修订本地文档并整板重跑。

## 全链路 E2E 端到端流程（8 阶段）

### 任务依赖图

```
1️⃣ 搜索 ──→ 2️⃣ 独立验证 ──→ 3A 圆桌委员A ──→ 4️⃣ 委员长 ──→ 5️⃣ 发布 ──→ 6️⃣ 发布后复核 ──→ 7️⃣ 失败协调 ──→ 8️⃣ 清理
                                              ↘ 3B 圆桌委员B ↗
```

每个下游任务通过 `--parent` 依赖上游，创建时设 `--initial-status blocked`。Dispatcher 在父任务完成后自动推进（promote）子任务为 ready 并 spawn worker。

**发布阶段**（第 5 阶段）一步完成：搜索目标帖 → 定位目标评论 → 绑定回复 → 输入定稿 → 点击发送。无演练、无中间步骤。

### 创建步骤

```bash
# 1. 准备时间戳和 board
STAMP=$(date +%Y%m%d-%H%M%S)
BOARD="xhs-e2e-full-${STAMP}"
hermes kanban boards create "$BOARD" --name "小红书完整E2E·${STAMP}"
hermes kanban boards set-default-workdir "$BOARD" "$(pwd)"
hermes kanban boards switch "$BOARD"
```

```bash
# 2. 为每张卡生成参数文件（含不可变的搜索/目标/定稿变量）
# runtime-params/xhs-${STAMP}-<stage>.sh
SESSION_NAME=xhs-${STAMP: -6}-<stage>
KEYWORD_LITERAL='...'
TARGET_TITLE_LITERAL='...'
TARGET_COMMENT_AUTHOR_LITERAL='...'
TARGET_COMMENT_EXCERPT_LITERAL='...'
APPROVED_DRAFT_LITERAL='...'
```

```bash
# 3. 逐级创建任务（--parent 依赖 + --initial-status blocked）
hermes kanban --board "$BOARD" create "1️⃣ 搜索" \
  --body "第一步读取：prompts/search-worker.md\nPARAM_FILE: runtime-params/xxx-search.sh" \
  --assignee agent-26c319b9362c7cec --workspace "dir:$(pwd)" \
  --max-runtime 12m --max-retries 1

hermes kanban --board "$BOARD" create "2️⃣ 独立验证" \
  --parent <搜索task_id> --initial-status blocked ...

# 3A/3B 圆桌委员并行（各自 parent=验证）
hermes kanban --board "$BOARD" create "3A 委员A" \
  --parent <验证task_id> --initial-status blocked \
  --body "...\nREVIEWER_FOCUS: 用户心理、帮助价值\nOUTPUT_FILE: roundtable/reviewer-a.md" ...

# 委员长 depends on 3A + 3B（双 parent）
hermes kanban --board "$BOARD" create "4️⃣ 委员长" \
  --parent <3A_id> --parent <3B_id> --initial-status blocked ...

# 5️⃣ 发布（一步完成：搜索→定位→绑定→输入→发送）
hermes kanban --board "$BOARD" create "5️⃣ 发布" \
  --parent <委员长_id> --initial-status blocked \
  --body "第一步读取：prompts/publish-send-worker.md\nPARAM_FILE: runtime-params/xxx-send.sh" ...

# 6️⃣ 发布后复核 → 7️⃣ 失败协调 → 8️⃣ 清理（逐级 --parent 上游）

# 4. Dispatch 首批（只 spawn ready 的，即搜索卡）
hermes kanban --board "$BOARD" dispatch --max 1 --json
```

### 运行与监控

```bash
# 后台 watcher
python3 watch_run.py &

# 轮询任务状态
hermes kanban --board "$BOARD" list --json
hermes kanban --board "$BOARD" show <task_id> --json
hermes kanban --board "$BOARD" log <task_id> | tail -40
```

Dispatcher 会在父任务完成后自动推进 blocked 子任务，无需手动 promote。

### 首次 E2E 实测结果（20260908）

| # | 阶段 | 结果 | 耗时 |
|---|------|------|------|
| 1 | 搜索 | ✅ `THREAD_UNCONFIRMED`，5 条评论全部读出 | ~2.5min |
| 2 | 独立验证 | ✅ `ACCOUNT_UNKNOWN`，目标帖+评论独立确认 | ~3min |
| 3A | 圆桌委员A | ✅ PASS，47 字定稿 | ~2min |
| 3B | 圆桌委员B | ✅ PASS，附账号门禁警告 | ~2min |
| 4 | 委员长 | ✅ APPROVE，采纳委员 A 稿 | ~1.5min |
| 5 | 发布 | ⚠️ `SETUP_ERROR`（CDP 连接不稳定） | 12min |
| 6 | 发布后复核 | ✅ `REPLY_NOT_FOUND`（正确：未发送） | ~2min |
| 7 | 失败协调 | ✅ `ESCALATE_MANUAL`（保守裁定） | ~2min |
| 8 | 清理 | ✅ 删除临时文件、关闭标签页、归档看板 | ~1min |

**候选**: 帖子「codex 总是还没完成任务就自动结束怎么办」→ 评论「哎我也是没招了」（Kiki 总裁）

**发送失败根因**: 基础设施问题（清理浏览器标签页时 CDP 连接断开），非逻辑 bug。

### 关键 Bug 修复

搜索和验证 worker 没有使用 `agent-browser read`，导致详情页评论正文永远读不到（`COMMENT_TEXT_UNREADABLE`）。修复：在 `search-worker.md` 第 5 节和 `verify-worker.md` 第 V3 节加入 `agent-browser read` 优先读取已渲染但缺失于 a11y tree 的评论正文。

**`agent-browser read` vs `snapshot -i -c`**:
- `snapshot -i -c`：返回 a11y tree，只包含交互元素（作者名、按钮），**不含评论正文**
- `agent-browser read`：返回页面可读文本，包含评论正文、日期、属地等

### 已知注意事项

1. **点击帖子标题会打开新标签页**：详情页在新 tab 中生成，需要 `agent-browser tab list --json` + `agent-browser tab tN` 切换。
2. **不要在 worker 运行期间清理标签页**：会导致 CDP 连接断开，引发 `SETUP_ERROR`。
3. **失败协调的参数文件是静态占位**：`PUBLISH_STATUS_LITERAL=PENDING` 等值在创建卡时写死，不会随运行时结果动态更新。协调员只能保守裁定（`ESCALATE_MANUAL`）。

## 可复现约束

- 所有执行卡统一使用本目录作为 `dir` workspace。
- Kanban 卡正文只引用本目录中的 prompt 文件。
- 创建 worker 卡时不传任何额外 `--skill`。
- 每一轮使用新的 board slug 与新的 task ID，使 worker 获得全新上下文。
- 不依赖旧任务评论、旧结果或旧 kanban.db 才能理解流程。
- `source-archive/` 是旧资料快照，只能作为可疑参考，不是权威规范。
- 当前有效规范以 `prompts/`、`schemas/` 与 `pipeline.json` 为准。

## 文件说明

### Prompts（8 个）

- `prompts/search-worker.md`：搜索 worker（含 `agent-browser read`）。
- `prompts/verify-worker.md`：独立验证 worker（含 `agent-browser read` 优先）。
- `prompts/review-worker.md`：圆桌委员 worker（纯文本，无浏览器）。
- `prompts/chair-worker.md`：委员长 worker（纯文本，综合裁定）。
- `prompts/publish-send-worker.md`：发布 worker（搜索→定位→绑定→输入→发送，一步完成）。
- `prompts/publish-verify-worker.md`：发布后独立复核。
- `prompts/failure-coordinator.md`：无副作用失败协调决策表。
- `prompts/cleanup-worker.md`：清理工（删临时文件、关标签、归档看板）。

### Schemas（7 个）

- `schemas/search-result.md`、`schemas/verify-result.md`、`schemas/review-result.md`、`schemas/chair-result.md`、`schemas/publish-send-result.md`、`schemas/publish-verify-result.md`、`schemas/failure-result.md`

### 工具与配置

- `pipeline.json`：当前调试阶段的任务图和参数。
- `run_iteration.py`：新建一轮 board、创建任务并立即 dispatch。
- `watch_run.py`：持续收集当前轮任务状态和 worker 日志。
- `resource_guard.py`：浏览器标签页数量守卫。
- `publish-target-pool.json`：发布泛化测试目标池（5 个不同布局目标）。
- `review-case.md`：圆桌输入样例（可由搜索阶段实时更新）。
- `highclaws-features.md`：产品事实摘要。
- `CHANGELOG.md`：每次流程修订及证据。
