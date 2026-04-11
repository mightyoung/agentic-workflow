<!-- tier:30% -->

# EXECUTING — Process

## Entry Criteria

- 已存在 `.specs/<feature>/tasks.md` 或 `.contract.json`（`task_plan.md` 仅作 legacy fallback）
- 用户明确要求实现、修复、编写
- 已能识别出要修改的文件或目标结果

快速模式（单文件/小任务/结果明确）：可跳过完整计划维护，但仍保留最小验证动作。

## Core Process Steps

### Step 1 — Read The Current Plan

读取 `.specs/<feature>/tasks.md` 或 `.contract.json`，确认：
- 当前要做哪一项
- 影响哪些文件
- 如何验证

不存在时：小任务直接执行；中等及以上先回 PLANNING。

### Step 1.5 — Parallel Dispatch Decision（M/L/XL 复杂度）

```
任务中有 ≥2 个独立子任务?
  ├─ 否 → 串行执行（常规流程）
  └─ 是 → 子任务是否共享文件（会冲突）?
             ├─ 是 → 串行执行（避免冲突）
             └─ 否 → 并行派发（使用 Agent tool，run_in_background: true）
```

### Step 2 — Prefer TDD

推荐顺序：写失败测试 → 最小实现 → 跑验证 → 必要时重构。

### Step 2.5 — TASK_NOTES Rolling Update

每个 P0 任务完成后，追加一条到 `SHARED_TASK_NOTES.md`（不修改历史）。
超过 20 条时，合并最旧 10 条为 `## [Archived N entries]`。

### Step 2.7 — Mid-Task Reflection Checkpoint（每个 P0 完成后自动触发）

检索因果记忆，判断是否命中已知错误模式：
- 精确命中 → STOP，阅读 Fix 字段，确认本次已规避
- Entity 历史命中 → WARNING，输出历史 bug 摘要，人工确认
- 无匹配 → CONTINUE

### Step 3 — Keep State Local

使用项目内状态文件维护执行上下文。

### Step 4 — Use Real Tracking Scripts

如需记录执行统计，使用 `run_tracker.py` / `step_recorder.py`。

## Exit Criteria（全部满足）

- 所有 P0 任务状态为 DONE 或 DONE_WITH_CONCERNS
- 相关测试已运行并通过（命令输出为证）
- `tasks.md` / `SHARED_TASK_NOTES.md` 已同步
