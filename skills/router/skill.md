---
name: router
version: 1.0.0
description: |
  智能路由 - 根据任务复杂度自动选择工作流阶段
  3层路由：负面过滤 → 显式命令 → 智能检测
tags: [phase, routing, core]
requires:
  tools: [Read, Write]
---

# ROUTER

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

ROUTER 是 agentic-workflow 的入口阶段，负责分析用户消息并路由到正确的工作流阶段。

### 核心职责

- 分析用户输入的复杂度
- 应用 4 层路由架构
- 选择合适的处理阶段
- 更新 SESSION-STATE 记录路由决策

### 4-Layer Routing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER MESSAGE                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L0: 负面过滤 (Negative Filter)                             │
│  - 识别无效/危险请求                                        │
│  - 直接拒绝并说明原因                                       │
└─────────────────────────────────────────────────────────────┘
                              │ PASS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L1: 显式命令 (Explicit Command)                           │
│  - 检测 /research, /planning, /executing 等命令             │
│  - 精确匹配，跳过智能检测                                   │
└─────────────────────────────────────────────────────────────┘
                              │ PASS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L2: 智能检测 (Smart Detection)                             │
│  - 关键词匹配 + 复杂度评估                                  │
│  - 识别 RESEARCH/THINKING/PLANNING 需求                     │
└─────────────────────────────────────────────────────────────┘
                              │ PASS
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  L3: 语义理解 (Semantic Understanding)                      │
│  - 意图分类                                                │
│  - 复杂度评估 (高/中/低)                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   SELECT PHASE  │
                    └─────────────────┘
```

## Preload Detection

> **IMPORTANT**: Preload 检测在路由决策之前执行，确保环境就绪

### 执行时机

```
USER MESSAGE
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  PRELOAD DETECTION (新增)                                   │
│  - 环境验证                                                  │
│  - 依赖检查                                                  │
│  - 会话状态验证                                              │
└─────────────────────────────────────────────────────────────┘
      │ PASS
      ▼
┌─────────────────────────────────────────────────────────────┐
│  L0: 负面过滤 (Negative Filter)                             │
└─────────────────────────────────────────────────────────────┘
      ...
```

### 1. 环境验证 (Environment Validation)

**检查项**:

| 检查项 | 验证方式 | 失败处理 |
|--------|----------|----------|
| 操作系统 | `uname -s` | 记录 warning，不阻止 |
| 必需工具 | `which git`, `which node`, `which npm` | 提示安装 |
| 磁盘空间 | `df -h` (可用 > 1GB) | 警告并建议清理 |
| 网络连接 | `curl -s --max-time 5 https://api.github.com` | 记录 offline 状态 |

**必需工具清单**:

| 工具 | 用途 | 最低版本 |
|------|------|----------|
| `git` | 代码版本控制 | 2.30+ |
| `node` | JavaScript 运行时 | 18.0+ |
| `npm` | 包管理器 | 9.0+ |

**验证脚本**:

```bash
# 环境检查函数
function preload_env_check() {
  local errors=()

  # 检查必需工具
  for tool in git node npm; do
    if ! command -v "$tool" &> /dev/null; then
      errors+=("REQUIRED_TOOL_MISSING: $tool is not installed")
    fi
  done

  # 检查磁盘空间 (macOS/ Linux 兼容)
  local available
  if [[ "$OSTYPE" == "darwin"* ]]; then
    available=$(df -h . | awk 'NR==2 {print $4}' | sed 's/Gi//')
  else
    available=$(df -h . | awk 'NR==2 {print $4}' | sed 's/G//')
  fi

  if (( $(echo "$available < 1" | bc -l) )); then
    errors+=("LOW_DISK_SPACE: Only ${available}GB available")
  fi

  # 检查网络连接
  if ! curl -s --max-time 5 https://api.github.com &> /dev/null; then
    errors+=("NETWORK_OFFLINE: Cannot reach api.github.com")
  fi

  return ${#errors[@]}
}
```

### 2. 依赖检查 (Dependency Checks)

**Skill 依赖**:

| Skill | 用途 | 必需 | 检查方式 |
|-------|------|------|----------|
| `tavily` | AI 搜索 | 否 | `skill("tavily", "test")` 降级 websearch |
| `research` | 调研能力 | 否 | 检查 skill.md 存在 |
| `thinking` | 思考能力 | 否 | 检查 skill.md 存在 |
| `planning` | 规划能力 | 否 | 检查 skill.md 存在 |
| `executing` | 执行能力 | 是 | 检查 skill.md 存在 |

