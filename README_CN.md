# Agentic Workflow | 统一智能体工作流

> 融合 10+ 世界顶级 Skills 精髓的 AI 开发工作流

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-4.9-blue.svg)](SKILL.md)

---

## 技能快速对照表

| 本 Skill 模块 | 源自成熟 Skill | 行业顶级优势 | 核心价值 |
|--------------|---------------|-------------|----------|
| **RESEARCH** | tavily, planning-with-files | AI 优化搜索 + 文件持久化 | 决策基于真实证据 |
| **THINKING** | best-minds | 专家级思维模拟 | 避免泛泛而谈 |
| **PLANNING** | writing-plans, planning-with-files | 敏捷任务拆分 + 文件记忆 | 进度可衡量可回滚 |
| **EXECUTING** | TDD, pua | 测试驱动 + 压力升级 | 代码正确性保障 |
| **REVIEWING** | verification, openspec | 分级审查 + 规范驱动 | 60%+ Bug 拦截 |
| **DEBUGGING** | systematic-debugging, pua | 5步方法论 + 7项检查 | 10x 调试效率 |

---

## 什么是 Agentic Workflow？

Agentic Workflow 是一个**统一的 AI 开发工作流 Skill**，融合了 10+ 个世界级 Skills 的精髓（v4.9 版本）。它为处理复杂开发任务提供了系统化方法，从思考规划到执行调试。

### 核心原则

**不问"你怎么看"，而是问"这个问题谁最懂？TA会怎么说？"**

这一原则借鉴自 best-minds 方法论，确保我们始终利用专家级思维而非泛泛而谈。

---

## v4.9 新特性

### 1. 自进化机制

| 特性 | 描述 | 状态 |
|------|------|------|
| **自反思日志** | COMPLETE 阶段结构化反思模板 | 新增 |
| **3x 确认规则** | WAL 模式晋升机制（3次纠正后晋升） | 新增 |
| **决策点** | 人类决策的自修正模式 | 已实现 |

### 2. 自进化循环

```
检测 → 决策点 → 人类审批 → 进化
     ↑                          ↓
     ←←←←← (模式学习) ←←←←←←←
```

### 3. WAL 协议（预写日志）

用户修正、偏好、决策的内存触发检测：

| 类型 | 示例 | 动作 |
|------|------|------|
| 修正 | "是X，不是Y" | 更新 SESSION-STATE |
| 偏好 | "我喜欢X" | 记录偏好 |
| 决策 | "用X方案" | 保存决策 |
| 数值 | 数字、URL、ID | 存储精确值 |

### 4. 三层记忆架构

```
SESSION-STATE.md     → 工作内存（当前会话）
memory/YYYY-MM-DD.md → 每日日志（可选）
MEMORY.md           → 长期记忆（可选）
```

---

## v4.8 预算控制与质量门禁

### 预算控制（信息性）

| 命令 | 功能 |
|------|------|
| `task_tracker.py --op=start` | 启动任务计时 |
| `task_tracker.py --op=budget` | 检查预算状态 |

> 注意：预算追踪仅为信息性，不会截断任务。

### 质量门禁

任务完成前的自动化验证：

| 门禁 | 工具 | 用途 |
|------|------|------|
| typecheck | tsc/pyright/mypy | 类型安全 |
| lint | eslint/flake8 | 代码风格 |
| test | jest/pytest | 功能测试 |

---

## 架构

### 状态机

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→
```

### 路由逻辑（4层）

| 层级 | 类型 | 说明 |
|------|------|------|
| L0 | 负面过滤 | DO NOT TRIGGER（闲聊） |
| L1 | 显式命令 | 强制触发（/agentic-workflow） |
| L2 | 智能检测 | 关键词匹配 |
| L3 | 语义理解（可选） | 间接表达 |

---

## 快速开始

### 显式命令（强制完整流程）

```
/agentic-workflow 帮我开发一个电商系统
```

### 自动检测

| 复杂度 | 行为 |
|--------|------|
| 高（多模块） | 完整流程 |
| 中（多步骤） | THINKING → PLANNING → EXECUTING |
| 低（单文件） | 直接执行 |

---

## 脚本

| 脚本 | 平台 | 用途 |
|------|------|------|
| `wal_scanner.py` | 跨平台 | WAL 触发检测 |
| `task_tracker.py` | 跨平台 | 预算控制 + 质量门禁 |
| `quality_gate.py` | 跨平台 | 自动化验证 |
| `memory_ops.py` | 跨平台 | SESSION-STATE 操作 |
| `memory_daily.py` | 跨平台 | 每日日志管理 |
| `memory_longterm.py` | 跨平台 | 长期记忆 |

**Windows 批处理脚本**（scripts/win/）：
- `init_session.bat`, `check_env.bat`, `quick_review.bat` 等

---

## 测试状态 (v4.9)

| 组件 | 状态 |
|------|------|
| 触发路由 | 100% (40/40) |
| Bash 脚本 | 100% (8/8) |
| Python 脚本 | 100% |
| Windows 脚本 | 100% (5/5) |
| 子智能体架构 | 100% (7/7) |
| 记忆系统 | Layer 1/2/3 已实现 |
| 质量门禁 | P0 - typecheck/lint/test |
| 预算控制 | P1 - start/budget/quality-gate |
| 自修正 | P2 - 决策点模式 |
| 3x 确认 | v4.9 - WAL 模式晋升 |

---

## 文件结构

```
agentic-workflow/
├── SKILL.md                    # 主技能定义
├── README.md / README_CN.md    # 文档（中英双语）
├── .gitignore                  # Git 忽略规则
├── agentic-workflow.lock       # 版本锁定文件
├── references/
│   ├── modules/                # 工作流模块
│   │   ├── executing.md
│   │   ├── thinking.md
│   │   ├── debugging.md
│   │   └── reviewing.md
│   ├── templates/              # 文件模板
│   │   ├── task_plan.md
│   │   └── session_state.md
│   ├── memory_integration.md   # 记忆系统
│   └── builtin_tdd.md          # 内置 TDD
├── scripts/
│   ├── wal_scanner.py         # WAL 触发扫描器
│   ├── task_tracker.py         # 任务预算控制
│   ├── quality_gate.py         # 质量门禁
│   ├── memory_ops.py           # 记忆操作
│   ├── memory_daily.py         # 每日日志
│   ├── memory_longterm.py      # 长期记忆
│   └── win/                   # Windows 批处理脚本
└── agents/                     # 子智能体定义
```

---

## 核心原则

### 铁律三则

1. **穷尽一切** - 没有穷尽所有方案之前，禁止说"无法解决"
2. **先做后问** - 遇到问题先自行搜索、读源码、验证，再提问
3. **主动出击** - 端到端交付，不只是"刚好够用"

### PUA 激励引擎

失败时自动触发：
- 穷尽 3 方案
- 先做后问
- 主动出击

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件。
