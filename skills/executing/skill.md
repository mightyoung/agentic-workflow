---
name: executing
version: 1.3.0
status: implemented
description: |
  执行阶段 - TDD 开发循环和代码实现
  当前版本对齐 .specs/<feature>/tasks.md、.contract.json、run_tracker.py 和 step_recorder.py
  Reflexion 强化: mid-task reflection checkpoint + AgentSys 子 agent schema 验证
  v1.3: 新增 memory_hints/memory_query/memory_intent 复用
tags: [phase, executing, tdd, reflexion, agentsys]
requires:
  tools: [Bash, Read, Write, Grep, Glob, Edit]
---

# EXECUTING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

EXECUTING 阶段负责把计划转成实际变更。

默认策略: `default_enable`。当前主线会优先为 EXECUTING 保留 skill，上游返回的 `skill_policy`
是 canonical 决策，`use_skill` 只是执行结果。

当前真实能力聚焦在：

- 基于 `.specs/<feature>/tasks.md` 和 `.contract.json` 执行任务
- TDD 或最小可验证实现
- 使用项目内状态文件
- 使用 `run_tracker.py` / `step_recorder.py` 做轻量执行追踪
- 先读取当前 phase 上下文里的 `memory_hints`、`memory_query` 和 `memory_intent`，避免重复踩已经被修复过的失败模式

## Entry Criteria

进入 EXECUTING 的常见条件：

- 已存在 `.specs/<feature>/tasks.md` 或 `.contract.json`；`task_plan.md` 仅作 legacy fallback
- 用户明确要求实现、修复、编写
- 已经能识别出要修改的文件或目标结果

快速模式：

- 单文件、小任务、结果明确
- 可以跳过完整计划维护
- 但仍应保留最小验证动作

## Exit Criteria

<HARD-GATE name="executing-exit-gate">
以下条件必须全部满足才能退出 EXECUTING：
1. 目标代码已实现（Read 真实文件确认，不是"我以为写了"）
2. 相关测试已运行并通过（有命令输出为证）
3. 如有计划文件（tasks.md / TodoWrite），关键 P0 任务状态已同步

禁止仅凭"代码应该可以工作"退出。必须运行测试并看到通过结果。
</HARD-GATE>

**Iron Law**: `NO COMPLETE WITHOUT TESTS PASSING FIRST`

退出 EXECUTING 的条件：

- 目标代码已实现
- 相关验证已执行（测试命令输出为证）
- 如有 `.specs/<feature>/tasks.md` 或 legacy `task_plan.md`，关键任务状态已同步
- 需要时已进入 REVIEWING 或 COMPLETE

## Core Process

### 1. Read The Current Plan

如果项目内存在 `.specs/<feature>/tasks.md` 或 `.contract.json`，先读取并确认：

- 当前要做哪一项
- 影响哪些文件
- 如何验证

如果不存在：

- 小任务可直接执行
- 中等及以上任务应先回到 PLANNING 创建计划

### 1.5. Parallel Agent Dispatch (M/L/XL 复杂度)

当任务包含 **≥2 个相互独立的 P0 子任务** 时，使用并行 agent 而非串行执行。

**决策树**:

```
任务中有 ≥2 个独立子任务?
  ├─ 否 → 串行执行（常规流程）
  └─ 是 → 进一步判断
       子任务是否共享文件（会冲突）?
         ├─ 是 → 串行执行（避免冲突）
         └─ 否 → 并行派发（见模板）
```

**并行派发 Prompt 模板**（在 AI agent 层面使用 Agent tool）：

```
# 同时派发多个子任务时：
- Agent 1: 实现 <模块A>，只修改 <文件列表A>，完成后输出 DONE/DONE_WITH_CONCERNS
- Agent 2: 实现 <模块B>，只修改 <文件列表B>，完成后输出 DONE/DONE_WITH_CONCERNS
# 规则:
# - 每个 agent 只操作自己的文件，禁止跨越
# - 每个 agent 收到的上下文是最小必要上下文，不传递完整历史
# - 等所有 agent 返回 DONE 后，主流程继续
```

**注意**: 并行 agent 使用 Claude Code 的 Agent tool（`run_in_background: true`），**不是** Python subprocess。

#### 1.5.1 子 Agent 输出 Schema 验证 (AgentSys, arXiv 2602.07398)

> 受 AgentSys 层级隔离思路启发：子 agent 返回结果必须通过 schema 验证，
> 非法/畸形输出丢弃并重试，防止脏数据污染主执行上下文。

**子 agent 返回必须包含以下字段**（缺少任一则视为失败）：

```json
{
  "task_id": "T001",
  "status": "DONE | DONE_WITH_CONCERNS | FAILED",
  "files_changed": ["src/foo.py", "tests/test_foo.py"],
  "test_result": "PASS | FAIL | SKIPPED",
  "concerns": "可选：遗留问题描述"
}
```

**验证规则**：
| 检查项 | 规则 | 失败处理 |
|--------|------|---------|
| `status` 字段存在 | 必须是 DONE/DONE_WITH_CONCERNS/FAILED 之一 | 丢弃结果，重派 agent |
| `test_result` 字段存在 | 必须是 PASS/FAIL/SKIPPED 之一 | 丢弃结果，重派 agent |
| `files_changed` 非空 | 至少包含一个文件路径 | 警告但不阻塞 |
| 结果不含外部 raw 数据 | 不允许嵌入 API 响应体/网页内容 | 截断到 500 字符 |