**验证脚本**:

```bash
# Skill 依赖检查函数
function preload_skill_check() {
  local errors=()
  local warnings=()
  local skill_dir="${HOME}/.claude/skills/agentic-workflow/skills"

  # 必须存在的 skills
  local required_skills=("executing" "router")
  for skill in "${required_skills[@]}"; do
    if [ ! -f "$skill_dir/$skill/skill.md" ]; then
      errors+=("REQUIRED_SKILL_MISSING: $skill/skill.md not found")
    fi
  done

  # 可选存在的 skills
  local optional_skills=("research" "thinking" "planning" "reviewing" "debugging" "complete")
  for skill in "${optional_skills[@]}"; do
    if [ ! -f "$skill_dir/$skill/skill.md" ]; then
      warnings+=("OPTIONAL_SKILL_MISSING: $skill/skill.md not found")
    fi
  done

  # 返回状态
  if [ ${#errors[@]} -gt 0 ]; then
    return 1  # 严重错误
  elif [ ${#warnings[@]} -gt 0 ]; then
    return 2  # 警告
  fi
  return 0  # 成功
}
```

### 3. 会话状态验证 (Session State Validation)

**检查项**:

| 检查项 | 验证方式 | 失败处理 |
|--------|----------|----------|
| 会话 ID | `SESSION_ID` 已设置 | 生成新 ID |
| 会话状态文件 | `~/.gstack/sessions/$SESSION_ID/state.md` 存在 | 初始化新会话 |
| 会话过期 | `last_active` 时间戳 | 超过 24h 则重置 |
| 阶段历史 | `current_phase` 已记录 | 初始化为 router |

**验证脚本**:

```bash
# 会话状态检查函数
function preload_session_check() {
  local errors=()
  local session_file="${HOME}/.gstack/sessions/${SESSION_ID:-default}/state.md"

  # 确保会话目录存在
  mkdir -p "$(dirname "$session_file")"

  # 检查会话状态文件
  if [ ! -f "$session_file" ]; then
    # 初始化新会话
    cat > "$session_file" << 'EOF'
# Session State

## 元数据
- session_id: {SESSION_ID}
- started_at: {TIMESTAMP}
- last_active: {TIMESTAMP}

## 路由状态
- current_phase: router
- routing_history: []
EOF
    return 0
  fi

  # 检查会话过期 (24h = 86400 秒)
  local last_active
  last_active=$(grep "last_active:" "$session_file" | awk -F': ' '{print $2}')
  local current_time
  current_time=$(date +%s)
  local elapsed=$((current_time - last_active))

  if [ $elapsed -gt 86400 ]; then
    errors+=("SESSION_EXPIRED: Session is ${elapsed}s old (max 86400s)")
  fi

  # 检查 current_phase
  if ! grep -q "current_phase:" "$session_file"; then
    errors+=("SESSION_STATE_CORRUPT: current_phase not found")
  fi

  return ${#errors[@]}
}
```

### Preload 错误处理

**错误级别**:

| 级别 | 代码 | 含义 | 处理方式 |
|------|------|------|----------|
| `CRITICAL` | 1 | 必需工具/Skill 缺失 | 阻止路由，请求用户修复 |
| `WARNING` | 2 | 可选组件缺失 | 记录警告，继续路由 |
| `INFO` | 0 | 检查通过 | 正常继续 |

**输出格式**:

```
## Preload Status

**状态**: [PASS | WARNING | CRITICAL]

**环境检查**:
- OS: {darwin|linux|windows}
- 工具: {git ✓, node ✓, npm ✓}
- 磁盘: {available}GB free
- 网络: {online|offline}

**依赖检查**:
- Required Skills: {all present|missing: xxx}
- Optional Skills: {all present|missing: xxx, yyy}

**会话检查**:
- Session ID: {SESSION_ID}
- Session Age: {X hours}
- Phase: {current_phase}

**下一步**:
{{#if CRITICAL}}
⚠️ 环境问题阻止路由: {具体错误}
请修复后重试。
{{#else}}
✓ 继续路由决策...
{{/if}}
```

**可操作的错误消息示例**:

