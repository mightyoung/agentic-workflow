---
name: planning
version: 1.0.0
description: |
  规划阶段 - 任务拆分和计划制定
  负责将复杂任务分解为可执行的子任务，创建 task_plan.md
tags: [phase, planning]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# PLANNING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

PLANNING 阶段是 agentic-workflow 的核心入口阶段，负责：
- 理解用户需求和原始意图
- 任务拆分与优先级排序
- 创建结构化的 task_plan.md
- 执行 HARD-GATE 设计门禁审查
- 进行 YAGNI 检查，删除不需要的功能

## Entry Criteria

满足以下任一条件时进入 PLANNING 阶段：
- 用户请求计划、规划、拆分任务
- 用户描述了需要实现的功能
- 用户提出了问题或需求
- 从 RESEARCH 阶段完成后的自然流入

## Exit Criteria

满足以下所有条件时退出 PLANNING 阶段：
- task_plan.md 已创建并通过 HARD-GATE 审查
- 所有子任务都有明确的验收标准
- YAGNI 检查已执行，不必要的功能已标记/移除
- 用户已确认计划或已自动进入下一个阶段

## Caching Integration

{{include: ../_shared/cache.md}}

### Planning Cache Key

```python
def planning_cache_key(requirements: str, context: dict) -> str:
    """生成 planning 缓存键"""
    content = json.dumps({
        "requirements": requirements,
        "context": sorted(context.items())
    }, sort_keys=True)
    return f"planning:{hashlib.sha256(content).hexdigest()[:16]}"
```

### Cache Check Flow

```
PLANNING Entry
    │
    ▼
┌─────────────────────────────────────┐
│  生成 Cache Key                       │
│  cache_key = planning_cache_key(...)  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Cache Hit?                          │
│  cache.get(cache_key)                │
└─────────────────────────────────────┘
    │
    ├── YES ──▶ 使用缓存的计划
    │            直接返回 task_plan
    │
    └── NO ──▶ 执行完整规划
                生成 task_plan
                存入缓存
                返回结果
```

## Core Process

### Step 1: 需求理解与澄清

1. 读取当前上下文，理解用户原始需求
2. 识别关键约束和边界条件
3. 使用 AskUserQuestion 格式与用户确认关键问题

### Step 2: 任务拆分

1. 使用 `planner` 子智能体进行任务分解
2. 将复杂任务拆分为 5-15 个可执行的子任务
3. 每个子任务包含：
   - 任务 ID 和名称
   - 详细描述和验收标准
   - 优先级（P0/P1/P2）
   - 依赖关系
   - 预估复杂度

### Step 3: 创建 task_plan.md

生成标准化的任务计划文档：

```markdown
# Task Plan

## Metadata
- task_id: <uuid>
- created_at: <timestamp>
- status: draft | approved | in_progress | completed

## Summary
<一句话描述整体任务>

## Goals
<主要目标列表>

## Non-Goals (YAGNI)
<明确排除的功能 - 这是 YAGNI 检查的结果>

## Task Breakdown

### P0 - 核心功能
- [ ] TASK-001: <任务名>
  - description: <详细描述>
  - acceptance: <验收标准>
  - dependencies: []
  - complexity: low | medium | high
  - owned_files: <文件所有权（可选，用于并行执行）>

### P1 - 重要功能
- [ ] TASK-002: <任务名>
  ...

### P2 - 优化功能
- [ ] TASK-003: <任务名>
  ...

## Interface Contracts (Optional - 用于并行执行)

组件间的接口定义，用于多 Agent 协作场景：

```markdown
### 共享类型
- src/types/auth.ts: AuthResponse, UserProfile

### API 接口
- POST /api/login → 返回 { token, user }
- POST /api/register → 返回 { token, user }

### 集成点
- Frontend 依赖 Backend API 契约
- Tests 依赖 Implementation 接口
```

## Owned Files (Optional - 用于并行执行)

文件所有权分配，用于多 Agent 并行实现场景：

| Agent | 文件/目录 |
|-------|-----------|
| agent-1 | src/components/, src/hooks/ |
| agent-2 | src/api/, src/services/ |
| agent-3 | tests/, e2e/ |

**规则**：
- 每个文件只有一个所有者
- 共享文件由 Lead 统一修改
- 接口契约定义后不可随意变更

## HARD-GATE Checklist

设计批准前的必须检查项：

- [ ] **需求完整性**: 所有关键需求都有对应的任务
- [ ] **验收标准**: 每个任务都有可验证的验收标准
- [ ] **依赖清晰**: 任务间的依赖关系已明确
- [ ] **YAGNI 通过**: 不需要的功能已被识别和排除
- [ ] **复杂度评估**: 高复杂度任务已拆分为更小的单元
```

### Step 4: HARD-GATE 设计门禁

**HARD-GATE 是强制门禁**，设计批准前禁止进入实现阶段。

执行以下检查：

1. **需求完整性检查**
   - 所有 P0 需求都有对应的任务
   - 没有遗漏的关键功能

