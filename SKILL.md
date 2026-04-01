---
name: agentic-workflow
description: |
  统一智能体工作流 - 用于任何复杂任务开发。
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施、实现、创建
  DO NOT TRIGGER when: 简单闲聊
version: 5.13.0
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow - 统一智能体工作流

## 单入口设计 (v5.13.0)

所有任务统一从 router 开始，智能选择执行阶段。

## 核心改进 (v5.13.0)

- **Contract 履约门禁**: `.contract.json` 的 goals/verification/owned_files 必须非占位符，draft 状态阻断完成
- **Contract 全链路**: PLANNING→EXECUTING 设置 active，EXECUTING→REVIEWING 设置 review
- **Frontier 调度**: `parallel_candidates` (并行就绪候选) + `conflict_groups` (冲突串行)
- **Team 编排**: TeamAgent 内部整合 artifact 管线，`workflow_engine --op team-run` 接入主线
- **自改进治理**: 完整的 self-improvement harness，smoke 路径含 frontier/checkpoint/team-run
- **错误自分类**: handle_workflow_failure() 分类 test/type/lint/syntax/runtime 错误，智能调整重试策略
- **完整状态机**: 12 phase (IDLE/DIRECT_ANSWER/SUBAGENT/PLANNING/RESEARCH/THINKING/EXECUTING/REVIEWING/DEBUGGING/REFINING/EXPLORING/OFFICE_HOURS/COMPLETE)
- **英文关键词**: 所有 phase 支持英文关键词路由

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

## Phase Skills (Prompt Templates)

> **注意**: Phase Skills 是 prompt 模板，不是可执行逻辑。它们为 LLM 提供阶段特定的指导原则和行为规范，但不直接驱动运行时行为。

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

# 计算 frontier
python3 scripts/workflow_engine.py --op frontier --workdir .

# 多 agent 团队执行
python3 scripts/workflow_engine.py --op team-run --workdir .

# 条件 checkpoint
python3 scripts/workflow_engine.py --op checkpoint --workdir .

# 恢复工作流
python3 scripts/workflow_engine.py --op resume

# 验证状态
python3 scripts/unified_state.py --op validate --workdir .

# 轨迹列表
python3 scripts/trajectory_logger.py --op list --workdir .
```

## 测试命令

```bash
# 完整测试套件 (354 tests)
python3 -m pytest tests/ -q

# 核心测试 (frontier_scheduler, failure_handling, quality_gate, workflow_engine)
python3 -m pytest tests/test_workflow_engine.py tests/test_frontier_scheduler.py tests/test_failure_handling.py tests/test_quality_gate.py -q

# 任务分解测试
python3 -m pytest tests/test_task_decomposer.py -v

# 工件注册测试
python3 -m pytest tests/test_artifact_registry.py -v

# 轨迹测试
python3 -m pytest tests/test_trajectory.py -v
```

## 自改进治理 (Self-Improvement)

完整的自治改进 harness，支持在隔离环境中安全地改造 harness 本身。

### 文件结构

```
.self-improvement/
  baseline_check.sh     # 基线检查（10-gate fail-closed）
  record_result.sh     # ledger 追加工具（fcntl 并发安全）
  results.tsv          # 机器可读 ledger
  zones.md             # Zone A/B/C 定义
  self_improve.sh      # 薄封装 runner（创建分支 + baseline + 记录）
```

### Zone 定义

| Zone | 内容 | 说明 |
|------|------|------|
| **A: Protected Core** | workflow_engine, unified_state, quality_gate, safe_io, trajectory_logger | 变更需完整验证 |
| **B: Guided Mutable Surface** | router, task_decomposer, task_tracker, search_adapter, memory_ops, skills/*, README, SKILL | 首选改进区 |
| **C: Experimental** | experimental/*, roadmap/*, bench_*, run_* | 安全迭代区 |

### 自改进流程

```bash
# 方式1: 使用统一 runner（推荐）
.self-improvement/self_improve.sh --hypothesis "improve routing heuristics"

# 方式2: 手动执行
git checkout -b self-improve/20260401-my-idea
.self-improvement/baseline_check.sh
# ... 做修改 ...
.self-improvement/baseline_check.sh  # 验证
.self-improvement/record_result.sh --hypothesis "..." --files "..." --status keep --notes "..."
```

### 基线检查项 (10 gates)

1. 自改进上下文（self-improve/* 或 worktree/* 或额外 worktree）
2. Git 状态（默认 dirty 阻断，--allow-dirty 放行）
3. 完整 pytest 套件（9 个测试文件）
4. mypy 类型检查
5. ruff lint 检查
6. Workflow smoke（init/snapshot/validate）
7. 质量门禁通过 fixture
8. 质量门禁失败 fixture
9. Schema 验证
10. Ledger 完整性

## 废弃说明

- `scripts/workflow_state.py` 已废弃，功能已合并到 `unified_state.py`