| 错误 | 可操作消息 |
|------|-----------|
| `git not installed` | "请安装 Git: https://git-scm.com/downloads" |
| `tavily skill missing` | "tavily skill 不可用，将降级使用 websearch" |
| `SESSION_EXPIRED` | "会话已过期 (24h+)，已自动重置" |
| `LOW_DISK_SPACE` | "磁盘空间不足，请清理: `brew cleanup` 或 `rm -rf ~/Library/Caches/*`" |

## Entry Criteria

ROUTER 阶段在以下情况被调用：

1. **会话开始** - 用户发送新消息，没有当前阶段
2. **阶段完成** - 上一阶段已完成，需要确定下一阶段
3. **用户请求重新路由** - 用户明确要求重新分析任务

## Exit Criteria

ROUTER 阶段完成的条件：

- [ ] 已完成 L0 负面过滤
- [ ] 已确定路由层级 (L1/L2/L3)
- [ ] 已选择目标阶段
- [ ] SESSION-STATE 已更新 (phase, routing_reason, complexity)
- [ ] 上下文已准备完毕

## Layer-by-Layer Routing Logic

### L0: 负面过滤 (Negative Filter)

**目的**: 识别并拒绝无效或危险的请求

**拒绝关键词**:

| 类别 | 关键词 | 响应 |
|------|--------|------|
| 恶意软件 | 病毒、木马、攻击、破解 | 拒绝并警告 |
| 敏感操作 | rm -rf /, 格式化硬盘 | 拒绝并警告 |
| 社会工程 | 钓鱼、欺诈、冒充 | 拒绝并警告 |
| 无意义请求 | asdhfkasdhf, asdf | 询问用户意图 |

**无意义请求统计检测** (Statistical Detection):

```
IF 字符重复率 > 80% THEN
    候选为无意义请求
ELSE IF 汉字覆盖率 < 10% AND 英文覆盖率 < 10% AND 数字覆盖率 < 10% THEN
    候选为无意义请求
ELSE IF 连续辅音字母 > 15 THEN
    候选为无意义请求
END

IF 候选为无意义请求 THEN
    询问用户意图: "我没有理解你的意思，请重新描述你的需求"
END
```

**处理流程**:

```
IF 匹配拒绝关键词 THEN
    拒绝请求
    说明拒绝原因
    记录到 SESSION-STATE (blocked: true, block_reason:)
    EXIT ROUTER
END
```

### L1: 显式命令 (Explicit Command)

**目的**: 精确匹配用户明确指定的命令

**命令映射表**:

| 命令 | 目标阶段 | 优先级 |
|------|----------|--------|
| `/research` | RESEARCH | 1 |
| `/thinking` | THINKING | 1 |
| `/planning` | PLANNING | 1 |
| `/executing` | EXECUTING | 1 |
| `/reviewing` | REVIEWING | 1 |
| `/complete` | COMPLETE | 1 |
| `/debug` | DEBUGGING | 1 |
| `/retro` | RETRO | 1 |
| `/office-hours` | OFFICE-HOURS | 1 |
| `/help` | HELP | 1 |

**L1 动态命令检测**:
```
# /retro 回顾 - 用户明确要求回顾
if 包含_any(消息, ["回顾", "retro", "复盘", "总结经验"]):
    → RETRO (standalone)
```

**处理流程**:

```
IF 匹配 L1 命令 THEN
    SELECT 对应阶段
    记录到 SESSION-STATE (phase: X, routing_reason: "explicit_command")
    EXIT ROUTER
END
```

**遥测记录**:
```bash
decision_record "explicit_command" "用户显式命令" "$SELECTED_PHASE" ""
```

### L2: 智能检测 (Smart Detection)

**目的**: 通过关键词和模式匹配识别任务类型

**关键词分类表**:

| 阶段 | 触发关键词 | 模式 |
|------|------------|------|
| RESEARCH | 搜索、调研、研究、查找、有什么、有哪些、选型 | 调研类 |
| THINKING | 思考、想想、分析一下、怎么看、有什么想法、思考一下 | 分析类 |
| PLANNING | 计划、规划、怎么实现、如何做、设计 | 规划类 |
| EXECUTING | 写代码、开发、实现、做、功能、执行、帮我 | 执行类 |
| REVIEWING | review、审核、检查、看看有什么问题 | 审查类 |
| DEBUGGING | 报错、错误、异常、bug、调试、debug、修复 | 调试类 |
| OFFICE-HOURS | 想法、概念、产品、不确定方向、帮我构思、怎么开始 | 产品咨询类 |

