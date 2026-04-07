---
name: Telemetry
description: 已禁用的遥测说明，保留为历史文档
version: 2.0.0
created: 2026-03-21
status: disabled
---

# Telemetry (Disabled)

该文档仅保留历史说明，不代表当前主线运行能力。

## 当前状态

- 遥测不属于主线运行面
- 不依赖 telemetry daemon
- 不依赖 `SESSION-STATE.md` 作为权威状态来源
- 当前权威状态来源是 `.workflow_state.json`

## 主线建议

如需分析阶段事件、决策和恢复过程，请优先使用：

- `.workflow_state.json`
- `.specs/<feature>/spec.md`
- `.specs/<feature>/plan.md`
- `.specs/<feature>/tasks.md`
- `.contract.json`
- `.research/findings/findings_{session}.md`
- `.reviews/review/review_{session}.md`
