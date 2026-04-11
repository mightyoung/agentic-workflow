<!-- tier:45% -->

# REVIEWING - 过程与两阶段

## 进入条件

- 用户明确要求审查、review、检查、审计
- EXECUTING 已完成一轮实现
- 需要在 COMPLETE 前做质量门禁

## Stage 0: Collect Evidence (必先)

**禁止在执行以下命令之前写任何审查意见。**

```bash
# 1. 查看实际代码变更
git diff HEAD~1

# 2. 运行自动质量门
python3 scripts/quality_gate.py --workdir .

# 3. 运行测试确认无回归
pytest -v
```

### Stage 0.5: 查询历史问题记录

对 git diff 中每个主要变更文件，查询实体图历史：

```bash
python3 scripts/memory_longterm.py \
  --op search-entity \
  --query "${变更文件名}" \
  --limit 3 2>/dev/null || true
```

**处理规则**:
- 有命中 → 在 Stage 2 中额外关注历史问题点
- 无命中 → 正常审查，完成后考虑记录新的经验

## Stage 1: Spec Compliance Review (First)

> 顺序铁律: Spec Compliance 必须在 Code Quality 之前

对照 `.specs/<feature>/tasks.md` 或 `.contract.json` 逐项核对：

| 检查点 | 是否满足 | 证据 |
|--------|---------|------|
| 所有 P0 任务已实现 | ✅/❌ | file:line |
| 验收标准全部通过 | ✅/❌ | test output |
| owned_files 列表完整 | ✅/❌ | git diff |
| 接口契约一致（API 签名、返回值）| ✅/❌ | file:line |

**如果有任何 P0 Spec 未满足**:
- 立即标记为 🔴 致命，进入 DEBUGGING
- 不必继续 Stage 2（合规性问题修复后才有意义）

## Stage 2: Code Quality Review (Second)

仅在 Stage 1 无致命合规问题时执行。

对 git diff 中的每个文件，分析：
- 代码是否做到了 diff 声称的功能？
- 是否遗漏边界条件处理？
- 测试是否充分？
- 是否存在安全隐患？

## 审查输出格式

必须包含具体 file:line：

```markdown
## 审查结论

### 🔴 致命
- `src/user.py:42` - NPE when user.email is None: add null check

### 🟡 严重
- `src/auth.py:78` - SQL injection risk: use parameterized query

### 🟢 建议
- `tests/test_auth.py:15` - missing test for expired token
```

## Stage 3: Route After Review

- 有阻断问题（🔴）→ 进入 DEBUGGING
- 无阻断问题 → 进入 COMPLETE

## 出口条件

以下三项必须全部完成，审查才算有效：

1. 已运行 `git diff HEAD~1` 并基于真实代码变更写出意见（不是泛泛而谈）
2. 审查意见必须包含至少一条 `file:line` 格式的具体定位
3. 已运行 `pytest -v` 或等效测试命令，确认无回归

**退出条件**（全部满足）:
- 致命问题已修复或明确记录
- 严重问题已记录并给出建议（含 file:line）
- 用户已看到审查结论
- 后续流转到 DEBUGGING 或 COMPLETE
