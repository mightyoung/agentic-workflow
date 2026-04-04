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

### 1. Run Automatic Checks (Required)

**Before doing any manual review, run these commands:**

```bash
# View actual code changes in this session
git diff HEAD~1

# Run quality gate to catch automated issues
python3 scripts/quality_gate.py --workdir .

# Run tests to verify nothing broke
pytest -v
```

### 2. Define Scope

From the quality gate output and git diff, determine which files actually changed.
Do NOT review files that weren't modified.

优先确定：

- git diff 中显示的实际变更文件
- `task_plan.md` 中本轮涉及的文件
- quality_gate 报告的问题文件

如果范围不明确，应先缩小范围，不要做无边界审查。

### 3. Review Changed Files (Required)

For each file in the git diff, read the actual file content and analyze:
- Does the code do what the diff claims?
- Are there edge cases not handled?
- Are tests adequate?

输出格式必须包含具体文件:行号：

```markdown
## 审查结论

### 🔴 致命
- `src/user.py:42` - NPE when user.email is None: add null check

### 🟡 严重
- `src/auth.py:78` - SQL injection risk: use parameterized query

### 🟢 建议
- `tests/test_auth.py:15` - missing test for expired token
```

### 4. Route After Review

- 有阻断问题：进入 DEBUGGING
- 无阻断问题：进入 COMPLETE

## Validation

Minimum validation actions (required before completing review):

```bash
# 1. Git diff must be reviewed
git diff HEAD~1

# 2. Quality gate must be run
python3 scripts/quality_gate.py --workdir .

# 3. Tests must be run
pytest -v
```

All three must pass before exiting REVIEWING.
