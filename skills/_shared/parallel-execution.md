---
name: parallel-execution
version: 1.1.0
description: |
  并行执行规则 - 定义 phase 并行化策略和依赖关系
  支持独立 phase 并行执行以提升性能
  默认启用并行优先模式
tags: [core, optimization, parallel, default-enabled]
---

# Parallel Execution

## Overview

并行执行通过同时运行独立 phase 来提升整体吞吐量，同时保持逻辑正确性。

**默认行为**: 并行执行已启用，无需额外配置

## 核心原则

1. **并行优先**: 默认启用并行，除非显式禁用
2. **依赖驱动**: 独立任务并行，有依赖任务串行
3. **文件所有权**: 每个文件一个所有者，避免冲突
4. **质量门禁**: 并行不牺牲质量，每个输出通过验证

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

## 任务依赖图 (Task Graph)

### 任务类型分类

| 类型 | 说明 | 处理方式 |
|------|------|---------|
| **独立任务** | 无依赖，可并行执行 | Band 内并行 |
| **顺序任务** | 前置依赖必须串行 | 等待依赖完成 |
| **混合任务** | 部分并行部分串行 | 分组后并行 |

### 依赖图表示

```
## 独立任务 (最佳并行)

Task A ─┐
Task B ─┼─→ Integration
Task C ─┘

## 顺序任务 (必要依赖)

Task A → Task B → Task C

## 钻石任务 (混合)

        ┌→ Task B ─┐
Task A ─┤          ├─→ Task D
        └→ Task C ─┘
```

### 任务描述模板

```markdown
## Task: [任务名称]

## Objective
[具体目标描述]

## Owned Files
- src/api/auth.ts        (Owner: coder)
- src/types/auth.ts       (shared - read only)

## Dependencies
- Task A (必须先完成)

## Requirements
- [具体需求列表]

## Acceptance Criteria
- [可验证的验收标准]
```

## 文件所有权策略 (File Ownership)

### 原则

1. **唯一所有者**: 每个文件只有一个明确的所有者
2. **无冲突**: 避免多个 Agent 同时修改同一文件
3. **只读共享**: 非所有者需要文件时，通过只读方式访问

### 所有权分配

| Agent | Owned Files | 说明 |
|-------|-------------|------|
| researcher | findings.md | 研究结果唯一来源 |
| thinker | analysis.md | 分析结论唯一来源 |
| planner | task_plan.md | 任务规划唯一来源 |
| coder | src/** | 所有源代码 |
| reviewer | (read-only) | 只读访问所有文件 |
| debugger | (read-only) | 调试时只读 |

### 冲突解决

```
文件冲突场景:
Agent-A 和 Agent-B 同时需要修改 config.py

解决方案:
1. 优先分配给主要负责的 Agent
2. 另一个 Agent 等待完成后获取最新版本
3. 使用 merge 工具处理冲突
```

## 并发限制保护

### 限制规则

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `max_parallel_phases` | 3 | 最多并行 phase 数 |
| `max_concurrent_subagents` | 3 | 最多并行 subagent 数 |
| `task_timeout_seconds` | 900 | 单任务超时 (15分钟) |
| `parallel_research_thinking` | true | RESEARCH+THINKING 并行 |
| `parallel_review_checks` | true | 三个审查子项并行 |
| `partial_executing_review` | true | EXECUTING 时提前开始审查 |

### 限流机制

```python
# 参考 deer-flow 实现
if len(active_subagents) >= max_concurrent_subagents:
    # 排队等待，不丢弃任务
    pending_queue.add(task)

# SSE 事件推送状态
- task_started: 子 agent 开始
- task_running: 每个新消息
- task_completed: 成功完成
- task_failed: 失败 (重试 ≤ 2 次)
- task_timed_out: 超时
```

### 超时处理

```
任务执行超时 (默认 15 分钟):
1. 记录部分完成状态
2. 标记任务为 TIMED_OUT
3. 可选: 重试一次或升级处理
```

### 用户可配置

```bash
# 默认已启用并行（无需显式指定）
/agentic-workflow

# 禁用并行 (保守模式 - 调试时使用)
/agentic-workflow --no-parallel

# 查看当前配置
/agentic-workflow --config

# 激进并行 (可能影响质量 - 谨慎使用)
/agentic-workflow --aggressive-parallel
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

## Git Worktree 隔离 (v5.7.1)

### 适用场景

当并行任务存在**高风险文件冲突**时，使用 Git Worktree 提供**进程级硬隔离**：

| 场景 | 文件冲突风险 | 推荐方案 |
|------|------------|---------|
| 多 Agent 修改同一模块 | 高 | **Worktree 隔离** |
| 独立功能开发 | 低 | 文件所有权策略 |
| Review + Debug 并行 | 中 | 文件所有权策略 |

### Worktree 隔离原理

```
传统并行 (文件所有权):
┌─────────────────┐     ┌─────────────────┐
│   Agent-A       │     │   Agent-B       │
│   Owner: src/a  │     │   Owner: src/b  │
│   Write: src/a │     │   Write: src/b  │
└────────┬────────┘     └────────┬────────┘
         │                           │
         └───────────┬───────────────┘
                     ▼
            文件系统 (可能冲突)

Worktree 隔离:
┌─────────────────┐     ┌─────────────────┐
│  Agent-A        │     │  Agent-B        │
│  Branch: wt/A  │     │  Branch: wt/B  │
│  Worktree: .wt/A│    │  Worktree: .wt/B│
└────────┬────────┘     └────────┬────────┘
         │                           │
         ▼                           ▼
    独立目录                    独立目录
    (无冲突)                    (无冲突)
```

### 使用方法

```bash
# 创建 worktree
python scripts/worktree_manager.py --op=create --task-id=T001 --branch=feature-a

# 进入 worktree 工作
cd .worktrees/task-T001

# 完成工作后标记并合并
python scripts/worktree_manager.py --op=completed --task-id=T001
python scripts/worktree_manager.py --op=merge --task-id=T001
```

### 脚本命令

| 命令 | 说明 |
|------|------|
| `--op=create --task-id=T001` | 为任务创建独立 worktree |
| `--op=list` | 列出所有 worktree |
| `--op=completed --task-id=T001` | 标记任务完成 |
| `--op=merge --task-id=T001` | 合并回主分支 |
| `--op=cleanup` | 清理已完成的 worktree |
| `--op=prune` | 清理失效引用 |

### 何时使用 Worktree

- **高风险场景**: 多 Agent 可能同时修改有关联的文件
- **安全优先**: 需要确保任务完全隔离
- **复杂合并**: 预期会有文件冲突需要手动处理

### 何时不用 Worktree

- **低风险场景**: 文件所有权策略已足够
- **简单任务**: 单文件或明确分离的模块
- **快速任务**: Worktree 创建/删除有开销
