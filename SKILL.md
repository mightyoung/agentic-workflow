---
name: agentic-workflow
description: |
  统一智能体工作流 - 用于任何复杂任务开发。
  TRIGGER when: 用户提到开发、修复、规划、分析、审查、调研、实施、实现、创建
  DO NOT TRIGGER when: 简单问答闲聊（天气、问候、谢谢）、日常对话无开发意图
version: 4.13.0
tags: [core, workflow, tdd, debugging, planning]
requires:
  tools: [Read, Write, Bash, Grep, Glob]
  env: []
---

## 三层内容加载 (v4.6新增)

| 层级 | 内容 | 加载时机 |
|------|------|----------|
| **Layer 1** | name + description + TRIGGER/DO NOT TRIGGER | 始终加载 (~100词) |
| **Layer 2** | SKILL.md 核心内容 | skill触发时加载 (~500行) |
| **Layer 3** | references/ + scripts/ | 按需加载 |

> **设计原则**：参考 anthropics/skills 的渐进式披露模式，控制context长度。

# Agentic Workflow - 统一智能体工作流

> 融合 best-minds, brainstorming, writing-plans, planning-with-files, TDD, systematic-debugging, verification, pua, tavily 精髓

---

## v4.2 新架构：双通道工作流

### 通道1：显式命令（强制完整流程）

用户可以使用 `/agentic-workflow` 命令显式调用完整工作流：

```
/agentic-workflow 帮我开发一个电商系统
/agentic-workflow 修复这个复杂的分布式事务bug
/agentic-workflow 规划这个大型项目
```

**效果**：强制执行完整流程 THINKING → PLANNING → EXECUTING → REVIEWING

### 通道2：智能自动检测

根据任务复杂度自动判断：

| 复杂度 | 特征 | 行为 |
|--------|------|------|
| **高** | 多模块、多文件、技术选型 | 自动触发完整流程 |
| **中** | 多步骤功能 | THINKING → PLANNING → EXECUTING |
| **低** | 单文件简单修改 | 直接 EXECUTING |

**复杂度判断规则**：
```python
if 包含("系统", "架构", "大型", "复杂", "分布式") or 文件数 > 3:
    → 完整流程
elif 包含("模块", "功能", "多个") or 步骤 > 2:
    → 基础流程
else:
    → 直接执行
```

---

## 核心原则

### 1. 专家模拟思维 (Best-Minds)
不要问"你怎么看"，而是问"这个问题谁最懂？TA会怎么说？"。

### 2. 文件持久化 (Planning-with-Files + RESEARCH)
- task_plan.md - 任务计划
- findings.md - 研究发现
- progress.md - 进度追踪

### 3. TDD 驱动
测试先行 → 失败 → 实现 → 通过

### 4. RESEARCH 前置搜索 (Tavily)
- 思考前先搜索最佳实践
- **优先使用 tavily skill 进行搜索**：`skill("tavily", "搜索内容")`
  - 如果 tavily 不可用或失败，降级使用 websearch
- 将搜索结果存入 findings.md

### 5. PUA 激励引擎 (失败时触发)

### 6. 注意力管理
- **铁律一：穷尽一切** - 没有穷尽所有方案之前，禁止说"无法解决"
- **铁律二：先做后问** - 遇到问题先自行搜索、读源码、验证，再提问
- **铁律三：主动出击** - 端到端交付，不只是"刚好够用"
- 每3个动作循环重读 task_plan.md

### 7. 禁止询问原则

> Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The human might be asleep... You are autonomous.

### 8. HARD-GATE 设计门禁 (v4.12新增)

> **核心原则**：在设计被用户批准之前，禁止任何实现动作。

