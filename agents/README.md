# Subagents Index

核心子智能体定义索引。

## 子智能体列表

| 智能体 | 职责 | 对应阶段 | 定义文件 |
|--------|------|----------|----------|
| **researcher** | 研究搜索 | RESEARCH | `researcher.md` |
| **planner** | 任务规划 | PLANNING | `planner.md` |
| **coder** | 代码实现 | EXECUTING | `coder.md` |
| **reviewer** | 代码审查 | REVIEWING | `reviewer.md` |
| **debugger** | 调试修复 | DEBUGGING | `debugger.md` |
| **security_expert** | 安全审查 | THINKING/REVIEWING | `security_expert.md` |
| **performance_expert** | 性能优化 | THINKING/REVIEWING | `performance_expert.md` |

## 与 WORKFLOW 阶段对应

```
IDLE → RESEARCH → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
              ↓           ↓           ↓           ↓
         DEBUGGING ←────────────────────────────────────→

RESEARCH   → researcher (搜索)
THINKING   → (内置专家模拟) / security_expert / performance_expert
PLANNING   → planner (规划)
EXECUTING  → coder (实现)
REVIEWING  → reviewer (审查) / security_expert / performance_expert
DEBUGGING  → debugger (调试)
```

## 专家子智能体

| 专家 | 职责 | 触发场景 |
|------|------|----------|
| **security_expert** | 安全审查 | 涉及认证、权限、加密、数据安全 |
| **performance_expert** | 性能优化 | 涉及性能瓶颈、延迟、缓存、数据库优化 |

## 子智能体调用方式

当需要并行执行独立任务时，可以派生子智能体：

```yaml
# 派生子智能体示例
subagents:
  - researcher:
      task: "搜索分布式事务最佳实践"
  - planner:
      task: "规划任务拆分"
```

## 执行模式

| 模式 | 适用场景 |
|------|----------|
| **并行** | 独立任务（多文件审查、多模块开发） |
| **串行** | 依赖任务（规划→执行） |
| **后台** | 非阻塞任务（大规模搜索） |

## 注意事项

- **THINKING 阶段不使用子智能体** - 专家模拟是主智能体的内置能力
- **EXECUTING 阶段 coder 可处理测试** - 复杂测试可调用 ecc-workflow 的 /e2e
- **子智能体共享主智能体上下文** - 适合需要上下文连贯性的任务
