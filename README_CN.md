# Agentic Workflow | 统一智能体工作流

> 融合 10+ 世界顶级 Skills 精髓的 AI 开发工作流

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/mightyoung/agentic-workflow)](https://github.com/mightyoung/agentic-workflow)
[![Version](https://img.shields.io/badge/Version-4.13-blue.svg)](SKILL.md)

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

Agentic Workflow 是一个**统一的 AI 开发工作流 Skill**，融合了 10+ 个世界级 Skills 的精髓（v4.13 版本）。它为处理复杂开发任务提供了系统化方法，从思考规划到执行调试。

### 核心原则

**不问"你怎么看"，而是问"这个问题谁最懂？TA会怎么说？"**

这一原则借鉴自 best-minds 方法论，确保我们始终利用专家级思维而非泛泛而谈。

---

## v4.13 新特性

### 1. YAGNI 检查 (v4.13)

> **核心原则**：不要提前实现尚未需要的功能。

| 问题 | 如果答案是"是" | 正确做法 |
|------|----------------|---------|
| 用户明确要求了这个功能吗？ | ❌ 不是当前需要的 | 删除它 |
| 这个功能在用户故事中有提到吗？ | ❌ 没有 | 删除它 |
| 移除它会导致测试失败吗？ | ❌ 不会 | 删除它 |
| 这是为了"以防万一"吗？ | ✅ 过度设计 | 删除它 |

### 2. 频繁提交规则 (v4.13)

> **核心原则**：每完成一个有意义的独立工作单元，立即提交。

| 完成动作 | 必须提交 |
|---------|---------|
| 一个函数/方法 | ✅ |
| 一个测试用例 | ✅ |
| 一个小功能模块 | ✅ |
| 修复一个 bug | ✅ |
| 完成重构（行为不变） | ✅ |
| 完成文档更新 | ✅ |

---

## v4.12 新特性

### 1. HARD-GATE 设计门禁

> **核心原则**：在设计被用户批准之前，禁止任何实现动作。

```
<HARD-GATE>
在以下条件满足之前，禁止执行任何实现动作：
- ❌ 编写任何代码
- ❌ 搭建项目结构
- ❌ 执行任何实现动作
- ❌ 调用实现类技能

必须完成：
- ✅ 理解用户真正想要什么
- ✅ 提出 2-3 个方案含权衡分析
- ✅ 获得用户对设计的分段批准
- ✅ 将设计写入文档
```

### 2. Red Flags - 防止自我合理化

> **核心原则**：如果有哪怕 1% 的可能性技能适用，你必须调用它。

| 当你这样想时 | 实际含义是 | 正确做法 |
|-------------|-----------|---------|
| "这只是简单问题" | 问题即任务，需要检查技能 | STOP，检查技能 |
| "我需要先了解更多" | 技能检查在获取上下文之前 | 先调用技能 |
| "快速看一下文件" | 文件缺少对话上下文 | 先调用技能 |

### 3. 分段设计确认

复杂设计分段呈现，逐步获取批准：

| 项目类型 | 设计篇幅 | 确认节奏 |
|----------|----------|----------|
| 简单（单文件） | 几句话 | 1次确认 |
| 中等（2-3文件） | 每部分100-200字 | 每部分确认 |
| 复杂（多系统） | 每部分200-300字 | 每部分确认 |

---

## v4.11 新特性：空闲检测与结果追踪

### 空闲检测

用户长时间(>30分钟)不活动后再次发送消息时：

1. **检测**: 读取 SESSION-STATE.md 的时间戳
2. **判断**: 如果 last_active > 30分钟，输出空闲恢复卡
3. **恢复**: 用户选择后从断点继续或开始新任务

### 结果追踪 (JSONL)

任务执行历史，Append-only JSONL 格式：

```json
{"timestamp": "2026-03-20T10:45:00", "task_id": "T001", "status": "success", "duration_seconds": 300}
```

---

## v4.9 自进化机制

### 自反思日志

COMPLETE 阶段结构化自反思：

```markdown
## 自反思日志

### 任务
[任务描述]

### 执行结果
- 状态: 成功/部分成功/失败
- 关键决策: [做了哪些决定]

### 观察
- 发现了什么: [执行中的观察]
- 意外情况: [未曾预料的问题]

### 教训
- 下次如何改进: [具体的改进建议]
- 模式识别: [是否是重复出现的模式]

### WAL 模式晋升检查
- 相似纠正次数: N
- 是否需要晋升: [是/否]
```

### 3x 确认规则

检测到同一模式被纠正3次或以上，触发晋升确认：

```
检测到3次相似纠正: "用户偏好使用 X 而非 Y"
是否确认该模式为永久规则?
  [1] 确认并添加到 PATTERNS.md
  [2] 暂时忽略
  [3] 查看历史记录
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

## 测试状态 (v4.13)

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
| HARD-GATE | v4.12 - 设计门禁 |
| Red Flags | v4.12 - 防止自我合理化 |
| 分段设计 | v4.12 - 分步确认 |
| YAGNI 检查 | v4.13 - 防止过度设计 |
| 频繁提交 | v4.13 - 每单元提交 |

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
