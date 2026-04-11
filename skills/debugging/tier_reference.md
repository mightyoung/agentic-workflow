<!-- tier:100% -->

## Completion Status Protocol

### 状态定义

| 状态 | 含义 | 使用场景 |
|------|------|----------|
| `DONE` | 完成 | 问题已定位、修复、验证，测试通过 |
| `DONE_WITH_CONCERNS` | 完成但有顾虑 | 修复完成但有未解决的边缘情况或技术债务 |
| `BLOCKED` | 阻塞 | 无法继续调试（缺信息、缺工具、缺权限） |
| `NEEDS_CONTEXT` | 需要更多上下文 | 需要用户提供额外信息才能继续 |

### 状态转换

```
[开始调试]
    │
    ▼
┌─────────────────────────────────┐
│  分析中...                       │
│  (执行 5步调试法)                │
└─────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────────────┐
│  状态判断：                                          │
│  ├─ 问题修复且测试通过 → DONE                        │
│  ├─ 有边缘问题待后续 → DONE_WITH_CONCERNS            │
│  ├─ 缺关键信息/工具   → NEEDS_CONTEXT → 用户询问     │
│  └─ 无法解决           → BLOCKED → 升级             │
└──────────────────────────────────────────────────────┘
```

### 输出格式模板

```markdown
## DEBUGGING Completion Report

### 问题摘要
- **问题描述**: [简述]
- **影响范围**: [影响范围]
- **紧急程度**: P0/P1/P2/P3

### 调试过程
- **调试轮次**: N 次
- **使用策略**: [使用的调试策略]
- **关键发现**: [1-2个关键发现]

### 修复结果
- **修复方案**: [描述]
- **测试覆盖**: [覆盖情况]
- **风险评估**: [风险]

### 最终状态
- **Completion Status**: [DONE / DONE_WITH_CONCERNS / BLOCKED / NEEDS_CONTEXT]
- **后续行动**: [如需要]
```

---

## 复盘模板（完整）

```markdown
## 问题回顾
- 问题描述：
- 发生时间：
- 影响范围：

## 根因分析
- 直接原因：
- 根本原因：
- 5Why 追溯：

## 修复方案
- 修复内容：
- 验证方法：
- 测试覆盖：

## 经验教训
- 做得好的：
- 需要改进的：
- 预防措施：
```

---

## Hypothesis Generation Framework — 完整细节

### 6 类失败模式

| 类别 | 描述 | 检查点 |
|------|------|--------|
| **Logic Error** | 算法错误、边界问题、off-by-one | 条件判断、循环、数据结构 |
| **Data Issue** | 类型错误、空值、编码问题 | 输入验证、类型转换、空值处理 |
| **State Problem** | 竞态条件、缓存过期、状态初始化 | 并发、缓存、初始化逻辑 |
| **Integration Failure** | API契约、版本不兼容、配置错误 | 接口调用、版本、配置 |
| **Resource Issue** | 内存泄漏、连接池耗尽、超时 | 资源管理、连接、限流 |
| **Environment** | 依赖缺失、权限问题、时区 | 依赖、环境变量、权限 |

### 证据标准

| 证据类型 | 强度 | 示例 |
|----------|------|------|
| **Direct** | 强 | 代码在 `file.ts:42` 显示 `if (x > 0)` 应为 `if (x >= 0)` |
| **Correlational** | 中 | 错误率在 commit `abc123` 后增加 |
| **Testimonial** | 弱 | "在我机器上能跑" |
| **Absence** | 可变 | 代码路径中未找到空值检查 |

### 置信度评估

| 级别 | 标准 |
|------|------|
| **High (>80%)** | 多条直接证据，清晰因果链，无矛盾证据 |
| **Medium (50-80%)** | 部分直接证据，合理因果链，轻微歧义 |
| **Low (<50%)** | 大部分相关证据，因果链不完整，存在矛盾证据 |

### 假设验证流程（完整）

```
1. 生成 N 个假设（覆盖不同失败模式）
2. 每个假设定义：
   - 确认证据：什么证据会确认此假设？
   - 否定证据：什么证据会否定此假设？
3. 收集证据，标注强度和来源
4. 评估置信度
5. 仲裁：比较所有假设，确定最可能根因
```

---

## Reflexion Entry — 完整 Bash 示例

```bash
# 示例：Python 类型注解问题
python3 scripts/memory_longterm.py \
  --op add-experience \
  --exp "Task:type-annotation Trigger:Python 3.9 union syntax \
  Mistake:used str|Path without __future__ import \
  Fix:add 'from __future__ import annotations' at module top \
  Signal:TypeError unsupported operand type(s) for |"
```

---

## 铁律检查表

| 铁律 | 要求 | 检查点 |
|------|------|--------|
| **穷尽一切** | 没有穷尽所有方案之前，禁止说"无法解决" | 尝试了多少种调试方案？ |
| **先做后问** | 遇到问题先自行搜索、读源码、验证，再提问 | 搜索了多少文档/源码？ |
| **主动出击** | 端到端交付，不只是"刚好够用" | 修复是否完整？测试覆盖够吗？ |

---

## 边缘情况处理

### 无法复现的问题

1. 收集详细环境信息（OS、版本、配置、日志）
2. 分析可能的非确定性因素（并发、时间、外部依赖）
3. 添加更多日志后等待复现
4. 考虑使用混沌工程手段主动触发

### 第三方依赖问题

1. 先确认是否为已知 bug（查 changelog、issues）
2. 尝试降级/升级依赖版本
3. 考虑 patch 或 workaround
4. 记录到 Reflexion Entry 供后续参考

### 环境差异问题

1. 对比所有环境变量和配置
2. 检查依赖版本锁定（lockfile）
3. 使用容器隔离复现
4. 7项检查清单中的"环境检查"重点过

---

## Implemented vs Planned

| 功能 | 状态 | 说明 |
|------|------|------|
| 5步调试法 | Implemented | Step 1–5 + Step 0.5 + Step 5.5 |
| 压力升级机制 | Implemented | 2/3/4/5次失败分级响应 |
| 7项检查清单 | Implemented | Step 3 中全覆盖 |
| ACH 竞争假设法 | Implemented | Step 2 中集成 |
| Reflexion 记忆检索 | Implemented | Step 0.5 |
| Reflexion 反思写入 | Implemented | Step 5.5 |
| MAGMA 因果图集成 | Implemented | search-causal 命令 |
| context-aware 激活档位 | Implemented | 0%/25%/50% 三档 |
| Simple-Failure Downgrade | Implemented | Step 4.5 |
| error_classifier 集成 | Implemented | 触发档位升级的错误类型 |
