<!-- tier:20% -->

# REVIEWING - 核心方法论

## 核心骨架

1. **收集证据** - 查看实际代码变更、运行自动检查、执行测试
2. **规范合规检查** - 对照 spec-kit 逐项验证 P0 任务是否实现
3. **代码质量审查** - 逐文件分析边界条件、测试覆盖、安全隐患
4. **路由决策** - 有阻断问题进入 DEBUGGING，否则进入 COMPLETE

## 铁律

**NO REVIEWING WITHOUT READING THE ACTUAL DIFF FIRST**

禁止泛泛而谈。无 file:line = 未审查。

## 二阶段顺序

1. **Spec Compliance** (必先)：合规性问题会导致整个实现方向错误，越早发现成本越低
2. **Code Quality** (后)：仅在 Stage 1 无致命问题时执行

## 完成门禁 (三项全部满足才有效)

1. 已运行 `git diff HEAD~1` 并基于真实代码变更写出意见
2. 审查意见必须包含至少一条 `file:line` 格式的具体定位
3. 已运行 `pytest -v` 或等效测试命令，确认无回归

仅输出 "代码看起来不错" = 无效审查
