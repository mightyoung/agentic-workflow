# ECC集成测试设计文档

## 测试概述

本测试套件设计用于评估 `agentic-workflow` skill 的以下方面：
1. **Skill触发检测** - 能否在不显式调用时正确激活
2. **阶段触发效果** - 各阶段对任务的优化作用
3. **运行质量提升** - 执行效果、速度、上下文优化
4. **ECC引用触发** - ecc-workflow的正确触发和降级
5. **端到端集成** - 完整工作流测试

## 测试维度分布

| 维度 | 测试数量 | 权重 | 描述 |
|------|----------|------|------|
| Skill触发检测 | 8 | 15% | 隐式触发准确性 |
| 阶段触发效果 | 12 | 20% | 阶段执行优化 |
| 运行质量提升 | 15 | 25% | 质量/速度/上下文 |
| ECC引用触发 | 10 | 25% | ECC集成 |
| 端到端集成 | 5 | 15% | 完整流程 |
| **总计** | **50** | **100%** | |

---

## 详细测试设计

### 1. Skill触发检测 (8个测试)

测试目标：验证 `agentic-workflow` 在用户不显式调用时能否正确激活

#### 测试用例

| ID | 测试场景 | 预期模块 | 评估指标 |
|----|----------|----------|----------|
| td01 | "帮我用TDD开发一个用户认证模块" | EXECUTING, RESEARCH | 触发延迟<500ms |
| td02 | "写一个排序算法然后修复测试失败的问题" | EXECUTING, DEBUGGING | 自动切换到DEBUGGING |
| td03 | "帮我审查这段代码然后优化性能" | REVIEWING, EXECUTING | 顺序触发两个阶段 |
| td04 | "分析这个API设计的最佳实践" | RESEARCH, THINKING | 触发Research优先 |
| td05 | "hello world" | - | 简单闲聊不触发 |
| td06 | "OK明白了谢谢" | - | 确认语句不触发 |
| td07 | "这个bug怎么调试最好" | DEBUGGING, THINKING | Debugging触发+思考 |
| td08 | "我想学习怎么做系统设计" | RESEARCH, THINKING | 学习意图触发Research |

---

### 2. 阶段触发效果 (12个测试)

测试目标：验证每个阶段触发后是否对任务执行产生优化作用

#### 评估维度
- **执行效率** (efficiency_gain): 该阶段带来的效率提升
- **上下文优化** (context_optimization): 上下文使用优化程度

#### 测试用例

| ID | 阶段 | 测试场景 | 预期行为 | 效率提升指标 |
|----|------|----------|----------|---------------|
| pe01 | RESEARCH | "搜索React状态管理最佳实践" | tavily调用+findings | 搜索时间减少60% |
| pe02 | THINKING | "谁最懂分布式缓存设计" | 专家识别+推理 | 推理深度增加 |
| pe03 | PLANNING | "规划电商后端开发" | task_plan+任务拆分 | 任务粒度2-5分钟 |
| pe04 | EXECUTING | "用TDD开发支付模块" | 红→绿→重构 | bug率降低50% |
| pe05 | REVIEWING | "全面审查Python项目" | 分级审查 | 问题发现率提升 |
| pe06 | DEBUGGING | "服务一直崩溃请调试" | 5步方法论 | 调试时间减少40% |
| pe07 | RESEARCH | "搜索K8s最佳实践" | tavily+结果存储 | 搜索质量提升 |
| pe08 | THINKING | "从安全专家角度看登录" | 专家模拟 | 视角更全面 |
| pe09 | PLANNING | "制定开发里程碑计划" | 阶段+里程碑 | 计划完整性提升 |
| pe10 | EXECUTING | "TDD实现队列数据结构" | 测试驱动 | 代码质量提升 |
| pe11 | REVIEWING | "审查Go代码并改进" | 问题分级 | 修复效率提升 |
| pe12 | DEBUGGING | "NPE错误反复出现" | 7项检查 | 根因定位更快 |

---

### 3. 运行质量提升 (15个测试)

测试目标：评估激活skill后的执行效果、速度、上下文优化

#### 评估指标

| 指标 | 公式 | 目标 |
|------|------|------|
| 代码质量提升 | (优化后质量 - 基准质量) / 基准质量 | >30% |
| Bug率降低 | (基准bug - 优化后bug) / 基准bug | >40% |
| Token使用效率 | 有用token / 总token | >60% |
| 执行时间 | 基准时间 / 优化后时间 | 允许适度增加以换取质量 |

#### 测试用例

| ID | 测试场景 | 基准 | 优化后 | 预期改进 |
|----|----------|------|--------|----------|
| qi01 | TDD开发REST API | 普通开发 | TDD循环 | 代码质量+40%, Bug-60% |
| qi02 | 搜索高并发缓存 | 直接实现 | Research+实现 | 方案完整性+50% |
| qi03 | 用户权限系统 | 简单实现 | 安全专家+设计 | 安全覆盖+70% |
| qi04 | 调试并发bug | 单次调试 | 5步调试法 | 修复成功率+30% |
| qi05 | 审查微服务 | 快速浏览 | 分级审查 | 问题发现+50% |
| qi06 | 重构大型系统 | 简单列表 | 详细计划+文件 | 任务覆盖+60% |
| qi07 | TDD+安全审计 | 普通开发 | TDD+Review | 安全问题-80% |
| qi08 | 调试内存泄漏 | 尝试修复 | 系统调试法 | 根因定位95% |
| qi09 | 可扩展架构 | 基础架构 | 专家设计+Research | 扩展性+60% |
| qi10 | CRUD管理系统 | 快速实现 | TDD+Review | 可维护性+40% |
| qi11 | 算法性能优化 | 简单优化 | 专家分析+Research | 性能提升100% |
| qi12 | 实时通信系统 | 基础实现 | 架构设计+Research | 架构评分+50% |
| qi13 | 修复遗留代码 | 逐个修复 | 系统审查+规划 | 重构覆盖+70% |
| qi14 | CI/CD流水线 | 简单配置 | 最佳实践+Research | 完整性+60% |
| qi15 | 容错系统设计 | 基础容错 | 专家设计+最佳实践 | 恢复时间-70% |

