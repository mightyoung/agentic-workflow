<!-- tier:70% -->

# EXECUTING — Full

## Overview

EXECUTING 阶段负责把计划转成实际变更。

默认策略: `default_enable`。上游返回的 `skill_policy` 是 canonical 决策，`use_skill` 只是执行结果。

当前真实能力聚焦在：
- 基于 `.specs/<feature>/tasks.md` 和 `.contract.json` 执行任务
- TDD 或最小可验证实现
- 使用项目内状态文件
- 使用 `run_tracker.py` / `step_recorder.py` 做轻量执行追踪
- 先读取当前 phase 上下文里的 `memory_hints`、`memory_query` 和 `memory_intent`，避免重复踩已经被修复过的失败模式
- 复用 `planning_summary` / `research_summary` / `thinking_summary` / `review_summary` 作为执行上下文，不再让 EXECUTING 自己重算上游已经完成的结论
- `progress.md` / `context_for_next_phase` / checkpoint / resume 会携带同一套摘要，便于执行中断后无损续接

## Core Process

### Step 1 — Read The Current Plan

如果项目内存在 `.specs/<feature>/tasks.md` 或 `.contract.json`，先读取并确认：
- 当前要做哪一项
- 影响哪些文件
- 如何验证

如果不存在：小任务可直接执行；中等及以上应先回到 PLANNING 创建计划。

### Step 1.5 — Parallel Agent Dispatch（M/L/XL 复杂度）

当任务包含 **≥2 个相互独立的 P0 子任务** 时，使用并行 agent 而非串行执行。

**注意**：并行 agent 使用 Claude Code 的 Agent tool（`run_in_background: true`），**不是** Python subprocess。

#### 1.5.1 子 Agent 输出 Schema 验证（AgentSys，arXiv 2602.07398）

受 AgentSys 层级隔离思路启发：子 agent 返回结果必须通过 schema 验证，非法/畸形输出丢弃并重试，防止脏数据污染主执行上下文。

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

### Step 2 — Prefer TDD When Practical

推荐顺序：
1. 写或补失败测试
2. 最小实现
3. 跑验证
4. 必要时重构

如果不适合 TDD，也至少要有清晰验证路径，例如：`pytest`、单个测试文件、构建命令、手动验证步骤。

### Step 2.5 — TASK_NOTES Rolling Update（P0-C）

每完成一个 P0 任务后，**必须**更新 `SHARED_TASK_NOTES.md`（跨迭代上下文桥接）：

```markdown
## [任务 ID] [任务名] — [完成时间]
- **完成情况**: DONE / DONE_WITH_CONCERNS
- **关键决策**: [本任务做出的重要架构/逻辑决策]
- **遗留问题**: [未解决或需下一步跟进的点]
- **影响文件**: [修改的文件列表]
```

**更新规则**：
- 每个 P0 任务结束时追加一条，不修改历史记录
- 超过 20 条时，将最旧的 10 条合并为摘要 `## [Archived N entries]`
- 并行 agent 收到任务时，**必须先读** SHARED_TASK_NOTES.md

### Step 2.7 — Mid-Task Reflection Checkpoint（Reflexion，arXiv 2303.11366）

受 Reflexion 启发：每完成一个 P0 任务后，自动检索因果记忆，在犯已知错误之前拦截，而非事后修复。

**触发条件**：每个 P0 任务完成后（状态变为 DONE/DONE_WITH_CONCERNS）自动执行。

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

### Step 3 — Keep State Local

默认使用项目内文件：
- `.workflow_state.json`
- `.specs/<feature>/tasks.md`
- `.contract.json`
- `task_plan.md`（legacy）
- `progress.md`
- `SHARED_TASK_NOTES.md`（跨迭代上下文）

### Step 4 — Use Real Tracking Scripts

如果要记录执行统计，使用真实脚本：

```bash
python3 scripts/run_tracker.py --op=start --run-id=R001 --category=EXECUTING
python3 scripts/step_recorder.py --op=start --run-id=R001 --phase=EXECUTING
python3 scripts/step_recorder.py --op=end --run-id=R001 --phase=EXECUTING --output-tokens=500
python3 scripts/run_tracker.py --op=finish --run-id=R001 --status=success
```

当前仓库默认产物：`.run_tracker.json`、`.step_records.json`

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

## Validation Commands

```bash
test -f .contract.json || test -f task_plan.md
python3 scripts/run_tracker.py --op=stats
```
