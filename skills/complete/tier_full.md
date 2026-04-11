<!-- tier:70% -->

# COMPLETE - 完整方法论与验证

## 完整验证工作流

### Final Verification Checklist (完整版)

```bash
# 1. 运行测试
pytest -v
# 期望: ✅ all tests passed

# 2. 运行质量门禁
python3 scripts/quality_gate.py --workdir .
# 期望: ✅ no fatal issues

# 3. 检查 secrets
git diff HEAD~1 | grep -E "(password|token|secret|api_key)" || echo "✓ No secrets found"

# 4. 检查 .workflow_state.json
python3 -c "import json; s=json.load(open('.workflow_state.json')); print(f'Current phase: {s.get(\"phase\")}')"
# 期望: Current phase: EXECUTING

# 5. 更新状态文件
python3 scripts/workflow_engine.py --op advance --phase COMPLETE --workdir .

# 6. 验证更新
python3 -c "import json; s=json.load(open('.workflow_state.json')); print(f'Updated phase: {s.get(\"phase\")}')"
# 期望: Updated phase: COMPLETE
```

## 完成状态应用规则

### 状态矩阵

| 情况 | 目标达成 | 验证通过 | 有阻断 | 选择状态 | 理由 |
|------|---------|---------|--------|---------|------|
| 完美 | ✅ | ✅ | ❌ | **DONE** | 无保留 |
| 有遗留 | ✅ | ✅ | ❌ | **DONE_WITH_CONCERNS** | 主目标达成，但有风险或不足 |
| 被卡 | ❌ | ❌ | ✅ | **BLOCKED** | 缺外部条件 |
| 不确定 | ? | ? | ? | **NEEDS_CONTEXT** | 无法判断 |

### DONE 的充要条件

```
DONE 当且仅当:
- ✅ 所有 P0 任务完成
- ✅ 验收标准全部通过
- ✅ 没有已知的致命风险
- ✅ 代码质量达标（无 🔴 问题）
- ✅ 测试通过，无回归
```

### DONE_WITH_CONCERNS 的使用

```
DONE_WITH_CONCERNS 当:
- ✅ 所有 P0 任务完成
- ✅ 验收标准全部通过
- ⚠️ 但存在以下至少一项:
  - P1/P2 任务未完成（且不阻塞主路径）
  - 存在已知的次要风险（已记录）
  - 性能优化空间（但当前可用）
  - 技术债（已记录，计划后续处理）
```

**例子**: 认证系统完成了，但密钥轮换还未实现（P1）→ DONE_WITH_CONCERNS

### BLOCKED 的使用

```
BLOCKED 当:
- ❌ 无法继续，因为:
  - 缺少外部 API 密钥或权限
  - 依赖的上游模块未完成
  - 用户未提供必要信息
  - 环境问题（数据库不可用等）
```

## Outcome Summary 模板

```markdown
## 阶段完成状态

**Status**: DONE_WITH_CONCERNS

### 本轮交付物

**实现的功能**:
- JWT token 生成和验证逻辑
- /login endpoint 实现
- token 刷新机制
- 单元测试（覆盖率 87%）

**实现的 P0 任务**: 4/4 ✅
- [✅] 创建 User 模型
- [✅] JWT 生成和验证
- [✅] /login endpoint
- [✅] Token 刷新逻辑

### 未完成项

**P1 任务** (计划下阶段):
- [ ] 速率限制（5 次/分钟）
- [ ] Token 撤销（logout 功能）

**已知的限制/风险**:
1. **SECRET_KEY 硬编码** (严重)
   - 当前: `SECRET_KEY = 'dev-key-123'`
   - 风险: 生产环境泄露密钥
   - 修复: 改为 `os.environ.get('JWT_SECRET_KEY')`
   - 优先级: 高，进入 DEBUG 前必须修复

2. **Token 过期时间固定** (中等)
   - 当前: expires_in=3600 (1 小时)
   - 问题: 可能过短，用户需要频繁刷新
   - 计划: 下阶段改为可配置

3. **缺少审计日志** (低)
   - 当前: 无登录事件记录
   - 计划: 下阶段补充
   - 不阻塞当前交付

### 验证状态

```
✅ pytest -v
  test_create_token PASSED
  test_validate_token PASSED
  test_invalid_token PASSED
  ======================== 3 passed in 0.12s ================

