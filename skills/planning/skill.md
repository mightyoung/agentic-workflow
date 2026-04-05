---
name: planning
version: 1.2.0
status: implemented
description: |
  规划阶段 - 任务拆分和计划制定
  正式规划链: .specs/<feature>/spec.md → plan.md → tasks.md → .contract.json
  task_plan.md 已降级为兼容投影层，供旧 runtime/frontier 读取
tags: [phase, planning]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# PLANNING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

PLANNING 阶段负责把任务拆成可以执行和验证的步骤。

**正式规划链** (spec-kit):
1. `.specs/<feature>/spec.md` - 用户故事和需求
2. `.specs/<feature>/plan.md` - 技术方案和约束
3. `.specs/<feature>/tasks.md` - 可执行任务清单
4. `.contract.json` - 履约契约（goals/verification/owned_files）

**兼容投影层** (legacy):
- `task_plan.md` - 仍可读取，供旧 runtime/frontier 使用
- 不再作为主要输出

## Entry Criteria

满足以下任一条件时进入 PLANNING：

- 用户要求计划、规划、拆分
- 任务明显涉及多个文件或步骤
- 执行前需要先定义范围、验收和顺序

## Exit Criteria (按复杂度分级)

<HARD-GATE name="planning-exit-gate">
根据复杂度，以下条件必须全部满足才能退出 PLANNING 进入 EXECUTING：

**XS/S**: TodoWrite 已列出所有任务项（每项有验收标准）
**M**: `.specs/<feature>/tasks.md` 已创建 + `.contract.json` 已生成
**L/XL**: 完整 spec-kit 已创建 + `.contract.json` 非 draft + 每个 P0 任务有 owned_files

禁止在没有任何计划产出的情况下进入 EXECUTING。
</HARD-GATE>

**Iron Law**: `NO EXECUTING WITHOUT A PLAN FIRST`

### XS/S 复杂度（简单任务）
- 使用 TodoWrite 列出任务项即可，**跳过 .specs/ 流程**
- 不需要 .contract.json

### M 复杂度（中等任务）
- `.specs/<feature>/spec.md` 已创建（用户故事 + 验收标准）
- `.specs/<feature>/plan.md` 已创建（技术方案 + 约束）
- `.specs/<feature>/tasks.md` 已创建（可执行任务清单）
- `.contract.json` 已创建或准备生成（用于履约门禁）
- `task_plan.md` 仅作为 legacy 投影，可选生成

### L/XL 复杂度（复杂任务）
- `.specs/<feature>/spec.md` 已创建（用户故事 + 验收标准）
- `.specs/<feature>/plan.md` 已创建（技术方案 + 约束）
- `.specs/<feature>/tasks.md` 已创建（可执行任务清单）
- `.contract.json` 已创建（非 draft 状态）
- 每个关键任务都有验收方式和 owned_files

## Auto-Verify

```bash
# 优先验证正式 spec 链；legacy task_plan 仅在兼容模式下接受
test -d .specs && find .specs -mindepth 1 -type f | grep -q . || test -f task_plan.md
```

## Current File Conventions

**正式规划链** (spec-kit):

| 阶段 | 文件 | 说明 |
|------|------|------|
| 需求 | `.specs/<feature>/spec.md` | 用户故事、验收标准 |
| 方案 | `.specs/<feature>/plan.md` | 技术方案、约束 |
| 任务 | `.specs/<feature>/tasks.md` | 可执行任务清单 |
| 履约 | `.contract.json` | 履约契约 |

**兼容投影层** (legacy, 只读):
- `task_plan.md` - 旧 runtime/frontier 仍可读取

## Core Process

### 1. Clarify Scope

- 提炼一句话目标
- 识别硬约束
- 明确不做什么

### 2. Break Work Down

优先拆成 P0 / P1 / P2：

- `P0`: 不完成就无法交付
- `P1`: 重要但不阻塞主路径
- `P2`: 优化项

每个任务至少包含：

- `status`
- `description`
- `acceptance`
- `owned_files`
- `verification`

### 3. Create Spec Artifacts

使用 workflow_engine 创建规范文件：

```bash
python3 scripts/workflow_engine.py --op init --prompt "任务描述"
```

或手动创建规范链：

```bash
mkdir -p .specs/<feature>/
# 创建 spec.md, plan.md, tasks.md
```

### 4. Create Contract

基于 plan.md 和 tasks.md 创建履约契约：

```bash
python3 -c "from contract_manager import create_phase_contract; create_phase_contract('任务名', '描述', '.')"
```

### 5. Output Contract Visualization（PLANNING 结束时必须输出）

PLANNING 阶段结束时，**必须**向用户输出可读的履约摘要：

```markdown
## 📋 任务契约

**目标**: {一句话目标}
**复杂度**: {XS/S/M/L/XL}
**预计阶段**: {阶段序列}

### P0 任务（必须完成）
- [ ] {任务1} — 验收: {验收条件}
- [ ] {任务2} — 验收: {验收条件}

### P1 任务（重要）
- [ ] {任务3}

### 明确不做
- {不在范围内的事项}

**进入 EXECUTING 后，AI 将按上述顺序逐项执行。**
```

此摘要让用户在 EXECUTING 开始前确认范围，避免执行偏差。

## Minimal Plan Schema

**spec.md** 应包含：

- 用户故事 (### Story N:)
- 验收标准 (**Acceptance Criteria:**)
- 成功标准 (## Success Criteria)
- 约束条件 (## Constraints)

**plan.md** 应包含：

- ## Goals
- ## Technical Context
- ## Structure Decisions
- ## Constraints

**tasks.md** 应包含：

- ## User Story 1
- ## User Story 2
- 每个任务含 Files, Verification, Blocked-By

## Validation

最小验证命令：

```bash
# 使用 spec-kit 验证工具
bash scripts/check_template.sh .

# 创建规范链（spec -> plan -> tasks -> contract）
python3 -m task_decomposer --from-spec --feature-id myfeature
python3 -c "from contract_manager import create_phase_contract; create_phase_contract('任务名', '描述', '.')"
```

Windows:

```bat
scripts\win\check_template.bat .
```

## Implemented Vs Planned

以下内容当前不应视为已落地的 planning runtime：

- 复杂状态机自动推进
- Dev Agent Record 自动持久化
- trajectory 自动写回 `task_plan.md`
- HARD-GATE 自动评分系统

这些能力如果需要，应在脚本层实现后再回填文档。
