---
name: gstack
version: 1.0.0
description: |
  gstack workflow integration - QA, Ship, and other specialized workflows
  This skill provides delegation to gstack specialized commands.
tags: [integration, gstack, qa, ship]
requires:
  tools: [Read, Write, Bash]
---

# gstack Skill

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

gstack 是专业工作流集成技能，提供 QA 测试和 Ship 发布等专业化工作流。

## Commands

| Command | Description |
|---------|-------------|
| `/qa` | 功能 QA 测试工作流 |
| `/ship` | 发布 Ship 工作流 |
| `/retro` | 独立回顾工作流 |

## Usage

```bash
# 调用 gstack QA 工作流
skill("gstack", "/qa", scope=TARGET_FILES)

# 调用 gstack Ship 工作流
skill("gstack", "/ship", scope=TARGET_SCOPE)

# 调用 gstack Retro 工作流
skill("gstack", "/retro")
```

## Command Details

### QA Workflow

详见: `commands/qa.md`

### Ship Workflow

详见: `commands/ship.md`

### Retro Workflow

详见: `commands/retro.md`

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}