2. **验收标准检查**
   - 每个任务都有明确的验收标准
   - **验收标准可测试性检查清单**:
     ```
     FOR EACH 任务的验收标准:
         IF 可以用自动化测试验证 THEN
             PASS - 标注 "可自动测试"
         ELSE IF 可以通过运行程序直接验证 THEN
             PASS - 标注 "可手动测试"
         ELSE IF 验收标准模糊（如"性能好"、"用户体验好"）THEN
             FAIL - 需要量化指标
             建议修改为: "XX指标 < YY值"
         END
     END
     ```

3. **YAGNI 检查**
   - 识别并标记不需要的功能
   - 将 YAGNI 项放入 Non-Goals
   - 确保不在 YAGNI 上的功能不被"镀金"

4. **复杂度检查**
   - 高复杂度任务是否已拆分
   - 是否存在环威胁务依赖

**复杂度量化定义**:

| 等级 | 代码行数 | 文件数 | 外部依赖 | 技术难度 | 路由 |
|------|----------|--------|----------|----------|------|
| **LOW** | < 100行 | 1个 | 0个 | 低（熟悉的技术） | 直接 EXECUTING |
| **MEDIUM** | 100-500行 | 2-5个 | 1-3个 | 中（需学习） | THINKING → PLANNING → EXECUTING |
| **HIGH** | > 500行 | > 5个 | > 3个 | 高（新技术/未知领域） | RESEARCH → THINKING → PLANNING → EXECUTING |

**复杂度自动评估规则**:

```
# 自动复杂度计算
IF 代码行数预估 > 500 OR 文件数 > 5 OR 外部依赖数 > 3 THEN
    COMPLEXITY = HIGH
ELSE IF 代码行数预估 > 100 OR 文件数 > 1 OR 外部依赖数 > 0 THEN
    COMPLEXITY = MEDIUM
ELSE
    COMPLEXITY = LOW
END

# 技术难度Override
IF 涉及 新技术/未知领域 THEN
    COMPLEXITY = HIGH (即使其他指标较低)
END
```

### Step 5: 用户确认

使用 AskUserQuestion 格式请求用户确认计划：

```
## Re-ground
- **任务**: <任务摘要>
- **子任务数**: <数量>
- **核心任务**: <P0 任务列表>

## Simplify
计划将你的需求拆分为 <N> 个子任务，其中 <M> 个是核心功能（P0）。
实现顺序已考虑依赖关系。

## Recommend
**推荐**: 确认计划，开始实现
**Completeness**: 8/10 - 核心路径完整，边缘情况可在实现中发现

## Options

A) 确认计划，开始实现
   - 进入 IMPLEMENTATION 阶段

B) 修改计划
   - 指出需要修改的具体任务

C) 补充信息后重新规划
   - 提供额外信息，触发重新规划
```

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}

## Completion Status Protocol

PLANNING 阶段结束时，必须报告以下状态之一：

### DONE
所有检查通过，计划已获批准。

```
[PLANNING] DONE
- task_plan.md created
- HARD-GATE passed
- YAGNI check completed
- user approved
```

### DONE_WITH_CONCERNS
存在未完全解决的问题，但可以继续。

```
[PLANNING] DONE_WITH_CONCERNS
- concerns: [列出关注点]
- mitigation: [说明如何处理]
```

### BLOCKED
存在阻塞问题，无法继续。

```
[PLANNING] BLOCKED
- blockers: [列出阻塞原因]
- required_actions: [需要的操作]
```

### NEEDS_CONTEXT
需要更多上下文或用户输入。

```
[PLANNING] NEEDS_CONTEXT
- missing: [缺少的信息]
- questions: [需要回答的问题]
```

## Implementation Notes

### 使用 planner 子智能体

PLANNING 阶段使用 `planner` 子智能体进行任务分解：

```bash
# 触发 planner 子智能体
agent: planner
task: "将以下需求拆分为可执行的子任务：<需求描述>"
```

### Team Lead 协调模式 (复杂任务)

当任务需要多 Agent 并行执行时，采用以下协调协议：

**任务分解规则：**
1. **独立任务** - 每个任务可独立执行，无状态依赖
2. **清晰边界** - 每个文件只有一个所有者
3. **接口契约** - 共享边界定义类型、API、数据格式
4. **依赖图管理** - 使用 blockedBy/blocks 表达任务依赖

**团队生命周期：**
1. **Spawn** - 创建团队，派生 Agent
2. **Assign** - 分配任务，明确文件所有权
3. **Monitor** - 检查进度，在里程碑节点介入
4. **Collect** - 收集结果
5. **Synthesize** - 合并为统一输出
6. **Shutdown** - 优雅关闭

### task_plan.md 位置

- 位于项目根目录
- 文件名固定为 `task_plan.md`
- 每次规划覆盖已有文件

### 自动进入下一阶段

PLANNING 阶段完成后：
1. 如果用户确认 → 自动进入 IMPLEMENTATION 阶段
2. 如果需要更多输入 → 等待用户响应
3. 如果被阻塞 → 报告 BLOCKED 状态
