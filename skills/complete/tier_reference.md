<!-- tier:reference -->

# COMPLETE - 参考、示例与特殊场景

## 完整审查示例

### 场景：认证系统实现完成，进入 COMPLETE

#### Step 1: Run Final Verification

```bash
$ pytest -v
test_auth.py::test_create_token PASSED                       [33%]
test_auth.py::test_validate_token PASSED                     [66%]
test_auth.py::test_invalid_token PASSED                      [100%]
======================== 3 passed in 0.12s ===================

$ python3 scripts/quality_gate.py --workdir .
✓ No hardcoded secrets detected
✓ No SQL injection patterns found
✓ No obvious XSS patterns
Warnings: 2
  - src/auth.py:3 - SECRET_KEY hardcoded (not in .gitignore)
  - tests/test_auth.py:5 - Missing test for expired token

$ git diff HEAD~1 | grep -E "(password|secret|key)" || echo "✓ No obvious secrets in diff"
✓ No obvious secrets in diff
```

**问题**: quality_gate 报告了 2 个 warnings（SECRET_KEY 硬编码）

**决策**: DONE_WITH_CONCERNS，因为存在已知风险（SECRET_KEY 硬编码）

#### Step 2: Update State

```bash
$ python3 scripts/workflow_engine.py --op advance --phase COMPLETE --workdir .
✓ Phase updated: EXECUTING → COMPLETE

$ python3 -c "import json; s=json.load(open('.workflow_state.json')); print(f'Phase: {s[\"phase\"]}')"
Phase: COMPLETE
```

#### Step 3: Summarize Outcome

```markdown
## 完成状态

**Status**: DONE_WITH_CONCERNS

### 本轮交付物

**实现的功能**:
- JWT token 生成和验证
- /login endpoint
- token 刷新机制
- 单元测试（3/3 通过，覆盖率 87%）

**P0 任务完成**: 4/4 ✅

### 已知风险 (未阻塞，已记录)

1. **SECRET_KEY 硬编码** ⚠️ 高优先级
   - 文件: src/auth.py:3
   - 问题: 生产环境会泄露密钥
   - 修复: 改为 `os.environ.get('JWT_SECRET_KEY')`
   - 建议: 进入 DEBUG 立即修复

2. **缺少过期 token 测试** ⚠️ 中优先级
   - 当前: test_invalid_token 测试无效签名，但未测试过期
   - 建议: 补充 test_expired_token

### 验证证据

```
✅ pytest: 3/3 通过
✅ quality_gate: 2 warnings（非致命），无 error
✅ secrets check: 无新增 secrets（硬编码 SECRET_KEY 是历史遗留）
✅ .workflow_state.json: phase 已更新为 COMPLETE
```

### 后续建议

1. **立即** (critical)
   - [ ] 改 SECRET_KEY 为环境变量 (30 分钟)
   - [ ] 补充 test_expired_token (15 分钟)
   - [ ] 重新运行 pytest 验证
   - [ ] 更新本状态为 DONE

2. **下阶段** (P1)
   - [ ] 实现速率限制 (1 小时)
   - [ ] 实现 token 撤销/logout (1 小时)
   - [ ] 集成测试 (2 小时)

3. **长期** (P2)
   - [ ] 审计日志 (2 小时)
   - [ ] 密钥轮换 (未评估)
```

#### Step 4: Optional - Capture Learnings

```bash
$ python3 scripts/memory_longterm.py --op=refine --days=7
✓ Refining experiences from last 7 days...

Found patterns:
1. JWT token 过期检查易漏
   - Files affected: src/auth.py
   - Pattern: validate_token 未验证 'exp' 字段

2. SECRET_KEY 硬编码模式
   - Root cause: 开发时的便利做法，生产前未改
   - Prevention: 添加 pre-commit hook 检查硬编码密钥

3. Test coverage for error paths
   - Gap: happy path 有测，error path 测试不足
   - Recommendation: 添加 test_expired_token 类的测试
```

## 特殊场景

### 场景 1: BLOCKED 状态

当无法继续时使用：

```markdown
## 完成状态

**Status**: BLOCKED

**阻挡原因**:
- 需要 AWS_ACCESS_KEY 和 AWS_SECRET_KEY 环境变量
- 当前环境未设置，导致 S3 集成测试无法运行

**证据**:
```
$ pytest -v
FAILED test_integration.py::test_s3_upload - NoCredentialsError: Unable to locate credentials
```

**需要的行动**:
1. 获取 AWS 凭证
2. 设置环境变量: `export AWS_ACCESS_KEY=xxx AWS_SECRET_KEY=yyy`
3. 重新运行测试

**预计解决时间**: 24 小时（等待 AWS 凭证）
```

