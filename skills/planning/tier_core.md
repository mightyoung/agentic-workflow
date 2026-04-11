<!-- tier:25% -->

# PLANNING - 核心方法论

## 核心骨架 (3-5 步)

1. **明确目标** - 提炼一句话目标，识别硬约束，明确不做什么
2. **拆分任务** - 拆成 P0/P1/P2，每个任务包含 status、description、acceptance、owned_files、verification
3. **创建规范链** - `.specs/<feature>/spec.md` → `plan.md` → `tasks.md` → `.contract.json`
4. **输出契约摘要** - 向用户展示任务范围、P0 任务、明确不做事项

## 铁律

**NO EXECUTING WITHOUT A PLAN FIRST**

规划完全是为了避免执行偏差，禁止在没有任何计划产出的情况下进入 EXECUTING。

## 复杂度分级 & 出口条件

| 复杂度 | 产出物 | 必须达成 |
|--------|--------|---------|
| **XS/S** | TodoWrite | 任务项已列出，每项有验收标准 |
| **M** | .specs/ + .contract.json | spec.md、plan.md、tasks.md、contract.json 全部创建 |
| **L/XL** | 完整 spec-kit | contract.json 非 draft，每个 P0 任务有 owned_files |

**硬门禁**: 未产出任何计划 = 禁止进入 EXECUTING

## 规划模式自动检测

- **canonical**: tasks.md 存在 → 使用完整 spec-kit
- **legacy**: task_plan.md 存在但无 tasks.md → 兼容旧投影
- **lightweight**: XS/S 复杂度 → 轻量 TodoWrite
