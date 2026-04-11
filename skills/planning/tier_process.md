<!-- tier:40% -->

# PLANNING - 过程与决策点

## 进入条件

- 用户明确要求计划、规划、拆分
- 任务涉及多个文件或步骤
- 执行前需要先定义范围、验收和顺序

## 核心过程

### 1. Clarify Scope

- 提炼一句话目标
- 识别硬约束（如 API 版本、库依赖、性能要求）
- 明确不做什么（out of scope）

### 2. Break Work Down

**优先拆成 P0 / P1 / P2**：

- **P0**: 不完成就无法交付
- **P1**: 重要但不阻塞主路径
- **P2**: 优化项

每个任务至少包含：
- `status`
- `description`
- `acceptance` - 验收标准
- `owned_files` - 涉及的文件
- `verification` - 验证方式

### 3. Create Spec Artifacts

根据复杂度选择：

**XS/S**: 跳过 .specs/ 流程，仅用 TodoWrite

**M+**: 创建规范链

```bash
mkdir -p .specs/<feature>/
# 手动创建: spec.md, plan.md, tasks.md
```

或使用 workflow_engine 自动初始化：

```bash
python3 scripts/workflow_engine.py --op init --prompt "任务描述"
```

### 4. Create Contract

基于 plan.md 和 tasks.md 创建履约契约：

```bash
python3 -c "from contract_manager import create_phase_contract; create_phase_contract('任务名', '描述', '.')"
```

### 5. Output Contract Visualization

PLANNING 结束时**必须**输出可读的摘要，让用户在 EXECUTING 前确认范围：

```markdown
## 📋 任务契约

**目标**: {一句话目标}
**复杂度**: {XS/S/M/L/XL}
**预计阶段**: {阶段序列}

### P0 任务（必须完成）
- [ ] {任务} — 验收: {条件}

### P1 任务（重要）
- [ ] {任务}

### 明确不做
- {out of scope 事项}

**进入 EXECUTING 后，AI 将按上述顺序逐项执行。**
```

## 关键决策点

| 决策 | 条件 | 结果 |
|------|------|------|
| **规划模式选择** | 是否存在 tasks.md | canonical / legacy / lightweight |
| **复杂度路由** | 任务范围大小 | XS/S → lightweight / M → spec-kit / L/XL → full |
| **记忆复用检查** | 是否有 memory_hints | 先复用历史经验，再决定新增任务 |

## 出口条件详解

### XS/S 复杂度

- TodoWrite 已列出所有任务项
- 每项有验收标准
- 不需要 .contract.json

### M 复杂度

- `.specs/<feature>/spec.md` 已创建（用户故事 + 验收标准）
- `.specs/<feature>/plan.md` 已创建（技术方案 + 约束）
- `.specs/<feature>/tasks.md` 已创建（可执行任务清单）
- `.contract.json` 已创建或准备生成

### L/XL 复杂度

- 完整 spec-kit 已创建（spec.md、plan.md、tasks.md）
- `.contract.json` 已创建（非 draft 状态）
- 每个 P0 任务都有 owned_files 列表
