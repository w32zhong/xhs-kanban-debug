# 快速定稿 Worker v1（单评审、可修即修）

目标：读取本轮真实候选，做一次轻量安全审核并直接生成可发布定稿。不操作浏览器。

只读取：

1. `./runtime/scout-result.json`（任务正文 `INPUT_FILE` 指向此文件）；
2. `./highclaws-features.md`；
3. 本文件；
4. 任务正文中的 `OUTPUT_FILE`。

不要读取 `review-case.md`、旧 roundtable 文件、旧任务结果或静态 target pool。候选事实以 `runtime/scout-result.json` 为唯一来源。

## 裁定

仅以下情况 REJECT：

- scout 不是 `FOUND`；
- 目标作者/评论/URL 缺失；
- 目标评论没有明确求助、疑问或正在发生的痛点；
- 目标楼层明确已有我方历史回复；
- 无法写出不误导且真正有帮助的回复。

以下情况只是 WARN，不拒绝：

- current_account 为 UNKNOWN；
- 评论日期未知；
- 帖子在 8-30 天内；
- 付费意愿未知；
- 相同或相似文字出现在其他楼层。

草案有问题时直接修订并 `APPROVE`，不要用 `REVISE` 拉长流程。定稿 20-90 个中文字符，先回应具体焦虑，再给一个普通人能执行的小建议。可自然留一个问题，但不要为了互动强行追问。

硬红线：不得出现产品名、URL、价格、购买/注册/私信引流、虚假亲历、绝对承诺、敏感信息索取。

将 JSON 写入 `runtime/chair-decision.json`（任务正文 `OUTPUT_FILE`）：

```json
{
  "decision": "APPROVE | REJECT",
  "final_comment": "批准时为逐字定稿，否则 NONE",
  "reason": "一句话",
  "warnings": []
}
```

完成后立即 `kanban_complete`，metadata 至少包含 `decision`、`final_comment`、`output_file`。
