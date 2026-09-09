# 小红书 Kanban 流程调试包

目标：把小红书线索发现、独立验证、圆桌起草、发布与复核流程调试成可由较小模型稳定执行的流程。

## 新环境配置

本项目不含硬编码路径。克隆到任意目录即可使用：

```bash
# 1. 克隆到你想要的位置
git clone <repo-url> /path/to/xhs-kanban-workflow
cd /path/to/xhs-kanban-workflow

# 2. 使用专用 worker profile；不要使用 default profile
hermes profile list
python3 scripts/configure-worker-profile.py \
  --profile agent-xxxxxxxxxxxxxxxx \
  --workspace "$(pwd)"

# 3. 配置当前小红书账号昵称。账号名是运行参数，不写死在 prompt/pipeline 中
# 推荐复制示例后本地填写；也可完全通过命令行/环境变量传入：
#   "profile": "agent-xxxxxxxxxxxxxxxx",
#   "account_name": "你的小红书昵称"
# 仓库默认 runner-config.json 保持为空，不绑定任何 sandbox/profile/账号。

# 4. 一键运行一轮（适合手动或 cron；不保证一定发布）
python3 run.py \
  --profile agent-xxxxxxxxxxxxxxxx \
  --account-name '你的小红书昵称'

# 通用变量可通过参数覆盖，不需要编辑源码
python3 run.py \
  --profile agent-xxxxxxxxxxxxxxxx \
  --workspace /absolute/path/to/xhs-kanban-workflow \
  --account-name '你的小红书昵称'

# 只优化侦察兵、不启动圆桌和发布：
python3 run.py --scout-only \
  --profile agent-xxxxxxxxxxxxxxxx \
  --account-name '你的小红书昵称'

# 也可编辑 runner-config.json，或设置 XHS_AGENT_PROFILE / XHS_WORKSPACE / XHS_ACCOUNT_NAME。
# run.py 使用进程锁避免重叠；每轮开始前删除旧的 `xhs*` 工作流看板，
# 然后重建固定 slug `xhs-run`，因此 Kanban UI 中始终只需查看同一个看板。
# 无论成功、拒绝、超时或异常，都会保留当前 `xhs-run` 看板供查看，同时清理本轮 tabs、
# runtime-params、evidence、logs、roundtable 临时文件。
# stdout 只输出一份紧凑 JSON，适合 cronjob 直接收集。

# 4. 底层调试：仅创建 board 并 dispatch（run.py 会调用它）
python3 run_iteration.py

# 5. 确定性收尾器仍可单独调用
```

所有 prompt 文件使用相对路径（`./prompts/...`、`./schemas/...`），Kanban worker 的 cwd 自动设为 workspace 目录。


## 当前阶段

采用 bottom-up 调试。搜索、独立验证、综合圆桌/委员长、发布后独立复核和失败协调均已完成有界实跑。

当前按用户要求**只使用 Qwen 小虾**，暂不使用 Mimo。继续使用本地 prompt、schema 和参数文件机制，从全新 board/task/session/context 执行并观测流程；发现可泛化问题即修订本地文档并整板重跑。

**当前方向**：保留并行双委员圆桌，流程为 `搜索与核验 → 两位委员并行提高回答 → 委员长综合定稿 → 精确发布 → 发布复核`。提速来自动态数据链、share URL 复用、3 秒语义门禁和无效分支早停，不再通过删除有价值的讨论节点换速度。圆桌默认改进并放行，只有特别严重且改写无法修复的问题才拒绝。

## 全链路 E2E 流程（6 个 LLM 任务，圆桌并行）

### 任务依赖图

```text
1️⃣ 搜索与核验 ──┬─→ 2A 圆桌·用户帮助 ──┐
                 └─→ 2B 圆桌·表达优化 ──┴─→ 3️⃣ 委员长定稿 ──→ 4️⃣ 精确发布 ──→ 5️⃣ 发布复核
```

结构依赖由 `--parent` 保存。Scout 找到候选后，两位委员同时启动；两份建议完成后委员长综合。委员建议以提高回答为主，`REVISE` 不会阻断流程，单个 `REJECT` 也由委员长独立复核；只有委员长确认存在无法改写修复的严重问题，才停止发布。

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
  --assignee $(python3 -c "import json; print(json.load(open('pipeline.json'))['default_assignee'])") --workspace "dir:$(pwd)" \
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

# 6️⃣ 发布后复核完成后，运行确定性收尾脚本（不启动 LLM worker）
# python3 finalize_run.py --input runtime-params/<run>-finalize.json

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
| 5 | 发布 | ✅ `SEND_SUCCESS`，定稿逐字输入并发送到正确楼层 | ~8.5min |
| 6 | 发布后复核 | ✅ `VERIFIED`，正确线程内定稿恰好出现 1 次 | ~4.5min |
| 收尾 | `finalize_run.py` | ✅ 确定性 `NO_ACTION`；清理本轮文件与冗余标签 | 无 LLM |

