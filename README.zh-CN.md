# 集成开发工作流

> **一条命令启动一切。** 面向 AI 编码代理的完整开发工作流编排器。

[![npm 版本](https://img.shields.io/npm/v/integrated-dev-workflow.svg)](https://www.npmjs.com/package/integrated-dev-workflow)
[![许可证: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 问题所在

AI 编码代理经常面临以下问题：
- **范围蔓延** —— 任务边界不清晰，持续扩大
- **上下文丢失** —— 长会话中失去进度追踪
- **跳过验证** —— "能工作" 但没有测试
- **工作流不一致** —— 每个任务感觉都不一样

## 解决方案

此技能提供了一个**完整的编排工作流**，引导代理完成：
1. **需求** → 清晰、文档化的目标
2. **规划** → 带依赖的任务分解
3. **实现** → 正确的分支管理下的 TDD
4. **测试与审查** → 完成前的验证
5. **完成** → 干净的合并/PR 工作流

---

## 安装

### Claude Code / Claude Desktop

1. 进入项目根目录
2. 创建 `.claude/skills` 目录（如果不存在）
3. 将此技能文件夹复制到 `.claude/skills/`
4. 重启 Claude Code

```bash
mkdir -p .claude/skills
cp -r /path/to/integrated-dev-workflow .claude/skills/
```

### Pi Agent

```bash
pi install npm:integrated-dev-workflow
```

### 手动安装

1. 进入项目根目录
2. 创建 `.agents/skills` 目录（如果不存在）
3. 将此技能文件夹复制到 `.agents/skills/`

---

## 使用方法

### 快速开始

只需告诉代理你想构建什么：

```
"我想构建用户登录功能"
"实现购物车"
"创建用户管理 API"
"修复登录超时 bug"
"重构数据层"
```

技能将自动：
1. ✅ 检查之前的会话
2. ✅ 创建跟踪文件（task_plan.md, findings.md, progress.md）
3. ✅ 引导需求定义
4. ✅ 规划实现方案
5. ✅ 按最佳实践执行

### 手动调用

```bash
# 直接调用技能
skill("integrated-dev-workflow")
```

---

## 代理兼容性

| 功能 | Claude Code | Pi Agent | 通用 |
|---------|-------------|----------|---------|
| Hooks (PreToolUse/PostToolUse) | ✅ 完全支持 | ⚠️ 有限支持 | ❌ 不支持 |
| 会话恢复 | ✅ 自动 | ⚠️ 需脚本 | ❌ 手动 |
| 文件模板 | ✅ 全部 | ✅ 全部 | ✅ 全部 |
| TDD 工作流 | ✅ 完全 | ✅ 完全 | ✅ 完全 |
| 代码审查工作流 | ✅ 完全 | ✅ 完全 | ✅ 完全 |

### Claude Code 特定说明

此技能使用 hooks 实现持久提醒：
- **PreToolUse**: 在主要操作前提醒更新 task_plan.md
- **PostToolUse**: 文件更改后提示更新任务状态
- **Stop**: 结束会话前确认任务进度

### Pi Agent 限制

- Pi Agent 不支持 hooks
- 会话恢复需要手动脚本：
  ```bash
  python3 scripts/session-recovery.py .
  ```

### 通用代理

作为纯参考技能工作。代理必须手动：
- 检查现有跟踪文件
- 每次操作后更新进度
- 明确遵循工作流步骤

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

## 必需的子技能

此技能编排以下子技能：

| 技能 | 用途 |
|-------|---------|
| `planning-with-files` | 基于文件的任务追踪 |
| `brainstorming` | 需求澄清 |
| `writing-plans` | 任务细化 |
| `using-git-worktrees` | 分支管理 |
| `subagent-driven-development` | 任务执行 |
| `test-driven-development` | TDD 工作流 |
| `systematic-debugging` | 问题排查 |
| `verification-before-completion` | 质量验证 |
| `requesting-code-review` | 代码审查 |
| `receiving-code-review` | 审查处理 |
| `finishing-a-development-branch` | 完成工作 |

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
```
用户: "添加用户认证"

→ 创建 task_plan.md
→ 问: "认证应该包含什么？"
→ 文档化需求
→ 计划: 登录、注册、密码重置、token 处理
→ 每个都用 TDD 实现
→ 验证并创建 PR
```

### 示例 2: Bug 修复
```
用户: "修复登录超时"

→ 创建 task_plan.md
→ 问: "什么时候超时？"
→ 在 findings.md 中研究
→ 计划: 修复超时值、添加重试
→ 实现并验证
```

### 示例 3: 重构
```
用户: "重构数据层"

→ 创建 task_plan.md
→ 文档化当前问题
→ 计划: 提取接口、创建 repo、迁移调用者
→ 每步都带测试覆盖执行
→ 完整回归测试
```

---

## 故障排除

### 会话恢复失败
**解决方案:** 读取现有文件，询问用户继续还是重新开始

### 用户不想定义需求
**解决方案:** 创建最小化 task_plan.md，在 findings.md 中记录假设

### 任务太多
**解决方案:** 拆分成多个阶段，使用子任务文件

### 工作流中断
**解决方案:** 在停止前更新 task_plan.md 为精确的下一步

---

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE)。

---

## 贡献

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md) 或 [CONTRIBUTING.zh-CN.md](CONTRIBUTING.zh-CN.md)。
