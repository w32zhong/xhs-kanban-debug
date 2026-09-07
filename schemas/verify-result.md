# 独立验证结果固定格式

```text
VERIFY_RESULT
status: VERIFIED | TARGET_NOT_FOUND | TOKEN_URL_MISSING | NO_COMMENTS_CONFIRMED | NO_COMMENTS_UNCONFIRMED | COMMENT_TEXT_UNREADABLE | THREAD_UNCONFIRMED | REJECT_OUR_HISTORY | ACCOUNT_UNKNOWN | LOGIN_REQUIRED | BROWSER_ERROR | SETUP_ERROR
session_name: <session>
posts_opened: <0-1>
target_title: <参数指定标题；不要改写>
post_author: <页面原文或 UNKNOWN>
post_date: <页面原文或 UNKNOWN>
share_url: <点击产生、含 xsec_token 的 URL；无则 NONE>
current_account: <页面确认昵称或 UNKNOWN>
comment_state: <机械状态及证据>
evidence_mode: A11Y | VISUAL_EVIDENCE | A11Y_PLUS_VISUAL | NONE
target_comment_author: <无则 NONE>
target_comment_text: <逐字文本；无则 NONE>
target_comment_date: <页面原文；无则 NONE>
thread_check: <展开动作与结果；不确定写 UNCONFIRMED>
our_history_check: <明确证据；账号未知写 UNCONFIRMED>
evidence_file: <绝对路径或 NONE>
obstacles:
  - <无则 NONE>
```

规则：

- `VERIFIED` 需要标题、作者、日期、含 xsec_token 的 share URL、可读目标评论、线程展开证据和我方历史排除均明确。
- 当前账号未知时不能使用 `VERIFIED`，应使用 `ACCOUNT_UNKNOWN` 并保留所有已验证字段。
- 只有明确空状态文字才使用 `NO_COMMENTS_CONFIRMED`；只有输入框/“点击评论”必须用 `NO_COMMENTS_UNCONFIRMED`。
- 不得用相似标题、推测文字或 vision 结果替代页面证据。
