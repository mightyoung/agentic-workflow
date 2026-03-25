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
- last_updated: <timestamp>

## Summary
<一句话描述整体任务>

## Goals
<主要目标列表>

## Non-Goals (YAGNI)
<明确排除的功能 - 这是 YAGNI 检查的结果>

## Task Status State Machine

**任务级状态**（借鉴自 BMAD + SWE-agent）:

```
backlog → ready-for-dev → in-progress → review → done
                 ↑               │
                 └───────────────┘ (rework)
```

| 状态 | 含义 | 触发条件 | 适用任务类型 |
|------|------|----------|-------------|
| **backlog** | 任务待处理 | 初始创建 | ALL |
| **ready-for-dev** | 准备开发 | 具备执行条件 | ALL |
| **in-progress** | 开发中 | 开始实现 | ALL |
| **review** | 代码审查中 | 提请审查 | CREATE, MODIFY, HYBRID |
| **done** | 已完成 | 通过审查或直接完成 | ALL |

### 状态转换规则

**标准路径**（CREATE/MODIFY/HYBRID）:
```
backlog → ready-for-dev → in-progress → review → done
```

**简化路径**（RESEARCH/DEBUG/OPERATE）:
```
backlog → ready-for-dev → in-progress → done (跳过 review)
```

**回归路径**:
```
任意状态 → in-progress (rework)
```

**特殊情况**:
- **RESEARCH/REVIEW**: 不强制通过 review 状态，可直接 done
- **Fast Mode**: 跳过状态跟踪，任务在内存中执行
- **OPERATE**: 可选 review，取决于验证要求

## Task Breakdown

### P0 - 核心功能
- [ ] TASK-001: <任务名>
  - **status**: backlog
  - description: <详细描述>
  - acceptance: <验收标准>
  - dependencies: []
  - complexity: low | medium | high
  - **type: <任务类型 - 见下方分类表>**
  - **owned_files: <根据类型决定 - 见下方规则>**
  - **verification: <验证方法 - 见 Verification Protocol>**

### 任务类型分类

| 类型 | 说明 | 文件作用域要求 | 示例 |
|------|------|---------------|------|
| **CREATE** | 创建新文件/模块 | 必填 - 创建的文件列表 | "创建用户认证模块" |
| **MODIFY** | 修改现有文件 | 必填 - 修改的文件列表 | "添加深色模式支持" |
| **RESEARCH** | 研究/调研类任务 | `owned_files: N/A` | "研究最佳实践" |
| **DEBUG** | 调试/修复问题 | 可选 - 涉及的文件 | "修复无限循环错误" |
| **REVIEW** | 审查/评审类任务 | `owned_files: N/A` | "审查代码安全问题" |
| **OPERATE** | 运行/部署/运维 | 可选 - 影响的文件 | "运行完整测试套件" |
| **HYBRID** | 组合类型任务 | 主类型决定 | "研究并实现 XX" |

**文件作用域规则**:

| 任务类型 | owned_files 规则 |
|----------|------------------|
| CREATE/MODIFY | **必填**，声明将创建/修改的文件 |
| RESEARCH/REVIEW | `N/A` - 不涉及文件修改 |
| DEBUG/OPERATE | 可选 - 如果任务会影响文件则声明 |
| HYBRID | 声明主要类型的文件作用域 |

**冲突检测规则**:
- **禁止两个 MODIFY/CREATE 任务声明修改同一文件**
- 冲突解决：合并任务 或 分配给同一 Agent
- RESEARCH/REVIEW 任务不参与冲突检测

**冲突检测示例**:
```
✅ 正确:
- TASK-001: 实现登录功能 [CREATE] → owned_files: src/auth/login.ts
- TASK-002: 研究 SSO 方案 [RESEARCH] → owned_files: N/A

❌ 冲突:
- TASK-001: 实现登录功能 [MODIFY] → owned_files: src/auth.ts, src/App.tsx
- TASK-002: 添加导航菜单 [MODIFY] → owned_files: src/App.tsx, src/Nav.tsx
→ 解决：合并为 TASK-001 或分配给同一 Agent
```

### P1 - 重要功能
- [ ] TASK-002: <任务名>
  ...

### P2 - 优化功能
- [ ] TASK-003: <任务名>
  ...

## Dev Agent Record (执行记录)

**借鉴自 SWE-agent trajectory** - 记录每个任务的执行过程：

