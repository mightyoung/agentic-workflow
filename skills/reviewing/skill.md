---
name: reviewing
version: 1.0.0
description: |
  审查阶段 - 代码质量、安全和性能审查
  TRIGGER when: 用户提到审查、review、检查、审计
tags: [phase, reviewing]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# REVIEWING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

REVIEWING 阶段是 agentic-workflow 的质量门禁，负责对实现阶段的产出进行全方位审查，确保代码质量、安全性、性能和可维护性达到上线标准。

### 核心职责

| 维度 | 内容 | 子智能体 |
|------|------|---------|
| 代码质量 | 格式、命名、注释、架构 | reviewer |
| 安全检查 | 注入、越权、泄露、认证授权 | security_expert |
| 性能审查 | 复杂度、内存、IO、缓存 | performance_expert |
| 问题分级 | 🔴致命、🟡严重、🟢建议 | reviewer |

### 审查维度详解 (team-reviewer 模式)

#### Security 维度检查清单

| 检查项 | 内容 |
|--------|------|
| 输入验证 | SQL注入、XSS、CSRF、命令注入 |
| 认证授权 | 认证绕过、权限检查、Token管理 |
| 敏感数据 | 密钥暴露、日志泄露、加密存储 |
| 依赖漏洞 | 已知CVE、过期依赖 |
| API安全 | 限流、输入边界 |

#### Performance 维度检查清单

| 检查项 | 内容 |
|--------|------|
| 数据库 | N+1查询、缺失索引、全表扫描 |
| 内存 | 泄漏、过度分配、缓存效率 |
| 算法 | 时间/空间复杂度、循环嵌套 |
| 资源 | 连接池、文件句柄、清理逻辑 |

#### Architecture 维度检查清单

| 检查项 | 内容 |
|--------|------|
| SOLID原则 | 单一职责、开闭原则、里氏替换 |
| 边界 | 模块耦合、循环依赖、层次结构 |
| 抽象 | 过度工程、抽象不足 |
| 错误处理 | 一致性策略、异常暴露 |

#### Testing 维度检查清单

| 检查项 | 内容 |
|--------|------|
| 覆盖率 | 关键路径、边界条件、异常路径 |
| 隔离性 | 测试独立性、确定性、Mock准确性 |
| 可维护性 | 命名清晰、断言质量、脆弱性 |

#### Accessibility 维度检查清单 (UI场景)

| 检查项 | 内容 |
|--------|------|
| WCAG合规 | 对比度、语义化HTML、ARIA |
| 导航 | 键盘支持、焦点管理、Tab顺序 |
| 响应式 | 缩放支持、动态字体 |

### 与其他阶段的关系

```
EXECUTING → REVIEWING → COMPLETE
              ↓
         DEBUGGING (如果发现致命问题)
```

## Entry Criteria

进入 REVIEWING 阶段的条件：

1. **显式触发**：用户明确要求"审查"、"review"、"检查"、"审计"
2. **流程触发**：EXECUTING 阶段完成所有任务后自动进入
3. **决策点触发**：质量门禁失败后从 DECISION_POINT 进入

### 触发关键词

- `审查`、`review`、`检查`、`审计`
- `帮我review`、`代码审查`、`审查这段代码`
- `安全检查`、`性能检查`

## Exit Criteria

退出 REVIEWING 阶段的条件：

1. **所有 🔴 致命问题已修复或用户确认绕过**
2. **所有 🟡 严重问题已记录并有修复计划**
3. **审查报告已生成并展示给用户**
4. **用户确认或自动流转到 COMPLETE**

### 审查通过条件

```
ALL_PASSED = (
    fatal_issues == 0 OR user_acknowledged_fatal
) AND (
    serious_issues_recorded
) AND (
    report_generated
)
```

## Core Process

### Step 1: 准备审查环境

```bash
# 1. 确定审查范围
TARGET_FILES=$(确定要审查的文件列表)
SCOPE=$(用户指定范围 或 task_plan.md 中的实现任务)

# 2. 初始化审查报告
REVIEW_REPORT="review_report.md"

# 3. 遥测记录 - 审查开始
phase_enter "reviewing"

# 4. 派生子智能体进行专项审查
reviewer - 负责代码质量
security_expert - 负责安全审查
performance_expert - 负责性能审查
```

**遥测记录**:
```bash
phase_enter "reviewing"
decision_record "review_scope" "审查范围确定" "$TARGET_FILES" ""
```

