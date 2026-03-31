---
name: planning
version: 1.1.0
status: implemented
description: |
  规划阶段 - 任务拆分和计划制定
  当前版本对齐项目内 task_plan.md 与真实脚本 create_plan.sh
  注意: 自动任务分解(ID/依赖/优先级)能力在 task_decomposer.py 中实现
tags: [phase, planning]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# PLANNING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

PLANNING 阶段负责把任务拆成可以执行和验证的步骤，并生成项目内的 [task_plan.md](/Users/muyi/Downloads/dev/agentic-workflow/task_plan.md)。

当前真实实现以以下文件为准：

- [scripts/create_plan.sh](/Users/muyi/Downloads/dev/agentic-workflow/scripts/create_plan.sh)
- [scripts/win/create_plan.bat](/Users/muyi/Downloads/dev/agentic-workflow/scripts/win/create_plan.bat)
- [references/templates/task_plan.md](/Users/muyi/Downloads/dev/agentic-workflow/references/templates/task_plan.md)

## Entry Criteria

满足以下任一条件时进入 PLANNING：

- 用户要求计划、规划、拆分
- 任务明显涉及多个文件或步骤
- 执行前需要先定义范围、验收和顺序

## Exit Criteria

满足以下条件时退出：

- `task_plan.md` 已创建
- 任务至少按优先级拆分为可执行项
- 每个关键任务都有验收方式
- 已明确非目标范围，避免过度设计

## Current File Conventions

当前仓库统一使用项目内文件：

- `task_plan.md`
- `SESSION-STATE.md`
- `progress.md`

不再把 `task_plan_YYYY-MM-DD.md` 或 `~/.gstack/...` 视为默认标准。

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

### 3. Create The Plan File

推荐命令：

```bash
bash scripts/create_plan.sh "任务名称" .
```

该命令会生成项目内的 `task_plan.md`，并基于模板填入任务名称和时间戳。

### 4. Refine Manually

脚本生成的是最小骨架，随后应根据真实任务补充：

- 任务分解
- owned files
- 风险
- 验证命令

## Minimal Plan Schema

`task_plan.md` 应至少包含：

- `Summary`
- `Goals`
- `Non-Goals`
- `Task Breakdown`
- `Risks`
- `Verification`

## Validation

最小验证命令：

```bash
bash scripts/check_template.sh .
bash scripts/create_plan.sh "示例任务" .
```

Windows:

```bat
scripts\win\check_template.bat .
scripts\win\create_plan.bat "示例任务" .
```

## Implemented Vs Planned

以下内容当前不应视为已落地的 planning runtime：

- 复杂状态机自动推进
- Dev Agent Record 自动持久化
- trajectory 自动写回 `task_plan.md`
- HARD-GATE 自动评分系统

这些能力如果需要，应在脚本层实现后再回填文档。
