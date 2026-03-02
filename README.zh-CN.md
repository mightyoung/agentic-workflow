# 集成开发工作流

> 一条命令启动一切。面向 AI 编码代理的完整开发工作流编排器。

[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/integrated-dev-workflow)](https://github.com/mightyoung/integrated-dev-workflow)
[![GitHub forks](https://img.shields.io/github/forks/mightyoung/integrated-dev-workflow)](https://github.com/mightyoung/integrated-dev-workflow)

> **English** | [中文](README.zh-CN.md)

---

## 目录

- [什么是集成开发工作流？](#什么是集成开发工作流)
- [快速开始](#快速开始)
- [支持的 AI 代理](#支持的-ai-代理)
- [安装](#安装)
- [使用方法](#使用方法)
- [代理兼容性](#代理兼容性)
- [文件结构](#文件结构)
- [子技能集成](#子技能集成)
- [工作流阶段](#工作流阶段)
- [示例](#示例)
- [故障排除](#故障排除)
- [许可证](#许可证)
- [贡献](#贡献)

---

## 什么是集成开发工作流？

集成开发工作流**改变了**临时 AI 编码的现状。不再是每个功能都从零开始凭感觉编写，此技能提供了一个**完整的编排工作流**，引导代理完成：

1. **需求** — 清晰、文档化的目标
2. **规划** — 带依赖的任务分解
3. **实现** — 正确的分支管理下的 TDD
4. **测试与审查** — 完成前的验证
5. **完成** — 干净的合并/PR 工作流

---

## 快速开始

只需告诉代理你想构建什么：

```
我想构建用户登录功能
实现购物车
创建用户管理 API
修复登录超时 bug
重构数据层
```

技能将自动：

1. 检查之前的会话
2. 创建跟踪文件（task_plan.md, findings.md, progress.md）
3. 引导需求定义
4. 规划实现方案
5. 按最佳实践执行

---

## 支持的 AI 代理

| 代理 | 支持 | 说明 |
|-----|------|------|
| Claude Code | 完整 | 支持 Hooks |
| OpenCode | 完整 | 通过 .agents/skills |
| Cursor | 完整 | 通过 .cursor/skills |
| Trae | 完整 | 通过 .trae/skills |
| Pi Agent | 完整 | 通过 npm |
| Windsurf | 完整 | 通过 .windsurf/skills |
| Roo Code | 完整 | 通过 .roo/skills |
| Codex CLI | 完整 | 通过 .codex/skills |
| 通用 | 完整 | 参考技能 |

---

## 安装

### Claude Code

```bash
mkdir -p .claude/skills
cp -r /path/to/integrated-dev-workflow .claude/skills/
```

### OpenCode

```bash
mkdir -p .agents/skills
cp -r /path/to/integrated-dev-workflow .agents/skills/
```

### Cursor

```bash
mkdir -p .cursor/skills
cp -r /path/to/integrated-dev-workflow .cursor/skills/
```

### Trae

```bash
mkdir -p .trae/skills
cp -r /path/to/integrated-dev-workflow .trae/skills/
```

### Pi Agent

```bash
pi install npm:integrated-dev-workflow
```

### Windsurf

```bash
mkdir -p .windsurf/skills
cp -r /path/to/integrated-dev-workflow .windsurf/skills/
```

### 手动安装

```bash
mkdir -p .agents/skills
cp -r /path/to/integrated-dev-workflow .agents/skills/
```

---

## 使用方法

### 快速开始

只需告诉代理你想构建什么。技能会自动编排整个开发过程。

### 手动调用

```bash
skill("integrated-dev-workflow")
```

---

## 代理兼容性

### 功能对比

| 功能 | Claude Code | OpenCode | Cursor | Trae | Pi Agent | Windsurf |
|------|-------------|----------|--------|------|----------|----------|
| Hooks | 完整 | 完整 | 有限 | 有限 | 有限 | 有限 |
| 会话恢复 | 自动 | 自动 | 通过脚本 | 通过脚本 | 通过脚本 | 通过脚本 |
| 文件模板 | 全部 | 全部 | 全部 | 全部 | 全部 | 全部 |
| TDD 工作流 | 完整 | 完整 | 完整 | 完整 | 完整 | 完整 |
| 代码审查工作流 | 完整 | 完整 | 完整 | 完整 | 完整 | 完整 |

### Claude Code

此技能使用 hooks 实现持久提醒：

- **PreToolUse**：在主要操作前提醒更新 task_plan.md
- **PostToolUse**：文件更改后提示更新任务状态
- **Stop**：结束会话前确认任务进度

### OpenCode

通过 `.agents/skills` 目录完全支持：

1. 将此技能文件夹复制到 `.agents/skills/`
2. 技能自动被发现
3. 使用 `skill("integrated-dev-workflow")` 调用

### Cursor

与 Claude Code 类似，如果 Cursor 支持扩展，hooks 可能有效：

1. 尝试复制到 `.cursor/skills/`
2. 如果不支持 hooks，需要手动会话恢复

### Trae

Trae 基于 VS Code 扩展模型构建：

1. 复制到 `.trae/skills/` 或 VS Code 扩展文件夹
2. 可能需要手动管理工作流

### Pi Agent 限制

- Pi Agent 不支持 hooks
- 会话恢复需要手动脚本：
  ```bash
  python3 scripts/session-recovery.py .
  ```

---

## 文件结构

安装后，此技能会创建跟踪文件：

```
your-project/
├── task_plan.md      # 阶段追踪、任务清单
├── findings.md       # 研究、决策、笔记  
└── progress.md       # 会话日志、测试结果、错误
```

### task_plan.md

```markdown
# 任务计划

## 目标
[构建 X]

## 阶段
- [ ] 阶段 1: 需求
- [ ] 阶段 2: 规划
- [ ] 阶段 3: 实现
- [ ] 阶段 4: 测试与审查
- [ ] 阶段 5: 完成

## 当前阶段
阶段 1

## 任务
- [ ] 任务 1
- [ ] 任务 2
```

### findings.md

```markdown
# 发现

## 研究
- [研究笔记]

## 技术决策
- [做出的决策]

## 笔记
- [其他笔记]
```

### progress.md

```markdown
# 进度

## 会话日志
- 开始于: 2024-01-01 10:00
- 创建了 task_plan.md
- 与用户明确了需求

## 测试结果
| 测试 | 状态 |
|------|--------|
| | |

## 遇到的问题
| 错误 | 解决方案 |
|-------|------------|
| | |
```

---

## 子技能集成

此技能将 11 个子技能编排成无缝工作流。以下是它们如何协同工作：

### 阶段 1: 需求与设计

使用这些技能来定义和澄清需求：

- **brainstorming** - 深入的需求分析和澄清
- **planning-with-files** - 在 task_plan.md 中记录需求

### 阶段 2: 技术规划

使用这些技能来规划实现：

- **writing-plans** - 细化任务并分解为可操作项
- **planning-with-files** - 在 findings.md 中记录技术决策

### 阶段 3: 实现

使用这些技能来执行：

- **using-git-worktrees** - 创建隔离的功能分支
- **subagent-driven-development** - 委托和执行任务
- **test-driven-development** - 每个任务的 TDD 工作流
- **systematic-debugging** - 修复出现的问题
- **planning-with-files** - 每次操作后更新 progress.md

### 阶段 4: 测试与审查

使用这些技能来进行质量保证：

- **verification-before-completion** - 运行测试、验证构建
- **requesting-code-review** - 正式代码审查
- **receiving-code-review** - 处理反馈并修复问题

### 阶段 5: 完成

使用这些技能来结束：

- **finishing-a-development-branch** - 合并、PR 或清理选项
- **planning-with-files** - 最终状态更新

### 技能协调

此技能作为一个**编排器**，其作用包括：

1. **委托** 特定任务给专业技能
2. **协调** 技能之间的交接（例如 TDD → 调试 → 验证）
3. **持久化** 通过 planning-with-files 在所有阶段保存上下文
VJ|**为什么这样有效：** 每个子技能都是其领域的专家。通过将它们编排在一起，您可以在每个阶段获得同类最佳功能，而无需重新发明轮子。
NW|
NW|## 零依赖混合模式
NW|
NW|此技能以**两种模式**工作：
NW|
NW|### 模式 1: 高级模式（安装子技能）
NW|如果已安装子技能，此技能将委托它们以获得最佳体验：
NW|
NW|- 首先尝试 `skill("brainstorming")`
NW|- 如果技能未找到，使用内联降级指南
NW|
NW|### 模式 2: 独立模式（零依赖）
NW|如果子技能**未安装**，此技能使用**内置降级**内容：
NW|
NW|- 所有核心工作流都已内联文档化
NW|- 模板已嵌入此技能中
NW|- 您遵循相同的流程，但使用本文件中的指南
NW|
NW|### 工作原理
NW|
NW|1. **首先**：尝试调用子技能 `skill("xxx")`
NW|2. **如果未找到**：使用该步骤的内联降级指南
NW|3. **结果**：两种方式都能正常工作 - 只是体验级别不同
NW|
NW|**推荐**：安装子技能以获得最佳体验，但此技能完全可以在不安装它们的情况下工作！

---

## 工作流阶段

### 阶段 1: 需求与设计

- 与用户明确需求
- 创建规格说明（通过 spec-kit）
- 审查并批准规格

### 阶段 2: 技术规划

- 规划技术方案
- 分解任务
- 识别依赖关系

### 阶段 3: 实现

- 创建功能分支
- 每个任务使用 TDD
- 持续更新进度

### 阶段 4: 测试与审查

- 运行所有测试
- 验证构建通过
- 代码审查

### 阶段 5: 完成

- 最终验证
- 创建 PR / 合并
- 更新最终状态

---

## 示例

### 示例 1: 新功能

用户："添加用户认证"

- 创建 task_plan.md
- 问："认证应该包含什么？"
- 文档化需求
- 计划：登录、注册、密码重置、token 处理
- 每个都用 TDD 实现
- 验证并创建 PR

### 示例 2: Bug 修复

用户："修复登录超时"

- 创建 task_plan.md
- 问："什么时候超时？"
- 在 findings.md 中研究
- 计划：修复超时值、添加重试
- 实现并验证

### 示例 3: 重构

用户："重构数据层"

- 创建 task_plan.md
- 文档化当前问题
- 计划：提取接口、创建 repo、迁移调用者
- 每步都带测试覆盖执行
- 完整回归测试

---

## 故障排除

### 会话恢复失败

**解决方案：** 读取现有文件，询问用户继续还是重新开始

### 用户不想定义需求

**解决方案：** 创建最小化 task_plan.md，在 findings.md 中记录假设

### 任务太多

**解决方案：** 拆分成多个阶段，使用子任务文件

### 工作流中断

**解决方案：** 在停止前更新 task_plan.md 为精确的下一步

---

## 许可证

MIT 许可证 - 详见 LICENSE。

---

## 贡献

欢迎贡献！详见 CONTRIBUTING.md。

---

## 文档

| 文档 | 英文 | 中文 |
|------|------|------|
| 使用指南 | README.md | README.zh-CN.md |
| 贡献指南 | CONTRIBUTING.md | CONTRIBUTING.zh-CN.md |
| 压力测试 | tests/scenarios/pressure-tests.md | tests/scenarios/pressure-tests.zh-CN.md |
