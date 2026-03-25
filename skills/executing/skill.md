---
name: executing
version: 1.0.0
description: |
  执行阶段 - TDD 开发循环和代码实现
  触发条件：开发、实现、写、功能实现
tags: [phase, executing, tdd]
requires:
  tools: [Bash, Read, Write, Grep, Glob, Edit]
---

# EXECUTING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

EXECUTING 阶段是 agentic-workflow 的核心实现阶段，负责：
- TDD 开发循环（红-绿-重构）
- 代码实现与重构
- PUA 铁律执行
- 频繁提交规则
- 子任务分发

## Entry Criteria

进入 EXECUTING 阶段的条件：
- PLANNING 阶段已完成（task_plan.md 已创建）
- 用户明确要求实现/开发/编写
- 任务已拆分为可执行的子任务
- HARD-GATE 设计门禁已通过

**快速模式**（满足任一条件）：
- 用户明确说"写一个XXX函数/工具/脚本"
- 任务仅涉及单一文件/单一功能
- 用户说"帮我写" + 短任务（<20字）

**快速模式说明**：
- 跳过状态跟踪：快速模式不创建/更新 task_plan.md
- 使用简化 Trajectory：记录在内存中，任务完成后可选择持久化
- 单任务执行：不触发并行机制

## Exit Criteria

退出 EXECUTING 阶段的条件：
- task_plan.md 中所有任务已完成
- 所有测试通过
- 质量门禁通过（typecheck/lint/test）
- 代码已提交（频繁提交规则）

## Core Process

### Step 1: TDD 红绿重构循环

**强制执行流程**：

```
1. 写失败测试 → 2. 运行确保失败 → 3. 最小实现 → 4. 运行确保通过 → 5. 重构
```

#### 红 (Red)
- 编写一个失败的测试
- 测试必须先运行并确认失败
- 使用 assert 而非 print 调试
- 覆盖边界条件（空值、负数、极大值、特殊字符）

#### 绿 (Green)
- 编写最少的代码让测试通过
- 不要过度实现
- 专注于让当前测试通过

#### 重构 (Refactor)
- 在保持功能的前提下优化代码
- 确保所有测试仍然通过
- 应用代码质量清单

### Step 2: PUA 铁律执行

#### 铁律一：穷尽一切
- 测试失败后，必须尝试至少3种本质不同的解决方案
- 禁止在尝试2种方案后说"无法解决"
- 每种方案必须有明确的验证标准

#### 铁律二：先做后问
- 遇到问题先自行搜索、读源码、验证
- 向用户提问前必须先附上已排查的证据

#### 铁律三：主动出击
- 修复后主动检查同类问题
- 完成后验证结果正确性
- 主动补充未明确说但合理的需求

### Step 3: 压力升级机制

| 失败次数 | 等级 | 动作 |
|---------|------|------|
| 2次 | L1 | 停止当前思路，切换本质不同的方案 |
| 3次 | L2 | 搜索完整错误+读源码+列出3个假设 |
| 4次 | L3 | 执行7项检查清单，列出3个全新假设 |
| 5次+ | L4 | 最小PoC+隔离环境+完全不同的技术栈 |

### Step 4: 频繁提交规则

**提交时机**：

| 动作完成 | 必须提交 |
|---------|---------|
| 完成一个函数/方法 | ✅ |
| 完成一个测试用例 | ✅ |
| 完成一个小功能模块 | ✅ |
| 修复一个 bug | ✅ |
| 完成重构（行为不变） | ✅ |

**提交信息规范**：
```
<type>: <简短描述>

<可选的详细说明>
```

**type 类型**：
- `feat`: 新功能
- `fix`: 修复 bug
- `refactor`: 重构（行为不变）
- `docs`: 文档更新
- `test`: 测试相关
- `chore`: 工具/构建变更

**禁止的行为**：
- ❌ 等待"完成所有功能后再提交"
- ❌ 创建超大 commit（超过 500 行变更）
- ❌ 在不相关的工作中间提交

### Step 5: Trajectory 持久化

**借鉴自 SWE-agent** - 记录每个任务的执行过程，支持回溯和断点恢复：