```markdown
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

**适用场景**：创建功能、构建组件、添加功能、修改行为
**不适用**：简单文件修改、日常问答

### 9. 技能触发 Red Flags (v4.12新增)

> **核心原则**：如果有哪怕 1% 的可能性技能适用，你必须调用它。

**技能检查在以下动作之前执行**：
- 任何澄清问题
- 任何代码探索
- 任何实现动作

**Red Flags - 防止自我合理化**：

| 当你这样想时 | 实际含义是 | 正确做法 |
|-------------|-----------|---------|
| "这只是简单问题" | 问题即任务，需要检查技能 | STOP，检查技能 |
| "我需要先了解更多" | 技能检查在获取上下文之前 | 先调用技能 |
| "快速看一下文件" | 文件缺少对话上下文 | 先调用技能 |
| "这个技能有点过度" | 简单事情容易变复杂 | 使用技能 |
| "不需要用技能" | 如果技能存在就用它 | 调用技能 |
| "我记住这个技能了" | 技能在演进，读取当前版本 | 调用技能 |
| "这只算一个问题" | 行动=任务，需要检查技能 | 检查技能 |
| "感觉很有成效" | 无纪律的行动浪费时间 | 先检查技能 |

**优先级**：
1. **流程技能优先** (brainstorming, debugging) - 决定如何做
2. **实现技能次之** (TDD, code-review) - 指导执行

### 10. YAGNI 检查 (v4.13新增)

> **核心原则**：不要提前实现尚未需要的功能。

**YAGNI 检查在 PLANNING 阶段必须执行**：

| 问题 | 如果答案是"是" | 正确做法 |
|------|----------------|---------|
| 用户明确要求了这个功能吗？ | ❌ 不是当前需要的 | 删除它 |
| 这个功能在用户故事中有提到吗？ | ❌ 没有 | 删除它 |
| 移除它会导致测试失败吗？ | ❌ 不会 | 删除它 |
| 这是为了"以防万一"吗？ | ✅ 过度设计 | 删除它 |

**强制检查清单**（PLANNING 阶段每次任务拆分时）：

- [ ] 每个任务项是否对应用户明确说的需求？
- [ ] 是否有"我觉得以后可能需要"的代码？
- [ ] 是否在解决当前不存在的问题？
- [ ] 是否有提前优化性能/架构的冲动？

**如果检测到 YAGNI 违反**：
```
⚠️ YAGNI 警告
检测到: [描述可能不需要的功能]
原因: [为什么可能不需要]
建议: [删除或标记为 TODO]

[1] 删除这个功能
[2] 标记为 TODO（将来可能需要）
[3] 保留（用户确实需要）
```

---

## 快速开始

| 场景 | 执行 |
|------|------|
| 强制完整流程 | /agentic-workflow + 任务描述 |
| Bug修复 | DEBUGGING |
| 项目规划 | PLANNING |
| 技术调研 | RESEARCH + THINKING |
| 代码审查 | REVIEWING |
| 简单任务 | 直接执行 |

---

## 状态机

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→
```

### RESEARCH 阶段（自动触发）
- 触发条件：复杂任务（3+步骤）、新技术领域、需要外部参考
- **搜索工具：优先使用 tavily skill 进行搜索**
  - 如果 tavily 不可用或失败，降级使用 websearch
  - 使用 `skill("tavily", "搜索内容")` 调用
  - tavily 是 AI 优化的搜索，返回简洁相关内容
- 搜索范围：网络最佳实践、GitHub 成熟项目，社区讨论、官方文档
- 输出：结构化搜索结果存入 findings.md

---

## 自修正决策点 (v4.8)

### 核心设计原则

> Claude Code 是单会话同步模型，**无法实现自动循环修正**。正确的模式是**决策点模式**：机器检测问题 → 提示人类决策。

### 决策点类型

| 决策点 | 触发条件 | 检测机制 | 人类选项 |
|--------|----------|----------|----------|
| **预算超限** | 任务执行时间 > 预算 | `check_task_budget` | 延长时间/跳过/中止 |
| **质量门禁失败** | typecheck/lint/test 任一失败 | `quality_gate.py` | 重试/跳过/中止 |
| **循环停滞** | 3次尝试同一步骤无进展 | 人工判断 | 换方案/寻求帮助/中止 |
| **上下文耗尽** | 剩余 context < 20% | 感知 | 总结继续/请求用户帮助 |
| **空闲恢复** | 用户长时间不活动后再次发送消息 | 读取SESSION-STATE时间戳 | 从断点继续/查看进度/新任务 |

### 决策点触发流程

