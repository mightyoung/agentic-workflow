---
name: agentic-workflow
description: |
  统一智能体工作流 - 用于任何复杂任务开发。
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施、实现、创建
  DO NOT TRIGGER when: 简单闲聊
version: 5.11.0
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow - 统一智能体工作流

## 单入口设计 (v5.11.0)

所有任务统一从 router 开始，智能选择执行阶段。

## 核心改进 (v5.11.0)

- **硬门禁完全收口**: `complete_workflow()` 与 `advance_workflow(COMPLETE)` 使用相同门禁校验，P0/P1无verification的任务禁止完成
- **真实搜索集成**: RESEARCH phase 使用 Exa API + DuckDuckGo HTML 回退，带 URL 编码和 metadata 追踪
- **任务定向审查**: REVIEWING phase 优先审查 owned_files > file_changes > workdir_scan
- **质量门禁 fail-closed**: 代码任务门禁失败阻断完成，研究任务保持宽松

## 当前能力状态

### ✅ 稳定版 (核心运行时)

| 功能 | 脚本 | 测试 |
|------|------|------|
| 关键词路由 | `scripts/router.py` | 集成测试 |
| 统一状态管理 | `scripts/unified_state.py` | ✅ 专项测试 |
| 工作流引擎 | `scripts/workflow_engine.py` | ✅ 13 tests |
| 任务分解 | `scripts/task_decomposer.py` | ✅ 14 tests |
| 轨迹持久化 | `scripts/trajectory_logger.py` | ✅ 18 tests |
| Session状态 | `scripts/memory_ops.py` | 集成测试 |
| 任务追踪 | `scripts/task_tracker.py` | 集成测试 |
| 搜索适配器 | `scripts/search_adapter.py` | ✅ 集成 |

### 🔬 实验版 (未接入主线)

| 功能 | 脚本 |
|------|------|
| 语义路由 | `scripts/experimental/semantic_router.py` |
| 并行执行 | `scripts/experimental/parallel_executor.py` |
| 多Agent编排 | `scripts/experimental/agent_spawner.py` |
| 执行循环 | `scripts/experimental/execution_loop.py` |
| Generator-Evaluator | `scripts/experimental/evaluator.py` |
| 上下文管理 | `scripts/experimental/context_manager.py` |

## 状态机

```
IDLE → [ROUTER] → RESULT-ONLY → SUBAGENT → COMPLETE
                ↓
        OFFICE-HOURS → EXPLORING → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING/REFINING → COMPLETE
```

## 状态管理架构

**统一状态** (.workflow_state.json):
- `session_id`, `task`, `phase`, `trigger_type`, `artifacts`, `decisions`, `file_changes`
- `phase.history` 包含所有 phase 条目（含 entered_at/exited_at）

**轨迹** (./trajectories/):
- 完整执行过程记录
- 支持断点恢复

**工件注册** (.artifacts.json):
- progress.md, task_plan.md, SESSION-STATE.md, .task_tracker.json

## 快速开始

| 场景 | 触发 | 阶段 |
|------|------|------|
| 仅需结果 | "给我..."/"直接给..."/..."就行" | **SUBAGENT** |
| 完整流程 | /agentic-workflow | PLANNING→EXECUTING→REVIEWING |
| Bug修复 | bug/错误/调试 | DEBUGGING |
| 项目规划 | 计划/规划/拆分 | PLANNING |
| 技术调研 | 最佳实践/怎么做 | RESEARCH→THINKING |
| 代码审查 | 审查/review | REVIEWING |
| 产品咨询 | 产品想法/需求不明确 | OFFICE-HOURS |
| **深度探索** | "实验"/"想法"/"深层"/"本质" | **EXPLORING** |
| 迭代精炼 | 迭代/优化/精炼 | REFINING |
| 简单任务 | 其他 | EXECUTING |

## Phase Skills

| Phase | Skill | 核心职责 |
|-------|-------|----------|
| ROUTER | `skills/router/skill.md` | 关键词路由 |
| OFFICE-HOURS | `skills/office-hours/skill.md` | 产品咨询 |
| **EXPLORING** | `skills/exploring/skill.md` | 苏格拉底追问 |
| RESEARCH | `skills/research/skill.md` | 搜索最佳实践 |
| THINKING | `skills/thinking/skill.md` | 专家分析 |
| PLANNING | `skills/planning/skill.md` | 任务规划 |
| **EXECUTING** | `skills/executing/skill.md` | TDD实现 |
| REVIEWING | `skills/reviewing/skill.md` | 代码审查 |
| DEBUGGING | `skills/debugging/skill.md` | 5步调试 |
| REFINING | `skills/refining/skill.md` | 迭代精炼 |
| COMPLETE | `skills/complete/skill.md` | 验证复盘 |

## 核心原则

1. **专家模拟**: 不问"你怎么看"，问"谁最懂？"
2. **TDD驱动**: 测试先行 → 失败 → 实现 → 通过
3. **文件持久化**: findings.md, task_plan.md, progress.md
4. **PUA激励**: 穷尽3方案 → 先做后问 → 主动出击

## 铁律

- **穷尽一切**：没有穷尽所有方案之前，禁止说"无法解决"
- **先做后问**：遇到问题先自行搜索、读源码、验证，再提问
- **主动出击**：端到端交付，不只是"刚好够用"

## CLI 快速参考

```bash
# 工作流初始化
python3 scripts/workflow_engine.py --op init --prompt "实现REST API"

# 推进phase
python3 scripts/workflow_engine.py --op advance --phase EXECUTING

# 获取快照
python3 scripts/workflow_engine.py --op snapshot

# 恢复工作流
python3 scripts/workflow_engine.py --op resume

# 验证状态
python3 scripts/unified_state.py --op validate --workdir .

# 轨迹列表
python3 scripts/trajectory_logger.py --op list --workdir .
```

## 测试命令

```bash
# 核心测试 (74 tests)
python3 -m pytest tests/test_workflow_engine.py tests/test_e2e_business.py tests/test_workflow_chain.py tests/test_task_decomposer.py tests/test_artifact_registry.py tests/test_trajectory.py tests/test_failure_handling.py -q

# 任务分解测试
python3 -m pytest tests/test_task_decomposer.py -v

# 工件注册测试
python3 -m pytest tests/test_artifact_registry.py -v

# 轨迹测试
python3 -m pytest tests/test_trajectory.py -v
```

## 废弃说明

- `scripts/workflow_state.py` 已废弃，功能已合并到 `unified_state.py`
