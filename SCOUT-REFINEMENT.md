# 侦察兵快速迭代说明

本文件用于单独优化 `prompts/scout-worker.md`，不启动圆桌、发布或发布复核任务。

## 目标

当前优化只关注：

- 先刷新首页推荐流，再选帖子；
- `login_signal=SIDEBAR_SELF_ENTRY`：左侧栏出现个人入口“我”（用户所说的“你”入口），且不点击；
- 固定账号昵称由参数 `ACCOUNT_NAME_LITERAL=打钳的小虾` 传入；
- 找到第一个有内容价值的一级评论后，只检查该楼层；
- 未发现 `打钳的小虾` 回复时立即返回 `FOUND`；
- 禁止截图、Vision、环境探索和“寻找更优目标”。

权威执行规范位于：

- `prompts/scout-worker.md`
- `scout-pipeline.json`

## 单独运行一轮

```bash
cd /worktrees/folder-1/xhs-kanban-workflow
python3 run.py --scout-only \
  --profile agent-xxxxxxxxxxxxxxxx \
  --account-name '你的小红书昵称'
```

运行时只创建一张 `1️⃣ 搜索与核验·快速迭代` 卡，board 固定为 `xhs-scout`，使用 `--profile` 或 `XHS_AGENT_PROFILE` 提供的非 default profile；账号昵称由 `--account-name` 或 `XHS_ACCOUNT_NAME` 注入。

声明预算：

- Scout 单卡最长 6 分钟；
- Runner 最长等待 8 分钟；
- 最多滚动 2 次；
- 最多重新打开首页 1 次；
- 最多打开 2 篇帖子；
- Vision 调用为 0。

## 观察指标

每轮至少记录：

- 总耗时；
- `status`；
- `posts_checked`；
- `comments_checked`；
- `scroll_count`；
- `reload_count`；
- `timeline_refreshed`；
- 是否出现 screenshot、Vision、个人主页、`--help`、环境探索；
- 找到候选后是否继续打开其他帖子或扫描其他评论。

目标基线：

- 正常首屏命中：2–3 分钟；
- 第二篇命中：不超过 5 分钟；
- 任何满足条件且没有本账号回复的首个评论都必须立即早停。

## 完整流程

侦察兵稳定后再运行完整流程：

```bash
python3 run.py
```

不要在侦察兵调优阶段开启之前的无限 `run_loop.sh`，否则圆桌和发布阶段会污染耗时判断，并可能产生真实发布副作用。
