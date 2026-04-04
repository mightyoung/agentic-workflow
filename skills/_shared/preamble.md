---
name: preamble
version: 3.0.0
description: |
  标准化 Preamble - 每个 skill 启动时的最小共享约定
---

## Preamble

### 状态文件

- `.workflow_state.json` — 唯一真实状态源（session_id, task, phase, trigger_type）

### 阶段执行流程

1. 读取 `.workflow_state.json` 确认当前 phase 和 session
2. 执行当前阶段的 Core Process
3. 完成后推进：`python3 scripts/workflow_engine.py --op advance --phase NEXT --workdir .`

### 产出文件约定

| 阶段 | 产出文件 |
|------|---------|
| RESEARCH | `findings.md` |
| PLANNING | `task_plan.md` |
| EXECUTING | 实际代码变更 |
| REVIEWING | review 意见（含 file:line 定位） |