```
EXECUTING 阶段内:
    if check_task_budget(task_id)["over_budget"]:
        → 暂停执行
        → 输出决策卡片:
            ┌─────────────────────────────────────┐
            │ ⚠️ 任务 T001 已超出预算 (60s/300s) │
            │                                     │
            │ 已完成: 用户认证模块 70%            │
            │ 剩余: 权限管理、API集成、测试        │
            │                                     │
            │ [1] 延长时间 +60s                   │
            │ [2] 跳过剩余任务                   │
            │ [3] 中止并报告                     │
            └─────────────────────────────────────┘
        → 等待用户输入 (1/2/3)
        → 根据用户选择继续执行

REVIEWING 阶段:
    if not quality_gate.all_passed:
        → 输出决策卡片:
            ┌─────────────────────────────────────┐
            │ ✗ 质量门禁失败                      │
            │                                     │
            │ 失败项: lint (3个错误)              │
            │                                     │
            │ [1] 自动修复 lint 问题              │
            │ [2] 手动审查后再试                 │
            │ [3] 跳过 lint 继续                 │
            └─────────────────────────────────────┘
        → 等待用户输入
```

### 决策点集成到状态机

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓           ↓
         DEBUGGING ←──────┼───────────┼───────────┼───────────┼──→ DECISION_POINT
                                          ↓                       ↓
                                    (预算/质量/停滞)        (人类决策)
```

### 脚本支持

```bash
# 预算检查 - 返回决策建议
python scripts/task_tracker.py --op=budget --task-id=T001

# 质量门禁 - 返回通过/失败状态
python scripts/quality_gate.py --dir=src --gate=all --json

# 决策点提示模板
python scripts/task_tracker.py --op=get --task-id=T001 --path=.task_tracker.json
```

### 决策原则

1. **不自动猜测** - 所有修正决策由人类做出
2. **提供上下文** - 决策前输出完整的任务状态和选项
3. **记录决策** - 将决策结果写入 SESSION-STATE.md
4. **学习历史** - 相同的决策模式存入 MEMORY.md

---

## 路由逻辑 (v4.6)

> **设计原则**：参考 anthropics/skills 的 TRIGGER/DO NOT TRIGGER 模式

```python
# ============================================================================
# 第0层：负面过滤（最先执行，避免误触发）
# ============================================================================

# DO NOT TRIGGER - 简单闲聊不触发
if 包含_any(消息, ["天气", "笑话", "你好", "谢谢", " hi", "hello", "嗨"]) and not 包含_any(消息, ["开发", "代码", "帮我", "问题", "需要"]):
    → 直接回答  # 不触发工作流

# ============================================================================
# 第1层：显式命令（强制触发，最高优先级）
# ============================================================================

# 强制完整流程 - /agentic-workflow 命令
if 包含("/agentic-workflow"):
    → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE

# 强制 RESEARCH - 用户明确要求搜索/调研
if 包含_any(消息, ["帮我搜索", "查找最佳实践", "调研一下", "调研", "搜索一下", "网络上搜索", "在网上搜索"]):
    → RESEARCH → THINKING

# 强制 DEBUGGING - 用户明确要求调试/修复
if 包含_any(消息, ["帮我调试", "修复这个bug", "报错如下", "报错信息", "错误如下"]):
    → DEBUGGING

# 强制 REVIEWING - 用户明确要求审查
if 包含_any(消息, ["代码审查", "帮我review", "审查这段代码", "审计"]):
    → REVIEWING

# 强制继续任务 - 用户说"继续"时视为复杂任务延续
if 包含_any(消息, ["继续", "继续下一步", "继续任务", "下一步", "继续进行", "继续执行", "接着来", "继续做"]):
    → 完整工作流

# ============================================================================
# 第2层：智能检测（标准关键词匹配）
# ============================================================================

# RESEARCH - 技术调研/最佳实践
elif 包含_any(消息, ["最佳实践", "有什么", "有哪些", "选型", "怎么做", "如何实现", "参考", "案例", "怎么实现", "如何做"]):
    → RESEARCH → THINKING

# THINKING - 分析/专家视角
elif 包含_any(消息, ["谁最懂", "专家", "分析", "理解", "看看", "分析一下"]):
    → THINKING

# PLANNING - 任务规划
elif 包含_any(消息, ["计划", "规划", "拆分", "设计", "安排", "整理一下"]):
    → PLANNING

# DEBUGGING - 问题调试
elif 包含_any(消息, ["bug", "错误", "调试", "修复", "报错", "崩溃", "异常", "不动", "失败", "回报", "卡住", "挂起"]):
    → DEBUGGING

# REVIEWING - 代码审查
elif 包含_any(消息, ["审查", "review", "检查"]):
    → REVIEWING

