---
name: agentic-workflow
description: |
  智能体工作流：单入口设计，所有任务从 router 开始
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施
  DO NOT TRIGGER when: 简单闲聊
version: 6.3.0
tags: [core, workflow]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
---

# Agentic Workflow v6.3

## 工作流触发与路由

| 用户关键词 | 路由到阶段 |
|---|---|
| "bug"/"错误"/"修复" | **DEBUGGING** |
| "计划"/"拆分"/"规划" | **PLANNING** |
| "最佳实践"/"怎么做"/"如何" | **RESEARCH** |
| "审查"/"review"/"质量" | **REVIEWING** |
| "优化"/"迭代"/"精炼" | **REFINING** |
| "试验"/"想法"/"探索" | **EXPLORING** |
| 多模块/多文件任务 | **FULL_WORKFLOW** |
| "继续"/"resume"/"恢复" | 读 `.workflow_state.json` 恢复上下文 |

## FULL_WORKFLOW 强制阶段序列

按复杂度自动选择最小必经阶段（**禁止跳过**）：

| 复杂度 | 示例 | 必经阶段 |
|---|---|---|
| **XS** | 改 typo、加 import | EXECUTING → COMPLETE |
| **S** | 修已知 bug | DEBUGGING → EXECUTING → COMPLETE |
| **M** | 新增 API | PLANNING → EXECUTING → REVIEWING → COMPLETE |
| **L** | 重构模块 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE |
| **XL** | 设计新系统 | RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → REFINING → COMPLETE |

## 进度输出 (必须执行)

每进入新阶段时输出：
```
[N/M PHASE] 一句话描述当前目标
```

阶段完成时输出：
```
[N/M PHASE ✓] 一句话总结产出
```

## 阶段上下文传递 (必须执行)

| 当前阶段 | 下一阶段 | 必读内容 |
|---|---|---|
| RESEARCH | THINKING | 读 `findings_{session}.md` |
| THINKING | PLANNING | 基于分析结论拆分任务，生成 `.specs/<feature>/spec.md / plan.md / tasks.md / .contract.json` |
| PLANNING | EXECUTING | 逐项执行 `.specs/<feature>/tasks.md`；`task_plan.md` 仅作 legacy 投影 |
| EXECUTING | REVIEWING | 运行 `git diff` 查看代码变更，并更新 `.contract.json` |
| REVIEWING | REFINING | 针对 issues 逐项修复，并产出 `review_{session}.md` |

## 核心原则 (铁律，不可违反)

1. **穷尽一切** — 没穷尽 3 个方案前禁止说"无法解决"
2. **先做后问** — 遇到问题先搜索/读源码/验证，再提问
3. **主动出击** — 端到端交付，不只是"刚好够用"

## 禁止响应

以下响应明确禁止，遇到立即停止并重新分析：

| 禁止语句 | 原因 | 正确做法 |
|---|---|---|
| "我认为完成了" | 无证据声明 | 运行测试/`git diff`，给出证据 |
| "代码看起来不错" | REVIEWING 无实质内容 | 输出含 `file:line` 的具体意见 |
| "跳过 X 阶段直接做 Y" | 违反强制序列 | 按照强制阶段序列执行 |
| "根据我的知识..." (RESEARCH) | 跳过真实搜索 | 先执行 WebSearch；工具不可用时明确告知用户 |

## 搜索工具优先级 (RESEARCH 阶段自动降级)

1. **WebSearch** — Claude Code 原生（优先使用）
2. **WebFetch** — 当已知具体 URL 时
3. **工具都不可用** → **必明确告知用户**"搜索不可用，使用已有知识"，禁止静默降级

## 阶段切换命令

```bash
# 推进到下一阶段
python3 scripts/workflow_engine.py --op advance --phase {NEXT_PHASE} --workdir .

# 查看当前状态
python3 scripts/workflow_engine.py --op status --workdir .
```

## 关键文件约定

- `.workflow_state.json` — 唯一可信的状态文件
- `.specs/<feature>/spec.md` — 需求与验收标准
- `.specs/<feature>/plan.md` — 技术方案与约束
- `.specs/<feature>/tasks.md` — 执行任务清单
- `.contract.json` — 履约契约（COMPLETE 门禁）
- `task_plan.md` — legacy 兼容投影，非主线
- `findings_{session}.md` — RESEARCH 输出的研究结果（THINKING 必读）
- `review_{session}.md` — REVIEWING 输出的审查意见（REFINING 必读）
