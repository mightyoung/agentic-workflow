---
name: learn
version: 1.0.0
status: implemented
description: |
  学习提炼阶段 - 会话结束后提取可复用模式，写入长期记忆
  将 trajectory 中的成功/失败经验转化为持久 instincts
tags: [phase, learning, memory, post-session]
requires:
  tools: [Bash, Read, Write, Grep]
---

# LEARN

## Overview

LEARN 技能在任务完成后自动触发，从当前会话的执行轨迹中提取可复用的模式和经验，写入长期记忆库，供下次会话使用。

**核心价值**: 让每次任务完成后系统变得更聪明，而不是每次从零开始。

## Entry Criteria

以下情况触发 LEARN：

- 用户明确说："学习"/"记住"/"提炼经验"
- 任务完成后用户说："总结一下"/"记录一下"
- COMPLETE 阶段可选触发（复杂任务 M+ 后）

## Exit Criteria

<HARD-GATE name="learn-exit-gate">
LEARN 完成前必须：
1. 至少提取 1 条可复用模式（不是"这次做了X"，而是"当遇到Y情况时应该做Z"）
2. 已写入 memory_longterm.py 或 Claude Code 的 auto memory 系统
3. 输出的模式有具体触发条件和行动建议（可复用格式）
</HARD-GATE>

## Core Process

### Step 1: 提取会话关键事件

```bash
# 读取当前会话轨迹
python3 scripts/workflow_engine.py --op status --workdir . 2>/dev/null

# 查看最近的 git 变更（本次任务做了什么）
git log --oneline -5
git diff HEAD~1 --stat 2>/dev/null | head -20
```

### Step 2: 识别可复用模式

分析以下维度：

```
1. 成功模式（这次什么做对了？）
   - 问：如果下次遇到类似问题，我会用同样的方法吗？
   - 如果是 → 值得记录

2. 失败教训（这次踩了什么坑？）
   - 问：这个坑容易再次踩到吗？
   - 如果是 → 必须记录

3. 工具/命令发现（找到了什么有用的命令或工具？）
   - 问：以后还会用到吗？
   - 如果是 → 记录命令和场景

4. 假设被推翻（哪些预期是错的？）
   - 问：这个错误假设下次还可能犯吗？
   - 如果是 → 记录为反模式
```

### Step 3: 写入长期记忆

**方式 A — 使用 memory_longterm.py（项目级模式）**：

```bash
# 记录经验
python3 scripts/memory_longterm.py \
  --op add-experience \
  --exp "当遇到 [场景] 时，应该 [行动]，而不是 [常见误区]"

# 记录可复用模式
python3 scripts/memory_longterm.py \
  --op add-pattern \
  --pattern "[模式名称]" \
  --desc "[触发条件] → [推荐做法] → [预期效果]"
```

**方式 B — 使用 Claude Code auto memory（跨项目偏好）**：

对于跨项目通用的用户偏好，写入 `~/.claude/projects/.../memory/` 目录：

```markdown
# 用户偏好 / 反模式
- 类型: feedback
- 内容: 当 [具体场景] 时，用户偏好 [具体做法]
- 原因: [用户提供的原因或上次教训]
- 适用: 所有相关任务
```

### Step 4: 生成学习摘要

输出格式：

```markdown
## LEARN 摘要

### 本次会话亮点
- [做得好的1-2点，可复用]

### 模式提炼
| 触发场景 | 推荐行动 | 避免 |
|---------|---------|------|
| [场景] | [行动] | [反模式] |

### 已写入记忆
- [ ] 模式 N 条 → memory_longterm.py
- [ ] 偏好 N 条 → auto memory

### 下次注意
- [具体可执行的提醒]
```

## 模式质量标准

好的模式 vs 坏的模式：

| 好的（可复用）| 坏的（无用）|
|-------------|-----------|
| "当遇到 Python 3.9 类型注解报错时，先加 `from __future__ import annotations`" | "这次修复了一个类型错误" |
| "contract gate 对 STAGE trigger 不应启用，否则简单任务也被卡" | "今天修改了 contract_manager.py" |
| "REVIEWING 时先跑 git diff，再给意见，否则是假审查" | "完成了代码审查" |

**模式公式**: `当 [具体触发条件] 时 → [具体行动] → [因为/原因]`
