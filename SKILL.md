---
name: agentic-workflow
description: |
  统一智能体工作流 - 单入口设计，所有任务从 router 开始
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施
  DO NOT TRIGGER when: 简单闲聊
version: 6.1.0
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow

## 路由规则

**强制序列** — FULL_WORKFLOW 触发时必须依次经过:
`RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE` — 禁止跳过。

| 场景 | 关键词 | 阶段 |
|------|--------|------|
| 只需结果 | "给我..."/"直接给..."/"就行" | **SUBAGENT** |
| Bug修复 | bug/错误/调试 | DEBUGGING |
| 项目规划 | 计划/规划/拆分 | PLANNING |
| 技术调研 | 最佳实践/怎么做 | RESEARCH→THINKING |
| 代码审查 | 审查/review | REVIEWING |
| 产品咨询 | 产品想法/需求不明确 | OFFICE-HOURS |
| 深度探索 | "实验"/"想法"/"深层"/"本质" | EXPLORING |
| 迭代精炼 | 迭代/优化/精炼 | REFINING |
| 简单任务 | 其他 | EXECUTING |
| 继续 | 继续/resume/恢复 | 读取 .workflow_state.json 恢复上下文 |

## 进度输出格式

每进入新阶段时 **必须** 输出进度行：

```
[N/M PHASE] 一句话描述当前要做什么
```

阶段完成时输出：

```
[N/M PHASE done] 一句话总结产出
```

## 阶段切换与上下文传递

每个阶段结束时，**必须** 将关键产出传递给下一阶段：

| 当前阶段 | 产出 | 下一阶段必须读取 |
|---------|------|-----------------|
| RESEARCH | `findings.md` | THINKING 开始前读取 findings.md |
| THINKING | 分析结论（输出到对话） | PLANNING 基于 THINKING 结论拆分任务 |
| PLANNING | `task_plan.md` / TodoWrite | EXECUTING 逐项执行 |
| EXECUTING | 代码变更 | REVIEWING 运行 `git diff` 查看变更 |
| REVIEWING | review 意见 | REFINING 针对性修复（如有问题） |

## 原则与铁律

**核心原则**: 专家模拟 | TDD驱动 | 文件持久化 | PUA激励

**铁律**:
- **穷尽一切**：没有穷尽所有方案之前，禁止说"无法解决"
- **先做后问**：遇到问题先自行搜索、读源码、验证，再提问
- **主动出击**：端到端交付，不只是"刚好够用"

## 阶段切换

1. 读取 `.workflow_state.json` 确认当前 phase
2. 读取 `skill_prompt_{phase}_{session}.md` 获取阶段指令（如存在）
3. 执行阶段任务
4. 推进：`python3 scripts/workflow_engine.py --op advance --phase NEXT --workdir .`

## 搜索工具降级策略

RESEARCH 阶段搜索工具优先级（按可用性自动降级）：
1. **WebSearch** — Claude Code 原生，最优先
2. **WebFetch** — 当已知具体 URL 时
3. **AI 知识库** — 如果所有搜索工具都不可用，**必须明确告知用户**，不要静默用自身知识回答

## Forbidden Responses（禁止输出的内容）

以下响应是明确禁止的，遇到时必须停止并重新分析：

| 禁止语句 | 原因 | 正确做法 |
|---------|------|---------|
| "这个问题无法解决" | 违反铁律一（穷尽一切） | 列出3个方案再判断 |
| "我认为完成了" | 无证据声明 | 运行测试/diff，给出证据 |
| "代码看起来不错" | REVIEWING 无实质内容 | 给出 file:line 具体意见 |
| "根据我的知识..." (RESEARCH中) | 跳过真实搜索 | 先执行 WebSearch，工具不可用时明确告知 |
| "直接跳到实现吧" | 跳过 THINKING/PLANNING | 遵循强制阶段序列 |
| "先做个小版本，后面再改" | 无计划执行 | 先 PLANNING，再 EXECUTING |

## 深度控制（用户可覆盖）

用户可以显式控制流程深度，覆盖自动评估：

| 关键词 | 效果 | 等价复杂度 |
|--------|------|-----------|
| `快速` / `quick` / `--quick` | 强制走最短路径 | XS/S |
| `深入` / `thorough` / `--thorough` | 强制走完整路径 | L/XL |
| `标准` / 无修饰词 | 自动评估 | 按任务内容决定 |

**示例**:
- `/agentic-workflow 快速修复这个 bug` → DEBUGGING → EXECUTING → COMPLETE
- `/agentic-workflow 深入分析这个架构问题` → RESEARCH → THINKING → PLANNING → ...

## 复杂度路由

任务自动评估复杂度，路由到对应必经阶段序列：

| 复杂度 | 示例 | 必经阶段 |
|--------|------|---------|
| **XS** | 改 typo、加 import | EXECUTING → COMPLETE |
| **S** | 修已知 bug | DEBUGGING → EXECUTING → COMPLETE |
| **M** | 新增 API endpoint | PLANNING → EXECUTING → REVIEWING → COMPLETE |
| **L** | 重构模块 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE |
| **XL** | 设计新系统 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → REFINING → COMPLETE |