#### Trajectory 格式

```json
{
  "metadata": {
    "task_id": "TASK-001",
    "task_name": "<任务名>",
    "started_at": "<ISO timestamp>",
    "agent": "<agent-name>",
    "model": "<model-used>"
  },
  "trajectory": [
    {
      "step": 1,
      "action": "<执行的动作>",
      "observation": "<观察到的结果>",
      "thought": "<思考过程>",
      "state": {
        "open_file": "<当前打开的文件>",
        "working_dir": "<当前目录>",
        "modified_files": ["<变更的文件列表>"]
      },
      "timestamp": "<ISO timestamp>"
    }
  ],
  "decisions": [
    {
      "step": 2,
      "decision": "<决策描述>",
      "reasoning": "<决策原因>"
    }
  ],
  "challenges": [
    {
      "step": 3,
      "challenge": "<挑战描述>",
      "solution": "<解决方案>",
      "outcome": "<结果>"
    }
  ],
  "file_changes": [
    {
      "file": "<文件路径>",
      "action": "created|modified|deleted",
      "lines_added": <number>,
      "lines_removed": <number>
    }
  ]
}
```

#### Trajectory 存储

- 位置：`./trajectories/<task_id>_<timestamp>.json`
- 每个任务一个 trajectory 文件
- 任务完成后将 trajectory 摘要写入 task_plan.md 的 Dev Agent Record
- **自动创建目录**：如果 `./trajectories/` 不存在，自动创建

#### Trajectory 用途

1. **断点恢复**：任务中断后，可从 trajectory 最后一步恢复
2. **事后分析**：分析决策过程，识别改进点
3. **学习积累**：从 challenges 和 decisions 中提取可复用经验
4. **审计追踪**：完整记录谁在什么时候做了什么

#### Trajectory 记录时机

| 动作完成 | 记录 Trajectory | 说明 |
|---------|----------------|------|
| 完成一个关键决策 | ✅ | 影响架构/设计的重要决策 |
| 遇到并解决挑战 | ✅ | 任何意外问题及其解决 |
| 完成一个文件变更 | ✅ | 创建/修改/删除文件时 |
| 完成任务状态转换 | ✅ | 状态变更时记录 |
| 遇到执行错误 | ✅ | 错误信息和处理方式 |

**性能优化**：
- 批量写入：每 5 个步骤或每 30 秒写入一次（而非实时）
- 异步写入：不阻塞主执行流程
- 简化模式：对于简单任务可使用简化格式

#### Trajectory 简化模式

对于低复杂度任务，可使用简化格式：

```json
{
  "metadata": {"task_id", "task_name", "started_at", "agent"},
  "summary": "<一句话描述完成的工作>",
  "file_changes": [{"file", "action", "lines_added", "lines_removed"}],
  "issues_resolved": ["<问题描述>"],
  "completed_at": "<timestamp>"
}
```

### Step 6: 子任务分发

#### 强制原则：描述结果，而非方法

**CRITICAL**: 在委托子任务时，必须描述**WHAT（什么需要完成）**，而不是**HOW（如何实现）**。

```
✅ CORRECT: "实现用户认证功能，创建 src/auth/login.ts 和 src/auth/register.ts"
✅ CORRECT: "修复导航菜单的无限循环错误"
✅ CORRECT: "创建深色模式配色方案和切换组件"

❌ WRONG: "通过在 useEffect 中添加 useShallow 来修复状态管理问题"
❌ WRONG: "使用装饰器模式重构代码"
❌ WRONG: "先建 context 再写 provider 最后添加 hooks"
```

**为什么重要**:
- 子 agent 是领域专家，比协调者更懂如何实现
- 指定实现方法会限制 agent 的创造力
- 专家模拟原则要求"不问怎么做，问谁最懂"

**约束类型分类**（判断标准）

委托描述中可以包含约束，但必须是以下类型之一：

