---
name: agentic-workflow
description: |
  统一智能体工作流 - 用于任何复杂任务开发。
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施、实现、创建
  DO NOT TRIGGER when: 简单闲聊
version: 5.3.0
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow - 统一智能体工作流

## 单入口设计 (v5.3)

所有任务统一从 router 开始，智能选择执行阶段。

## 状态机

```
IDLE → [ROUTER] → OFFICE-HOURS → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING → COMPLETE
```

## 快速开始

| 场景 | 触发 | 阶段 |
|------|------|------|
| 完整流程 | /agentic-workflow | OFFICE-HOURS→THINKING→PLANNING→EXECUTING→REVIEWING |
| Bug修复 | bug/错误/调试 | DEBUGGING |
| 项目规划 | 计划/规划/拆分 | PLANNING |
| 技术调研 | 最佳实践/怎么做 | RESEARCH→THINKING |
| 代码审查 | 审查/review | REVIEWING |
| 产品咨询 | 产品想法/需求不明确 | OFFICE-HOURS |
| 简单任务 | 其他 | EXECUTING |

## 路由逻辑

详见: `skills/router/skill.md`

## Phase Skills

| Phase | Skill | 核心职责 |
|-------|-------|----------|
| ROUTER | `skills/router/skill.md` | 智能路由选择 |
| OFFICE-HOURS | `skills/office-hours/skill.md` | 产品咨询（重构产品想法） |
| RESEARCH | `skills/research/skill.md` | 搜索最佳实践 |
| THINKING | `skills/thinking/skill.md` | 专家视角分析 |
| PLANNING | `skills/planning/skill.md` | 任务规划 |
| EXECUTING | `skills/executing/skill.md` | TDD驱动实现 |
| REVIEWING | `skills/reviewing/skill.md` | 代码审查 |
| DEBUGGING | `skills/debugging/skill.md` | 5步调试法 |
| COMPLETE | `skills/complete/skill.md` | 验证与复盘 |
| RETRO | `skills/gstack/commands/retro.md` | 独立回顾（可选） |

## Shared Modules

| Module | 用途 |
|--------|------|
| `skills/_shared/preamble.md` | 标准化 preamble |
| `skills/_shared/ask-user-question.md` | 提问格式 |
| `skills/_shared/boil-the-lake.md` | 完整性原则 |
| `skills/_shared/telemetry.md` | 遥测（已禁用）|
| `skills/_shared/contributor-mode.md` | 贡献者模式 |

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
