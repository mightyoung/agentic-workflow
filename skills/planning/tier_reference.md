<!-- tier:reference -->

# PLANNING - 参考与示例

## 完整示例：中等复杂度 (M) 任务

### 场景
用户要求："帮我实现一个用户认证系统"

### Step 1: Clarify Scope

- **目标**: 实现基于 JWT 的用户认证系统
- **硬约束**: 必须支持刷新令牌、兼容 OAuth2 流程
- **不做**: 不实现社交登录、不做二步认证

### Step 2: Break Work Down

**P0 (必须)**:
1. 创建 User 模型和数据库迁移
2. 实现 JWT token 生成和验证
3. 实现 /login endpoint
4. 实现 token 刷新逻辑

**P1 (重要)**:
5. 添加速率限制
6. 实现 token 撤销

**P2 (优化)**:
7. 添加审计日志

### Step 3-5: Create Spec Kit & Contract

创建：
- `.specs/auth/spec.md` - 用户故事、验收标准
- `.specs/auth/plan.md` - 技术方案（JWT 秘钥管理、token 生命周期等）
- `.specs/auth/tasks.md` - P0/P1/P2 任务清单
- `.contract.json` - 履约契约

### Output

```markdown
## 📋 任务契约

**目标**: 实现基于 JWT 的用户认证系统
**复杂度**: M
**预计阶段**: PLANNING → EXECUTING → REVIEWING → COMPLETE

### P0 任务（必须完成）
- [ ] 创建 User 模型和迁移 — 验收: 数据库已创建，User 表含 email/password
- [ ] 实现 JWT token 生成和验证 — 验收: 单测覆盖 >80%
- [ ] 实现 /login endpoint — 验收: 正确的 email/password 返回 token，错误返回 401
- [ ] 实现 token 刷新逻辑 — 验收: refresh token 有效期 7 天

### P1 任务（重要）
- [ ] 添加速率限制 — 验收: 单个 IP 每分钟最多 5 次登录
- [ ] 实现 token 撤销 — 验收: logout 后 token 失效

### 明确不做
- 社交登录（Google/GitHub）
- 二步认证
- 密码重置流程（后续需求）

**进入 EXECUTING 后，AI 将按上述顺序逐项实现。**
```

## 规划失败的常见场景

### 场景 1: 估算错误

**症状**: 规划说 M 复杂度，实际执行时发现需要 L

**预防**:
- 规划时充分查询 memory_hints
- 对已有库/框架的陌生度单独估算（+1 级）
- 与专家讨论，而不是自己估算

### 场景 2: 范围蠕变

**症状**: 执行过程中不断追加 P0 任务

**预防**:
- 在规划时充分压缩范围到 3-5 个 P0
- 额外需求统一入 P1
- 契约中明确 "明确不做" 项

### 场景 3: 验收标准模糊

**症状**: 任务完成了但没人确定是否合格

**预防**:
- 每个任务的验收标准必须可测量（非 "看起来对"）
- 包含具体的输入、输出、边界条件

## 规划与记忆的融合

### 检查历史相似任务

```bash
# 在规划前运行
python3 scripts/memory_longterm.py --op search-entity --query "authentication" --limit 3
```

如果有命中：
- 查看之前的失败点，提前在规划中规避
- 复用已验证的技术方案
- 在任务描述中引用历史经验

### 规划完成后记录决策

如果本次规划做出了重要架构决策（如选择 JWT vs Session），应记入长期记忆，方便后续快速参考。

## Minimal Plan Schema (YAML 版本)

如果偏好结构化定义，可用：

```yaml
metadata:
  feature_id: auth
  complexity: M
  planning_mode: canonical

goals:
  - Implement JWT-based authentication

structure_decisions:
  - Use RS256 for token signing
  - 7-day expiry for access token, 30-day for refresh

constraints:
  - Must be compatible with OAuth2
  - Token validation must be <10ms

tasks:
  - id: T1
    title: Create User model
    priority: P0
    owned_files: [src/models/user.py, migrations/]
    
  - id: T2
    title: JWT token generation
    priority: P0
    owned_files: [src/auth/token.py]
```

## Implemented Vs Planned

当前**未实现**，但在规划文档中提到的能力：

- 复杂状态机自动推进
- Dev Agent Record 自动持久化
- trajectory 自动写回 `.specs/<feature>/tasks.md`
- HARD-GATE 自动评分系统

这些如果需要，应在脚本层实现后再回填文档。
