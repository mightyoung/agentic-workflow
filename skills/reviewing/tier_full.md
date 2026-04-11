<!-- tier:65% -->

# REVIEWING - 完整方法论与验证

## 完整二阶段审查工作流

### Stage 0 完整清单

```bash
# 1. 查看实际代码变更（必须）
git diff HEAD~1

# 2. 运行自动质量门（必须）
python3 scripts/quality_gate.py --workdir .

# 3. 运行测试确认无回归（必须）
pytest -v

# 4. 查询历史问题（建议）
python3 scripts/memory_longterm.py \
  --op search-entity \
  --query "changed_file_name" \
  --limit 3 2>/dev/null || true
```

### Stage 1: Spec Compliance Review 详解

#### 对照表模板

| 检查点 | 是否满足 | 证据 | 备注 |
|--------|---------|------|------|
| T1: 创建 User 模型 | ✅ | src/models/user.py:1-50 | fields 正确 |
| T2: 实现 JWT 生成 | ✅ | src/auth/token.py:10-30 | 签名算法正确 |
| T3: /login endpoint | ❌ | 无 | **P0 未实现，致命** |
| T4: Token 刷新逻辑 | ✅ | src/auth/refresh.py | 过期检查正确 |

#### P0 Spec 未满足的处理

如果发现任何 P0 任务未完成或验收标准不符：

```markdown
## 致命阻断问题

### 🔴 P0 任务未完成
- **任务**: [T3] 实现 /login endpoint
- **证据**: git diff 中无相关代码
- **影响**: 无法进行认证，整个系统无法使用
- **建议**: 进入 DEBUGGING，补充实现
```

此时**立即停止 Stage 2**，不必继续代码质量审查。

### Stage 2: Code Quality Review 详解

#### 逐文件分析清单

对 git diff 中的每个变更文件，按以下维度审查：

1. **功能正确性**
   - 代码是否实现了 diff 声称的功能？
   - 是否遗漏了特殊情况？

2. **边界条件**
   - null/empty 输入？
   - 数值溢出？
   - 并发竞态条件？

3. **错误处理**
   - 所有可能的错误都被处理了吗？
   - 错误消息是否有帮助？

4. **测试覆盖**
   - happy path 有测试吗？
   - error path 有测试吗？
   - 覆盖率 ≥80%？

5. **安全隐患**
   - SQL 注入？
   - XSS？
   - CSRF 保护？
   - 敏感数据泄露？

#### 审查意见示例

```markdown
## 审查结论

### 🔴 致命问题

#### `src/user.py:42` - NPE 漏洞
```python
def update_email(user, new_email):
    if user.email == new_email:  # ← user 可能为 None，会抛 AttributeError
        return
```
**修复**: 添加 null check
```python
if user is None or user.email == new_email:
    return
```

### 🟡 严重问题

#### `src/auth.py:78` - SQL 注入风险
```python
query = f"SELECT * FROM users WHERE email = '{email}'"  # ← 参数未转义
```
**修复**: 使用参数化查询
```python
query = "SELECT * FROM users WHERE email = ?"
cursor.execute(query, (email,))
```

### 🟢 建议

#### `tests/test_auth.py:15` - 缺少过期 token 测试
当前仅测试了有效 token，建议补充：
```python
def test_expired_token():
    token = create_token(expires_in=0)
    assert validate_token(token) is False
```
```

## 验证清单（审查完整性）

退出 REVIEWING 前，确保以下全部完成：

```bash
# ✓ Stage 0: 证据收集
git diff HEAD~1              # 已阅读实际变更
python3 scripts/quality_gate.py --workdir .  # 自动检查已运行
pytest -v                    # 测试已通过

# ✓ Stage 1: Spec 合规
# → 已对照 tasks.md / contract.json 逐项核对
# → 所有 P0 任务已实现，接口契约一致
# → 如有 P0 未满足，已标记为致命并停止 Stage 2

# ✓ Stage 2: 代码质量
# → 已逐文件分析
# → 已输出含 file:line 定位的审查意见
# → 已归类为 🔴 致命 / 🟡 严重 / 🟢 建议
```

## 关键原则

1. **顺序铁律**: Spec Compliance 必在 Code Quality 之前，不可颠倒
2. **证据优先**: 无 file:line = 未审查，无法接受
3. **不重复验证**: 如果 Stage 1 已发现致命问题，不必继续 Stage 2

## 特殊场景

### 场景：无 spec-kit 的实现（legacy 模式）

如果项目使用 legacy task_plan.md 而非完整 spec-kit：

- Stage 1 改为对照 task_plan.md 的任务清单
- 验收标准可能不如 spec.md 明确，需用代码推断意图
- 仍必须基于真实代码变更写意见

### 场景：纯代码 refactor，无新功能

- 跳过 Stage 1 Spec Compliance（因为没有新 spec）
- 重点关注 Stage 2 代码质量
- 确保无功能回归（pytest 必须通过）
