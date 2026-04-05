---
name: preamble
version: 3.0.0
description: |
  标准化 Preamble - 每个 skill 启动时的最小共享约定
  当前版本只引用真实存在的文件，不引用历史设计
---

## Preamble

### 状态文件

唯一可信的状态文件是 `.workflow_state.json`（位于项目根目录）。

```bash
# 读取当前状态
python3 scripts/workflow_engine.py --op status --workdir .

# 恢复上一次会话
python3 scripts/workflow_engine.py --op resume --workdir .
```

### 规划产出

| 文件 | 说明 |
|------|------|
| `.specs/<feature>/spec.md` | 用户故事 + 验收标准 |
| `.specs/<feature>/plan.md` | 技术方案 + 约束 |
| `.specs/<feature>/tasks.md` | 可执行任务清单 |
| `task_plan.md` | legacy，兼容旧 runtime |

### 研究产出

`findings_{session}.md` — RESEARCH 阶段输出，THINKING 阶段必须读取。

### 进度格式

每进入新阶段时输出：`[N/M PHASE] 一句话描述当前要做什么`

### 注意

- 不要引用 `SESSION-STATE.md`（已移除）
- 不要引用 `~/.gstack`（历史设计）
- 不要假定 telemetry daemon、preload 或 session 守护进程存在