**候选**: 帖子「codex 总是还没完成任务就自动结束怎么办」→ 评论「哎我也是没招了」（Kiki 总裁）

**最终结果**: 发布成功；独立复核确认目标上下文匹配、线程穷尽、定稿逐字恰好出现一次，且无跨线程或重复回复。

### 关键 Bug 修复

搜索和验证 worker 没有使用 `agent-browser read`，导致详情页评论正文永远读不到（`COMMENT_TEXT_UNREADABLE`）。修复：在 `search-worker.md` 第 5 节和 `verify-worker.md` 第 V3 节加入 `agent-browser read` 优先读取已渲染但缺失于 a11y tree 的评论正文。

**`agent-browser read` vs `snapshot -i -c`**:
- `snapshot -i -c`：返回 a11y tree，只包含交互元素（作者名、按钮），**不含评论正文**
- `agent-browser read`：返回页面可读文本，包含评论正文、日期、属地等

### 已知注意事项

1. **点击帖子标题会打开新标签页**：详情页在新 tab 中生成，需要 `agent-browser tab list --json` + `agent-browser tab tN` 切换。
2. **不要在 worker 运行期间清理标签页**：会导致 CDP 连接断开，引发 `SETUP_ERROR`。
3. **确定性收尾脚本必须接收运行时结构化结果**：将发布与复核 metadata 写入 JSON，再运行 `python3 finalize_run.py --input <json>`；不要保留 `PENDING` 静态占位。
4. **浏览器业务阶段固定零 Vision、零常规像素截图**：搜索、独立验证、发布和发布后复核只使用 fresh snapshot + `agent-browser read`。任何关键字段不明确都 fail-closed，不通过 Vision 猜测来解锁发送。

## 可复现约束

- 所有执行卡统一使用本目录作为 `dir` workspace。
- Kanban 卡正文只引用本目录中的 prompt 文件。
- 创建 worker 卡时不传任何额外 `--skill`。
- 每一轮使用新的 board slug 与新的 task ID，使 worker 获得全新上下文。
- 不依赖旧任务评论、旧结果或旧 kanban.db 才能理解流程。
- `source-archive/` 是旧资料快照，只能作为可疑参考，不是权威规范。
- 当前有效规范以 `prompts/`、`schemas/` 与 `pipeline.json` 为准。

## 文件说明

### Prompts（6 个业务 worker）

- `prompts/search-worker.md`：搜索 worker（含 `agent-browser read`）。
- `prompts/verify-worker.md`：独立验证 worker（含 `agent-browser read` 优先）。
- `prompts/review-worker.md`：圆桌委员 worker（纯文本，按本地短回复规范生成默认 1–2 句话）。
- `prompts/chair-worker.md`：委员长 worker（纯文本，执行最多 3 句话、1 个关键点的终审）。
- `prompts/xhs-reply-话术-原典.md`：从用户长期维护的 `old-xhs-docs/xhs-reply-话术.md` 逐字复制的原始话术资产；写稿与定稿 Agent 必须完整阅读。原典不做“优化式覆盖”，自动测试用 SHA-256 防止无意删改。
- `prompts/xhs-reply-style.md`：在原典之上的执行解释，负责长度、真实性和发布安全收敛；它补充原典，但不取代原典。
- `prompts/publish-send-worker.md`：发布 worker（搜索→定位→绑定→输入→发送，一步完成）。
- `prompts/publish-verify-worker.md`：发布后独立复核。

### Schemas（6 个）

- `schemas/search-result.md`、`schemas/verify-result.md`、`schemas/review-result.md`、`schemas/chair-result.md`、`schemas/publish-send-result.md`、`schemas/publish-verify-result.md`

### 工具与配置

- `pipeline.json`：当前调试阶段的任务图和参数。
- `finalize_run.py`：确定性协调与清理，不调用 LLM；严格决策表、前缀限定文件清理、保留 Kanban UI 和一个小红书登录态标签。
- `test_finalize_run.py`：收尾决策表和安全前缀回归测试。
- `run_iteration.py`：新建一轮 board、创建任务并立即 dispatch；账号昵称由 `--account-name` 运行时注入。
- `scripts/configure-worker-profile.py`：新环境一键启用原生 Kanban worker 工具、禁用 Vision 并固定项目 cwd。
- `scout-pipeline.json` / `SCOUT-REFINEMENT.md`：只运行侦察兵的快速提示词迭代入口。
- `watch_run.py`：持续收集当前轮任务状态和 worker 日志。
- `resource_guard.py`：浏览器标签页数量守卫。
- `publish-target-pool.json`：发布泛化测试目标池（5 个不同布局目标）。
- `review-case.md`：圆桌输入样例（可由搜索阶段实时更新）。
- `highclaws-features.md`：产品事实摘要。
- `CHANGELOG.md`：每次流程修订及证据。
