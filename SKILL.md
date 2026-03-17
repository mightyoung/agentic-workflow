---
name: agentic-workflow
description: >
  统一智能体工作流 - 用于任何复杂任务开发。
  包含：思考分析、任务规划、代码执行、规范审查、调试。
  当用户请求：开发功能、修复bug、规划项目、代码审查、实现需求时使用。
  自动管理任务进度，规范检查(OpenSpec可选)和错误恢复。
  不问"你怎么看"，而是问"这个问题谁最懂"。
---

# Agentic Workflow - 统一智能体工作流

> 融合 best-minds, brainstorming, writing-plans, planning-with-files, TDD, systematic-debugging, verification 精髓

## 核心原则

### 1. 专家模拟思维 (Best-Minds)
不要问"你怎么看"，而是问"这个问题谁最懂？TA会怎么说？"。

### 2. 文件持久化 (Planning-with-Files)
- task_plan.md - 任务计划
- findings.md - 研究发现
- progress.md - 进度追踪

### 3. TDD 驱动
测试先行 → 失败 → 实现 → 通过

### 4. 注意力管理
每3个动作循环重读 task_plan.md

---

## 状态机

```
IDLE → THINKING → PLANNING → EXECUTING → REVIEWING → COMPLETE
                    ↓           ↓           ↓
                 DEBUGGING ←────────────→
```

---

## 路由逻辑

根据用户输入自动路由到对应模块：

```python
if 包含("谁最懂", "专家", "顶级", "best minds"):
    → 专家模拟模块

elif 包含("计划", "规划", "拆分任务"):
    → 规划模块 + task_plan.md

elif 包含("bug", "错误", "调试", "修复"):
    → 调试模块

elif 包含("审查", "review", "检查spec"):
    → 审查模块

else:
    → 执行模块
```

---

## 模块详解

### 1. 专家模拟模块 (THINKING)

当用户问"你怎么看"时：

1. 这个问题谁最懂？
2. TA 会怎么说？
3. 基于 TA 的公开思想模拟回答
4. 引用来源和原话

**示例：**
```
用户: 你怎么看大语言模型的发展？
回答: 这个问题Andrej Karpathy最懂...
(模拟Andrej的观点)
```

### 2. 规划模块 (PLANNING)

1. **创建文件**
   - task_plan.md
   - findings.md
   - progress.md

2. **任务拆分**
   - 最小粒度: 2-5分钟
   - 每个任务独立可测试
   - 明确文件边界

3. **模板**
```markdown
# [任务名] 实施计划

> 专家视角: [谁最懂这个？TA会怎么说？]

## 目标
> 一句话描述

## 阶段

### Phase 1: [名称]
- [ ] 任务1
- [ ] 任务2

## 进度
- [Phase 1: 0%]

## 注意力提醒
> 每3步重读此文件
```

### 3. 执行模块 (EXECUTING)

**TDD 循环：**
1. 写失败测试
2. 运行确保失败
3. 最小代码实现
4. 运行确保通过
5. 提交

**子任务分发：**
- 独立任务 → 新子agent
- 传递精确上下文
- 两阶段审查

### 4. 审查模块 (REVIEWING)

**规范检查 (OpenSpec 可选)：**

方案A - 使用 OpenSpec:
1. 检查 openspec/changes/<name>/proposal.md
2. 验证实现是否符合 spec
3. 参考 design.md

方案B - 使用 Markdown:
1. 读取 task_plan.md
2. 验证每个任务是否完成
3. 检查是否符合目标

**质量检查：**
- 代码风格
- 潜在bug
- 性能问题
- 测试覆盖

### 5. 调试模块 (DEBUGGING)

**根因分析：**
1. 复现错误
2. 收集上下文
3. 分析因果链
4. 确定根因

**错误保留：**
- 保留错误上下文
- 不立即删除失败尝试

---

## Claude-MEM 集成

**规划前检索：**
```python
memory_search(query=当前任务)
```

**完成后存储：**
```python
memory_store(
    key=任务名,
    value=经验总结,
    namespace=agentic-workflow
)
```

---

## 完整工作流示例

```
用户: 帮我开发一个用户认证系统

1. THINKING: 这个问题谁最懂？(安全专家)
   → 添加专家视角到 task_plan.md

2. PLANNING: 创建计划文件
   → task_plan.md, findings.md, progress.md
   → 拆分任务：登录、注册、JWT

3. EXECUTING: TDD循环
   → 每个任务：测试→失败→实现→通过
   → 复杂任务分发子agent

4. REVIEWING: 规范检查
   → 验证是否符合 spec
   → 代码质量审查

5. COMPLETE: 更新文件状态
   → memory_store 存储经验
```

---

## 与其他 Skills 的关系

| 原 Skill | 融合后角色 |
|---------|-----------|
| best-minds | 专家模拟模块 |
| brainstorming | 被替换 |
| writing-plans | 规划模块 |
| planning-with-files | 文件模板 |
| TDD | 执行模块 |
| systematic-debugging | 调试模块 |
| verification | 审查模块 |
| openspec | 审查模块可选引用 |

---

## 注意事项

1. **单一入口**：这个技能是唯一入口，避免激活多个skill
2. **KV-Cache**：保持prompt稳定，避免频繁刷新
3. **按需加载**：只在需要时加载特定模块
4. **错误保留**：调试时保留错误上下文
