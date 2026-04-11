<!-- tier:100% -->

# EXECUTING — Reference

## Parallel Dispatch Prompt Template

并行派发时，在 AI agent 层面使用 Agent tool（`run_in_background: true`）：

```
# 同时派发多个子任务时：
- Agent 1: 实现 <模块A>，只修改 <文件列表A>，完成后输出 DONE/DONE_WITH_CONCERNS
- Agent 2: 实现 <模块B>，只修改 <文件列表B>，完成后输出 DONE/DONE_WITH_CONCERNS
# 规则:
# - 每个 agent 只操作自己的文件，禁止跨越
# - 每个 agent 收到的上下文是最小必要上下文，不传递完整历史
# - 等所有 agent 返回 DONE 后，主流程继续
```

## Mid-Task Reflection — Full Bash Examples

```bash
# Step 1: 检索与当前任务相关的已知因果链
python3 scripts/memory_longterm.py --op search-causal --query "<当前任务涉及的文件或模块名>"

# Step 2: 检索实体级历史（该文件曾经出过什么问题）
python3 scripts/memory_longterm.py --op search-entity --query "<主要修改的文件名>"
```

## TASK_NOTES Bash Append Example

```bash
# 追加任务笔记
cat >> SHARED_TASK_NOTES.md << 'EOF'

## T001 实现用户认证 — 2026-04-05
- **完成情况**: DONE
- **关键决策**: 使用 JWT refresh token，有效期 7 天
- **遗留问题**: 未实现 token 吊销列表
- **影响文件**: src/auth.py, tests/test_auth.py
EOF
```

## Implemented Vs Planned

以下内容目前**不**应视为默认已实现能力：

- `./trajectories/<task_id>_<timestamp>.json`
- trajectory 自动断点恢复
- trajectory 自动回写 `task_plan.md`（legacy）
- 自动并行执行编排
- phase telemetry API

如果后续实现这些能力，应先补脚本，再升级文档。

## Edge Cases

### 无计划文件时的快速模式

单文件、小任务、结果明确时：
- 可跳过完整计划维护
- 但仍应保留最小验证动作（至少一条测试命令或构建命令）

### memory_hints 复用

进入 EXECUTING 前，先读取当前 phase 上下文里的 `memory_hints`、`memory_query` 和 `memory_intent`：
- 避免重复踩已经被修复过的失败模式
- 复用 `planning_summary` / `research_summary` / `thinking_summary` / `review_summary` 作为执行上下文

### 中断后续接

`progress.md` / `context_for_next_phase` / checkpoint / resume 会携带同一套摘要，便于执行中断后无损续接。

### 子 agent schema 验证失败处理

- 第 1 次失败：重派，附上原始输出和 schema 要求
- 第 2 次失败：重派，简化任务范围
- 第 3 次失败（超上限）：标记为 FAILED，主流程接管，记录到 SHARED_TASK_NOTES.md

### 退出后的流转

- 需要审查时：进入 REVIEWING
- 任务全部完成时：进入 COMPLETE