| 约束类型 | 描述 | 示例 | 是否允许 |
|----------|------|------|---------|
| **输出约束** | 对最终输出的格式/质量要求 | "输出必须是有效的 JSON" | ✅ 允许 |
| **安全约束** | 安全相关的要求 | "必须防止 SQL 注入" | ✅ 允许 |
| **合规约束** | 项目规范/编码标准 | "必须符合 PEP8 规范" | ✅ 允许 |
| **接口约束** | 明确的 API/类型定义 | "必须实现 UserService 接口" | ✅ 允许 |
| **环境约束** | 运行环境/依赖要求 | "必须兼容 Node 18+" | ✅ 允许 |
| **实现建议** | 如何实现的建议 | "使用装饰器模式" | ❌ 禁止 |
| **技术选择** | 具体技术方案 | "用 useCallback 而非 useMemo" | ❌ 禁止 |

**判断原则**：约束是对**结果**的限制（允许）还是对**过程**的指导（禁止）？

```
✅ 正确示例："实现支付模块，输出必须是 JSON 格式，必须使用参数化查询"
❌ 错误示例："使用装饰器模式实现支付模块"
```

#### 委托格式

```
## 任务委托

**目标**: <清晰描述要完成的结果>

**文件作用域**:
- <具体文件路径>

**验收标准**:
- <可验证的完成条件>

**上下文**:
- <必要的背景信息（不要告诉如何实现）>
```

#### 执行要点

- 独立任务 → 新子 agent
- 传递精确上下文
- 两阶段审查
- 使用 coder 子智能体执行实现
- **禁止**在委托描述中包含实现细节

### Step 7: 每3个动作重读 task_plan.md

- 每执行3个动作后，重新读取 task_plan.md
- 确认当前进度与计划一致
- 根据需要更新进度

## TDD 强制检查清单

**适用范围**：功能开发、bug修复、重构等代码任务

**不适用**：文案创作、问题解答、数据分析、艺术创作

在写任何代码前，必须确认：

- [ ] 是否已创建测试文件？（test_*.py, *_test.go, *.spec.ts）
- [ ] 测试是否先运行失败？（red-green-refactor）
- [ ] 是否使用 assert 而非 print 调试？
- [ ] 是否覆盖边界条件？（空值、负数、极大值、特殊字符）
- [ ] 是否验证了同行代码的同类问题？

## 主动出击清单

完成任何功能实现后，必须逐项检查：

- [ ] 实现是否经过验证？（运行测试、实际执行）
- [ ] 同文件/同模块是否有类似问题？
- [ ] 上下游依赖是否受影响？
- [ ] 是否有边界情况没覆盖？
- [ ] 是否有更好的方案被忽略？
- [ ] 用户没有明确说的部分是否主动补充？

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| **DONE** | 任务完成 | 所有任务完成，测试通过，质量门禁通过 |
| **DONE_WITH_CONCERNS** | 完成但有顾虑 | 任务完成但有已知问题未解决 |
| **BLOCKED** | 被阻塞 | 依赖外部资源或等待用户决策 |
| **NEEDS_CONTEXT** | 需要更多上下文 | 信息不足无法继续 |

### 输出格式

```
## Completion Status

**状态**: [DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT]

**详情**:
- [具体状态说明]

**剩余工作** (如适用):
- [未完成的任务列表]

**阻塞因素** (如适用):
- [阻塞原因]
```

### 决策规则

1. **DONE**: 所有验收标准满足
2. **DONE_WITH_CONCERNS**: 功能完成但存在已知技术债务或次要问题
3. **BLOCKED**: 等待外部依赖、API、用户输入或其他不可控因素
4. **NEEDS_CONTEXT**: 需求不清晰、上下文不足、需要用户澄清

### 状态转换

```
EXECUTING
    ↓
[所有任务完成?] ─No─→ 继续执行
    │
   Yes
    ↓
[测试通过?] ─No─→ 修复测试
    │
   Yes
    ↓
[质量门禁通过?] ─No─→ 修复问题
    │
   Yes
    ↓
[有阻塞因素?] ─Yes─→ BLOCKED
    │
   No
    ↓
[有已知问题?] ─Yes─→ DONE_WITH_CONCERNS
    │
   No
    ↓
   DONE → REVIEWING
```
