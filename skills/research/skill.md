---
name: research
version: 1.0.0
status: implemented
description: |
  研究调研阶段 - 搜索最佳实践和技术方案
  将研究结果存入 findings.md
tags: [phase, research]
requires:
  tools: [Bash, Read, Write, Grep, Glob, WebSearch, WebFetch]
---

# RESEARCH

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

RESEARCH 阶段是 agentic-workflow 的技术调研阶段，负责在实施前搜索最佳实践、技术方案和成熟参考。

### 核心职责

- 搜索网络最佳实践和技术方案
- 收集 GitHub 成熟项目和社区经验
- 将研究结果结构化存入 findings.md
- 为 THINKING 和 PLANNING 阶段提供输入

### 与其他阶段的关系

| 阶段 | 关系 |
|------|------|
| THINKING | RESEARCH 的搜索结果作为专家视角输入 |
| PLANNING | RESEARCH 的发现作为规划依据 |
| EXECUTING | 执行前必须完成 RESEARCH（复杂任务） |

## Entry Criteria

以下条件满足时进入 RESEARCH 阶段：

1. **显式触发** - 用户明确要求搜索/调研：
   - "帮我搜索..."
   - "调研一下..."
   - "查找最佳实践..."
   - "选型建议..."

2. **隐式触发** - 任务涉及：
   - 复杂任务（3+ 步骤）
   - 新技术领域
   - 需要外部参考的技术决策
   - 最佳实践、怎么做、如何实现

3. **路由关键词**：
   - 最佳实践、有什么、有哪些、选型
   - 怎么做、怎么实现、如何实现、参考、案例

## Exit Criteria

满足以下条件时退出 RESEARCH 阶段：

- [ ] 已使用 WebSearch/WebFetch 完成搜索（或确认工具不可用）
- [ ] 搜索结果已分析并提取关键要点
- [ ] findings.md 已创建并包含结构化研究结果
- [ ] 研究结果已准备好传递给 THINKING/PLANNING 阶段使用

## Auto-Verify

阶段转换前自动验证（任一失败则阻止转换）：

```bash
# findings 文件存在且内容充实 (>100字)
test -f findings*.md && test $(wc -c < findings*.md) -gt 100
```

## Core Process

### Step 1: 识别研究问题

明确需要研究的核心问题：

```
用户请求: [原始用户请求]
研究问题: [提取的核心研究问题]
搜索范围: [网络最佳实践 | GitHub项目 | 官方文档 | 社区讨论]
```

### Step 2: 执行搜索

**搜索工具优先级**（按可用性自动降级）：

1. **WebSearch**（Claude Code 原生，最优先）
   ```bash
   WebSearch(query="distributed transaction best practices", num_results=10)
   ```
2. **WebFetch**（当已知具体 URL 时）
   ```bash
   WebFetch(url="https://docs.example.com/architecture", query="caching strategies")
   ```
3. **Tavily**（如果 tavily skill 可用）
   ```bash
   # 检查 tavily 是否可用，如果不可用则跳过
   WebSearch(fallback to knowledge base)
   ```

**降级策略**：如果所有搜索工具都不可用，明确告知用户并建议手动搜索，不要静默用自身知识回答。

**不要使用**：
- 假设 tavily 始终可用
- 假设百度搜索 API key 始终配置（需要 `BAIDU_QIANFAN_API_KEY`）

### Step 3: 来源可靠性评估

**来源分级表**:

| 等级 | 来源类型 | 可靠性 | 使用建议 |
|------|----------|--------|----------|
| **A级** | 官方文档、官方博客、RFC、标准 | 最高 | 优先引用，作为权威依据 |
| **B级** | GitHub 官方repo、知名开源项目、权威技术书籍 | 高 | 可信，可作为实现参考 |
| **C级** | 知名技术博客（如 Medium 精选、InfoQ）、行业报告 | 中 | 需交叉验证，仅作参考 |
| **D级** | 论坛帖子（Stack Overflow等）、个人博客、知乎回答 | 低 | 需多源交叉验证，谨慎使用 |

**关键发现验证规则**:

```
FOR EACH 关键发现 IN 搜索结果:
    IF 来源等级 < C级 THEN
        标记为"待验证"
        尝试在其他来源中交叉验证
    ELSE IF 无法交叉验证 THEN
        在 findings.md 中标注"可靠性待确认"
    END
END
```

**分析搜索结果**:

1. **网络最佳实践**

分析搜索结果，提取关键信息：

1. **网络最佳实践**
   - 来源分类（官方文档、技术博客、社区讨论）
   - 关键要点提取
   - 适用场景标注

2. **GitHub 成熟项目**
   - 项目名称和特点
   - 适用场景
   - 技术栈参考

3. **社区经验总结**
   - 常见陷阱
   - 最佳实践要点
   - 经验教训

### Step 4: 生成 findings.md

将研究结果存入 findings.md：

```markdown
# 研究发现 - [研究主题]

## 研究问题
> [核心问题描述]

## 网络最佳实践

### 来源1
- 关键要点：
- 适用场景：
- 参考链接：

### 来源2
...

## GitHub 成熟项目

| 项目 | 特点 | 适用场景 |
|------|------|----------|
|      |      |          |

## 社区经验总结
- 经验1：
- 经验2：
- 经验3：

## 技术决策

| 决策 | 备选方案 | 选择理由 |
|------|----------|----------|
|      |          |          |

## 待验证假设
- 假设1：
- 假设2：
```

### Step 5: 调用 researcher 子智能体（可选）

对于大规模研究任务，可派生 researcher 子智能体并行搜索：

```
→ 派生 researcher 子智能体
→ 并行执行多个搜索任务
→ 汇总搜索结果
→ 写入 findings.md
```

## AskUserQuestion Format

{{include: ../_shared/ask-user-question.md}}

## Boil the Lake

{{include: ../_shared/boil-the-lake.md}}

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 退出条件 |
|------|------|----------|
| **DONE** | 阶段完成 | 研究结果已存入 findings.md，可进入下一阶段 |
| **DONE_WITH_CONCERNS** | 完成但有顾虑 | 研究结果可用，但存在未解决的疑问 |
| **BLOCKED** | 阶段阻塞 | 无法完成搜索（如网络问题），需要用户介入 |
| **NEEDS_CONTEXT** | 需要更多上下文 | 研究问题不清晰，需要用户提供更多信息 |

### 状态转换

```
ENTRY → [执行搜索] → [分析结果] → [写入 findings.md] → DONE
                                ↓
                          [遇到问题]
                                ↓
                    BLOCKED / NEEDS_CONTEXT
```

### 研究质量检查清单

- [ ] 搜索覆盖了主要信息源（官方文档、技术博客、GitHub）
- [ ] 关键要点已提取而非简单复制
- [ ] 包含适用场景和局限性说明
- [ ] 研究结果结构化且易于后续使用
- [ ] 无硬编码 secrets 或敏感信息
