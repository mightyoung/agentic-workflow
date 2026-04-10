---
name: preamble
version: 3.1.0
description: 阶段启动时的最小共享约定 (v3.1: 更新状态管理约定)
---

## Preamble

### 状态管理

唯一可信的状态文件：`.workflow_state.json`（项目根目录）

```bash
python3 scripts/workflow_engine.py --op status --workdir .
python3 scripts/workflow_engine.py --op resume --workdir .
```

### 规划与产出文件

| 文件 | 说明 |
|------|------|
| `.specs/<feature>/spec.md` | 用户故事 + 验收标准 |
| `.specs/<feature>/plan.md` | 技术方案 + 约束 |
| `.specs/<feature>/tasks.md` | 可执行任务清单 |
| `task_plan.md` | 仅 legacy 兼容投影，非新任务主入口 |
| `.research/findings/findings_{session}.md` | RESEARCH 阶段输出 |
| `.research/findings/findings_latest.md` | 最近一次 RESEARCH 输出的便捷别名 |
| `.reviews/review/review_{session}.md` | REVIEWING 阶段输出 |
| `.reviews/review/review_latest.md` | 最近一次 REVIEWING 输出的便捷别名 |
| `progress.md` | 当前阶段的轻量进度与摘要投影 |
| `.workflow_state.json` | 当前运行态、阶段、复杂度和激活档位 |

### 结构化摘要

当前运行时会在不同阶段持续复用这些摘要，而不是每次重算：

- `planning_summary`：规划模式、计划摘要、worktree 建议
- `research_summary`：研究来源、证据状态、是否降级
- `thinking_summary`：方法、主要矛盾、阶段判断、局部攻坚点
- `review_summary`：审查范围、Files Reviewed、是否通过门禁
- `resume_summary`：恢复前情的统一摘要视图

### 进度格式

每进入新阶段时输出：`[N/M PHASE] 一句话描述当前目标`

### 禁止引用的过时文件

- `SESSION-STATE.md` — 已移除
- `~/.gstack` — 历史设计
- 假设 telemetry daemon、preload 或 session 守护进程存在
