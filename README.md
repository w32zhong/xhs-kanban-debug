# 小红书 Kanban 流程调试包

目标：把小红书线索发现、独立验证、圆桌起草、发布与复核流程调试成可由较小模型稳定执行的流程。

## 当前阶段

采用 bottom-up 调试。搜索、独立验证、综合圆桌/委员长，以及 Qwen 的发布输入/清空演练已经分别完成有界实跑；Qwen 已在五个不同评论目标上通过无副作用输入演练。

当前按用户要求**只使用 Qwen 小虾**，暂不使用 Mimo。继续使用本地 prompt、schema 和参数文件机制，从全新 board/task/session/context 执行并观测流程；发现可泛化问题即修订本地文档并整板重跑。发布输入/清空层已完成五个不同目标的无副作用泛化测试，下一步继续设计和调试发布后的独立复核/失败协调；未经明确安全门槛仍不产生真实发送副作用。

## 角色边界

- 当前聊天中的打钳是**独立流程调试者**，不属于看板任务图，不参与圆桌裁定。
- 完整流程中的“委员长”必须是看板内单独创建的 worker/session，使用与打钳同款的可靠模型；它负责每轮综合裁定与最终定稿。
- 调试阶段尚未运行到资源清理卡时，由独立调试者手动清理废弃标签、session 和 board，浏览器标签始终保持少于 10 个。
- 完整流程稳定后，最后的独立复核/清理角色负责正常收尾；调试者只负责观察、诊断和改进流程。

## 可复现约束

- 所有执行卡统一使用本目录作为 `dir` workspace。
- Kanban 卡正文只引用本目录中的 prompt 文件。
- 创建 worker 卡时不传任何额外 `--skill`。
- 每一轮使用新的 board slug 与新的 task ID，使 worker 获得全新上下文。
- 不依赖旧任务评论、旧结果或旧 kanban.db 才能理解流程。
- `source-archive/` 是旧资料快照，只能作为可疑参考，不是权威规范。
- 当前有效规范以 `prompts/`、`schemas/` 与 `pipeline.json` 为准。

## 文件说明

- `highclaws-features.md`：临时小助手重新研究官网后生成的产品事实摘要。
- `prompts/search-worker.md`：搜索 worker 的逐步执行手册。
- `schemas/search-result.md`：固定交付格式。
- `pipeline.json`：当前调试阶段的任务图和参数。
- `run_iteration.py`：新建一轮 board、创建任务并立即 dispatch。
- 发布泛化测试必须显式选择目标：`python3 run_iteration.py --target-id <publish-target-pool.json 中的 id>`。禁止连续五轮静默复用 `pipeline.json` 的同一目标；`current-run.json` 会记录本轮 `target_id`。
- `watch_and_refine.py`：持续观察任务状态和日志，记录疑似阻碍；发现明确规则问题后由委员长修改文档并重跑。
- `CHANGELOG.md`：每次流程修订及证据。
