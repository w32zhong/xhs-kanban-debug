# 委员长裁定格式

```text
CHAIR_RESULT
decision: APPROVE | REVISE | REJECT
consensus: <2-4句，综合两名委员全部维度>
angle_gate: <说明事实/目标/痛点/社交/零营销/安全/商业适配/发布可执行性是否通过>
final_comment: <APPROVE时为自然简洁的逐字定稿；否则NONE>
reasons:
  - <最多3项>
publish_constraints:
  - 必须逐字发送 final_comment
  - 不得追加产品名、URL、价格或引流语
```

委员长必须独立读取固定样例和两份委员输出；不能把当前聊天中的调试者当作板内节点。完成后写入指定 `OUTPUT_FILE` 并调用 `kanban_complete`。