```markdown
## Dev Agent Record

### TASK-001: <任务名>
- **status**: done
- **started_at**: <timestamp>
- **completed_at**: <timestamp>
- **executor**: <agent-name>
- **decisions**: <关键决策记录>
  - Decision 1: <描述及原因>
  - Decision 2: <描述及原因>
- **challenges**: <遇到的挑战及解决方案>
  - Challenge 1: <问题描述> → <解决方案>
- **learnings**: <从该任务中学到的可复用经验>
- **notes**: <其他补充说明>
```

### TASK-002: <任务名>
...

## File List (变更文件)

**借鉴自 SWE-agent** - 明确记录每个任务变更的文件：

```markdown
## File List

| Task ID | File Path | Action | Lines Changed |
|---------|----------|--------|---------------|
| TASK-001 | src/auth/login.ts | created | +120 |
| TASK-001 | src/auth/index.ts | modified | +15, -5 |
| TASK-002 | src/App.tsx | modified | +30, -10 |
```

**文件变更统计**:
- 总创建: X 个文件
- 总修改: Y 个文件
- 总删除: Z 个文件
- 总行数: +A, -B

**并行执行时的文件更新**：
- 每个任务独立更新自己的 File List 条目
- 不允许两个任务声明修改同一文件（冲突检测规则）
- 汇总统计在所有任务完成后计算

## Verification Protocol

## Verification Protocol

**验证协议** - 每个任务必须声明其验证方法，用于确保任务正确完成。

### 验证方法分类

| 验证方法 | 说明 | 适用场景 |
|----------|------|---------|
| **automated_test** | 自动化测试 | 有可运行的测试用例 |
| **manual_test** | 手动验证 | 需要人工操作验证 |
| **code_review** | 代码审查 | 需要 reviewer 确认 |
| **user_confirmation** | 用户确认 | 需要利益相关者确认 |
| **output_inspection** | 输出检查 | 验证生成的文件/内容 |
| **no_verification** | 无需验证 | 纯研究/分析任务 |

### Verification Protocol 模板

```markdown
## Verification Protocol

| Task ID | Type | Verification Method | Pass Criteria |
|---------|------|-------------------|---------------|
| TASK-001 | CREATE | automated_test | pytest 全部通过，覆盖率 >80% |
| TASK-002 | RESEARCH | output_inspection | findings.md 已生成，内容 >500 字 |
| TASK-003 | MODIFY | code_review | reviewer 批准，无安全漏洞 |
| TASK-004 | DEBUG | manual_test | 手动测试确认问题已修复 |
```

### Verification 执行规则

1. **验证前置**：任务完成前必须明确验证方法
2. **验证必做**：声明的验证方法必须执行
3. **验证失败**：验证失败的任务不能标记为完成
4. **无验证任务**：RESEARCH/REVIEW 类任务可标记为 `no_verification`

## Interface Contracts (用于并行执行)

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

## Owned Files (强制 - 用于并行执行)

文件所有权分配，用于多 Agent 并行实现场景。每个 task 必须声明其文件作用域。

**冲突检测规则**:
- 每个文件只能有一个所有者
- 如果两个任务声明修改同一文件 → **必须合并为一个任务**
- 共享文件（如类型定义、配置文件）→ 分配给主要任务，另一任务声明只读

**合并冲突示例**:
```
❌ 冲突:
- TASK-001: 实现登录功能 → owned_files: src/auth/login.ts, src/App.tsx
- TASK-002: 添加导航菜单 → owned_files: src/App.tsx, src/Nav.tsx

✅ 正确:
- TASK-001: 实现登录功能 + 添加导航菜单 → owned_files: src/auth/login.ts, src/App.tsx, src/Nav.tsx
```

