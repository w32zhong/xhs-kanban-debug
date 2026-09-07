# 圆桌委员结果格式

```text
REVIEW_RESULT
reviewer: <委员编号>
recommendation: PASS | REVISE | REJECT
key_risks:
  - <最多3项>
angle_findings:
  candidate_fit: <PASS|WARN|FAIL + 一句证据>
  factuality: <PASS|WARN|FAIL + 一句证据>
  user_psychology: <PASS|WARN|FAIL + 一句证据>
  social_naturalness: <PASS|WARN|FAIL + 一句证据>
  zero_marketing: <PASS|WARN|FAIL + 一句证据>
  anti_phishing_and_safety: <PASS|WARN|FAIL + 一句证据>
  commercial_signal: <PASS|UNKNOWN|FAIL + 一句证据>
  publishability: <PASS|WARN|FAIL + 一句证据>
required_changes:
  - <最多3项；没有写 NONE>
draft: <一条自然、简洁、可逐字发布的中文建议稿>
```

要求：一轮内依据 `roundtable-angles.md` 综合评估全部角度，不拆第二轮专项审核。`angle_findings` 八组必须全部填写；它们是对完整 46 项角度的归纳，不得漏掉自动 REJECT 门槛。完成后将同样内容写入任务指定的 `OUTPUT_FILE`，再调用 `kanban_complete`。
