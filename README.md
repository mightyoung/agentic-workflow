# Agentic Workflow | 统一智能体工作流

> 融合 7 大顶级 Skills 精髓的 AI 开发工作流 | Fusion of 7 Elite Skills for AI Development

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-2.0-blue.svg)](SKILL.md)

> **English** | [中文](#中文)

---

## What is Agentic Workflow?

Agentic Workflow is a **unified AI development workflow skill** that combines the essence of 7 world-class skills into a single, powerful framework. It provides a systematic approach to handling complex development tasks, from thinking and planning to execution and debugging.

### Core Philosophy

**Don't ask "What do you think?" — ask "Who knows this best? What would they say?"**

This principle, inspired by the best-minds approach, ensures we always leverage expert-level thinking rather than generic responses.

---

## Features | 功能特性

| Module | Description | Trigger Words |
|--------|-------------|---------------|
| **THINKING** | Expert simulation - identifies domain experts and simulates their thinking | 谁最懂, 顶级, 专家 |
| **PLANNING** | File-based task planning with task_plan.md, findings.md, progress.md | 计划, 规划, 拆分任务 |
| **EXECUTING** | TDD-driven development: test → fail → implement → pass | TDD, 测试驱动 |
| **REVIEWING** | Code quality review with optional OpenSpec compliance | 审查, review |
| **DEBUGGING** | Systematic debugging with root cause analysis | 调试, 修复bug |

---

## Architecture | 架构

```
IDLE → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
                    ↓           ↓           ↓
                 DEBUGGING ←────────────→
```

---

## Integrated Skills & Why We Fused Them | 融合 Skills 及原因

### 1. best-minds (Expert Simulation)
**Industry Best Practice**: Anthropic's Claude Code, Cursor use expert-level prompting.

**Why**: Generic "How do you think?" produces shallow responses. "Who knows this best?" ensures expert-level analysis.

**Reference**: [best-minds skill](https://github.com/Ceeon/best-minds)

### 2. planning-with-files (File-Based Planning)
**Industry Best Practice**: Manus AI's context engineering - "Filesystem as memory".

**Why**: Context window is RAM (volatile), filesystem is disk (persistent). Important information must be saved to disk.

**Reference**: [planning-with-files skill](https://github.com/OthmanAdi/planning-with-files)

### 3. TDD (Test-Driven Development)
**Industry Best Practice**: Industry standard since Kent Beck's "Test Driven Development".

**Why**: TDD ensures code correctness from the start, reduces bugs, and provides living documentation.

**Reference**: XP, Scrum methodologies

### 4. systematic-debugging (Systematic Debugging)
**Industry Best Practice**: Google's engineering practices, root cause analysis methodology.

**Why**: Ad-hoc debugging wastes time. Systematic approach (reproduce → collect → analyze → fix) is 10x more efficient.

**Reference**: Industry-standard debugging methodology (Google SRE, root cause analysis)

### 5. verification (Code Review)
**Industry Best Practice**: Google's code review standards, PR requirements.

**Why**: Code review catches 60%+ of bugs before production. Essential for maintainable code.

**Reference**: Industry-standard code review practices (Google, GitHub PR)

### 6. openspec (Spec-Driven Development)
**Industry Best Practice**: Technical Specification Document (TSD) methodology.

**Why**: Spec before code prevents scope creep and ensures alignment with requirements.

**Reference**: [openspec skill](https://github.com/anthropics/claude-code)

### 7. writing-plans (Task Planning)
**Industry Best Practice**: Agile user stories, sprint planning.

**Why**: Breaking tasks into 2-5 minute chunks ensures progress is measurable and reversible.

**Reference**: Agile methodology (Scrum, Kanban task breakdown)

---

## Evaluation Results | 评估结果

### Test Summary (Iteration 2 - Module Tests)

| Module | Test Cases | Pass Rate | Routing Accuracy |
|--------|-----------|-----------|------------------|
| THINKING | 2 | 100% | ✅ |
| PLANNING | 2 | 100% | ✅ |
| EXECUTING | 2 | 100% | ✅ |
| REVIEWING | 2 | 100% | ✅ |
| DEBUGGING | 2 | 100% | ✅ |
| **Total** | **10** | **100%** | **100%** |

### Routing Logic Verification

Each trigger word correctly routes to the appropriate module:

- `"谁最懂"` → THINKING module (identifies experts like Andrej Karpathy, Bruce Schneier)
- `"规划"` → PLANNING module (creates task_plan.md, findings.md, progress.md)
- `"TDD"` → EXECUTING module (follows test-first methodology)
- `"审查"` → REVIEWING module (performs code quality review)
- `"调试"` → DEBUGGING module (systematic root cause analysis)

### Comparison: With vs Without Skill

| Metric | With Skill | Without Skill |
|--------|------------|---------------|
| Pass Rate | **100%** | 78% |
| Methodological Compliance | Full TDD, Systematic Debugging | Partial |
| Documentation | task_plan.md created | Not created |

---

## Usage | 使用方法

### Trigger the Skill

In Claude Code, the skill automatically triggers when you:

1. **Develop features**: "帮我开发一个用户认证系统"
2. **Fix bugs**: "这个API返回500错误，请帮我调试"
3. **Plan projects**: "请帮我规划一个电商网站"
4. **Review code**: "请审查这段代码"
5. **Ask expert analysis**: "谁最懂Python异步编程？"

### Workflow Example

```
User: 帮我开发一个用户认证系统

1. THINKING: 谁最懂身份认证？(安全专家)
   → Add expert perspective to task_plan.md

2. PLANNING: Create task_plan.md
   → task_plan.md, findings.md, progress.md
   → Split: 登录、注册、JWT

3. EXECUTING: TDD循环
   → Test → Fail → Implement → Pass

4. REVIEWING: 规范检查
   → Verify against spec

5. COMPLETE: memory_store 存储经验
```

---

## File Structure | 文件结构

```
agentic-workflow/
├── SKILL.md              # Main skill file
├── README.md             # English documentation
├── README.zh-CN.md       # 中文文档
├── LICENSE               # MIT License
├── evals/                # Evaluation results
│   ├── iteration-1/      # Initial evaluation
│   └── iteration-2/      # Module tests
└── tests/                # Test cases
```

---

## Requirements | 要求

- Claude Code or compatible AI assistant
- For Claude Code: Version with Skill tool support

---

## Contributing | 贡献

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Related Skills | 相关 Skills

- [best-minds](https://github.com/Ceeon/best-minds) - Expert simulation
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) - File-based planning
- [TDD](https://en.wikipedia.org/wiki/Test-driven_development) - Test-driven development
- [systematic-debugging](https://sre.google/sre-book/postmortem-culture/) - Debugging methodology
- [openspec](https://github.com/anthropics/claude-code) - Specification-driven development

---

<a name="中文"></a>

---

# Agentic Workflow | 统一智能体工作流

> 融合 7 大顶级 Skills 精髓的 AI 开发工作流

## 什么是 Agentic Workflow？

Agentic Workflow 是一个**统一的 AI 开发工作流技能**，将 7 个世界级技能的精髓融合到一个强大的框架中。它为处理复杂开发任务提供了系统化的方法，从思考和规划到执行和调试。

### 核心哲学

**不要问"你怎么看"——要问"这个问题谁最懂？TA 会怎么说？"**

这个原则借鉴自 best-minds 方法论，确保我们始终利用专家级思维而非通用响应。

---

## 为什么融合？| Why We Fused

我们分析了 14+ 个 Claude Code Skills，发现存在以下问题：

1. **触发准确度问题**: 大量 Skills 导致 Claude 难以准确触发
2. **重复工作**: 多个 Skills 处理类似任务
3. **上下文碎片化**: 重要信息无法跨会话持久化

### 融合策略

| 原 Skill 数量 | 融合后 | 触发准确度 |
|--------------|--------|-----------|
| 14 | 1 | 大幅提升 |

通过融合为单一的 `agentic-workflow`，我们实现了：
- ✅ 单一入口，避免技能冲突
- ✅ 完整的开发工作流覆盖
- ✅ 文件持久化，跨会话记忆
- ✅ 100% 模块测试通过率

---

## 评估验证 | Validation

### 测试用例设计

我们设计了 10 个测试用例，覆盖 5 个核心模块：

| 模块 | 触发词 | 测试数 | 通过率 |
|-----|--------|-------|--------|
| THINKING | 谁最懂、顶级 | 2 | 100% |
| PLANNING | 规划、拆分任务 | 2 | 100% |
| EXECUTING | TDD、测试驱动 | 2 | 100% |
| REVIEWING | 审查、review | 2 | 100% |
| DEBUGGING | 调试、修复bug | 2 | 100% |

### 关键发现

1. **使用技能时通过率更高**: 100% vs 78%
2. **任务规划**: 使用技能时创建了 task_plan.md，未使用时未创建
3. **调试**: 使用技能时保留了错误上下文，系统性调试方法论正确应用
4. **专家模拟**: 正确识别领域专家（Andrew Svetlov、Bruce Schneier 等）

---

## 快速开始

### 在 Claude Code 中使用

当你说以下内容时，技能会自动触发：

1. **开发功能**: "帮我开发一个用户认证系统"
2. **调试修复**: "这个API返回500错误，请帮我调试"
3. **规划项目**: "请帮我规划一个电商网站"
4. **代码审查**: "请审查这段代码"
5. **专家分析**: "谁最懂Python异步编程？"

---

## 工作流示例

```
用户: 帮我开发一个用户认证系统

1. THINKING: 这个问题谁最懂？(安全专家)
   → 添加专家视角到 task_plan.md

2. PLANNING: 创建计划文件
   → task_plan.md, findings.md, progress.md
   → 拆分任务：登录、注册、JWT

3. EXECUTING: TDD循环
   → 测试 → 失败 → 实现 → 通过

4. REVIEWING: 规范检查
   → 验证是否符合 spec

5. COMPLETE: 更新文件状态
   → memory_store 存储经验
```

---

## 融合的 Skills 详解

### 1. best-minds (专家模拟)
- **来源**: Industry best practices
- **优势**: 专家级思维，避免泛泛而谈
- **融合原因**: "谁最懂"比"你怎么看"更能获取深度洞见

### 2. planning-with-files (文件规划)
- **来源**: [planning-with-files](https://github.com/OthmanAdi/planning-with-files)
- **优势**: Manus AI 的"文件系统即记忆"理念
- **融合原因**: 上下文窗口是 RAM(易失)，文件系统是磁盘(持久)

### 3. TDD (测试驱动开发)
- **来源**: 行业标准 (Kent Beck)
- **优势**: 从一开始就保证代码正确性
- **融合原因**: 测试先行 → 失败 → 实现 → 通过

### 4. systematic-debugging (系统调试)
- **来源**: Industry best practices
- **优势**: 根因分析，效率提升 10 倍
- **融合原因**: 临时调试是时间杀手，系统化方法才是正道

### 5. verification (代码审查)
- **来源**: Industry best practices
- **优势**: Google 级代码审查标准
- **融合原因**: 60%+ 的 bug 在审查阶段被catch

### 6. openspec (规范驱动)
- **来源**: [anthropics/claude-code](https://github.com/anthropics/claude-code)
- **优势**: 规范先行，防止范围蔓延
- **融合原因**: 代码之前先有规范，确保需求对齐

### 7. writing-plans (任务规划)
- **来源**: Industry best practices
- **优势**: 敏捷开发的任务拆分最佳实践
- **融合原因**: 2-5 分钟粒度确保进度可衡量、可回滚

---

## 文件结构

```
agentic-workflow/
├── SKILL.md              # 主技能文件
├── README.md             # 英文文档
├── README.zh-CN.md       # 中文文档
├── LICENSE               # MIT 许可证
├── evals/                # 评估结果
│   ├── iteration-1/      # 初始评估
│   └── iteration-2/      # 模块测试
└── tests/                # 测试用例
```

---

## 相关 Skills

- [best-minds](https://github.com/Ceeon/best-minds) - 专家模拟
- [planning-with-files](https://github.com/OthmanAdi/planning-with-files) - 文件规划
- [TDD](https://github.com/obra/superpowers) - 测试驱动开发
- [systematic-debugging](https://github.com/obra/superpowers) - 系统调试
- [openspec](https://github.com/anthropics/claude-code) - 规范驱动开发

---

## 贡献

欢迎贡献！请阅读 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md) 了解更多。

---

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)
