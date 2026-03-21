---
name: parallel-execution
version: 1.0.0
description: |
  并行执行规则 - 定义 phase 并行化策略和依赖关系
  支持独立 phase 并行执行以提升性能
tags: [core, optimization, parallel]
---

# Parallel Execution

## Overview

并行执行通过同时运行独立 phase 来提升整体吞吐量，同时保持逻辑正确性。

## 依赖关系图

```
                    ┌──────────────────────────────────────────────────────┐
                    │                    PHASE DEPENDENCY GRAPH             │
                    └──────────────────────────────────────────────────────┘

    ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
    │ROUTER   │────▶│RESEARCH │────▶│THINKING │────▶│PLANNING │────▶│EXECUTING│
    └─────────┘     └─────────┘     └─────────┘     └─────────┘     └─────────┘
                          │                                                   │
                          │               ┌───────────────────────────────┘   │
                          │               │                                       │
                          ▼               ▼                                       ▼
                    ┌─────────┐     ┌─────────┐                         ┌─────────┐
                    │ REVIEW  │◀────│COMPLETE │                         │ REVIEW  │
                    └─────────┘     └─────────┘                         └─────────┘
                          │
                          ▼
                    ┌─────────┐
                    │DEBUGGING│
                    └─────────┘

    ═══════════════════════════════════════════════════════════════════════════════
    PARALLEL BANDS (phases in same band can execute in parallel)
    ═══════════════════════════════════════════════════════════════════════════════

    Band 0: [ROUTER]                           - Sequential (entry point)
    Band 1: [RESEARCH || THINKING]             - RESEARCH 结果可立即被 THINKING 消费
    Band 2: [PLANNING]                         - 依赖 RESEARCH + THINKING
    Band 3: [EXECUTING]                        - 依赖 PLANNING
    Band 4: [REVIEWING || DEBUGGING]           - REVIEWING 可与 DEBUGGING 并行 (部分)
    Band 5: [COMPLETE]                         - 串行收尾
```

## 并行执行规则

### 规则 1: RESEARCH + THINKING 并行

**原理**: RESEARCH 完成后，结果立即可用于 THINKING 分析。

```
# 传统串行:
RESEARCH (5min) → THINKING (3min) = 8min

# 并行优化:
RESEARCH (5min) ──────────────────▶ THINKING (3min)
         └─────────────────────────────────────┘
              总时间: 5min (重叠等待 RESEARCH 结果)
```

**实现条件**:
- RESEARCH 有明确的输出 (findings.md)
- THINKING 可以在收到 findings.md 后立即开始
- 使用事件驱动: RESEARCH 完成 → 触发 THINKING

### 规则 2: REVIEWING 内并行子检查

**原理**: 代码质量、安全、性能三个维度可以并行检查。

```
# 并行审查
┌─────────────────────────────────────────────────────────┐
│                    REVIEWING PHASE                       │
│                                                          │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│   │reviewer  │  │security  │  │perf-     │             │
│   │          │  │_expert   │  │expert    │             │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│        │             │             │                    │
│        └──────────────┼─────────────┘                    │
│                       ▼                                   │
│              ┌────────────────┐                          │
│              │   MERGE +      │                          │
│              │   AGGREGATE    │                          │
│              └────────────────┘                          │
└─────────────────────────────────────────────────────────┘
         Total: max(code, security, perf) ≈ 3min
```

### 规则 3: EXECUTING + REVIEWING 部分并行

**原理**: REVIEWING 的某些检查可以在 EXECUTING 仍在运行时开始。

```
# 阶段级并行
EXECUTING ─────────────────────────────────────▶ [完成]
    │
    │  某些检查可以提前开始:
    │  - 代码格式检查 (lint)
    │  - 静态分析
    │  - 依赖审计
    ▼
REVIEWING ─────────────────────────────────────▶ [完成]

Total: max(EXECUTING, REVIEWING) < EXECUTING + REVIEWING
```

### 规则 4: DEBUGGING 与 REVIEWING 可并行

**原理**: DEBUGGING 修复问题时，REVIEWING 可以检查其他部分。

```
EXECUTING ─────▶ REVIEWING (发现问题)
                        │
                        ▼
                  DEBUGGING ◀──▶ REVIEWING (其他部分)
                        │
                        ▼
                    COMPLETE
```

## 并行度控制

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_parallel_phases` | 3 | 最多并行 phase 数 |
| `parallel_research_thinking` | true | RESEARCH+THINKING 并行 |
| `parallel_review_checks` | true | 三个审查子项并行 |
| `partial_executing_review` | true | EXECUTING 时提前开始审查 |
| `aggressive_parallel` | false | 激进并行 (可能影响质量) |

### 用户可配置

```bash
# 启用所有优化
/agentic-workflow --parallel --cache

# 仅启用并行
/agentic-workflow --parallel

# 禁用并行 (保守模式)
/agentic-workflow --no-parallel

# 查看当前配置
/agentic-workflow --config
```

## 并行安全保证

### 依赖检查清单

在并行执行前，必须验证:

- [ ] 数据依赖: 读取的数据源已完成写入
- [ ] 状态依赖: 前置 phase 的 SESSION-STATE 已更新
- [ ] 文件依赖: 所需文件已存在且版本正确
- [ ] 资源依赖: 共享资源无冲突

### 回滚机制

如果并行执行失败:

1. **部分完成**: 记录已完成的部分
2. **状态回滚**: 恢复到并行开始前的状态
3. **串重试**: 使用串行模式重新执行

```
Parallel Rollback:

START: [STATE_A]
   │
   ├─▶ PHASE_1 ──▶ [STATE_B']
   │
   └─▶ PHASE_2 ──▶ [STATE_B''] ⚠️ FAIL
   │
   ▼
ROLLBACK: [STATE_A] → 重试串行
```

## 状态机集成

### 并行状态更新

```markdown
## Parallel Execution State

- parallel_enabled: {true|false}
- active_bands: [band indices with running phases]
- completed_phases: [list of completed phases]
- pending_dependencies: {phase: [dependencies]}
- rollback_point: {state_id}

## Phase Status (per band)

| Band | Phases | Status | Dependencies Met |
|------|--------|--------|------------------|
| 0 | ROUTER | DONE | - |
| 1 | RESEARCH, THINKING | RUNNING | ROUTER |
| 2 | PLANNING | PENDING | RESEARCH, THINKING |
| 3 | EXECUTING | PENDING | PLANNING |
| 4 | REVIEWING, DEBUGGING | PENDING | EXECUTING |
| 5 | COMPLETE | PENDING | REVIEWING |
```

## 性能指标

### 预期提升

| 场景 | 串行时间 | 并行时间 | 提升 |
|------|----------|----------|------|
| RESEARCH → THINKING | 8min | 5min | 37.5% |
| REVIEWING (3子项) | 9min | 3min | 66.7% |
| EXECUTING + REVIEWING | 15min | 10min | 33.3% |
| 完整流程 (无缓存) | 45min | 28min | 37.8% |

### 监控指标

- `parallel_phases_active`: 当前并行 phase 数
- `parallel_band_utilization`: 各 band 利用率
- `parallel_wait_time`: 等待依赖的时间
- `parallel_rollback_count`: 回滚次数

## 配置示例

```yaml
# agentic-workflow 配置
performance:
  parallel:
    enabled: true
    max_degree: 3
    bands:
      - name: research_thinking
        phases: [research, thinking]
        parallel: true
      - name: review_checks
        phases: [reviewer, security_expert, performance_expert]
        parallel: true
      - name: executing_review
        phases: [executing, reviewing]
        partial: true  # 部分重叠
```
