---
name: complete
version: 1.0.0
description: |
  完成阶段 - 收尾工作、自反思和状态更新
  包含：SESSION-STATE.md 更新、自反思日志、WAL 模式晋升、VBR 验证清单
tags: [phase, complete]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# COMPLETE

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

COMPLETE 阶段是工作流的最终阶段，负责任务收尾、自反思和状态持久化。

## Entry Criteria

进入 COMPLETE 阶段的条件：
- REVIEWING 阶段已完成
- 所有质量门禁通过（或用户确认跳过）
- 任务目标已达成或用户确认中止

## Exit Criteria

退出 COMPLETE 阶段的条件：
- SESSION-STATE.md 已更新
- 自反思日志已写入
- VBR 验证清单已确认
- 可选：MEMORY.md 已提炼（如有重要经验）

## Core Process

### Step 1: VBR 验证清单

在报告完成前，必须确认以下各项全部通过：

```markdown
## VBR 验证清单

- [ ] **测试通过** - 所有测试用例通过
- [ ] **质量门禁通过** - typecheck/lint/test 全部绿灯
- [ ] **无硬编码 secrets** - 代码中无 API keys、passwords、tokens
- [ ] **验证输出已生成** - 功能从用户视角验证可用
- [ ] **SESSION-STATE 已更新** - 任务结果、决策、偏好已记录
- [ ] **自反思已完成** - 结构化反思日志已写入
```

**如果任何项未通过**，输出决策卡片：

```
┌─────────────────────────────────────┐
│ ⚠️ VBR 验证未通过                    │
│                                     │
│ 未通过项: [列出未通过的项目]         │
│                                     │
│ [1] 修复问题后重试                  │
│ [2] 手动审查后再试                 │
│ [3] 跳过并继续                     │
└─────────────────────────────────────┘
```

**遥测记录**:
```bash
# 阶段进入
phase_enter "complete"

# VBR 检查通过时
VBR_PASS_COUNT=6
VBR_TOTAL_COUNT=6
VBR_PASS_RATE=$(echo "scale=2; $VBR_PASS_COUNT / $VBR_TOTAL_COUNT" | bc)
metric_record "vbr_pass_rate" "$VBR_PASS_RATE" "ratio" "complete"
decision_record "vbr_check" "验证清单检查" "PASSED" "items: $VBR_PASS_COUNT/$VBR_TOTAL_COUNT"

# VBR 检查失败时
error_record "vbr_failed" "medium" "VBR 检查未通过: $FAILED_ITEMS" "user_acknowledged" "true"
```

### Step 2: Document Preview (Optional)

如果任务产出需要预览文档渲染效果：

```bash
# 使用 Browser Daemon 预览 Markdown 文档
try:
    skill("gstack", "/preview", context={
        "document": DOC_PATH,
        "format": "markdown"
    })
except SkillNotFound:
    # Fallback - 提供手动预览指令
    echo "Open $DOC_PATH in browser for preview"
```

**Browser Daemon 预览能力** ({{include: ../_shared/browser-daemon.md}})：

| 操作 | 用途 |
|------|------|
| `/screenshot` | 截取渲染后的文档页面 |
| `/eval` | 执行 JavaScript 验证交互 |

**支持的预览格式**：
- Markdown (.md) - 渲染为 HTML 预览
- PDF - 截取 PDF 内容
- HTML - 直接在浏览器中打开

### Step 3: Release Gate (Optional)

如果任务需要发布：

```python
try:
    skill("gstack", "/ship")
except SkillNotFound:
    # Fallback - 提供手动发布检查清单
    manual_release_checklist()
```

**手动发布检查清单**:
- [ ] 代码已提交到版本控制
- [ ] 发布版本已打标签
- [ ] CHANGELOG 已更新
- [ ] 发布说明已准备

### Step 4: 更新 SESSION-STATE.md

将任务结果、关键决策、用户偏好更新到当前会话状态文件。

