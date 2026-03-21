---
name: gstack/retro
version: 1.0.0
description: |
  Standalone retrospective workflow - triggered explicitly via /retro
tags: [retro, retrospective, review]
requires:
  tools: [Read, Write, Bash]
---

# Retro Command

Standalone retrospective workflow - triggered explicitly via /retro

## Entry Criteria

- 用户明确要求 "/retro" 或 "回顾"

## Exit Criteria

- 回顾报告已生成
- 经验教训已记录

## Core Process

1. 收集本次任务的关键决策
2. 分析成功点和改进点
3. 生成可操作的建议
4. 输出回顾报告

## Retrospective Format

```markdown
# 回顾报告

## 任务概述
- 任务描述: {任务描述}
- 完成时间: {完成时间}
- 整体评价: {成功/部分成功/失败}

## 关键决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| {决策1} | {选择} | {原因} |
| {决策2} | {选择} | {原因} |

## 成功点

- {成功点1}
- {成功点2}

## 改进点

- {改进点1}
- {改进点2}

## 可操作建议

1. {建议1}
2. {建议2}
3. {建议3}

## 模式识别

- {识别到的模式}
- {是否是重复出现的模式}

## 下次行动计划

- {下次遇到类似任务时的具体行动}
```
