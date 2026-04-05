---
name: executing
version: 1.1.0
status: implemented
description: |
  执行阶段 - TDD 开发循环和代码实现
  当前版本对齐 .specs/<feature>/tasks.md、.contract.json、run_tracker.py 和 step_recorder.py
  注意: Trajectory持久化在 trajectory_logger.py 中实现
tags: [phase, executing, tdd]
requires:
  tools: [Bash, Read, Write, Grep, Glob, Edit]
---

# EXECUTING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

EXECUTING 阶段负责把计划转成实际变更。

当前真实能力聚焦在：

- 基于 `.specs/<feature>/tasks.md` 和 `.contract.json` 执行任务
- TDD 或最小可验证实现
- 使用项目内状态文件
- 使用 `run_tracker.py` / `step_recorder.py` 做轻量执行追踪

## Entry Criteria

进入 EXECUTING 的常见条件：

- 已存在 `.specs/<feature>/tasks.md` 或 `.contract.json`；`task_plan.md` 仅作 legacy fallback
- 用户明确要求实现、修复、编写
- 已经能识别出要修改的文件或目标结果

快速模式：

- 单文件、小任务、结果明确
- 可以跳过完整计划维护
- 但仍应保留最小验证动作

## Exit Criteria

<HARD-GATE name="executing-exit-gate">
以下条件必须全部满足才能退出 EXECUTING：
1. 目标代码已实现（Read 真实文件确认，不是"我以为写了"）
2. 相关测试已运行并通过（有命令输出为证）
3. 如有计划文件（tasks.md / TodoWrite），关键 P0 任务状态已同步

禁止仅凭"代码应该可以工作"退出。必须运行测试并看到通过结果。
</HARD-GATE>

**Iron Law**: `NO COMPLETE WITHOUT TESTS PASSING FIRST`

退出 EXECUTING 的条件：

- 目标代码已实现
- 相关验证已执行（测试命令输出为证）
- 如有 `.specs/<feature>/tasks.md` 或 legacy `task_plan.md`，关键任务状态已同步
- 需要时已进入 REVIEWING 或 COMPLETE

## Core Process

### 1. Read The Current Plan

如果项目内存在 `.specs/<feature>/tasks.md` 或 `.contract.json`，先读取并确认：

- 当前要做哪一项
- 影响哪些文件
- 如何验证

如果不存在：

- 小任务可直接执行
- 中等及以上任务应先回到 PLANNING 创建计划

### 2. Prefer TDD When Practical

推荐顺序：

1. 写或补失败测试
2. 最小实现
3. 跑验证
4. 必要时重构

如果不适合 TDD，也至少要有清晰验证路径，例如：

- `pytest`
- 单个测试文件
- 构建命令
- 手动验证步骤

### 3. Keep State Local

默认使用项目内文件：

- `.workflow_state.json`
- `.specs/<feature>/tasks.md`
- `.contract.json`
- `task_plan.md`（legacy）
- `progress.md`

### 4. Use Real Tracking Scripts

如果要记录执行统计，使用真实脚本：

```bash
python3 scripts/run_tracker.py --op=start --run-id=R001 --category=EXECUTING
python3 scripts/step_recorder.py --op=start --run-id=R001 --phase=EXECUTING
python3 scripts/step_recorder.py --op=end --run-id=R001 --phase=EXECUTING --output-tokens=500
python3 scripts/run_tracker.py --op=finish --run-id=R001 --status=success
```

当前仓库默认产物是：

- `.run_tracker.json`
- `.step_records.json`

## Implemented Vs Planned

以下内容目前不应视为默认已实现能力：

- `./trajectories/<task_id>_<timestamp>.json`
- trajectory 自动断点恢复
- trajectory 自动回写 `task_plan.md`（legacy）
- 自动并行执行编排
- phase telemetry API

如果后续实现这些能力，应先补脚本，再升级文档。

## Practical Rules

### TDD

- 能测就先测
- 不能测时，至少先定义验证方式

### PUA Rules

- 穷尽一切：关键卡点不要只试一种思路
- 先做后问：先读代码、跑验证、收集证据
- 主动出击：修完当前点后顺手检查同类问题

### Commits

- 小步提交比大包提交更安全
- 不要混入无关改动

## Validation

最小验证：

```bash
test -f .contract.json || test -f task_plan.md
python3 scripts/run_tracker.py --op=stats
```
