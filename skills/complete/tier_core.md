<!-- tier:25% -->

# COMPLETE - 核心方法论

## 核心骨架 (4 步)

1. **运行最终验证** - 执行测试、质量门禁，确保无回归
2. **更新状态文件** - 更新 `.workflow_state.json`，phase 设为 COMPLETE
3. **输出完成状态** - 明确说明 DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT
4. **记录可复用经验** - 对 M+ 任务提炼经验，供后续快速参考

## 铁律

**NO DONE WITHOUT EVIDENCE FIRST**

禁止凭"我认为通过了"就宣布完成。必须运行测试看到通过结果。

## 完成状态定义

| 状态 | 含义 | 触发条件 |
|------|------|----------|
| **DONE** | 任务完全完成 | 目标达成，验证通过，无风险 |
| **DONE_WITH_CONCERNS** | 完成但有遗留问题 | 主目标达成，但存在风险或未完成项 |
| **BLOCKED** | 任务被阻塞 | 缺少外部条件、权限或关键输入 |
| **NEEDS_CONTEXT** | 需要更多上下文 | 无法判断是否完成 |

## 完成门禁 (三项全部满足)

1. 运行测试并看到通过结果（无例外）
2. 更新 `.workflow_state.json`（phase = COMPLETE）
3. 输出明确的完成状态（DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT）

无验证证据 = 未完成