# EXECUTING-FAST - 简单任务（明确小功能）
elif 包含("写一个", "帮我写") and not 包含_any(消息, ["系统", "架构"]):
    → EXECUTING-FAST

# ============================================================================
# 第3层：语义理解（间接表达，v4.3新增）
# ============================================================================

# 隐式 DEBUGGING - 问题描述
elif 包含_any(消息, ["响应很慢", "太慢了", "跑不通", "不能用", "失效", "超时", "卡死", "无响应", "不动了", "没有反应", "卡住了", "运行出错", "启动失败", "连接失败"]):
    → DEBUGGING + performance_expert

# 隐式 THINKING - 分析需求
elif 包含_any(消息, ["这个怎么实现", "那个行不行", "哪个好", "建议", "看法", "思路", "怎么选", "哪个更", "有什么区别", "分析一下", "帮我看看", "给点意见"]):
    → THINKING

# 隐式 PLANNING - 整理需求
elif 包含_any(消息, ["要做什么", "步骤", "先后顺序", "先做哪个", "怎么做", "如何开始", "从哪里入手", "规划一下", "安排一下"]):
    → PLANNING

# 隐式 RESEARCH - 理解需求
elif 包含_any(消息, ["了解一下", "想知道", "查一下", "找一下", "有没有", "哪里有", "如何实现", "怎么做的", "是什么原理"]):
    → RESEARCH → THINKING

# ============================================================================
# 默认执行
# ============================================================================
else:
    → EXECUTING

```

### 路由说明 (v4.6)

**简化原则**：删除L3隐式意图识别（准确率不可靠）

| 层级 | 类型 | 说明 |
|------|------|------|
| 第0层 | 负面过滤 | DO NOT TRIGGER，最先执行 |
| 第1层 | 显式命令 | 强制触发，优先级最高 |
| 第2层 | 智能检测 | 关键词匹配 |
| 第3层 | 语义理解 | 间接表达（可选启用） |

**判断逻辑**：
1. 先执行负面过滤（DO NOT TRIGGER）
2. 再检查显式命令（/agentic-workflow）
3. 然后检查强制触发关键词
4. 最后fallback到默认执行

**负面触发条件（DO NOT TRIGGER）**：
- 简单闲聊：天气、笑话、问候、谢谢
- 日常对话无开发意图：除非明确提到开发/代码/帮我/问题/需要

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

### 记忆操作命令 (v4.6)

| 命令 | 脚本 | 功能 |
|------|------|------|
| `/check-memory` | `memory_ops.py` | 检查当前 SESSION-STATE 状态 |
| `/save-memory` | `memory_longterm.py --op=refine` | 从日志提炼到 MEMORY.md |
| `/search-memory [关键词]` | `memory_longterm.py --op=search` | 搜索长期记忆 |
| `/clear-session` | 手动删除 | 清除 SESSION-STATE，开始新会话 |
| `/show-daily [日期]` | `memory_daily.py --op=show` | 查看每日日志 |
| `/log-task` | `memory_daily.py --op=add-task` | 记录任务到每日日志 |
| `/log-lesson` | `memory_daily.py --op=add-lesson` | 记录教训到每日日志 |

---

## 完整工作流示例

```
用户: 帮我开发一个用户认证系统

1. THINKING: 谁最懂？(安全专家) → 添加专家视角
2. PLANNING: 创建计划文件 → 拆分任务
3. EXECUTING: TDD循环 → 测试→失败→实现→通过
4. REVIEWING: 规范检查 → 代码质量审查
5. COMPLETE: 更新 SESSION-STATE.md + 可选提炼到 MEMORY.md
```

---

## COMPLETE 阶段 (v4.9新增)

任务完成后必须执行以下动作:

### 1. 更新 SESSION-STATE.md
将任务结果、关键决策、用户偏好更新到当前会话状态文件。

### 2. 自反思日志 (v4.9新增)
完成任何任务后，进行结构化自反思:

```markdown
## 自反思日志

### 任务
[任务描述]

### 执行结果
- 状态: 成功/部分成功/失败
- 关键决策: [做了哪些决定]
- 用户反馈: [用户的纠正或确认]

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

### 3. WAL 模式晋升 (v4.9新增)
如果检测到同一模式被纠正3次或以上，触发晋升确认:

```
检测到3次相似纠正: "用户偏好使用 X 而非 Y"
是否确认该模式为永久规则?
  [1] 确认并添加到 PATTERNS.md
  [2] 暂时忽略
  [3] 查看历史记录
```

### 4. 可选: 提炼到 MEMORY.md
如果任务包含重要经验且可跨会话复用:
```bash
python scripts/memory_longterm.py --op=refine --days=7
```

### VBR 验证清单 (v4.10新增)
在报告完成前，必须确认以下各项：

- [ ] **测试通过** - 所有测试用例通过
- [ ] **质量门禁通过** - typecheck/lint/test 全部绿灯
- [ ] **无硬编码 secrets** - 代码中无 API keys、passwords、tokens
- [ ] **验证输出已生成** - 功能从用户视角验证可用
- [ ] **SESSION-STATE 已更新** - 任务结果、决策、偏好已记录
- [ ] **自反思已完成** - 结构化反思日志已写入

如果任何项未通过，报告 [2] 手动审查后再试 或 [3] 跳过 质量门禁继续。

### 空闲检测机制 (v4.11新增)
当用户在长时间(>30分钟)不活动后再次发送消息时:

1. **检测**: 读取 SESSION-STATE.md 的时间戳
2. **判断**: 如果 last_active > 30分钟，输出空闲恢复卡
3. **恢复**: 用户选择后从断点继续或开始新任务

```
┌─────────────────────────────────────┐
│ 💓 空闲检测                          │
│ 任务: 用户认证模块 (中断于EXECUTING)  │
│ 空闲时间: 45分钟                     │
│                                     │
│ [1] 从断点继续                      │
│ [2] 查看详细进度                    │
│ [3] 新任务                          │
└─────────────────────────────────────┘
```

### 上下文管理最佳实践 (v4.12新增)

当感觉到响应变长或历史变深时，主动采取以下行动:

1. **感知信号**:
   - 单次响应超过500行
   - 历史消息超过20轮
   - 用户提示"太长了"

2. **行动选项**:
   - 主动询问用户是否需要总结
   - 在 SESSION-STATE.md 记录关键进度
   - 使用 `/compact` 命令手动压缩上下文

3. **预防措施**:
   - 复杂任务开始前先做总结
   - 每完成一个子任务主动更新 SESSION-STATE
   - 关键决策立即持久化，避免依赖上下文

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

## Subagent 集成 (v4.0)