### Step 2: 并行专项审查

并行启动三个子智能体进行审查：

```bash
# 并行执行三个专项审查
BEGIN parallel_review

# 2.1 代码质量审查 (reviewer)
reviewer:
  - 代码风格（格式、命名、注释）
  - 潜在bug（空指针、越界、竞态）
  - 测试覆盖（边界条件、异常路径）
  - 架构合理性（模块划分、依赖关系）

# 2.2 安全审查 (security_expert)
security_expert:
  - SQL注入、XSS、CSRF
  - 认证授权绕过
  - 敏感数据泄露
  - 加密和密钥管理

# 2.3 性能审查 (performance_expert)
performance_expert:
  - 时间复杂度（O(n²)、循环嵌套）
  - 内存泄漏和资源占用
  - 数据库查询效率
  - 缓存策略合理性

END parallel_review
```

### QA Delegation (Optional)

在并行审查完成后，尝试委托 gstack /qa 进行功能 QA 测试：

```bash
# 尝试委托 gstack QA 工作流
try:
    skill("gstack", "/qa", scope=TARGET_FILES)
except SkillNotFound:
    # Fallback - 继续使用内置 review (reviewer 子智能体)
    pass
```

**说明**：
- QA 测试是可选的，增强型功能测试
- 如果 gstack skill 不可用，继续使用内置 reviewer 子智能体
- QA 结果会并入审查报告

### E2E Visual Testing (Optional)

在代码审查完成后，可选的 E2E 视觉回归测试：

```bash
# 使用 Browser Daemon 进行视觉回归测试
try:
    skill("gstack", "/browser-e2e", context={
        "url": TARGET_URL,
        "baseline": BASELINE_SCREENSHOT,
        "threshold": 5  # 5% 差异阈值
    })
except SkillNotFound:
    # Fallback - 手动测试检查清单
    manual_e2e_checklist()
```

**Browser Daemon 能力** ({{include: ../_shared/browser-daemon.md}})：

| 操作 | 用途 |
|------|------|
| `/screenshot` | 截取页面或元素 |
| `/click` | 模拟用户点击 |
| `/fill` | 填表交互 |
| `/scroll` | 页面滚动 |
| `/a11y` | 获取 accessibility tree |

**E2E 测试场景**：
- 登录/注册流程
- 表单提交
- 页面导航
- 响应式布局验证

**错误处理**：
- 如果 Browser Daemon 不可用，使用手动测试检查清单
- 不阻断审查流程，仅作为增强能力

### Step 3: 汇总审查结果

```bash
# 汇总三个子智能体的审查结果
FATAL_COUNT=$(grep -c "🔴 致命" review_report.md)
SERIOUS_COUNT=$(grep -c "🟡 严重" review_report.md)
SUGGESTION_COUNT=$(grep -c "🟢 建议" review_report.md)

# 遥测记录 - 审查结果汇总
metric_record "issues_found" "fatal:$FATAL_COUNT, serious:$SERIOUS_COUNT, suggestion:$SUGGESTION_COUNT" "count" "reviewing"
```

### Step 4: 问题分级与输出

按照标准模板输出审查结论：

```markdown
## 审查结论

### 🔴 致命 (N)
1. [问题] - 位置: `file:line` - 影响: [一句话] - 修复: [简短建议]

### 🟡 严重 (N)
1. [问题] - 位置: `file:line` - 影响: [一句话] - 修复: [简短建议]

### 🟢 建议 (N)
1. [建议] - 位置: `file:line`
```

### Step 5: 决策点处理

如果存在 🔴 致命问题，触发决策点：

```markdown
## 决策卡片

┌─────────────────────────────────────┐
│ 🔴 审查失败 - 发现 N 个致命问题      │
│                                     │
│ [1] 自动修复所有致命问题            │
│ [2] 手动审查后再试                 │
│ [3] 忽略致命问题继续（需确认）      │
└─────────────────────────────────────┘
```

### Step 6: 规范检查

```bash
# 检查是否按照 task_plan.md 完成所有任务
for task in $(cat task_plan.md | grep -E "^- \[ \]"); do
  TASK_NAME=$(echo "$task" | sed 's/- \[ \] //')
  if ! grep -r "$TASK_NAME" src/; then
    echo "⚠️ 任务未完成: $TASK_NAME"
  fi
done
```

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 条件 |
|------|------|------|
| **DONE** | 审查通过，可以继续 | fatal=0, serious已记录 |
| **DONE_WITH_CONCERNS** | 有严重问题但已确认绕过 | fatal已修复但有残留风险 |
| **BLOCKED** | 审查失败，阻断继续 | fatal>0 且用户未确认 |
| **NEEDS_CONTEXT** | 需要更多信息 | 审查范围不明确 |

