---
name: reviewing
version: 1.2.0
status: implemented
description: |
  审查阶段 - 代码质量、安全和性能审查
  当前版本对齐 .specs/<feature>/tasks.md、.contract.json 与真实审查输出
  v1.2: 强化 two-stage review、memory_hints 复用与 Files Reviewed 完成门
tags: [phase, reviewing]
requires:
  tools: [Bash, Read, Write, Grep, Glob]
---

# REVIEWING

## Preamble

{{include: ../_shared/preamble.md}}

## Overview

REVIEWING 阶段负责对实现结果做质量审查，并输出可执行的问题清单。

默认策略: `conditional_enable`。只有在真实 diff、需要门禁审查或高风险变更时，才默认启用完整 skill；`use_skill`
是运行时执行结果，`skill_policy` 是上游 canonical 决策。

当前真实口径：

- 以项目文件和实际变更为审查对象
- 以 `.reviews/review/review_{session}.md` 或 `.reviews/review/review_latest.md` / 直接问题列表为主要输出
- 必要时参考 `.specs/<feature>/tasks.md` 与 `.contract.json` 确认范围
- 先检查当前 phase 上下文里的 `memory_hints`、`memory_query` 和 `memory_intent`，优先复用历史失败模式和既有审查结论
- 不假定存在 `phase_enter(...)`、`decision_record(...)`、`metric_record(...)` 之类 API
- 代码任务审查会按两阶段执行：先 `Spec Compliance`，再 `Code Quality`
- 真实完成门要求 `Files Reviewed` 非空，模板 review 不再能冒充有效审查

## Entry Criteria

进入 REVIEWING 的常见条件：

- 用户明确要求审查、review、检查、审计
- EXECUTING 已完成一轮实现
- 需要在 COMPLETE 前做质量门禁

## Exit Criteria

<HARD-GATE name="reviewing-exit-gate">
以下三项必须全部完成，审查才算有效：
1. 已运行 `git diff HEAD~1` 并基于真实代码变更写出意见（不是泛泛而谈）
2. 审查意见必须包含至少一条 `file:line` 格式的具体定位
3. 已运行 `pytest -v` 或等效测试命令，确认无回归

仅输出"代码看起来不错"不是有效审查。无 file:line = 未审查。
</HARD-GATE>

**Iron Law**: `NO REVIEWING WITHOUT READING THE ACTUAL DIFF FIRST`

退出条件（全部满足）：

- 致命问题已修复或明确记录
- 严重问题已记录并给出建议（含 file:line）
- 用户已看到审查结论
- 后续流转到 DEBUGGING 或 COMPLETE

## Core Process

### Stage 0: Collect Evidence (Required First)

**禁止在执行以下命令之前写任何审查意见。**

```bash
# 1. 查看实际代码变更
git diff HEAD~1

# 2. 运行自动质量门
python3 scripts/quality_gate.py --workdir .

# 3. 运行测试确认无回归
pytest -v
```

### Stage 0.5: Entity History Search (MAGMA Entity Graph)

> 审查变更文件前，先查询该文件的**历史问题记录**。
> 复发的 bug 最容易被漏掉——这一步保证不重蹈覆辙。

```bash
# 对 git diff 中每个主要变更文件，查询实体图历史
# 示例: 审查 src/auth.py 时
python3 scripts/memory_longterm.py \
  --op search-entity \
  --query "${变更文件名，如: auth.py / memory_longterm.py}" \
  --limit 3 2>/dev/null || true
```

**处理规则**：
- 有命中 → 在 Stage 2 Code Quality 审查中额外关注历史问题点
- 无命中 → 正常审查，审查完成后考虑是否写入新的 entity-related experience

### Stage 1: Spec Compliance Review (First)

> **顺序铁律**: Spec Compliance 必须在 Code Quality 之前。
> 合规性问题可能导致整个实现方向错误，发现越早成本越低。

对照 `.specs/<feature>/tasks.md` 或 `.contract.json` 逐项核对：

| 检查点 | 是否满足 | 证据 |
|--------|---------|------|
| 所有 P0 任务已实现 | ✅/❌ | file:line |
| 验收标准全部通过 | ✅/❌ | test output |
| owned_files 列表完整 | ✅/❌ | git diff |
| 接口契约一致（API 签名、返回值）| ✅/❌ | file:line |

如果 **有任何 P0 Spec 未满足**：
- 立即标记为 🔴 致命，进入 DEBUGGING
- 不必继续 Stage 2（代码质量问题在合规性问题修复后才有意义）

### Stage 2: Code Quality Review (Second)

仅在 Stage 1 无致命合规问题时执行。

For each file in the git diff, read the actual file content and analyze:
- Does the code do what the diff claims?
- Are there edge cases not handled?
- Are tests adequate?
- 审查摘要会回流到 `review_summary`，供 COMPLETE / RESUME / checkpoint 复用

输出格式必须包含具体文件:行号：

```markdown
## 审查结论

### 🔴 致命
- `src/user.py:42` - NPE when user.email is None: add null check

### 🟡 严重
- `src/auth.py:78` - SQL injection risk: use parameterized query

### 🟢 建议
- `tests/test_auth.py:15` - missing test for expired token
```

### Stage 3: Route After Review

- 有阻断问题（🔴）：进入 DEBUGGING
- 无阻断问题：进入 COMPLETE

## Validation

二阶段审查完整性检查（退出前必须全部满足）：

```bash
# Stage 0: 证据收集
git diff HEAD~1              # 已阅读实际变更 ✓
python3 scripts/quality_gate.py --workdir .  # 自动检查已运行 ✓
pytest -v                    # 测试已通过 ✓

# Stage 1: Spec 合规
# → 已对照 tasks.md / contract.json 逐项核对
# → 所有 P0 任务已实现，接口契约一致

# Stage 2: 代码质量
# → 已输出含 file:line 定位的审查意见
```

**两个阶段的顺序不可颠倒**。无 file:line = 未审查。