### 场景 2: NEEDS_CONTEXT

当无法判断完成状态时：

```markdown
## 完成状态

**Status**: NEEDS_CONTEXT

**困惑点**:
- 验收标准要求 "性能 > 1000 req/sec"
- 当前环境是本地开发机，无法代表真实性能
- 需要在生产环境或负载测试环境验证

**需要的上下文**:
1. 性能测试环境的访问权限
2. 真实流量模式的模拟数据
3. 性能基线（之前的版本是多少 req/sec）

**建议的后续行动**:
1. 在性能测试环境运行压力测试
2. 如果未达标，进入 DEBUGGING
3. 如果达标，更新为 DONE
```

### 场景 3: 无状态文件 (.workflow_state.json 不存在)

```bash
# 如果项目本身不使用 .workflow_state.json
# 可以跳过该步骤，直接输出完成状态：

## 完成状态

**Status**: DONE

（这个项目不使用 .workflow_state.json，仅输出最终状态）
```

## 完成状态转移规则

```
状态转移图:

EXECUTING
    ↓
COMPLETE
    ├─→ DONE (问题已修复，无风险)
    ├─→ DONE_WITH_CONCERNS (主目标达成，但有遗留)
    ├─→ BLOCKED (外部阻塞)
    └─→ NEEDS_CONTEXT (无法判断)
```

## 与长期记忆的融合

### 自动经验提炼

对于 M+ 复杂度的任务，COMPLETE 末尾建议记录：

```bash
# 提炼本次会话中学到的东西
python3 scripts/memory_longterm.py --op=refine --days=1
```

可提炼的经验：
- **失败模式** - 这次做错了什么，下次怎么避免
- **解决方案** - 有效的解决方法，下次直接用
- **设计决策** - 为什么选择 A 而不是 B，供后续参考
- **工具技巧** - 有用的命令、库、最佳实践

### 经验复用

如果下次遇到类似任务，可以：

```bash
# 搜索相关经验
python3 scripts/memory_longterm.py --op search-entity --query "JWT" --limit 5
```

快速找到之前遇到的陷阱和解决方案。

## 反模式与陷阱

### 反模式 1: "凭感觉"宣布完成

```markdown
❌ 不可接受
所有代码都写好了，应该没问题。
```

**问题**: 无验证证据，可能有隐藏的 bug

**正确做法**: 总是运行 pytest -v，给出输出为证

### 反模式 2: 忽视已知风险

```markdown
❌ 不可接受的 DONE
Status: DONE
(但实际有多个 quality_gate warnings 未处理)
```

**问题**: 已知风险应该用 DONE_WITH_CONCERNS 标记

**正确做法**: 
```markdown
✅ 正确的 DONE_WITH_CONCERNS
Status: DONE_WITH_CONCERNS

**已知风险**:
- SECRET_KEY 硬编码 (HIGH)
- 缺少过期 token 测试 (MEDIUM)

**建议**: 下个 session 立即修复
```

### 反模式 3: 夸大完成程度

```markdown
❌ 不正确
Status: DONE
本阶段实现了完整的认证系统，包括 OAuth2、MFA 等
(但实际只做了 JWT 基础)
```

**问题**: 夸大会导致后续期望管理混乱

**正确做法**: 诚实列出做了什么、没做什么

### 反模式 4: 不记录经验

当完成 M+ 任务时，仅输出总结但不提炼经验 → 知识丢失

**正确做法**: 用 /learn 或 memory_longterm 记录本次的决策、陷阱、解决方案

## 与其他阶段的关系

```
PLANNING
    ↓
EXECUTING (实现)
    ↓
REVIEWING (审查)
    ↓
COMPLETE (你在这里)
    └─→ 可能回到 DEBUGGING 修复
```

如果 COMPLETE 发现重大问题（如 quality_gate 致命错误）：
- 不直接标记 DONE
- 改为 BLOCKED 或进入 DEBUGGING
- 完成修复后再回到 COMPLETE

## 工作流状态机

```json
{
  ".workflow_state.json": {
    "phase": "COMPLETE",
    "entry_time": "2026-04-11T10:30:00Z",
    "completion_time": "2026-04-11T10:45:00Z",
    "status": "DONE_WITH_CONCERNS",
    "risks": [
      {
        "id": "SECRET_KEY_HARDCODED",
        "severity": "HIGH",
        "file": "src/auth.py:3",
        "action_required": true,
        "estimated_fix_time": "30 min"
      }
    ],
    "summary": "JWT 认证核心功能完成，已知 1 个高优先级问题待修"
  }
}
```
