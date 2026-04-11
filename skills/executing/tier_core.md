<!-- tier:10% -->

# EXECUTING — Core

## 核心方法

1. 读计划 — 确认当前任务、影响文件、验证方式
2. 写测试 — 先写失败测试，再写最小实现
3. 最小实现 — 只做刚好能让测试通过的代码
4. 跑验证 — 运行测试，看到通过结果为止
5. 同步状态 — 更新 tasks.md / SHARED_TASK_NOTES.md

## Iron Law

**NO COMPLETE WITHOUT TESTS PASSING FIRST**

## Hard-Gate（退出条件，全部必须满足）

- 目标代码已实现（Read 真实文件确认）
- 相关测试已运行并通过（有命令输出为证）
- 关键 P0 任务状态已同步至计划文件

## Default 策略

TDD when practical；不适合 TDD 时，至少定义清晰验证路径（pytest / 构建命令 / 手动步骤）。
