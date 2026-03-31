---
name: reviewing
version: 1.1.0
status: implemented
description: |
  审查阶段 - 代码质量、安全和性能审查
  当前版本对齐项目内 task_plan.md 与真实审查输出
tags: [phase, reviewing]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# REVIEWING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

REVIEWING 阶段负责对实现结果做质量审查，并输出可执行的问题清单。

当前真实口径：

- 以项目文件和实际变更为审查对象
- 以 `review_report.md` 或直接问题列表为主要输出
- 必要时参考 `task_plan.md` 确认范围
- 不假定存在 `phase_enter(...)`、`decision_record(...)`、`metric_record(...)` 之类 API

## Entry Criteria

进入 REVIEWING 的常见条件：

- 用户明确要求审查、review、检查、审计
- EXECUTING 已完成一轮实现
- 需要在 COMPLETE 前做质量门禁

## Exit Criteria

退出 REVIEWING 的条件：

- 致命问题已修复或明确记录
- 严重问题已记录并给出建议
- 用户已看到审查结论
- 后续流转到 DEBUGGING 或 COMPLETE

## Core Process

### 1. Define Scope

优先确定：

- 用户指定的文件
- 当前 diff
- `task_plan.md` 中本轮涉及的文件

如果范围不明确，应先缩小范围，不要做无边界审查。

### 2. Review By Dimension

建议至少覆盖这些维度：

- 代码正确性
- 安全性
- 性能风险
- 可维护性
- 测试覆盖

### 3. Use Real Outputs

如果需要落盘，使用项目内文件：

- `review_report.md`
- `findings.md`

如需辅助检查，可结合现有脚本或命令，例如：

```bash
bash scripts/quick_review.sh src/
pytest
```

### 4. Output Findings Clearly

建议按严重度输出：

```markdown
## 审查结论

### 🔴 致命
- 问题描述，位置，影响，修复建议

### 🟡 严重
- 问题描述，位置，影响，修复建议

### 🟢 建议
- 可优化项
```

### 5. Route After Review

- 有阻断问题：进入 DEBUGGING
- 无阻断问题：进入 COMPLETE

## Implemented Vs Planned

以下内容当前不应视为默认已实现：

- `phase_enter(...)`
- `decision_record(...)`
- `metric_record(...)`
- 自动汇总三类 reviewer 子代理结果的固定 runtime
- 自动 gstack QA / browser E2E 集成

这些能力如果需要，应作为可选增强或未来实现说明。

## Validation

最小验证动作：

```bash
test -f task_plan.md || true
test -f review_report.md || true
```