**匹配优先级规则**:

```
# 当多个阶段关键词匹配时，按以下优先级选择:
# 1. 精确匹配优先于模糊匹配（匹配字符越长越精确）
# 2. 长度相同时：DEBUGGING > REVIEWING > THINKING > PLANNING > RESEARCH > EXECUTING
# 3. 特殊命令（/xxx）永远优先于关键词匹配

IF "看看有什么问题" THEN
    匹配 REVIEWING（"看看" + "问题" = 8字符）
    不匹配 RESEARCH（只有"问题" = 2字符）
    → 选择 REVIEWING
END
```

**复杂度评估规则**:

```
# 步骤/模块/文件数量
STEP_COUNT = 统计步骤、模块、文件数量

# 技术难度评估
IF 涉及 新技术/未知领域 THEN
    TECH_DIFFICULTY = HIGH
ELSE IF 涉及 团队不熟悉的技术 THEN
    TECH_DIFFICULTY = MEDIUM
ELSE
    TECH_DIFFICULTY = LOW
END

# 依赖复杂度
IF 涉及 外部API/数据库/分布式 THEN
    DEPENDENCY_COMPLEXITY = HIGH
ELSE IF 涉及 内部模块交互 THEN
    DEPENDENCY_COMPLEXITY = MEDIUM
ELSE
    DEPENDENCY_COMPLEXITY = LOW
END

# 综合复杂度
IF STEP_COUNT >= 3 OR TECH_DIFFICULTY = HIGH OR DEPENDENCY_COMPLEXITY = HIGH THEN
    complexity = HIGH
ELSE IF STEP_COUNT = 2 OR TECH_DIFFICULTY = MEDIUM OR DEPENDENCY_COMPLEXITY = MEDIUM THEN
    complexity = MEDIUM
ELSE
    complexity = LOW
END
```

**遥测记录**:
```bash
decision_record "complexity_assessment" "$COMPLEXITY_REASON" "$COMPLEXITY" "HIGH, MEDIUM, LOW"
```

### L3: 语义理解 (Semantic Understanding)

**目的**: 基于意图分类和复杂度选择最佳阶段

**意图分类**:

| 意图 | 描述 | 默认阶段 |
|------|------|----------|
| `inquiry` | 简单问题/查询 | EXECUTING |
| `implementation` | 开发/实现任务 | EXECUTING |
| `investigation` | 研究/调研任务 | RESEARCH |
| `analysis` | 分析/思考任务 | THINKING |
| `planning` | 规划/设计任务 | PLANNING |
| `verification` | 验证/测试任务 | REVIEWING |
| `debug` | 调试/修复错误 | DEBUGGING |
| `idea` | 产品想法/概念不明确 | OFFICE-HOURS |

**复杂度等级**:

| 等级 | 指标 | 路由策略 |
|------|------|----------|
| HIGH | 3+ 步骤, 多文件, 新技术 | RESEARCH → THINKING → PLANNING → EXECUTING |
| MEDIUM | 2-3 步骤, 2+ 文件 | THINKING → PLANNING → EXECUTING |
| LOW | 1 步骤, 单文件, 简单 | 直接 EXECUTING |

**遥测记录**:
```bash
decision_record "intent_classification" "$INTENT" "$SELECTED_PHASE" ""
decision_record "agent_routing" "基于复杂度和意图选择阶段" "$SELECTED_PHASE" "alternative_phase1, alternative_phase2"
```

## Phase Selection Matrix

```
┌────────────────────────────────────────────────────────────────────┐
│                    PHASE SELECTION MATRIX                          │
├──────────────┬─────────────────────────────────────────────────────┤
│  Complexity  │  Intent → Default Phase                              │
├──────────────┼─────────────────────────────────────────────────────┤
│  HIGH        │  inquiry → EXECUTING                                │
│              │  implementation → RESEARCH → THINKING → PLANNING    │
│              │  investigation → RESEARCH                            │
│              │  analysis → THINKING                                │
│              │  planning → PLANNING                                │
├──────────────┼─────────────────────────────────────────────────────┤
│  MEDIUM      │  inquiry → EXECUTING                                │
│              │  implementation → THINKING → PLANNING → EXECUTING   │
│              │  investigation → RESEARCH                           │
│              │  analysis → THINKING                                │
│              │  planning → PLANNING                               │
├──────────────┼─────────────────────────────────────────────────────┤
│  LOW         │  inquiry → EXECUTING                                │
│              │  implementation → EXECUTING                         │
│              │  investigation → EXECUTING                          │
│              │  analysis → EXECUTING                              │
│              │  planning → EXECUTING                              │
└──────────────┴─────────────────────────────────────────────────────┘
```

