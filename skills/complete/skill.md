---
name: complete
version: 1.2.0
status: implemented
description: |
  完成阶段 - 收尾工作、自反思和状态更新
  当前版本对齐 .workflow_state.json 状态管理
  v1.2: 新增可选 learn 技能触发建议与总结摘要复用
tags: [phase, complete]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# COMPLETE

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

COMPLETE 阶段负责收尾、同步状态、记录经验，并给出清晰的结束状态。

当前真实口径：

- 使用项目内 `.workflow_state.json` 作为唯一状态源
- 必要时调用 `memory_longterm.py`
- 以文字总结、验证结果和后续建议为主
- 不假定存在 telemetry API、preview runtime 或 release runtime
- 会优先复用 `planning_summary` / `review_summary` / `research_summary` / `thinking_summary` / `resume_summary`
  中的结构化结论，避免 COMPLETE 再重复生成一份新的长摘要
- 结束前如果任务规模达到 M+，应把可复用经验交给 learn / memory_longterm，而不是只写一次性结论

## Entry Criteria

进入 COMPLETE 的常见条件：

- REVIEWING 已完成，或用户接受当前结果
- 本轮任务已经达到可交付状态
- 需要做最终同步与总结

## Exit Criteria

<HARD-GATE name="complete-exit-gate">
声称任务完成之前，必须：
1. 运行测试并看到通过结果（不得仅凭"我认为通过了"）
2. 更新 `.workflow_state.json`（phase = COMPLETE）
3. 输出明确的完成状态（DONE / DONE_WITH_CONCERNS / BLOCKED）

无验证证据 = 未完成。
</HARD-GATE>

**Iron Law**: `NO DONE WITHOUT EVIDENCE FIRST`

退出 COMPLETE 的条件（全部满足）：

- `.workflow_state.json` 已更新（phase 设为 COMPLETE）
- 验证状态已说明（有命令输出为证）
- 自反思或经验记录已补充
- 已明确输出 `DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT`

### 可选: 触发 LEARN

对于 M+ 复杂度的任务，COMPLETE 后建议触发 learn 技能提炼经验：

```bash
# 提炼本次会话模式
python3 scripts/memory_longterm.py --op refine --days 1
```

## Core Process

### 1. Run Final Verification Checklist

最小核对项：

- 测试是否通过
- 质量门禁是否通过
- 是否存在 secrets 风险
- 用户可见结果是否已验证
- 状态文件是否已同步

### 2. Update Project-Local State

更新 workflow 状态到完成：

```bash
python3 scripts/workflow_engine.py --op advance --phase COMPLETE --workdir .
```

如需写入可复用经验，可使用：

```bash
python3 scripts/memory_ops.py --op=update --key=task --value="任务描述"
```

### 3. Summarize The Outcome

建议至少说明：

- 本轮完成了什么
- 没完成什么
- 存在哪些风险或遗留项
- 下一步该做什么

### 4. Capture Reusable Learnings

如果本轮有可复用经验，可选择提炼：

```bash
python3 scripts/memory_longterm.py --op=refine --days=7
```

### 4.5. Summary Reuse Rules (新增)

COMPLETE 阶段不会重新推导上游已经算过的摘要，而是直接复用：

- `planning_summary`：用于说明计划是否 canonical / legacy / lightweight
- `research_summary`：用于说明证据是否 verified / degraded
- `review_summary`：用于说明审查是否完成、是否存在阻断项
- `thinking_summary`：用于保留本轮的调查结论和主要矛盾
- `resume_summary`：用于恢复场景下对齐前情

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| **DONE** | 任务完全完成 | 目标达成，验证通过 |
| **DONE_WITH_CONCERNS** | 完成但有遗留问题 | 主目标达成，但存在风险或未完成项 |
| **BLOCKED** | 任务被阻塞 | 缺少外部条件、权限或关键输入 |
| **NEEDS_CONTEXT** | 需要更多上下文 | 无法判断是否完成 |

### 推荐输出格式

```markdown
## 阶段完成状态

**Status**: DONE

**Summary**:
- 一句话说明完成情况

**Details**:
- 完成项
- 未完成项
- 遗留风险

**Next Actions**:
- 建议的后续动作
```

## Implemented Vs Planned

以下内容当前不应视为默认已实现：

- `phase_enter(...)`
- `metric_record(...)`
- `decision_record(...)`
- `error_record(...)`
- 自动文档预览 runtime
- 自动发布 gate runtime
- WAL 晋升自动固化规则

如果需要这些能力，应先在脚本层实现，再更新文档。

## Validation

最小验证动作：

```bash
test -f .workflow_state.json && python3 -c "import json; s=json.load(open('.workflow_state.json')); print(f'Phase: {s.get(\"phase\", \"unknown\")}')" || true
python3 scripts/memory_longterm.py --op=search --query="经验" || true
```
