<!-- tier:reference -->

# REVIEWING - 参考、示例与反模式

## 完整审查示例

### 场景
已完成 EXECUTING，现在进行 REVIEWING

### Stage 0: Collect Evidence

```bash
$ git diff HEAD~1
diff --git a/src/auth.py b/src/auth.py
index abc123..def456 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,5 +1,25 @@
 import jwt
+import secrets
 
+def create_token(user_id, expires_in=3600):
+    payload = {
+        'user_id': user_id,
+        'iat': datetime.now(),
+    }
+    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
+
+def validate_token(token):
+    try:
+        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
+        return payload
+    except:
+        return None

$ python3 scripts/quality_gate.py --workdir .
✓ No hardcoded secrets
✓ No SQL injection patterns
✓ No obvious XSS patterns
Warnings: 2
  - src/auth.py:12 - broad exception catch

$ pytest -v
test_auth.py::test_create_token PASSED
test_auth.py::test_validate_token PASSED
test_auth.py::test_invalid_token PASSED
======================== 3 passed in 0.12s ===================

$ python3 scripts/memory_longterm.py --op search-entity --query "auth.py" --limit 3
Found 1 match:
  - 2026-03-01: JWT timing bug in token validation - fixed by adding datetime conversion
```

### Stage 1: Spec Compliance

对照 `.specs/auth/tasks.md`：

| 任务 | P级 | 状态 | 证据 |
|------|-----|------|------|
| T1: 创建 User 模型 | P0 | ✅ | (已在前面审查) |
| T2: JWT 生成和验证 | P0 | ✅ | src/auth.py:3-16 |
| T3: /login endpoint | P0 | ❓ | 本次 diff 不包含 |
| T4: Token 刷新 | P0 | ❓ | 本次 diff 不包含 |

**发现**: T2 已实现，但 T3/T4 不在本次 diff。

**检查上下文**: 这是 JWT token 功能的第一个 PR，T3/T4 在后续 PR 中。规划时应该明确。

### Stage 2: Code Quality

#### 文件 1: src/auth.py

**问题 1**: 广泛的异常捕获

```python
except:  # ← 捕获所有异常，包括 KeyboardInterrupt、SystemExit
    return None
```

**建议**: 捕获特定异常
```python
except (jwt.InvalidSignatureError, jwt.ExpiredSignatureError, KeyError):
    return None
```

**问题 2**: 缺少 token 过期检查

当前 decode 不验证 'exp' 字段，token 理论上永不过期。

**建议**: 添加过期检查
```python
jwt.decode(token, SECRET_KEY, algorithms=['HS256'], options={"verify_exp": True})
```

**问题 3**: SECRET_KEY 未定义

```python
return jwt.encode(payload, SECRET_KEY, algorithm='HS256')
```

SECRET_KEY 全局引用但未在文件中定义，应该从 env 或 config 读取。

#### 文件 2: tests/test_auth.py

**问题 4**: 缺少异常路径测试

当前有 3 个测试，全部是 happy path。缺少：
- 无效签名
- 过期 token
- 缺少必要字段

### 最终审查结论

```markdown
## 审查结论

**阶段**: Stage 2 Code Quality (Stage 1 Spec Compliance 已跳过，因为不涉及 P0 spec)

### 🟡 严重问题

#### `src/auth.py:12` - 异常捕获过于宽泛
```python
except:
    return None
```
**问题**: 捕获 KeyboardInterrupt 等系统异常，可能掩盖重大错误
**修复**: 改为捕获特定异常
```python
except (jwt.InvalidSignatureError, jwt.ExpiredSignatureError):
    return None
```

#### `src/auth.py:8` - 缺少 token 过期时间
当前 payload 无 'exp' 字段，token 永不过期
**修复**: 添加
```python
'exp': datetime.utcnow() + timedelta(seconds=expires_in)
```

#### `src/auth.py:3` - SECRET_KEY 未定义
**修复**: 从环境变量读取
```python
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
```

### 🟢 建议

#### `tests/test_auth.py` - 缺少错误路径测试
建议补充：
- test_invalid_signature
- test_expired_token
- test_missing_fields

## 验证状态

✅ git diff 已读取
✅ 自动检查已运行（2 warnings）
✅ 测试已通过（3/3）
✅ 意见已定位（file:line）

## 后续行动

🔄 进入 DEBUGGING → 修复 3 个严重问题 → 补充测试 → 重新审查
```

## 反模式与陷阱

### 反模式 1: "代码看起来不错"

```markdown
❌ 不可接受的审查
今天的代码质量很好。没有发现任何问题。
```

**问题**: 无 file:line，无具体意见，无法验证是否真的审查过

**正确做法**:
```markdown
✅ 可接受的审查
审查了 src/auth.py，发现以下问题：
- src/auth.py:12 - 异常捕获过于宽泛，应改为捕获 jwt.InvalidSignatureError
- src/auth.py:8 - 缺少 token 过期时间，建议添加 'exp' 字段
```

### 反模式 2: 跳过 Stage 0

```bash
❌ 审查而不查看 diff
(直接输出意见，未运行 git diff / pytest)
```

**问题**: 可能审查错误的代码，或遗漏测试失败

**正确做法**: 先运行命令，后输出意见

### 反模式 3: Stage 顺序颠倒

```markdown
❌ 先审代码质量，再检查 spec
（阶段顺序错误）
```

**问题**: 发现代码质量问题后，才发现 P0 spec 未完成 → 白费时间

**正确做法**: Stage 1 Spec Compliance 必在 Stage 2 前，如发现 P0 未满足立即停止

### 反模式 4: 不复用历史经验

```bash
❌ 忽视 memory_longterm
（审查时未查询历史问题，导致复发同样的 bug）
```

**正确做法**: Stage 0.5 必须查询历史，如有命中应在 Stage 2 中特别关注

## 审查与 Spec 的融合

### 当存在完整 spec-kit 时

```
REVIEWING.Stage 1
├─ 对照 .specs/<feature>/tasks.md
├─ 逐项检查 P0 任务是否实现
├─ 对照 .contract.json 验证接口契约
└─ 如有 P0 未满足 → HARD-GATE BLOCK
```

### 当仅有 legacy task_plan.md 时

```
REVIEWING.Stage 1 (Lightweight)
├─ 对照 task_plan.md 的任务清单
├─ 代码推断验收标准（可能不清晰）
└─ 仍然要求 file:line 定位
```

## 与长期记忆的融合

### 查询历史问题

```bash
python3 scripts/memory_longterm.py \
  --op search-entity \
  --query "auth.py" \
  --limit 3
```

如果返回历史问题（如 "JWT timing bug")：

- 在 Stage 2 中重点检查时间相关逻辑
- 可能需要额外的单元测试
- 考虑在本次审查中补充防护措施

### 记录新发现的问题

如果本次审查发现新的系统性问题（如认证中 token 过期检查的设计），可选择记入长期记忆，避免下次重复。
