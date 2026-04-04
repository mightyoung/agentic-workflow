# Developer Guide

## 项目能力状态

### 稳定版 (核心运行时)

| 功能 | 脚本 | 测试 |
|------|------|------|
| 关键词路由 | `scripts/router.py` | 集成测试 |
| 统一状态管理 | `scripts/unified_state.py` | ✅ 专项测试 |
| 工作流引擎 | `scripts/workflow_engine.py` | ✅ 22 tests |
| 任务分解 | `scripts/task_decomposer.py` | ✅ 14 tests |
| 轨迹持久化 | `scripts/trajectory_logger.py` | ✅ 18 tests |
| Session状态 | `scripts/memory_ops.py` | 集成测试 |
| 任务追踪 | `scripts/task_tracker.py` | 集成测试 |
| 搜索适配器 | `scripts/search_adapter.py` | ✅ 集成 |
| **小团队编排** | `scripts/team_agent.py` | ✅ 22 tests |

### 实验版 (未接入主线)

| 功能 | 脚本 | 状态 |
|------|------|------|
| 语义路由 | `scripts/experimental/semantic_router.py` | 待评估 |
| 并行执行 | `scripts/experimental/parallel_executor.py` | 待毕业 |
| 多Agent编排 | `scripts/experimental/agent_spawner.py` | 被替代 (team_agent) |
| 执行循环 | `scripts/experimental/execution_loop.py` | 部分毕业 → reflexion.py |
| Generator-Evaluator | `scripts/experimental/evaluator.py` | 待评估 |
| 上下文管理 | `scripts/experimental/context_manager.py` | 被替代 (trajectory_logger) |

**已毕业**: `scripts/reflexion.py` (从 execution_loop.py 反思引擎毕业)

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
# 核心测试 (312 tests,不含 benchmark)
python3 -m pytest tests/ --ignore=tests/bench/ -q

# Benchmark 测试 (84 tests, TDD 学习/性能基准)
python3 -m pytest tests/bench/ -q

# 完整测试套件 (396 tests = 312 core + 84 benchmark)
python3 -m pytest tests/ -q

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
6. Workflow smoke（init/snapshot/validate/frontier/checkpoint/team-run）
7. 质量门禁通过 fixture
8. 质量门禁失败 fixture
9. Schema 验证
10. Ledger 完整性

## 架构说明

### 状态管理

- `.workflow_state.json` — 唯一真实数据源
- `.artifacts.json` — 工件注册表
- `trajectories/` — 完整执行轨迹

### 状态机 (12 phases)

```
IDLE → [ROUTER] → RESULT-ONLY → SUBAGENT → COMPLETE
                ↓
        OFFICE-HOURS → EXPLORING → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING/REFINING → COMPLETE
```

## 废弃说明

- `scripts/workflow_state.py` 已废弃，功能已合并到 `unified_state.py`
- `SESSION-STATE.md` 已废弃，使用 `.workflow_state.json`