✅ python3 scripts/quality_gate.py --workdir .
  No hardcoded secrets
  No SQL injection patterns
  ✓ All checks passed

✅ .workflow_state.json updated
  "phase": "COMPLETE"
```

### 技术债记录

| 项目 | 优先级 | 预计工作量 | 分配 |
|------|--------|-----------|------|
| SECRET_KEY 环境变量化 | 高 | 30 分钟 | 必须 |
| Token 过期可配置 | 中 | 1 小时 | P1 |
| 审计日志 | 低 | 2 小时 | P2 |

### 建议的后续行动

1. **立即** (当前 session)
   - [ ] 修改 src/auth.py:3，SECRET_KEY 改为环境变量
   - [ ] 重新运行 pytest 验证修复
   - [ ] 更新 COMPLETE 状态为 DONE

2. **下阶段** (新 task)
   - [ ] 实现 P1 任务（速率限制、token 撤销）
   - [ ] 性能监控（token 验证耗时 > 10ms 告警）
   - [ ] 集成测试（与业务逻辑的完整流程）

3. **长期** (roadmap)
   - [ ] 密钥轮换机制
   - [ ] OAuth2 集成
   - [ ] MFA 支持
```

## 经验提炼 (对 M+ 复杂度)

### 提炼指令

```bash
# 方法 1: 使用 memory_longterm 提炼
python3 scripts/memory_longterm.py --op=refine --days=7

# 方法 2: 使用 learn 技能（如果可用）
/learn --context="JWT 认证实现" --duration=7d
```

### 可提炼的经验类型

| 经验类型 | 示例 | 复用价值 |
|---------|------|--------|
| **失败模式** | "JWT token 过期检查容易漏掉，导致永不过期的 token" | 高 |
| **解决方案** | "用 jwt.decode(..., options={'verify_exp': True}) 确保过期检查" | 高 |
| **设计决策** | "选择 RS256 而非 HS256 用于 token 签名（非对称密钥更安全）" | 中 |
| **工具/库** | "使用 PyJWT 库需要注意的版本差异" | 中 |
| **性能陷阱** | "token 验证不应放在 CRITICAL PATH 中，可用缓存优化" | 中 |

### 记录格式

```markdown
## 经验: JWT 认证实现中的常见陷阱

**失败模式**: token 过期检查容易被漏掉，导致永不过期的 token

**根本原因**: 
- jwt.decode 默认不验证 'exp' 字段
- 新手容易忽略，以为自动校验

**解决方案**:
```python
# ❌ 错误做法
payload = jwt.decode(token, SECRET_KEY)

# ✅ 正确做法
payload = jwt.decode(token, SECRET_KEY, options={"verify_exp": True})
```

**何时会踩坑**: 实现认证系统时，token 需要过期时间但未配置

**预防措施**:
- 在规划阶段明确 token 生命周期（访问令牌、刷新令牌分开）
- 在审查 stage 1 (Spec Compliance) 中检查过期时间配置
- 添加单元测试验证过期 token 被拒绝

**关联文件**: .specs/auth/plan.md (第 X 行), src/auth.py:8-15
```

## Implemented Vs Planned

当前**未实现**，但在 COMPLETE 文档中提到的能力：

- `phase_enter(...)` API
- `metric_record(...)` API
- `decision_record(...)` API
- `error_record(...)` API
- 自动文档预览 runtime
- 自动发布 gate runtime
- WAL 晋升自动固化规则

如果需要这些能力，应先在脚本层实现，再更新文档。

## 验证清单 (出口前检查)

```bash
# ✅ 证据收集
pytest -v                      # 测试通过
python3 scripts/quality_gate.py # 质量检查通过
git diff HEAD~1 | grep secret   # 无 secrets

# ✅ 状态更新
python3 scripts/workflow_engine.py --op advance --phase COMPLETE
python3 -c "import json; print(json.load(open('.workflow_state.json')).get('phase'))"
# 期望输出: COMPLETE

# ✅ 完成状态已声明
# (已输出 DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT 之一，带理由)

# ✅ 可复用经验已记录（可选但推荐）
# (对 M+ 任务执行过 /learn 或 memory_longterm)
```
