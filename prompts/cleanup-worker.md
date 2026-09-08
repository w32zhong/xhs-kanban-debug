# 清理工 Worker v0.1

目标：在 E2E 全链路完成后，清理本轮所有运行时临时产物和浏览器标签页，使项目目录恢复到"只有源码和规范"的干净状态。**禁止修改 `prompts/`、`schemas/`、`*.json`（不含 `current-run.json`/`full-e2e-current.json`）中的规范文件。**

只读取：

1. 本文件；
2. `/worktrees/folder-1/xhs-kanban-debug/schemas/cleanup-result.md`（若存在）。

基础 `kanban_show` 后直接执行。禁止读取 README、旧日志、Kanban DB 或额外 Skill。

## C1：清理本地临时文件

按以下 glob 删除本轮运行产生的临时文件（不删除目录本身）：

```bash
# 删除本轮 evidence 截图
rm -f /worktrees/folder-1/xhs-kanban-debug/evidence/*.png

# 删除本轮 watch 日志
rm -f /worktrees/folder-1/xhs-kanban-debug/logs/*-watch.log

# 删除本轮运行时参数文件
rm -f /worktrees/folder-1/xhs-kanban-debug/runtime-params/*.sh

# 删除本轮圆桌运行时产出（保留 canonical reviewer-a.md/reviewer-b.md/chair-final.md）
rm -f /worktrees/folder-1/xhs-kanban-debug/roundtable/e2e-*.md

# 删除本轮状态文件（存在才删）
rm -f /worktrees/folder-1/xhs-kanban-debug/current-run.json
rm -f /worktrees/folder-1/xhs-kanban-debug/full-e2e-current.json
rm -f /worktrees/folder-1/xhs-kanban-debug/target-rotation-state.json
```

验证删除结果：

```bash
echo "=== remaining evidence ===" && ls /worktrees/folder-1/xhs-kanban-debug/evidence/ 2>/dev/null | wc -l
echo "=== remaining logs ===" && ls /worktrees/folder-1/xhs-kanban-debug/logs/ 2>/dev/null | wc -l
echo "=== remaining params ===" && ls /worktrees/folder-1/xhs-kanban-debug/runtime-params/ 2>/dev/null | wc -l
```

## C2：清理浏览器标签页

列出所有标签页，关闭除 Kanban UI 以外的所有标签：

```bash
agent-browser tab list --json
```

对每个非 Kanban UI 的标签（通常是小红书帖子详情页），执行：

```bash
agent-browser tab close <tabId>
```

验证只剩 Kanban UI：

```bash
agent-browser tab list --json
```

预期只剩 1 个标签（Kanban UI，URL 含 `:10012/`）。

## C3：归档看板（可选）

如果任务正文包含 `ARCHIVE_BOARD=YES`，归档本轮看板：

```bash
hermes kanban boards rm <board_slug>
```

如果未指定 `ARCHIVE_BOARD=YES`，跳过此步，保留看板供人工检查。

## C4：完成

报告清理结果：

- 已删除文件数（按类别）
- 已关闭标签页数
- 剩余标签页列表
- 看板是否归档

调用注入的 `kanban_complete`。