---

### 4. ECC引用触发 (10个测试)

测试目标：验证ecc-workflow的正确触发和降级机制

#### 降级策略

```
尝试ECC → 不存在 → 内置版本
           ↓
      内置版本:
      - TDD: references/builtin_tdd.md
      - Review: references/modules/reviewing.md
      - E2E: references/builtin_e2e.md
```

#### 测试用例

| ID | 任务类型 | 预期ECC调用 | 降级版本 | 验证点 |
|----|----------|-------------|----------|--------|
| ec01 | TDD开发 | skill("ecc-workflow", "/tdd") | builtin_tdd.md | TDD循环执行 |
| ec02 | 代码审查 | skill("ecc-workflow", "/code-review") | reviewing.md | 审查流程 |
| ec03 | E2E测试 | skill("ecc-workflow", "/e2e") | builtin_e2e.md | E2E用例生成 |
| ec04 | TDD实现 | skill("ecc-workflow", "/tdd") | builtin_tdd | 红→绿→重构 |
| ec05 | 代码审查+优化 | skill("ecc-workflow", "/code-review") | reviewing.md | 分级审查 |
| ec06 | E2E测试覆盖 | skill("ecc-workflow", "/e2e") | builtin_e2e | 流程测试 |
| ec07 | 测试优先开发 | 自动检测 | 内置TDD | 测试先行 |
| ec08 | 全面代码审查 | 自动检测 | 内置Review | 问题分级 |
| ec09 | E2E测试创建 | 自动检测 | 内置E2E | 端到端覆盖 |
| ec10 | 测试驱动 | 自动检测 | 内置TDD | 失败→实现→通过 |

---

### 5. 端到端集成 (5个测试)

测试目标：验证完整工作流和跨阶段协调

#### 测试用例

| ID | 测试场景 | 流程 | 产出文件 | 完成标准 |
|----|----------|------|-----------|----------|
| ee01 | 认证系统 | Planning→Executing→Reviewing | task_plan.md, 测试, 代码 | 可运行系统 |
| ee02 | 高并发系统 | Research→Thinking→Planning→Executing | findings.md, 系统代码 | 设计+代码 |
| ee03 | Bug修复+重构 | Debugging→Executing→Reviewing | 调试记录, 测试, 重构 | Bug修复+测试 |
| ee04 | 分析+审查+优化 | Thinking→Reviewing→Executing | 分析报告, 审查报告, 代码 | 完整优化 |
| ee05 | 微服务项目 | Research→Planning→Executing→Reviewing | 所有文件 | 完整项目结构 |

---

## 评估指标体系

### 核心指标

| 指标 | 计算公式 | 目标值 |
|------|----------|--------|
| 触发准确率 | 正确触发次数 / 总触发次数 | >95% |
| 阶段有效性 | (优化后指标 - 基准) / 基准 | 显著正向 |
| ECC降级率 | 降级次数 / ECC调用次数 | <20% |
| 质量提升 | with_skill_score / baseline_score | >1.3 |
| 执行速度 | baseline_time / with_skill_time | >0.8 |
| 上下文效率 | 有用信息token / 总token | >60% |

### 测量方法

1. **Token统计**: 使用Claude Code API的token统计
2. **执行时间**: 记录每个测试的开始/结束时间
3. **质量评分**: 使用LLM-as-a-judge进行评分
4. **上下文分析**: 分析prompt中的信息复用程度

---

## 测试方法论

### A/B对比测试设计

```
基准组 (Baseline):
  - 不激活agentic-workflow
  - 直接执行用户请求

实验组 (Treatment):
  - 激活agentic-workflow
  - 完整流程执行

对比维度:
  - 输出质量
  - Token消耗
  - 执行时间
  - 上下文利用率
```

### 评估流程

1. **准备阶段**: 加载测试用例，初始化环境
2. **执行阶段**: 按类别运行测试，记录指标
3. **分析阶段**: 对比基准和实验组，计算改进
4. **报告阶段**: 生成详细的测试报告

---

## 运行测试

```bash
# 运行所有测试
python tests/run_ecc_test.py

# 查看测试结果
cat ecc_test_results.json

# 生成HTML报告
python tests/generate_ecc_report.py --input ecc_test_results.json --output ecc_report.html
```

---

## 预期结果

基于设计的目标，我们预期：

| 维度 | 预期结果 |
|------|----------|
| 触发准确率 | >95% |
| 阶段有效性 | 显著正向 |
| ECC降级处理 | 正常工作 |
| 质量提升 | 30%+ |
| 整体通过率 | >85% |
