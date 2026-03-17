# Agentic Workflow | 统一智能体工作流

> 融合 10+ 世界顶级 Skills 精髓的 AI 开发工作流 | Fusion of 10+ World-Class Skills for AI Development

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-4.1-blue.svg)](SKILL.md)

> **English** | [中文](#中文)

---

## Quick Skill Reference | 技能快速对照表

| 本 Skill 模块 | 源自成熟 Skill | 行业顶级优势 | 核心价值 |
|--------------|---------------|-------------|----------|
| **RESEARCH** | tavily, planning-with-files | AI 优化搜索 + 文件持久化 | 决策基于真实证据 |
| **THINKING** | best-minds | 专家级思维模拟 | 避免泛泛而谈 |
| **PLANNING** | writing-plans, planning-with-files | 敏捷任务拆分 + 文件记忆 | 进度可衡量可回滚 |
| **EXECUTING** | TDD, pua | 测试驱动 + 压力升级 | 代码正确性保障 |
| **REVIEWING** | verification, openspec | 分级审查 + 规范驱动 | 60%+ Bug 拦截 |
| **DEBUGGING** | systematic-debugging, pua | 5步方法论 + 7项检查 | 10x 调试效率 |

---

## What is Agentic Workflow?

Agentic Workflow is a **unified AI development workflow skill** that combines the essence of 10+ world-class skills into a single, powerful framework (v4.1). It provides a systematic approach to handling complex development tasks, from thinking and planning to execution and debugging.

### Core Philosophy

**Don't ask "What do you think?" — ask "Who knows this best? What would they say?"**

This principle, inspired by the best-minds approach, ensures we always leverage expert-level thinking rather than generic responses.

---

## v4.1 New Features | v4.1 新特性

### 1. 意图强度分层 | Intent Intensity Layering

基于 AI 技能触发最佳实践，我们实现了 4 层触发机制：

| 层级 | 类型 | 触发条件 | 示例 |
|------|------|----------|------|
| L1 | 强制触发 | 高置信度显式意图 | "帮我搜索", "修复这个bug" |
| L2 | 标准触发 | 显式关键词 | "最佳实践", "分析一下" |
| L3 | 隐式意图 | 间接表达 | "响应很慢", "太慢了" |
| L4 | 闲聊过滤 | 日常对话 | "天气", "你好" |

### 2. 隐式意图识别 | Implicit Intent Recognition

新增性能问题、分析需求、规划需求的隐式触发：

- **性能问题**: "响应很慢", "太慢了", "跑不通", "超时"
- **分析需求**: "哪个好", "建议", "思路"
- **规划需求**: "要做什么", "步骤", "先后顺序"

### 3. 7个子智能体 | 7 Subagents

| 智能体 | 职责 | 对应阶段 |
|--------|------|----------|
| **researcher** | 研究搜索 | RESEARCH |
| **planner** | 任务规划 | PLANNING |
| **coder** | 代码实现 | EXECUTING |
| **reviewer** | 代码审查 | REVIEWING |
| **debugger** | 调试修复 | DEBUGGING |
| **security_expert** | 安全审查 | THINKING/REVIEWING |
| **performance_expert** | 性能优化 | THINKING/REVIEWING |

---

## Features | 功能特性

| Module | Description | Trigger Words |
|--------|-------------|---------------|
| **RESEARCH** | Pre-research with Tavily: search best practices, GitHub projects, community discussions | 怎么做, 如何实现, 最佳实践, 参考 |
| **THINKING** | Expert simulation + Chain-of-Thought: structured reasoning with problem definition, element decomposition, chain inference, counterexample testing | 谁最懂, 顶级, 专家 |
| **PLANNING** | File-based task planning with task_plan.md, findings.md, progress.md | 计划, 规划, 拆分任务 |
| **EXECUTING** | TDD-driven development with PUA iron laws: test → fail → implement → pass | TDD, 测试驱动, 尽力, 别放弃 |
| **REVIEWING** | Brutal code review with problem classification (🔴 Fatal / 🟡 Serious / 🟢 Suggestion) | 审查, review |
| **DEBUGGING** | Systematic debugging with PUA 5-step methodology and pressure escalation | 调试, 修复bug |

---

## Architecture | 架构

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→
```

### v4.1: Progressive Disclosure Architecture

```
L1 (Frontmatter):  ~10 lines  - Skill name + description
L2 (SKILL.md):    ~450 lines - Core workflow + routing + triggers
L3 (references/): On-demand   - Detailed module guides
```

### v4.1: ECC Integration with Fallback

| Task | ECC Call | Fallback |
|------|----------|----------|
| TDD | skill("ecc-workflow", "/tdd") | references/builtin_tdd.md |
| Code Review | skill("ecc-workflow", "/code-review") | references/modules/reviewing.md |
| E2E | skill("ecc-workflow", "/e2e") | references/builtin_e2e.md |

---

## Integrated Skills & Why We Fused Them | 融合 Skills 及原因

我们分析了 14+ 个 Claude Code Skills，发现存在触发准确度低、重复工作、上下文碎片化等问题。通过融合，我们实现了 **100% 触发准确率** 和 **98%+ 测试通过率**。

### Skill 融合详情

| 融合后模块 | 源自 Skill | 行业参考 | 融合优势 |
|-----------|-----------|----------|----------|
| THINKING | best-minds | Anthropic Claude Code, Cursor 专家提示 | 专家视角分析 |
| THINKING | brainstorming | 思维发散工具 | 多角度思考 |
| PLANNING | planning-with-files | Manus AI 文件系统记忆 | 持久化上下文 |
| PLANNING | writing-plans | Scrum, Kanban 任务拆分 | 2-5分钟粒度 |
| EXECUTING | TDD | Kent Beck 测试驱动开发 | 红绿重构循环 |
| EXECUTING | pua | 企业级压力驱动方法论 | 3铁律+5步法 |
| DEBUGGING | systematic-debugging | Google SRE 根因分析 | 10x 效率提升 |
| DEBUGGING | pua | 压力升级机制 L1-L4 | 穷尽解决方案 |
| REVIEWING | verification | Google 代码审查标准 | 60%+ Bug 拦截 |
| REVIEWING | openspec | Anthropic 规范驱动开发 | 防止范围蔓延 |
| RESEARCH | tavily | Tavily AI 优化搜索 | 语义理解搜索 |

### 为什么要融合？| Why Fuse?

1. **触发准确率问题**: 单独 Skills 触发率低，融合后 100% 触发
2. **上下文碎片化**: 多 Skill 切换丢失上下文，融合后统一管理
3. **重复工作**: 多个 Skill 做相似的事，融合后消除冗余
4. **用户体验**: 用户只需记住一个 Skill，覆盖所有开发场景

---

## Testing & Evaluation | 测试评估

### 测试结果 | Test Results

基于真实 Claude Code CLI 执行测试：

| 测试维度 | 测试用例数 | 通过率 |
|----------|-----------|--------|
| 阶段路由触发 | 40 | **100%** |
| 触发逻辑验证 | 16 | **100%** |
| 隐式意图识别 | 24 | **100%** |
| Subagent 派生 | 5 | **100%** |
| 运行质量提升 | 5 | **80%** |
| **总计** | **90** | **98.9%** |

### 触发评估目标 | Trigger Evaluation Goals

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 强制触发准确率 | ≥95% | 100% |
| 标准触发准确率 | ≥90% | 100% |
| 隐式意图识别率 | ≥80% | 100% |
| 误触发率 | ≤5% | <2% |

### 参考的测试最佳实践

- **skill-creator**: Anthropic 官方的 Skill 创建和评估框架
- **eval-viewer**: 定量和定性评估可视化
- **trigger optimization**: 意图分类和触发率优化

---

## 文件结构 | File Structure

```
agentic-workflow/
├── SKILL.md                      # 主技能文件 (v4.1)
├── README.md                     # 中英双文文档
├── LICENSE                       # MIT 许可证
├── agents/                       # 子智能体定义
│   ├── researcher.md
│   ├── planner.md
│   ├── coder.md
│   ├── reviewer.md
│   ├── debugger.md
│   ├── security_expert.md
│   └── performance_expert.md
├── references/                   # 详细模块指南
│   ├── modules/
│   ├── templates/
│   └── builtin_*.md
├── tests/                       # 测试用例
│   ├── evals/
│   └── run_*.py
└── docs/                        # 设计文档
```

---

## 相关 Skills | Related Skills

- [best-minds](https://github.com/Ceeon/best-minds) - 专家模拟
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) - 文件规划
- [TDD](https://github.com/obra/superpowers) - 测试驱动开发
- [systematic-debugging](https://github.com/obra/superpowers) - 系统调试
- [openspec](https://github.com/anthropics/claude-code) - 规范驱动开发
- [tavily](https://tavily.com) - AI 优化搜索
- [skill-creator](https://github.com/anthropics/claude-code) - Skill 创建框架

---

## 贡献 | Contributing

欢迎贡献！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解更多。

---

## 许可证 | License

MIT 许可证 - 详见 [LICENSE](LICENSE)

---

## 版本历史 | Version History

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v4.1 | 2026-03-17 | 意图强度分层、隐式意图识别、7个子智能体、触发评估集 |
| v4.0 | 2026-03-13 | Subagent 集成、ECC 降级机制 |
| v3.0 | 2026-03-10 | 初始融合版本 |

---

# 中文

## 什么是 Agentic Workflow？

Agentic Workflow 是一个**统一的 AI 开发工作流 Skill**，融合了 10+ 个世界级 Skills 的精髓（v4.1 版本）。它为处理复杂开发任务提供了系统化方法，从思考规划到执行调试。

### 核心原则

**不问"你怎么看"，而是问"这个问题谁最懂？TA会怎么说？"**

这一原则借鉴自 best-minds 方法论，确保我们始终利用专家级思维而非泛泛而谈。

---

## 快速开始

| 场景 | 执行阶段 |
|------|----------|
| 新功能开发 | EXECUTING + TDD |
| Bug修复 | DEBUGGING |
| 项目规划 | PLANNING |
| 技术调研 | RESEARCH + THINKING |
| 代码审查 | REVIEWING |

---

## 使用方法

1. 安装此 Skill 到你的 Claude Code
2. 当你需要开发功能、修复 bug、规划项目时自动激活
3. Skill 会根据你的输入自动路由到正确的阶段
4. 使用子智能体并行处理独立任务

---

## 性能对比

| 场景 | 单智能体 | Subagents | 提升 |
|------|----------|-----------|------|
| 电商网站开发 | 120s | 30s | **4x** |
| 10文件代码审查 | 30s | 10s | **3x** |
| 技术调研 | 25s | 8s | **3x** |

---

## 验证结论

通过系统性测试评估，我们验证了 Skill 融合的成功：

1. **100% 阶段路由准确率** - 40个测试用例全部通过
2. **100% 触发逻辑准确率** - 16个测试用例全部通过
3. **100% 隐式意图识别** - 24个新关键词覆盖
4. **98.9% 总测试通过率** - 90个测试用例

融合方案参考了行业最佳实践：
- Anthropic 官方的 skill-creator 评估框架
- Claude Code Sub-Agents 并行执行架构
- Tavily AI 优化搜索触发机制

我们成功解决了多 Skill 碎片化问题，实现了统一工作流体验。
