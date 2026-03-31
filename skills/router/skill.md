---
name: router
version: 1.6.0
status: implemented
description: |
  轻量路由 - 基于当前脚本实现选择工作流阶段
  顺序：负面过滤 → 强制触发 → 阶段关键词匹配
tags: [phase, routing, core]
requires:
  tools: [Read, Write]
---

# ROUTER

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

ROUTER 是 agentic-workflow 的入口阶段，负责把用户消息映射到一个当前已实现的入口结果。

### 核心职责

- 识别是否跳过工作流直接回答
- 识别是否进入完整流程
- 在 `RESEARCH / THINKING / PLANNING / DEBUGGING / REVIEWING / EXECUTING` 中选择一个阶段
- 为后续 phase 提供一个简单、可复现的入口规则

## Current Implementation

当前真实逻辑以 [scripts/router.py](/Users/muyi/Downloads/dev/agentic-workflow/scripts/router.py) 为准。

路由顺序如下：

1. `check_negative_trigger(text)`
2. `check_force_trigger(text)`
3. `detect_stage(text)`

返回值格式：

```python
(trigger_type, stage)
```

其中：

- `("DIRECT_ANSWER", "闲聊")`
- `("FULL_WORKFLOW", "完整流程")`
- `("STAGE", "<PHASE>")`

## Actual Routing Rules

### 1. Negative Filter

如果消息包含明显闲聊词，并且不含开发上下文，则直接回答，不触发工作流。

示例负面词：

- `天气`
- `笑话`
- `你好`
- `谢谢`
- `hello`

示例开发上下文词：

- `开发`
- `代码`
- `帮我`
- `问题`
- `需要`

### 2. Force Trigger

如果消息包含以下强制词，直接进入 `FULL_WORKFLOW`：

- `/agentic-workflow`
- `继续`
- `继续下一步`
- `继续任务`
- `下一步`
- `继续执行`

### 3. Stage Detection

如果没有命中前两层，则按 `ROUTE_KEYWORDS` 的顺序做关键词匹配。

当前顺序是：

1. `RESEARCH`
2. `THINKING`
3. `PLANNING`
4. `DEBUGGING`
5. `REVIEWING`
6. `EXECUTING`

说明：

- 这是顺序匹配，不是语义理解
- 如果一个 prompt 同时命中多个阶段，先命中的阶段获胜
- 如果没有任何关键词命中，则默认 `EXECUTING`

## Implemented Vs Planned

以下能力当前没有在 [scripts/router.py](/Users/muyi/Downloads/dev/agentic-workflow/scripts/router.py) 中实现，不应视为已落地：

- preload detection
- 环境检查前置链路
- `~/.gstack` 会话状态验证
- 多层复杂度评估
- L3 语义理解
- 基于会话历史的动态重路由
- `/research`、`/planning` 等完整显式命令体系

这些内容如果保留，必须明确标为目标设计，而不是当前行为。

## Entry Criteria

ROUTER 阶段在以下情况被调用：

1. 会话开始
2. 阶段完成后需要决定下一步
3. 用户明确要求重新分析任务

## Exit Criteria

ROUTER 阶段完成的条件：

- [ ] 已完成负面过滤
- [ ] 已检查强制触发
- [ ] 已选择目标阶段
- [ ] 如需记录状态，调用现有脚本而不是假定 telemetry API

## Validation

最小验证命令：

```bash
python3 scripts/router.py "帮我搜索最佳实践"
python3 scripts/router.py "修复这个bug"
python3 tests/run_phase_test.py
```