```bash
# 会话状态文件路径
SESSION_STATE_FILE="${HOME}/.gstack/sessions/${SESSION_ID:-default}/state.md"

# 确保会话目录存在
mkdir -p "$(dirname "$SESSION_STATE_FILE")"
```

更新以下内容：

```markdown
## 任务完成记录

### 当前任务
- task_id: {task_id}
- task_description: {任务描述}
- status: completed|partial|failed
- completed_at: {TIMESTAMP}

### 关键决策
- {决策点}: {选择} (原因: {原因})

### 用户偏好
- {偏好类型}: {偏好内容}
```

### Step 5: 自反思日志

完成任何任务后，进行结构化自反思：

```markdown
## 自反思日志

### 任务
[任务描述]

### 执行结果
- 状态: 成功/部分成功/失败
- 关键决策: [做了哪些决定]
- 用户反馈: [用户的纠正或确认]

### 观察
- 发现了什么: [执行中的观察]
- 意外情况: [未曾预料的问题]

### 教训
- 下次如何改进: [具体的改进建议]
- 模式识别: [是否是重复出现的模式]

### WAL 模式晋升检查
- 相似纠正次数: N
- 是否需要晋升: [是/否]
- 晋升规则: [如需晋升，描述规则内容]
```

### Step 6: WAL 模式晋升检查

如果检测到同一模式被纠正 3 次或以上，触发晋升确认：

```
┌─────────────────────────────────────┐
│ WAL 模式晋升检测                      │
│                                     │
│ 检测到3次相似纠正: "用户偏好使用 X"  │
│                                     │
│ [1] 确认并添加到 PATTERNS.md         │
│ [2] 暂时忽略                        │
│ [3] 查看历史记录                    │
└─────────────────────────────────────┘
```

**WAL 模式晋升规则**：
- 当同一模式被用户纠正 3 次或以上时
- 该模式可晋升为永久规则
- 永久规则存储在 PATTERNS.md

### Step 7: 可选提炼到 MEMORY.md

如果任务包含重要经验且可跨会话复用：

```bash
python scripts/memory_longterm.py --op=refine --days=7
```

### Step 8: 空闲检测机制

当用户在长时间(>30分钟)不活动后再次发送消息时：

1. **检测**: 读取 SESSION-STATE.md 的时间戳
2. **判断**: 如果 last_active > 30分钟，输出空闲恢复卡
3. **恢复**: 用户选择后从断点继续或开始新任务

```
┌─────────────────────────────────────┐
│ 💓 空闲检测                          │
│ 任务: 用户认证模块 (中断于EXECUTING)  │
│ 空闲时间: 45分钟                     │
│                                     │
│ [1] 从断点继续                      │
│ [2] 查看详细进度                    │
│ [3] 新任务                          │
└─────────────────────────────────────┘
```

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| **DONE** | 任务完全完成 | 所有目标达成，VBR 全部通过 |
| **DONE_WITH_CONCERNS** | 完成但有遗留问题 | 目标达成，VBR 有项未通过但用户确认可继续 |
| **BLOCKED** | 任务被阻塞 | 无法继续，等待外部条件或用户决策 |
| **NEEDS_CONTEXT** | 需要更多上下文 | 信息不足，需要用户提供更多信息 |

### 状态输出格式

```markdown
## 阶段完成状态

**Status**: [DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT]

**Summary**:
[一句话总结完成情况]

**Details**:
- 完成项: [列表]
- 未完成项: [列表，如有]
- 遗留问题: [列表，如有]

**Next Actions**:
- [建议的后续步骤，如有]
```

### 决策点集成

COMPLETE 阶段可能触发的决策点：

| 决策点 | 触发条件 | 用户选项 |
|--------|----------|----------|
| **VBR 失败** | 验证清单任一项未通过 | 修复/审查/跳过 |
| **WAL 晋升** | 3次以上相似纠正 | 确认规则/忽略/查看历史 |
| **空闲恢复** | 30分钟以上不活动 | 继续/查看进度/新任务 |
