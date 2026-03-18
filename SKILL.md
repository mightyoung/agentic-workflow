---
name: agentic-workflow
description: >
  统一智能体工作流 - 用于任何复杂任务开发。
  触发条件：
    1. 显式命令：/agentic-workflow 强制走完整流程
    2. 自动检测：复杂任务自动触发完整流程（涉及多模块、多文件、技术选型）
    3. 开发需求：实现功能、编写代码、创建项目
    4. 问题修复：调试bug、修复错误、解决崩溃
    5. 分析规划：研究最佳实践、制定方案、任务拆分
    6. 代码审查：审查代码、检查质量
  不触发：
    - 简单问答闲聊（天气、问候、谢谢）
    - 日常对话无开发意图
  核心方法：TDD驱动、专家模拟思维、文件持久化、PUA激励。
  v4.3: 语义触发优化 + 隐式意图扩展
---

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

## 路由逻辑

根据输入自动路由，支持双通道 + 智能复杂度检测：

```python
# ============================================================================
# 复杂度检测函数
# ============================================================================

def 复杂度检测为(任务描述) -> str:
    """
    根据任务描述判断复杂度
    返回: "高" | "中" | "低"
    """
    高复杂度关键词 = [
        "系统", "架构", "大型", "复杂", "分布式",
        "微服务", "集群", "高并发", "底层",
        "重新设计", "重构", "迁移"
    ]
    中复杂度关键词 = [
        "模块", "功能", "多个", "集成",
        "开发", "实现", "创建"
    ]
    低复杂度关键词 = [
        "一个", "简单", "小", "单个",
        "修改", "修复", "调整"
    ]

    # 高复杂度检测
    if 包含任意(任务描述, 高复杂度关键词):
        return "高"

    # 中复杂度检测
    if 包含任意(任务描述, 中复杂度关键词):
        return "中"

    # 默认低复杂度
    return "低"

# ============================================================================
# 路由决策：双通道 + 智能复杂度检测
# ============================================================================

# ============================================================================
# 通道1：显式命令 /agentic-workflow（强制完整流程）
# ============================================================================

if 包含("/agentic-workflow"):
    → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE

# ============================================================================
# 通道2：智能复杂度检测 + 自动触发
# ============================================================================

# 复杂度高：自动触发完整流程
if 复杂度检测为("高"):
    → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE

# 复杂度中：基础流程
elif 复杂度检测为("中"):
    → THINKING → PLANNING → EXECUTING

# 复杂度低：直接执行
elif 复杂度检测为("低"):
    → EXECUTING

# ============================================================================
# 第1层：强制触发（高置信度 - 显式意图）
# ============================================================================

# 强制 RESEARCH - 用户明确要求搜索/调研
# 注意：当用户要求"网络上搜索"时，优先使用 tavily skill，如果不可用则降级使用 websearch
if 包含("帮我搜索", "查找最佳实践", "调研一下", "调研", "搜索一下", "网络上搜索", "在网上搜索"):
    → RESEARCH → THINKING

# 强制继续任务 - 用户说"继续"、"继续下一步"时，视为完整任务的一部分
# 这类情况往往是复杂任务的延续，应该触发完整工作流
if 包含("继续", "继续下一步", "继续任务", "下一步", "继续进行", "继续执行", "接着来", "继续做"):
    → 复杂度检测("高") → THINKING → PLANNING → EXECUTING → REVIEWING

# 强制 DEBUGGING - 用户明确要求调试/修复
if 包含("帮我调试", "修复这个bug", "报错如下", "报错信息", "错误如下"):
    → DEBUGGING

# 强制 REVIEWING - 用户明确要求审查
if 包含("代码审查", "帮我review", "审查这段代码", "审计"):
    → REVIEWING

# ============================================================================
# 第2层：标准触发（显式关键词）
# ============================================================================

# RESEARCH - 技术调研/最佳实践
elif 包含("最佳实践", "有什么", "有哪些", "选型", "怎么做", "如何实现", "参考", "案例", "怎么实现", "如何做"):
    → RESEARCH → THINKING

# THINKING - 分析/专家视角
elif 包含("谁最懂", "专家", "分析", "理解", "看看", "分析一下"):
    → THINKING

# PLANNING - 任务规划
elif 包含("计划", "规划", "拆分", "设计", "安排", "整理一下"):
    → PLANNING

# DEBUGGING - 问题调试
elif 包含("bug", "错误", "调试", "修复", "报错", "崩溃", "异常", "不动", "失败", "回报", "卡住", "挂起"):
    → DEBUGGING

# REVIEWING - 代码审查
elif 包含("审查", "review", "检查"):
    → REVIEWING

# EXECUTING-FAST - 简单任务
elif 包含("写一个", "帮我写") and not 包含("系统", "架构"):
    → EXECUTING-FAST

# ============================================================================
# 第3层：隐式意图识别（语义理解 - 间接表达）
# ============================================================================

# 隐式 DEBUGGING - 问题描述（语义理解，不只是关键词匹配）
elif 包含("响应很慢", "太慢了", "跑不通", "不能用", "失效", "超时", "卡死", "无响应", "不动了", "没有反应", "卡住了", "运行出错", "启动失败", "连接失败"):
    → DEBUGGING + performance_expert

# 隐式 THINKING - 分析需求（理解用户需要分析和建议）
elif 包含("这个怎么实现", "那个行不行", "哪个好", "建议", "看法", "思路", "怎么选", "哪个更", "有什么区别", "分析一下", "帮我看看", "给点意见"):
    → THINKING

# 隐式 PLANNING - 整理需求（理解用户需要规划）
elif 包含("要做什么", "步骤", "先后顺序", "先做哪个", "怎么做", "如何开始", "从哪里入手", "规划一下", "安排一下"):
    → PLANNING

# 隐式 RESEARCH - 理解需求（用户需要搜索、调研）
elif 包含("了解一下", "想知道", "查一下", "找一下", "有没有", "哪里有", "如何实现", "怎么做的", "是什么原理"):
    → RESEARCH → THINKING

# ============================================================================
# 第4层：闲聊过滤 + 默认执行
# ============================================================================

# 闲聊过滤 - 简单问答、日常对话不触发工作流
elif 包含("天气", "笑话", "你好", "谢谢", " hi", "hello", "嗨", "嘿", "干嘛呢", "最近怎样") and not 包含("开发", "代码", "帮我", "问题", "需要"):
    → 直接回答

# EXECUTING (默认)
else:
    → EXECUTING
```

