---
name: agentic-workflow
description: |
  统一智能体工作流 - 单入口设计，所有任务从 router 开始
  TRIGGER when: 开发、修复、规划、分析、审查、调研、实施
  DO NOT TRIGGER when: 简单闲聊
version: 5.14.0
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

## 状态机

```
IDLE → [ROUTER] → RESULT-ONLY → SUBAGENT → COMPLETE
                ↓
        OFFICE-HOURS → EXPLORING → RESEARCH/THINKING/PLANNING/EXECUTING/REVIEWING/DEBUGGING/REFINING → COMPLETE
```

## 原则与铁律

**核心原则**: 专家模拟 | TDD驱动 | 文件持久化 | PUA激励

**铁律**:
- **穷尽一切**：没有穷尽所有方案之前，禁止说"无法解决"
- **先做后问**：遇到问题先自行搜索、读源码、验证，再提问
- **主动出击**：端到端交付，不只是"刚好够用"

## 阶段切换

1. 读取 `.workflow_state.json` 确认当前 phase
2. 读取 `skill_prompt_{phase}_{session}.md` 获取阶段指令
3. 执行阶段任务 → `python3 scripts/workflow_engine.py --op advance --phase NEXT`
4. 写 `progress.md` 记录进度