**Agent 分配**:
| Agent | 文件/目录 |
|-------|-----------|
| coder | src/** (所有源代码) |
| researcher | findings.md |
| thinker | analysis.md |
| planner | task_plan.md |
| reviewer | (read-only) |

## HARD-GATE Checklist

设计批准前的必须检查项：

- [ ] **需求完整性**: 所有关键需求都有对应的任务
- [ ] **验收标准**: 每个任务都有可验证的验收标准
- [ ] **依赖清晰**: 任务间的依赖关系已明确
- [ ] **YAGNI 通过**: 不需要的功能已被识别和排除
- [ ] **复杂度评估**: 高复杂度任务已拆分为更小的单元
- [ ] **状态机对齐**: 每个任务都有初始状态 (backlog)，状态转换符合状态机定义
- [ ] **文件作用域**: CREATE/MODIFY 任务已声明 owned_files，无冲突
```

## Quality Scoring System (量化质量评分)

**借鉴自 BMAD**：每个计划必须达到质量分数阈值才能进入下一阶段。

### 评分维度 (100 分制)

| 维度 | 分值 | 评估内容 |
|------|------|----------|
| **需求完整性** | 25 | 所有关键需求都有对应任务，无遗漏 |
| **任务可执行性** | 25 | 每个任务都有明确的所有者、验收标准、文件作用域 |
| **依赖关系** | 20 | 任务间依赖清晰，无环形依赖 |
| **复杂度合理性** | 15 | 任务拆分合理，无过度拆分或不足拆分 |
| **YAGNI 合规** | 15 | 不需要的功能已识别和排除 |

### 质量阈值

| 分数范围 | 状态 | 行动 |
|----------|------|------|
| **≥ 90** | ✅ 通过 | 进入用户确认阶段 |
| **75-89** | ⚠️ 需要改进 | 根据反馈迭代改进 |
| **< 75** | ❌ 不通过 | 重新规划 |

### 评分计算示例

```
需求完整性: 22/25 (需求基本完整，有小遗漏)
任务可执行性: 23/25 (任务定义清晰，验收标准完善)
依赖关系: 18/20 (依赖清晰，有一处可优化)
复杂度合理性: 12/15 (拆分基本合理)
YAGNI 合规: 13/15 (有轻微镀金倾向)

总分: 88/100 → 需要改进 (75-89)
```

### 评分执行流程

```
1. 生成 task_plan.md 后
2. 计算质量分数
3. IF 分数 ≥ 90:
     → 进入 Approval Point
   ELSE:
     → 输出改进建议
     → 请求用户反馈
     → 迭代改进
     → 重新评分
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

### Step 5: Approval Points (审批点)

**借鉴自 BMAD**：在关键节点设置审批点，必须达到质量阈值才能通过。

#### 审批点类型

| 审批点 | 触发条件 | 阈值 | 失败处理 |
|--------|----------|------|----------|
| **AP-1: 计划审批** | task_plan.md 生成后 | ≥ 90 | 迭代改进直至通过 |
| **AP-2: 里程碑审批** | 重要阶段完成时 | ≥ 85 | 暂停，等待决策 |
| **AP-3: 发布审批** | 进入 REVIEWING 前 | ≥ 90 | 修复或延期 |

#### 审批流程

```
┌─────────────────────────────────────────┐
│  生成 task_plan.md                       │
└─────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  AP-1: 计划审批                          │
│  计算质量分数                             │
└─────────────────────────────────────────┘
            │
    ┌───────┼───────┐
    │       │       │
   ≥90    75-89   <75
    │       │       │
    ▼       ▼       ▼
  通过   改进    重新
  继续   迭代    规划
            │       │
            ▼       ▼
        输出建议  阻塞
        请求反馈  重新
            │     生成
            ◄─────┘
```

#### 质量分数报告模板

```markdown
## Quality Score Report

| 维度 | 得分 | 满分 | 状态 |
|------|------|------|------|
| 需求完整性 | X/25 | 25 | ✅/⚠️/❌ |
| 任务可执行性 | X/25 | 25 | ✅/⚠️/❌ |
| 依赖关系 | X/20 | 20 | ✅/⚠️/❌ |
| 复杂度合理性 | X/15 | 15 | ✅/⚠️/❌ |
| YAGNI 合规 | X/15 | 15 | ✅/⚠️/❌ |
| **总分** | **X/100** | 100 | **✅/⚠️/❌** |

### 改进建议
<具体可操作的改进建议>

### 审批决定
[ ✅ 通过 | ⚠️ 需要改进 | ❌ 不通过 ]
```

#### 用户确认

使用 AskUserQuestion 格式请求用户确认计划：

```
## Re-ground
- **任务**: <任务摘要>
- **子任务数**: <数量>
- **核心任务**: <P0 任务列表>
- **质量分数**: <X>/100 (<状态>)

## Simplify
计划将你的需求拆分为 <N> 个子任务，其中 <M> 个是核心功能（P0）。
实现顺序已考虑依赖关系。

## Approve
**质量评分**: <X>/100 (<状态>)
<基于阈值的推荐操作>

## Options

A) 确认计划，开始实现
   - 进入 IMPLEMENTATION 阶段
   - (需要质量分数 ≥ 90)

B) 修改计划
   - 指出需要修改的具体任务
   - 将触发重新评分

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
