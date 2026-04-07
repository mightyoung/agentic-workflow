---
name: using-agentic-workflow
version: 1.0.0
description: Use before ANY task — routes the request through the agentic-workflow pipeline and loads the correct phase skill
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<HARD-GATE name="skill-check-before-response">
STOP. Before responding to ANY user message, you MUST answer:
1. Is this a multi-step task, bug fix, feature, refactor, or research request?
2. If YES → apply agentic-workflow routing below.
3. If NO (pure Q&A, single-file trivial edit) → proceed directly.

YOU CANNOT SKIP THIS CHECK. Even "simple" tasks escalate.
</HARD-GATE>

## 路由规则（每次响应前检查）

| 场景 | 关键词 | 进入阶段 |
|------|--------|---------|
| 复杂任务/完整流程 | 开发/构建/设计/实现 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE |
| Bug修复 | bug/错误/调试/失败/报错 | DEBUGGING → EXECUTING → COMPLETE |
| 项目规划 | 计划/规划/拆分/架构 | PLANNING → EXECUTING |
| 技术调研 | 最佳实践/选型/怎么做/调研 | RESEARCH → THINKING |
| 代码审查 | 审查/review/检查/分析 | REVIEWING |
| 继续上次 | 继续/resume/恢复 | 读 `.workflow_state.json` 恢复 |
| 简单任务 | 其他（单文件改动/明确小任务） | 直接 EXECUTING |

## 进度格式（强制）

每进入新阶段时 **必须** 输出：

```
[N/M PHASE] 一句话描述当前要做什么
```

阶段完成时：

```
[N/M PHASE done] 一句话总结产出
```

## 阶段上下文传递（强制）

| 当前阶段 | 必须传给下一阶段 |
|---------|----------------|
| RESEARCH | `.research/findings/findings_{session}.md`（优先）或 `.research/findings/findings_latest.md` — THINKING 开始前读取 |
| THINKING | 分析结论 → PLANNING 基于结论创建 `.specs/<feature>/spec.md / plan.md / tasks.md / .contract.json` |
| PLANNING | `.specs/<feature>/tasks.md` / `.contract.json` → EXECUTING 逐项执行；`task_plan.md` 仅 legacy fallback |
| EXECUTING | 代码变更 → REVIEWING 运行 `git diff` |
| REVIEWING | `.reviews/review/review_{session}.md`（优先）或 `.reviews/review/review_latest.md` → REFINING 针对性修复 |

## Iron Law

```
NO PHASE SKIP — FULL_WORKFLOW 触发时禁止跳过任何必经阶段
NO FIX WITHOUT ROOT CAUSE — DEBUGGING 时禁止在未确认根因前修改代码
NO COMPLETE WITHOUT VERIFICATION — 禁止在未运行验证命令前声称任务完成
```

## Red Flags（自我检查）

如果你有以下想法，立刻停止 — 你在走捷径：

| 想法 | 现实 |
|------|------|
| "这是个简单问题，直接回答" | 简单问题也可能需要 DEBUGGING/REVIEWING |
| "先做再说，做完再计划" | PLANNING 在 EXECUTING 之前，顺序不可颠倒 |
| "用户没说要走完整流程" | FULL_WORKFLOW 触发词见上表，不需要用户显式声明 |
| "我已经知道答案了" | 先验证，再声称完成 |
| "REVIEWING 可以快速过一遍" | REVIEWING 必须运行 git diff + quality_gate + pytest |

## 搜索工具降级策略

RESEARCH 阶段按可用性自动降级：
1. **WebSearch** — Claude Code 原生，最优先
2. **WebFetch** — 已知 URL 时使用
3. **AI 知识库** — 所有搜索工具不可用时，**必须明确告知用户**，不得静默使用自身知识

## 验证前禁止完成

<HARD-GATE name="verification-before-complete">
宣称任务完成之前，必须：
1. 运行相关测试（pytest / npm test）并看到通过结果
2. 对于代码变更：运行 `git diff` 确认实际变更
3. 对于 REVIEWING：输出含具体 file:line 的审查意见

无证据 = 未完成。不得仅凭"我认为完成了"声称完成。
</HARD-GATE>
