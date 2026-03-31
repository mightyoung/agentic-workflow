---
name: agentic-workflow
description: |
  统一智能体工作流 - 用于任何复杂任务开发。
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施、实现、创建
  DO NOT TRIGGER when: 简单闲聊
version: 5.7.1
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow - 统一智能体工作流

## 单入口设计 (v5.6)

所有任务统一从 router 开始，智能选择执行阶段。

## 当前实现状态

当前仓库已经落地的主要运行面在 `scripts/`：

- `scripts/router.py`: 轻量关键词路由，按“负面过滤 → 强制触发 → 阶段关键词 → 默认 EXECUTING”执行
- `scripts/workflow_engine.py`: 最小 workflow runtime，负责把路由、状态、追踪串起来（已收口到 unified_state.py）
- `scripts/memory_ops.py`: 在项目内维护 `SESSION-STATE.md`
- `scripts/run_tracker.py`: 记录 `.run_tracker.json`
- `scripts/step_recorder.py`: 记录 `.step_records.json`

### Workflow Runtime Layer

这几份脚本和它们依赖的项目内文件，构成了当前真正可执行的 workflow runtime layer：

- `router.py` 决定入口 phase
- `workflow_engine.py` 负责初始化和推进最小 phase runtime
- `workflow_engine.py` 同时提供 phase 推荐与 runtime state 校验
- `workflow_engine.py` 还能解析 `task_plan.md` 并给出下一批待执行任务
- `SESSION-STATE.md` 和 `progress.md` 保存会话/进度状态
- `task_plan.md` 保存规划结果
- `run_tracker.py` 和 `step_recorder.py` 保存轻量执行追踪

它是一个文件驱动的最小 runtime，不是完整 orchestration engine。后续更复杂的 phase 描述、trajectory 设计和并行编排，都应视为在这个 runtime 之上的演进目标。

以下内容仍应视为目标设计或文档规范，而不是全部已经实现的运行时能力：

- 多层语义路由
- 完整 phase orchestration API
- trajectory 文件体系 `./trajectories/<task_id>_<timestamp>.json`

## 状态机

```
IDLE → [ROUTER] → RESULT-ONLY → SUBAGENT → COMPLETE
                ↓
        OFFICE-HOURS → EXPLORING → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING/REFINING → COMPLETE
```

## 并行执行 (v5.6)

默认启用并行优先，独立任务自动并行执行。详见: `skills/_shared/parallel-execution.md`

### 并行 Band 设计

| Band | Phase | 说明 |
|------|-------|------|
| Band 1 | RESEARCH \|\| THINKING | 并行 |
| Band 4 | REVIEWING \|\| DEBUGGING | 部分并行 |

## 快速开始

| 场景 | 触发 | 阶段 |
|------|------|------|
| 仅需结果 | "给我..."/"直接给..."/..."就行" | **SUBAGENT** (跳过所有PHASE) |
| 完整流程 | /agentic-workflow | OFFICE-HOURS→EXPLORING→THINKING→PLANNING→EXECUTING→REVIEWING |
| Bug修复 | bug/错误/调试 | DEBUGGING |
| 项目规划 | 计划/规划/拆分 | PLANNING |
| 技术调研 | 最佳实践/怎么做 | RESEARCH→THINKING |
| 代码审查 | 审查/review | REVIEWING |
| 产品咨询 | 产品想法/需求不明确 | OFFICE-HOURS |
| **深度探索** | "实验"/"想法"/"深层"/"本质" | **EXPLORING** |
| 迭代精炼 | 迭代/优化/精炼/发现问题/反馈循环 | REFINING |
| 简单任务 | 其他 | EXECUTING |

## 路由逻辑

详见: `skills/router/skill.md`

## Phase Skills

| Phase | Skill | 核心职责 |
|-------|-------|----------|
| ROUTER | `skills/router/skill.md` | 智能路由选择 |
| OFFICE-HOURS | `skills/office-hours/skill.md` | 产品咨询（重构产品想法） |
| **EXPLORING** | `skills/exploring/skill.md` | 苏格拉底式深度追问 |
| RESEARCH | `skills/research/skill.md` | 搜索最佳实践 |
| THINKING | `skills/thinking/skill.md` | 专家视角分析 |
| PLANNING | `skills/planning/skill.md` | 任务规划 |
| **EXECUTING** | `skills/executing/skill.md` | TDD驱动实现 + Trajectory持久化 |
| REVIEWING | `skills/reviewing/skill.md` | 代码审查 |
| DEBUGGING | `skills/debugging/skill.md` | 5步调试法 |
| COMPLETE | `skills/complete/skill.md` | 验证与复盘 |
| RETRO | `skills/gstack/commands/retro.md` | 独立回顾（可选） |

### v5.7 执行增强

**Trajectory 持久化**（目标设计，当前未完整实现）：
- 目标是记录每个任务的完整执行过程（步骤、决策、挑战）
- 当前仓库中已实现的是 `run_tracker.py` 和 `step_recorder.py`
- `./trajectories/<task_id>_<timestamp>.json` 仍应视为 roadmap

**快速模式**：
- 跳过状态跟踪，不创建 task_plan.md
- 使用简化 Trajectory（内存中记录）
- 适用于低复杂度任务

## Utility Skills

| Skill | 核心职责 |
|-------|----------|
| `skills/baidu-search/skill.md` | 百度AI搜索（tavily降级方案） |

## Shared Modules

| Module | 用途 |
|--------|------|
| `skills/_shared/preamble.md` | 标准化 preamble |
| `skills/_shared/ask-user-question.md` | 提问格式 |
| `skills/_shared/boil-the-lake.md` | 完整性原则 |
| `skills/_shared/telemetry.md` | 遥测（已禁用）|
| `skills/_shared/contributor-mode.md` | 贡献者模式 |
| `skills/_shared/parallel-execution.md` | 并行执行（默认启用）|

## Evaluation Scripts (v5.7)

基于 OpenYoung 评估机制增强的轻量化追踪系统：

| Script | 用途 |
|--------|------|
| `run_tracker.py` | 追踪执行统计 (steps, tokens, duration) |
| `step_recorder.py` | 记录每个 phase 的执行情况 |
| `reward_calculator.py` | 多维度奖励计算 |
| `experience_store.py` | 经验存储与查询 |
| `pattern_detector.py` | 失败模式检测与建议 |

## 核心原则

1. **专家模拟**: 不问"你怎么看"，问"谁最懂？"
2. **TDD驱动**: 测试先行 → 失败 → 实现 → 通过
3. **文件持久化**: findings.md, task_plan.md, progress.md
4. **PUA激励**: 穷尽3方案 → 先做后问 → 主动出击

## 铁律

- **穷尽一切**：没有穷尽所有方案之前，禁止说"无法解决"
- **先做后问**：遇到问题先自行搜索、读源码、验证，再提问
- **主动出击**：端到端交付，不只是"刚好够用"

## Subagent 集成

详见: `agents/README.md`
