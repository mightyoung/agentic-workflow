---
name: agentic-workflow
description: >
  统一智能体工作流 - 用于任何复杂任务开发。
  包含：思考分析、任务规划、代码执行，规范审查、调试。
  当用户请求：开发功能、修复bug、规划项目、代码审查、实现需求时使用。
  自动管理任务进度，规范检查(OpenSpec可选)和错误恢复。
  不问"你怎么看"，而是问"这个问题谁最懂"。
  v3.0: 渐进式披萨架构 + ECC降级集成
---

# Agentic Workflow - 统一智能体工作流

> 融合 best-minds, brainstorming, writing-plans, planning-with-files, TDD, systematic-debugging, verification, pua, tavily 精髓

## 核心原则

### 1. 专家模拟思维 (Best-Minds)
不要问"你怎么看"，而是问"这个问题谁最懂？TA会怎么说？"。

### 2. 文件持久化 (Planning-with-Files + RESEARCH)
- task_plan.md - 任务计划
- findings.md - 研究发现
- progress.md - 进度追踪

### 3. TDD 驱动
测试先行 → 失败 → 实现 → 通过

### 4. RESEARCH 前置搜索 (Tavily) - 必须显式调用
- 思考前先搜索最佳实践
- **必须使用 Skill 工具调用 tavily skill 进行搜索**
- 规划前先调研成熟案例
- 将搜索结果存入 findings.md

### 5. PUA 激励引擎 (失败时触发)

### 6. 注意力管理
- **铁律一：穷尽一切** - 没有穷尽所有方案之前，禁止说"无法解决"
- **铁律二：先做后问** - 遇到问题先自行搜索、读源码、验证，再提问
- **铁律三：主动出击** - 端到端交付，不只是"刚好够用"
- 每3个动作循环重读 task_plan.md

---

## 快速开始

| 场景 | 执行 |
|------|------|
| 新功能开发 | EXECUTING + TDD |
| Bug修复 | DEBUGGING |
| 项目规划 | PLANNING |
| 技术调研 | RESEARCH + THINKING |
| 代码审查 | REVIEWING |

完整流程：状态机 → 路由逻辑 → 模块执行 → 经验存储

---

## 状态机

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→
```

### RESEARCH 阶段（自动触发）
- 触发条件：复杂任务（3+步骤）、新技术领域、需要外部参考
- 搜索范围：网络最佳实践、GitHub 成熟项目，社区讨论、官方文档
- 输出：结构化搜索结果存入 findings.md

---

## 路由逻辑

根据输入自动路由：

```python
# 闲聊不触发
if 包含("天气", "笑话", "你好", "谢谢") and not 包含("开发", "代码"):
    → 直接回答

# RESEARCH - 最高优先级
if 包含("最佳实践", "有什么", "有哪些", "选型", "怎么做", "如何实现", "参考", "案例"):
    → RESEARCH → THINKING

# THINKING
elif 包含("谁最懂", "专家", "分析", "理解"):
    → THINKING

# PLANNING
elif 包含("计划", "规划", "拆分", "设计", "安排"):
    → PLANNING

# DEBUGGING
elif 包含("bug", "错误", "调试", "修复", "报错", "崩溃", "异常"):
    → DEBUGGING

# REVIEWING
elif 包含("审查", "review", "检查", "代码审查"):
    → REVIEWING

# EXECUTING-FAST (简单任务)
elif 包含("写一个", "帮我写") and not 包含("系统", "架构"):
    → EXECUTING-FAST

# EXECUTING (默认)
else:
    → EXECUTING
```

---

## 模块概览

| 模块 | 触发词 | 核心动作 | 详细指南 |
|------|--------|----------|----------|
| RESEARCH | 最佳实践、怎么做、参考 | 搜索 → findings.md | `references/modules/executing.md` |
| THINKING | 谁最懂、专家、分析 | 模拟专家推理 | `references/modules/thinking.md` |
| PLANNING | 计划、规划、拆分 | 写 task_plan.md | `references/templates/` |
| EXECUTING | 开发、实现、写 | TDD循环 → 重构 | `references/modules/executing.md` |
| REVIEWING | 审查、review、检查 | 代码审查 → 分级 | `references/modules/reviewing.md` |
| DEBUGGING | bug、错误、调试 | 5步方法论 | `references/modules/debugging.md` |

### 快速动作

- **TDD循环**: 写测试 → 失败 → 实现 → 通过 → 重构
- **PUA铁律**: 穷尽3方案 → 先做后问 → 主动出击
- **调试5步**: 闻味道 → 揪头发 → 照镜子 → 执行 → 复盘

---

## 完整工作流示例

```
用户: 帮我开发一个用户认证系统

1. THINKING: 谁最懂？(安全专家) → 添加专家视角
2. PLANNING: 创建计划文件 → 拆分任务
3. EXECUTING: TDD循环 → 测试→失败→实现→通过
4. REVIEWING: 规范检查 → 代码质量审查
5. COMPLETE: memory_store 存储经验
```

---

## 与其他 Skills 的关系

| 原 Skill | 融合后角色 |
|---------|-----------|
| best-minds | THINKING |
| brainstorming | 被替换 |
| writing-plans | PLANNING |
| planning-with-files | 文件模板 |
| TDD | EXECUTING |
| pua | EXECUTING + DEBUGGING |
| systematic-debugging | DEBUGGING |
| verification | REVIEWING |
| tavily | RESEARCH |
| ecc-workflow | 工具命令（按需调用+降级） |

---

## ECC命令集成

需要特定命令时尝试调用 ecc-workflow，失败则使用内置版本：

| 任务 | ECC调用 | 内置版本 |
|------|---------|----------|
| TDD | `skill("ecc-workflow", "/tdd")` | `references/builtin_tdd.md` |
| 代码审查 | `skill("ecc-workflow", "/code-review")` | `references/modules/reviewing.md` |
| E2E | `skill("ecc-workflow", "/e2e")` | `references/builtin_e2e.md` |

**降级流程**: 尝试ECC → 不存在 → 提示用户(安装或内置)

详见: `references/ecc_integration.md`

---

## PUA 风味扩展包

详见 `references/pua_flavors.md`

---

## 注意事项

1. **单一入口** - 这个技能是唯一入口
2. **KV-Cache** - 保持prompt稳定
3. **按需加载** - 需要时读取 references/
4. **错误保留** - 调试保留上下文
5. **PUA自动** - 失败2次+进入增强模式
6. **穷尽原则** - 没说"无法解决"前必须尝试3方案

---

## 文件索引

| 文件 | 用途 |
|------|------|
| `references/templates/` | 任务计划模板 |
| `references/modules/executing.md` | 执行模块详解 |
| `references/modules/thinking.md` | 专家推理详解 |
| `references/modules/debugging.md` | 调试方法论 |
| `references/modules/reviewing.md` | 代码审查指南 |
| `references/quick_ref.md` | 快速参考卡 |
| `references/ecc_integration.md` | ECC集成指南 |
| `references/builtin_tdd.md` | TDD内置版 |
| `references/builtin_e2e.md` | E2E内置版 |
| `references/pua_flavors.md` | PUA风味 |
| `references/memory_integration.md` | 记忆集成 |
