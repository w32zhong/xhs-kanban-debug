# 搜索结果固定格式

完成摘要必须严格包含以下字段。不要只写自然语言总结。

```text
SEARCH_RESULT
status: FOUND | NO_CANDIDATE | SETUP_ERROR | LOGIN_REQUIRED | SEARCH_TRIGGER_FAILED | TOKEN_URL_MISSING | THREAD_UNCONFIRMED | BROWSER_ERROR
keyword: <任务关键词>
session_name: <浏览器 session>
current_account: <页面明确确认的昵称/UID；无法确认写 UNKNOWN>
posts_checked: <0-1；当前单帖快速稳定性测试上限为1>

candidate:
  post_title: <无则 NONE>
  post_author: <无则 NONE>
  post_date: <页面原文；无则 NONE>
  url: <完整带 xsec_token URL；无则 NONE>
  target_comment_author: <无则 NONE>
  target_comment_text: <逐字文本；无则 NONE>
  target_comment_date: <页面原文；无则 NONE>
  context: <目标评论为何体现需求，最多 3 句>
  thread_check: <展开了什么，以及是否明确看见我方回复；不确定必须写 UNCONFIRMED>
  evidence_file: NONE

obstacles:
  - <实际阻碍；没有写 NONE>
commands_or_steps_before_failure:
  - <失败前的关键命令/动作；成功可写 NONE>
```

规则：

- `FOUND` 只能用于 URL、目标作者、逐字评论、7 天内日期与目标线程检查均有页面证据的情况。
- 目标评论存在 `展开 N 条回复` 时，必须先展开并在 `thread_check` 中写明 `EXPANDED N`；未展开不得使用 `FOUND`。
- 无法确认目标线程没有我方回复时，必须使用 `THREAD_UNCONFIRMED`，不能用 `FOUND`，但仍应保留候选的完整字段供独立验证。
- `current_account: UNKNOWN` 时不得声称“确定没有我方回复”；只能报告页面中未发现明确绑定到目标楼层的我方昵称。
- 不得将“点击成功”“页面大概有该内容”写成验证完成。
