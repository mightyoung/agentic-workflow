<!-- tier:60% -->

# PLANNING - 完整方法论与验证

## 完整 spec-kit 流程

### 规范链文件结构

| 阶段 | 文件 | 内容 |
|------|------|------|
| 需求 | `.specs/<feature>/spec.md` | 用户故事、验收标准、成功标准、约束条件 |
| 方案 | `.specs/<feature>/plan.md` | Goals、Technical Context、Structure Decisions、Constraints |
| 任务 | `.specs/<feature>/tasks.md` | 每个 User Story 的 Files、Verification、Blocked-By |
| 履约 | `.contract.json` | 履约契约（goals/verification/owned_files） |

### spec.md 最小模板

```markdown
## Story N: [故事名]
[故事内容]

**Acceptance Criteria:**
- [ ] 标准1
- [ ] 标准2

## Success Criteria
[成功指标]

## Constraints
[约束条件]
```

### plan.md 最小模板

```markdown
## Goals
[项目目标]

## Technical Context
[技术背景]

## Structure Decisions
[架构决策]

## Constraints
[约束条件]
```

### tasks.md 最小模板

```markdown
## User Story 1
- **Files**: [涉及文件]
- **Verification**: [验证方式]
- **Blocked-By**: [前置任务]

## User Story 2
[同上]
```

## 自动验证命令

```bash
# 验证规范链完整性
bash scripts/check_template.sh .

# 从 spec.md 生成规范链
python3 -m task_decomposer --from-spec --feature-id myfeature

# 生成履约契约
python3 -c "from contract_manager import create_phase_contract; create_phase_contract('任务名', '描述', '.')"
```

Windows:

```bat
scripts\win\check_template.bat .
```

## 记忆与规划融合

开始拆分前，优先检查当前 phase 上下文里的 `memory_hints`、`memory_query` 和 `memory_intent`：

- 长期记忆中**已有相似失败**？先复用修复模式
- **已验证的约束**？避免重复探索
- **已成功的实现**？参考而非重做

## 复杂度自动路由规则

| 复杂度 | 特征 | 规划策略 |
|--------|------|---------|
| **XS** | <3 小任务 | TodoWrite，无 .specs/ |
| **S** | 3-5 小任务 | TodoWrite，无 .specs/ |
| **M** | 6-15 任务，2-3 个 P0 | 完整 spec-kit，生成 contract.json |
| **L** | 15+ 任务，多个 P0，跨多模块 | 完整 spec-kit，contract.json 非 draft |
| **XL** | 复杂系统，高风险 | 完整 spec-kit + security review |

## 兼容投影层

**legacy task_plan.md**：
- 仍可被旧 runtime/frontier 读取
- 不再作为主要输出
- 如需生成，在完整 spec-kit 之后

## 反模式与注意

- **反模式1**: 在没有验收标准的情况下拆分任务 → 结果执行偏差
- **反模式2**: 一次拆出超过 20 个任务 → 执行时容易遗漏
- **反模式3**: P0/P1/P2 划分不清 → 优先级混乱
- **最佳实践**: 每个任务控制在 4h-8h 内完成

## 规划模式自动检测逻辑

```python
if os.path.exists('.specs/<feature>/tasks.md'):
    planning_mode = 'canonical'  # 完整 spec-kit
elif os.path.exists('task_plan.md'):
    planning_mode = 'legacy'     # 兼容旧投影
else:
    if complexity in ['XS', 'S']:
        planning_mode = 'lightweight'  # TodoWrite 式
    else:
        planning_mode = 'canonical'    # 创建完整 spec-kit
```