## Fast Path Detection

> **Fast Path**: 简单任务跳过不必要阶段，直接执行

### Fast Path 识别标准

**简单任务特征**:

| 特征 | 判断条件 | 示例 |
|------|----------|------|
| 单文件修改 | 涉及 ≤1 个文件 | "帮我修改 utils.js 的这个函数" |
| 无技术选型 | 不需要选择技术方案 | "写一个排序函数" |
| 无多轮调试 | 不需要反复修改 | "添加一个 console.log" |
| 明确需求 | 用户已描述清楚要什么 | "把这个变量改名" |
| 无研究需求 | 不需要搜索最佳实践 | "实现一个已有的设计" |

**快速识别规则**:

```
IF 匹配以下任一条件 THEN Fast Path = true:

1. 单命令执行:
   - 包含 "写一个函数" / "帮我改" / "添加日志"
   - 不包含 "怎么做" / "最佳实践" / "如何实现"

2. 明确文件+操作:
   - 包含具体文件名 + 具体修改操作
   - 操作类型: add, fix, modify, refactor

3. 复制粘贴类:
   - "把这个代码复制到..."
   - "帮我把这个函数移到..."

4. 小改动:
   - 涉及行数 < 20 行
   - 不涉及配置变更
   - 不涉及依赖变更
```

### Fast Path 流程

```
                    ┌─────────────────────────────────────┐
                    │           ROUTER DECISION            │
                    └─────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    │                                   │
                    ▼                                   ▼
              ┌───────────┐                    ┌───────────────┐
              │ FAST PATH │                    │ STANDARD PATH │
              └───────────┘                    └───────────────┘
                    │                                   │
                    ▼                                   ▼
    ┌───────────────────────────────────┐    ┌───────────────────────┐
    │  ROUTER → EXECUTING → COMPLETE    │    │  Full Phase Flow      │
    │                                   │    │  (根据复杂度选择)      │
    │  跳过: RESEARCH, THINKING, PLANNING│    └───────────────────────┘
    │  跳过: REVIEWING (除非用户要求)     │
    └───────────────────────────────────┘
```

### Fast Path vs Standard Path

| 维度 | Fast Path | Standard Path |
|------|-----------|--------------|
| 适用场景 | 简单、明确的小改动 | 复杂、多阶段任务 |
| Phase 序列 | EXECUTING | RESEARCH→THINKING→PLANNING→EXECUTING→REVIEWING |
| 审查 | 跳过 (除非发现严重问题) | 完整审查 |
| 缓存 | 启用 | 启用 |
| 典型时间 | < 2min | 15-45min |

### 用户控制

```bash
# 强制使用标准路径
/agentic-workflow --no-fast-path "帮我开发一个电商系统"

/# 查看是否使用 fast path
/agentic-workflow --show-path "帮我改这个bug"
# 输出: Fast Path: YES (理由: 单文件修改)

# 手动指定路径
/agentic-workflow --path standard "..."
```

### Fast Path 决策输出

```
## Router Status

**状态**: DONE

**路由层级**: L2/L3 (Fast Path 识别)

**选中阶段**: EXECUTING

**路由原因**: simple_single_file_modification

**复杂度**: LOW

**Fast Path**: YES
- 理由: 单文件修改，无技术选型需求
- 跳过: RESEARCH, THINKING, PLANNING, REVIEWING
- 预计时间: < 2 分钟

**下一步**: 进入 EXECUTING 阶段
```

## State Machine Integration

### 状态流转

```
                    ┌─────────────┐
                    │   ROUTER    │
                    └─────────────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
              ▼           ▼           ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐
        │RESEARCH │ │THINKING │ │EXECUTING│
        └─────────┘ └─────────┘ └─────────┘
              │           │           │
              └───────────┴───────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │   ROUTER    │  (再路由)
                    └─────────────┘
```

### SESSION-STATE 更新

ROUTER 完成后，必须更新 SESSION-STATE：

