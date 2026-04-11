<!-- tier:50% -->

# COMPLETE - 过程与决策

## 进入条件

- REVIEWING 已完成，或用户接受当前结果
- 本轮任务已达到可交付状态
- 需要做最终同步与总结

## 核心过程

### 1. Run Final Verification Checklist

最小核对项：

- ✅ 测试是否通过（pytest -v 输出为证）
- ✅ 质量门禁是否通过（quality_gate.py 输出为证）
- ✅ 是否存在 secrets 风险（git diff + grep 检查）
- ✅ 用户可见结果是否已验证（手动或自动化演示）
- ✅ 状态文件是否已同步（.workflow_state.json）

### 2. Update Project-Local State

更新 workflow 状态到完成：

```bash
python3 scripts/workflow_engine.py --op advance --phase COMPLETE --workdir .
```

### 3. Summarize The Outcome

建议至少说明：

- **完成了什么** - 本轮的交付物清单
- **没完成什么** - 后续需要的项
- **存在哪些风险或遗留项** - 技术债、性能隐患、安全考量
- **下一步该做什么** - 建议的后续行动

### 4. Capture Reusable Learnings

对于 M+ 复杂度的任务，可选择提炼经验：

```bash
python3 scripts/memory_longterm.py --op=refine --days=7
```

## 出口条件详解

以下条件必须全部满足，任务才能声称完成：

1. **验证证据已收集**
   - 运行 `pytest -v` 看到通过结果
   - 运行 `python3 scripts/quality_gate.py` 无致命问题
   - git diff 中无泄露的 secrets

2. **状态文件已更新**
   ```bash
   # .workflow_state.json 中
   "phase": "COMPLETE"
   ```

3. **完成状态已明确声明**
   - DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT 四选一
   - 必须有理由和证据支撑

4. **可复用经验已记录**（可选，但 M+ 任务建议做）
   - 用 memory_longterm 或 learn 技能记录本次发现
   - 包含关键决策、解决的问题、下次可复用的方案

## 摘要复用规则

COMPLETE 阶段**优先复用**上游已生成的摘要，而非重新推导：

| 来源 | 说明 | 用途 |
|------|------|------|
| `planning_summary` | 计划阶段的产出 | 说明规划是否 canonical/legacy/lightweight |
| `research_summary` | 研究阶段的产出 | 说明证据是否 verified/degraded |
| `review_summary` | 审查阶段的产出 | 说明审查是否完成、是否有阻断 |
| `thinking_summary` | 调查过程中的结论 | 保留本轮的主要发现和矛盾 |
| `resume_summary` | 恢复场景的对齐 | 快速追赶前情背景 |

**原则**: 不在 COMPLETE 中重新生成 planning_summary、review_summary 等，直接引用。

## 关键决策点

| 决策 | 条件 | 结果 |
|------|------|------|
| **完成状态选择** | 是否有阻断问题 | DONE / DONE_WITH_CONCERNS / BLOCKED |
| **经验提炼** | 任务复杂度 | XS/S 不必，M+ 建议提炼 |
| **后续行动** | 是否有技术债 | 生成 follow-up task 或记录为 P2 |

## 特殊场景：DONE_WITH_CONCERNS

当主目标达成但存在风险或未完成项时使用：

```markdown
## 完成状态

**Status**: DONE_WITH_CONCERNS

**完成项**:
- ✅ 核心认证功能已实现
- ✅ 所有 P0 测试已通过

**遗留项**:
- ⚠️ 性能优化（token 验证耗时 >10ms）- P1，后续优化
- ⚠️ 审计日志缺少（设计已做，实现 P2）

**风险**:
- JWT SECRET_KEY 当前为硬编码，需改为从 env 读取
- token 过期时间固定为 1h，可能过短 - 监控后调整

**建议**:
1. 立即改为从环境变量读取 SECRET_KEY
2. 性能监控：添加 token 验证耗时指标
3. 下阶段实现审计日志和可配置过期时间
```