### 状态流转

```
REVIEWING
    ├── fatal == 0 → DONE → COMPLETE
    ├── fatal > 0 AND user_acknowledged → DONE_WITH_CONCERNS → COMPLETE
    ├── fatal > 0 AND user_rejected → BLOCKED → DEBUGGING/EXECUTING
    └── scope_unclear → NEEDS_CONTEXT → 询问用户
```

### 自我检验清单

在输出审查结论前，必须确认：

- [ ] 我是否因为用户是"上级"而降低了问题严重程度？
- [ ] 我是否因为代码"能跑"而忽略了设计问题？
- [ ] 我是否因为"时间紧"而跳过了安全检查？
- [ ] 我是否在描述中使用了"可能"、"或许"等模糊词？
- [ ] 我是否对每个问题都给出了具体位置和修复建议？

### 不留情面原则

> 审查时只说真话，不迎合谄媚

- 问题是问题，优点是优点，分开陈述
- 用户不爱听的话更要直说
- 温和的语气是专业，温和的内容是失职
- "这个设计有问题" > "可能可以改进"

## 发现去重规则

多个审查者可能发现相同或重叠的问题，使用以下规则进行去重：

### 去重合并规则

| 情况 | 处理方式 |
|------|---------|
| 同一位置同一问题 | 合并为一条发现，标注所有来源审查者 |
| 同一位置不同问题 | 保留为独立发现，标注"共置问题" |
| 同一问题不同位置 | 保留独立发现，标注跨位置关联 |
| 严重度冲突 | 采用更高级别的严重度 |
| 修复建议冲突 | 同时保留两条建议，标注各审查者来源 |

### 严重度校准标准

| 严重度 | 影响 | 可能性 | 示例 |
|--------|------|--------|------|
| **Critical** | 数据丢失、安全 breach、完全失败 | 确定或非常可能 | SQL注入、认证绕过、数据损坏 |
| **High** | 重大功能影响、降级 | 可能 | 内存泄漏、缺少验证、流程断裂 |
| **Medium** | 部分影响、存在 workaround | 罕见但可能 | N+1查询、缺少边缘情况、不清晰错误 |
| **Low** | 最小影响、 cosmetic | 不太可能 | 样式问题、轻微优化、命名 |

### 严重度校准规则

- 对外部用户可利用的安全漏洞：始终为 Critical 或 High
- 热路径性能问题：至少 Medium
- 关键路径缺少测试：至少 Medium
- 核心功能可访问性违规：至少 Medium
- 无功能影响的代码样式问题：Low

## 合并报告模板

多个审查者完成审查后，使用以下模板生成统一报告：

```markdown
## Code Review Report

**审查目标**: {files/PR/directory}
**审查者**: {dimension-1}, {dimension-2}, {dimension-3}
**日期**: {date}
**审查文件数**: {count}

### Critical Findings ({count})

#### [CR-001] {标题}

**位置**: `{file}:{line}`
**维度**: {Security/Performance/Architecture/Testing}
**严重度**: Critical

**Evidence**:
{发现描述，包含代码片段}

**Impact**:
{不修复可能发生的问题}

**Recommended Fix**:
{具体修复建议，包含代码示例}

### High Findings ({count})

...

### Medium Findings ({count})

...

### Low Findings ({count})

...

### Summary

| 维度 | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
| Security | 1 | 2 | 3 | 0 | 6 |
| Performance | 0 | 1 | 4 | 2 | 7 |
| Architecture | 0 | 0 | 2 | 3 | 5 |
| **Total** | **1** | **3** | **9** | **5** | **18** |

### Recommendation

{总体评估和优先行动项}
```

## 快速参考卡

```
REVIEWING 阶段命令：
─────────────────────
/reviewing           启动审查流程
/reviewing --scope   指定审查范围
/reviewing --report  生成审查报告

问题分级：
─────────────────────
🔴 致命 → 必须修复，禁止合并
🟡 严重 → 必须修复，可暂缓
🟢 建议 → 可选改进

审查维度：
─────────────────────
1. 代码质量（reviewer）
2. 安全检查（security_expert）
3. 性能审查（performance_expert）
```