**重派上限**：同一子任务最多重派 2 次，超过则标记为 FAILED 并由主流程接管。

### 2. Prefer TDD When Practical

推荐顺序：

1. 写或补失败测试
2. 最小实现
3. 跑验证
4. 必要时重构

如果不适合 TDD，也至少要有清晰验证路径，例如：

- `pytest`
- 单个测试文件
- 构建命令
- 手动验证步骤

### 2.5. TASK_NOTES Rolling Update (P0-C)

每完成一个 P0 任务后，**必须**更新 `SHARED_TASK_NOTES.md`（跨迭代上下文桥接）：

```markdown
# SHARED_TASK_NOTES.md 格式

## [任务 ID] [任务名] — [完成时间]
- **完成情况**: DONE / DONE_WITH_CONCERNS
- **关键决策**: [本任务做出的重要架构/逻辑决策]
- **遗留问题**: [未解决或需下一步跟进的点]
- **影响文件**: [修改的文件列表]
```

**更新规则**:
- 每个 P0 任务结束时追加一条，不修改历史记录
- 超过 20 条时，将最旧的 10 条合并为摘要 `## [Archived N entries]`
- 并行 agent 收到任务时，**必须先读** SHARED_TASK_NOTES.md

```bash
# 追加任务笔记（示例）
cat >> SHARED_TASK_NOTES.md << 'EOF'

## T001 实现用户认证 — 2026-04-05
- **完成情况**: DONE
- **关键决策**: 使用 JWT refresh token，有效期 7 天
- **遗留问题**: 未实现 token 吊销列表
- **影响文件**: src/auth.py, tests/test_auth.py
EOF
```

### 2.7. Mid-Task Reflection Checkpoint (Reflexion, arXiv 2303.11366)

> 受 Reflexion 启发：每完成一个 P0 任务后，自动检索因果记忆，
> 在犯已知错误之前拦截，而非事后修复。

**触发条件**：每个 P0 任务完成后（状态变为 DONE/DONE_WITH_CONCERNS）自动执行。

**执行流程**：

```bash
# Step 1: 检索与当前任务相关的已知因果链
python3 scripts/memory_longterm.py --op search-causal --query "<当前任务涉及的文件或模块名>"

# Step 2: 检索实体级历史（该文件曾经出过什么问题）
python3 scripts/memory_longterm.py --op search-entity --query "<主要修改的文件名>"
```

**反思决策矩阵**：

| 检索结果 | 动作 |
|---------|------|
| Signal 精确匹配（因果链命中） | **STOP** — 阅读 Fix 字段，检查本次实现是否已避免同一 Mistake |
| Entity 历史命中（文件有 bug 记录） | **WARNING** — 输出历史 bug 摘要，人工确认是否复现 |
| 无匹配 | **CONTINUE** — 继续下一个任务 |

**输出格式**（匹配时必须输出）：

```markdown
### Mid-Task Reflection — [任务 ID]
- **因果链匹配**: [Signal] → [Fix] (来自经验 #ID)
- **本次是否已规避**: [是/否 + 简要说明]
- **实体历史**: [文件名] 曾在 [日期] 出现 [问题描述]
- **决策**: CONTINUE / 需要补充修复
```

**注意**：如果 `memory_longterm.py` 或图索引不可用，静默跳过（不阻塞执行流）。

### 3. Keep State Local

默认使用项目内文件：

- `.workflow_state.json`
- `.specs/<feature>/tasks.md`
- `.contract.json`
- `task_plan.md`（legacy）
- `progress.md`
- `SHARED_TASK_NOTES.md`（跨迭代上下文，本阶段新增）

### 4. Use Real Tracking Scripts

如果要记录执行统计，使用真实脚本：

```bash
python3 scripts/run_tracker.py --op=start --run-id=R001 --category=EXECUTING
python3 scripts/step_recorder.py --op=start --run-id=R001 --phase=EXECUTING
python3 scripts/step_recorder.py --op=end --run-id=R001 --phase=EXECUTING --output-tokens=500
python3 scripts/run_tracker.py --op=finish --run-id=R001 --status=success
```

当前仓库默认产物是：

- `.run_tracker.json`
- `.step_records.json`

## Implemented Vs Planned

以下内容目前不应视为默认已实现能力：

- `./trajectories/<task_id>_<timestamp>.json`
- trajectory 自动断点恢复
- trajectory 自动回写 `task_plan.md`（legacy）
- 自动并行执行编排
- phase telemetry API

如果后续实现这些能力，应先补脚本，再升级文档。

## Practical Rules

### TDD

- 能测就先测
- 不能测时，至少先定义验证方式

### PUA Rules

- 穷尽一切：关键卡点不要只试一种思路
- 先做后问：先读代码、跑验证、收集证据
- 主动出击：修完当前点后顺手检查同类问题

### Commits

- 小步提交比大包提交更安全
- 不要混入无关改动

## Validation

最小验证：

```bash
test -f .contract.json || test -f task_plan.md
python3 scripts/run_tracker.py --op=stats
```
