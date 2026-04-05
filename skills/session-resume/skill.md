---
name: session-resume
version: 1.0.0
status: implemented
description: |
  会话恢复 - 从上次保存点恢复工作状态
  对应 session-save 技能，也响应 "继续" 关键词
tags: [session, state, resume]
requires:
  tools: [Bash, Read, Write]
---

# SESSION-RESUME

## Overview

从上次保存点恢复工作状态，无需用户重新解释上下文。

## Entry Criteria

- 用户说："继续"/"resume"/"恢复"/"上次"
- 用户说："从哪停的？"/"我们做到哪了？"
- 会话开始时检测到 `.workflow_state.json` 存在

## Core Process

### Step 1: 读取保存点

```bash
# 读取工作流状态
python3 scripts/workflow_engine.py --op status --workdir . 2>/dev/null

# 读取 session resume 文件（如存在）
test -f .session_resume.md && cat .session_resume.md

# 读取 workflow state
cat .workflow_state.json 2>/dev/null | python3 -c "
import json,sys
try:
    s = json.load(sys.stdin)
    print('Phase:', s.get('phase','unknown'))
    print('Task:', s.get('task','unknown')[:150])
    print('Session:', s.get('session_id','unknown'))
    meta = s.get('metadata',{})
    if meta.get('complexity'):
        print('Complexity:', meta['complexity'])
    if meta.get('phase_sequence'):
        print('Sequence:', ' → '.join(meta['phase_sequence']))
except:
    print('No state found')
"

# 检查是否有 WIP stash
git stash list | grep -i "wip" | head -3
```

### Step 2: 恢复未提交变更

```bash
# 如果有 WIP stash，恢复它
git stash list | grep -iq "wip" && git stash pop
```

### Step 3: 输出恢复摘要

向用户报告当前状态：

```
## 会话恢复

**上次会话**: {session_id}
**当前阶段**: {phase} ({current_step}/{total_steps})
**任务**: {task_description}

**已完成**:
- {completed_item_1}
- {completed_item_2}

**下一步**: {next_action}

继续执行？
```

### Step 4: 继续执行

确认用户意图后，直接从上次中断的阶段继续，无需重新 PLANNING。

<HARD-GATE name="resume-continuity">
恢复后禁止重新走完整流程（除非用户明确要求重新开始）。
已完成的阶段不得重复执行。直接从 current_phase 继续。
</HARD-GATE>
