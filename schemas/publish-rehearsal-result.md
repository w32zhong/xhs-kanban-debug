# 发布演练结果固定格式

```text
PUBLISH_REHEARSAL_RESULT
status: READY_TO_PUBLISH | TARGET_NOT_FOUND | TOKEN_URL_MISSING | COMMENT_TARGET_NOT_FOUND | COMMENT_CONTEXT_UNCONFIRMED | REPLY_CONTEXT_UNCONFIRMED | WRONG_REPLY_TARGET | LOGIN_REQUIRED | BROWSER_ERROR | SETUP_ERROR
session_name: <session>
target_title: <参数指定标题>
share_url: <点击产生且含 xsec_token；无则 NONE>
target_comment_author: <参数指定作者>
reply_context_evidence: <目标作者、回复按钮和激活后编辑器绑定证据>
reply_context_evidence_mode: A11Y | VISUAL_EVIDENCE | NONE
editor_empty: YES | NO | UNKNOWN
text_typed: NO
send_clicked: NO
evidence_file: <绝对路径或 NONE>
obstacles:
  - <无则 NONE>
```

规则：

- 只有目标标题逐字命中、URL 含 xsec_token、目标作者楼层明确、点击其相邻“回复”后编辑器明确绑定目标、编辑器为空时，才可用 `READY_TO_PUBLISH`。
- 小红书底部 editable 可能始终存在且位置不动；这不是失败证据。若 a11y snapshot 不显示回复对象，允许复用唯一一张 P4 截图做一次受限视觉读取；视觉看到“回复 <目标作者>”可作为 `VISUAL_EVIDENCE`。
- 本任务任何情况下 `text_typed` 和 `send_clicked` 都必须是 `NO`；否则报告意外并停止。
- 完成后调用 `kanban_complete`，不得只输出摘要。