### 语义触发说明 (v4.3 新增)

**核心原则**：不只是关键词匹配，而是理解用户意图

| 触发类型 | 关键词示例 | 语义理解 |
|----------|-----------|----------|
| RESEARCH | "了解一下" | 用户需要搜索、调研 |
| THINKING | "哪个好" | 用户需要分析建议 |
| PLANNING | "怎么做" | 用户需要规划步骤 |
| DEBUGGING | "卡住了" | 用户遇到问题 |

**判断逻辑**：
1. 先检查显式命令（/agentic-workflow）
2. 再检查语义意图（理解用户真正需要什么）
3. 最后fallback到默认执行

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

## 文件索引

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
| `references/pua_flavors.md` | PUA风味 |
| `references/memory_integration.md` | 记忆集成 |

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

### 隐式意图测试用例

| ID | 用例 | 预期阶段 | 验证 |
|----|------|----------|------|
| t11 | "这个API响应很慢" | DEBUGGING+performance | ✓ |
| t12 | "太慢了" | DEBUGGING | ✓ |
| t13 | "跑不通" | DEBUGGING | ✓ |
| t14 | "哪个方案好" | THINKING | ✓ |
| t15 | "要做什么" | PLANNING | ✓ |

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
| 隐式意图识别率 | ≥80% | - |
| 误触发率 | ≤5% | - |

### 评估方法

使用 skill-creator 的优化流程：
1. 构建真实用户提示测试集
2. 运行触发测试记录结果
3. 分析误触发/漏触发案例
4. 优化触发关键词
5. 迭代验证

详见：`references/trigger_evaluation.md`