基于 [Claude Code Sub-Agents](https://code.claude.com/docs/en/sub-agents) 和 [Agent Teams](https://code.claude.com/docs/en/agent-teams) 最佳实践，agentic-workflow 可以派生子智能体并行执行任务。

### 子智能体架构

```
agentic-workflow (主智能体/Leader)
    ↓ 派生请求
ecc-workflow (子智能体调度层)
    ↓ 执行
ECC Subagents (6个核心子智能体)
```

### 核心子智能体

| 智能体 | 职责 | 触发条件 |
|--------|------|----------|
| **researcher** | 研究搜索 | 最佳实践、搜索、调研 |
| **coder** | 代码实现 | 编写代码、功能实现 |
| **reviewer** | 代码审查 | 审查、review |
| **debugger** | 调试修复 | bug、错误、调试 |
| **planner** | 任务规划 | 计划、拆分 |
| **tester** | 测试编写 | 写测试、测试用例 |

### 调用方式

当需要并行执行独立任务时，使用 ecc-workflow 派生子智能体：

```
用户: 帮我审查这个10个文件的PR

→ agentic-workflow 路由到 REVIEWING
→ ecc-workflow 派生 3 个 reviewer 子智能体
  - reviewer_1: 审查文件 1-4
  - reviewer_2: 审查文件 5-7
  - reviewer_3: 审查文件 8-10
→ 并行执行
→ 汇总审查结果
→ 返回给用户
```

### 并行决策矩阵

| 任务类型 | 执行模式 | 示例 |
|----------|----------|------|
| 独立任务 | 并行 | 多文件审查、多模块开发 |
| 依赖任务 | 串行 | 规划→执行、测试→修复 |
| 后台任务 | 后台 | 大规模搜索、构建 |
| 复杂任务 | 混合 | 研究+规划+执行 |

### 效率提升

| 场景 | 单智能体 | Subagents | 提升 |
|------|----------|-----------|------|
| 电商网站开发 | 120s | 30s | **4x** |
| 10文件代码审查 | 30s | 10s | **3x** |
| 技术调研 | 25s | 8s | **3x** |

详细设计见: `docs/ecc_subagents_integration_design.md`

---

## PUA 激励 (v4.4)

默认使用阿里味作为激励风格：
> "底层逻辑是什么？顶层设计在哪里？抓手在哪？如何保证闭环？"

详见: `references/modules/debugging.md` (5步调试法)

---

## 注意事项

1. **单一入口** - 这个技能是唯一入口
2. **KV-Cache** - 保持prompt稳定
3. **按需加载** - 需要时读取 references/
4. **错误保留** - 调试保留上下文
5. **穷尽原则** - 没说"无法解决"前必须尝试3方案

---

## Subagents 子智能体 (v4.0)

基于 [Claude Code Sub-Agents](https://code.claude.com/docs/en/sub-agents) 最佳实践，agentic-workflow 内置 7 个专业化子智能体。

### 子智能体列表

| 智能体 | 职责 | 对应阶段 | 触发条件 |
|--------|------|----------|----------|
| **researcher** | 研究搜索 | RESEARCH | 最佳实践、搜索、调研 |
| **planner** | 任务规划 | PLANNING | 计划、拆分 |
| **coder** | 代码实现 | EXECUTING | 编写代码、功能实现 |
| **reviewer** | 代码审查 | REVIEWING | 审查、review |
| **debugger** | 调试修复 | DEBUGGING | bug、错误、调试 |
| **security_expert** | 安全审查 | THINKING/REVIEWING | 认证、权限、加密、数据安全 |
| **performance_expert** | 性能优化 | THINKING/REVIEWING | 性能瓶颈、延迟、缓存、数据库优化 |

### 架构

```
agentic-workflow (主智能体/Leader)
    ↓ 派生
7个子智能体 (独立上下文)
    ↓ 执行
结果汇总 → 返回用户
```

### 调用时机

当任务有独立可并行处理的部分时，使用子智能体：

```
用户: 帮我审查这个10个文件的PR

→ 派生 3 个 reviewer 子智能体 (并行)
→ 汇总审查结果
→ 返回用户
```

详细定义见 `agents/` 目录。

### 与 WORKFLOW 阶段对应

| 阶段 | 子智能体 | 说明 |
|------|----------|------|
| RESEARCH | researcher | 搜索最佳实践 |
| THINKING | security_expert / performance_expert | 专家模拟 + 专项分析 |
| PLANNING | planner | 任务拆分规划 |
| EXECUTING | coder | 代码实现 |
| REVIEWING | reviewer / security_expert / performance_expert | 代码审查 + 专项审查 |
| DEBUGGING | debugger | 问题调试 |

### 并行决策

| 任务类型 | 执行模式 |
|----------|----------|
| 独立任务 | 并行 |
| 依赖任务 | 串行 |
| 混合任务 | 分组并行 |

详见：`references/modules/spawn_subagents.md`

---

## 文件索引 (v4.6)

| 文件 | 用途 |
|------|------|
| `agents/` | 子智能体定义 |
| `references/templates/` | 任务计划模板 |
| `references/modules/spawn_subagents.md` | 子智能体调用模块 |
| `references/modules/executing.md` | 执行模块详解 |
| `references/modules/thinking.md` | 专家推理详解 |
| `references/modules/debugging.md` | 调试方法论 |
| `references/modules/reviewing.md` | 代码审查指南 |
| `references/quick_ref.md` | 快速参考卡 |
| `references/ecc_integration.md` | ECC集成指南 |
| `references/builtin_tdd.md` | TDD内置版 |
| `references/builtin_e2e.md` | E2E内置版 |
| `references/memory_integration.md` | 记忆集成 |
| `scripts/` | 可执行脚本（Bash/Python） |
| `scripts/win/` | Windows 批处理脚本 |
| `agentic-workflow.lock` | 版本锁定文件 |

---

## 脚本调用 (v4.6新增)

当需要自动化执行时，Agent 应该根据操作系统自动选择合适的脚本版本：

### 系统检测逻辑

Agent 在调用脚本前应自动检测操作系统：

```python
import platform
import os

def get_script_runner():
    """根据操作系统返回脚本运行器和路径"""
    system = platform.system().lower()

    if system == "windows" or os.name == "nt":
        return {
            "name": "Windows",
            "shell": "cmd",
            "python": "python",
            "script_ext": ".bat",
            "path_sep": "\\",
            "scripts_dir": "scripts\\win"  # Windows 批处理脚本
        }
    elif system == "darwin" or system == "linux":
        return {
            "name": "Unix/Linux/macOS",
            "shell": "bash",
            "python": "python3",
            "script_ext": ".sh",
            "path_sep": "/",
            "scripts_dir": "scripts"  # Bash/Python 脚本
        }
```

### 跨平台脚本调用示例

```python
# 自动选择正确的脚本版本
runner = get_script_runner()

if runner["name"] == "Windows":
    # Windows: 使用批处理脚本
    run("scripts\\win\\init_session.bat")
    run("scripts\\win\\check_env.bat")
    run("scripts\\win\\quick_review.bat src\\")
else:
    # Unix/Linux/macOS: 使用 Bash 脚本
    run("bash scripts/init_session.sh")
    run("bash scripts/check_env.sh")
    run("bash scripts/quick_review.sh src/")
```

### Python 脚本（跨平台）

Python 脚本在所有操作系统上均可运行：

```bash
# WAL 触发扫描 - 检测用户消息中的修正/偏好/决策信息
python scripts/wal_scanner.py "用户消息文本"

# 记忆操作 - 更新 SESSION-STATE
python scripts/memory_ops.py --op=update --key=preference --value="用户偏好"

# 任务状态追踪
python scripts/task_tracker.py --op=status --task-id=xxx
```

### Bash 脚本（Unix/Linux/macOS）

```bash
# 初始化会话
bash scripts/init_session.sh

# 检查环境
bash scripts/check_env.sh

# 快速审查
bash scripts/quick_review.sh src/
```

### Windows 批处理脚本

```batch
:: 初始化会话
scripts\win\init_session.bat

:: 检查环境
scripts\win\check_env.bat

:: 快速审查
scripts\win\quick_review.bat src\
```

### 脚本优先级

| 类型 | 跨平台 | 优先级 | 适用场景 |
|------|--------|--------|----------|
| Python | ✅ | 高 | 需要复杂逻辑、数据处理、跨平台兼容 |
| Bash | ❌ | 中 | Unix/Linux/macOS 快速任务 |
| Batch | ❌ | 低 | Windows 快速任务（仅 Windows） |

详见：`scripts/README.md`

---

## 触发评估集 (v4.1)

基于最佳实践，建立触发评估机制用于持续优化：

### 强制触发测试用例

| ID | 用例 | 预期阶段 | 验证 |
|----|------|----------|------|
| t01 | "帮我搜索分布式事务最佳实践" | RESEARCH | ✓ |
| t02 | "修复这个bug" | DEBUGGING | ✓ |
| t03 | "代码审查一下" | REVIEWING | ✓ |
| t04 | "报错如下：..." | DEBUGGING | ✓ |
| t05 | "帮我调试这个API" | DEBUGGING | ✓ |

### 标准触发测试用例

| ID | 用例 | 预期阶段 | 验证 |
|----|------|----------|------|
| t06 | "有什么好的缓存策略" | RESEARCH | ✓ |
| t07 | "怎么做用户认证" | RESEARCH | ✓ |
| t08 | "分析一下这个方案" | THINKING | ✓ |
| t09 | "帮我规划这个项目" | PLANNING | ✓ |
| t10 | "检查这段代码" | REVIEWING | ✓ |

### 不触发测试用例

| ID | 用例 | 预期阶段 | 验证 |
|----|------|----------|------|
| n01 | "今天天气怎么样" | 直接回答 | ✓ |
| n02 | "谢谢你" | 直接回答 | ✓ |
| n03 | "你好呀" | 直接回答 | ✓ |
| n04 | "给我讲个笑话" | 直接回答 | ✓ |

### 触发率目标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 强制触发准确率 | ≥95% | - |
| 标准触发准确率 | ≥90% | - |
| 误触发率 | ≤5% | - |

### 评估方法

使用 skill-creator 的优化流程：
1. 构建真实用户提示测试集
2. 运行触发测试记录结果
3. 分析误触发/漏触发案例
4. 优化触发关键词
5. 迭代验证

详见：`references/trigger_evaluation.md`