```markdown
## 路由决策
- current_phase: {SELECTED_PHASE}
- routing_layer: {L0|L1|L2|L3}
- routing_reason: {具体原因}
- complexity: {HIGH|MEDIUM|LOW}
- matched_keywords: [{匹配的关键词列表}]
- blocked: {true|false}
- block_reason: {如果被阻止，说明原因}
```

**遥测记录**:
```bash
# 路由决策完成时记录
metric_record "routing_layer_used" "$ROUTING_LAYER" "count" "router"
metric_record "complexity_level" "$COMPLEXITY" "level" "router"
```

## Traceability

### 路由日志格式

```
[ROUTER] L0 Negative Filter: PASS (no blocking keywords)
[ROUTER] L1 Explicit Command: PASS (/planning detected)
[ROUTER] L2 Smart Detection: SKIP (L1 matched)
[ROUTER] Selected Phase: PLANNING
[ROUTER] Routing Reason: explicit_command
[ROUTER] Complexity: MEDIUM
```

### 决策追溯

所有路由决策必须可追溯：

1. **记录原始用户消息**
2. **记录每个 Layer 的匹配结果**
3. **记录最终决策及其依据**
4. **存入 SESSION-STATE 供后续使用**

## Fallback Rules

### 默认行为

当所有 Layer 都无法确定时：

```
DEFAULT_PHASE = EXECUTING
COMPLEXITY = LOW
ROUTING_REASON = "fallback_default"
```

### 异常处理

| 异常情况 | 处理方式 |
|----------|----------|
| L0 触发 | 拒绝并说明原因 |
| L1-L3 都失败 | 使用默认路由 |
| 复杂度无法评估 | 假设为 MEDIUM |
| 阶段命令无效 | 提示有效命令列表 |

## Integration Points

### 引用其他 Skills

| Phase | Skill 文件 | 用途 |
|-------|------------|------|
| RESEARCH | `skills/research/skill.md` | 调研阶段 |
| THINKING | `skills/thinking/skill.md` | 思考阶段 |
| PLANNING | `skills/planning/skill.md` | 规划阶段 |
| EXECUTING | `skills/executing/skill.md` | 执行阶段 |
| REVIEWING | `skills/reviewing/skill.md` | 审查阶段 |
| COMPLETE | `skills/complete/skill.md` | 完成阶段 |
| DEBUGGING | `skills/debugging/skill.md` | 调试阶段 |
| RETRO | `skills/gstack/commands/retro.md` | 独立回顾（可选） |

### 兼容性

- **命令兼容性**: 支持 `/agentic-workflow` 命令及其缩写
- **阶段兼容性**: 所有 phase skill 遵循统一的 preamble 和结构
- **状态兼容性**: SESSION-STATE 格式跨所有阶段一致

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 退出条件 |
|------|------|----------|
| **DONE** | 路由完成 | 已选择阶段，状态已更新 |
| **BLOCKED** | 被阻止 | L0 负面过滤触发 |
| **AMBIGUOUS** | 模糊不清 | 无法确定用户意图 |

### 输出格式

```
## Router Status

**状态**: [DONE | BLOCKED | AMBIGUOUS]

**路由层级**: [L0 | L1 | L2 | L3]

**选中阶段**: {PHASE_NAME}

**路由原因**: {详细原因}

**复杂度**: [HIGH | MEDIUM | LOW]

**匹配关键词**: [{列表}]

**下一步**: 进入 {NEXT_PHASE} 阶段
```

## Design Principles

1. **Single Entry**: 所有用户消息首先经过 ROUTER
2. **Priority**: L0 负面过滤 > L1 显式命令 > L2 智能检测 > L3 语义理解
3. **Fallback**: 无法确定时默认 EXECUTING
4. **Traceability**: 所有决策记录到 SESSION-STATE
5. **Backward Compatibility**: 保持与 /agentic-workflow 命令的兼容性

## Quick Reference

### 路由决策速查

```
用户说 "/planning"         → PLANNING (L1)
用户说 "帮我搜索..."        → RESEARCH (L2)
用户说 "思考一下..."       → THINKING (L2)
用户说 "写一个函数"        → EXECUTING (L3, LOW)
用户说 "帮我开发一个系统"  → RESEARCH (L3, HIGH)
用户说 "asdfasdf"         → BLOCKED (L0)
```

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}
