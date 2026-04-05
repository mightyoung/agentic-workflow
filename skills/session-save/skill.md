---
name: session-save
version: 1.0.0
status: implemented
description: |
  会话保存 - 保存当前工作状态，以便在新会话中恢复
  对应 session-resume 技能
tags: [session, state, persistence]
requires:
  tools: [Bash, Read, Write]
---

# SESSION-SAVE

## Overview

保存当前工作进度，使下次会话能够无缝恢复。适用于：
- 长任务中途暂停
- 切换上下文前
- 会话将结束时

## Entry Criteria

- 用户说："保存"/"暂停"/"先停这里"/"save"
- 上下文即将用完（最后 20% 时主动建议保存）

## Core Process

### Step 1: 收集当前状态

```bash
# 工作流状态
python3 scripts/workflow_engine.py --op status --workdir . 2>/dev/null

# Git 状态（未提交变更）
git status --short
git stash list | head -5

# 当前任务进度
cat .workflow_state.json 2>/dev/null | python3 -c "
import json,sys
s = json.load(sys.stdin)
print(f'Phase: {s.get(\"phase\",\"unknown\")}')
print(f'Task: {s.get(\"task\",\"unknown\")[:100]}')
print(f'Session: {s.get(\"session_id\",\"unknown\")}')
"
```

### Step 2: 暂存未提交工作

```bash
# 如果有未提交变更，创建 WIP commit 或 stash
git diff --stat | grep -q . && git stash push -m "wip: $(date +%Y-%m-%d) session save"
```

### Step 3: 生成恢复摘要

写入 `.session_resume.md`（供下次会话读取）：

```markdown
# Session Resume Point — {datetime}

## 未完成任务
{task_description}

## 当前阶段
- Phase: {current_phase}
- 已完成步骤: {completed_steps}
- 下一步: {next_action}

## 关键文件
- {file1}: {what_was_done}
- {file2}: {what_was_done}

## 注意事项
- {important_context}

## 恢复命令
\`\`\`bash
python3 scripts/workflow_engine.py --op resume --workdir .
\`\`\`
```

### Step 4: 输出确认

```
✓ 会话已保存
  Session: {session_id}
  Phase: {phase}
  恢复：输入 "继续" 或使用 /session-resume
```
