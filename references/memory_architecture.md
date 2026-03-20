# 记忆系统架构 (v4.11)

> 借鉴 proactive-agent 的 WAL 协议 + 三层记忆架构
> 本地文件实现，无需外部插件依赖

---

## v4.11 新增功能

| 功能 | 描述 | 脚本 |
|------|------|------|
| **断路器** | 检测循环停滞，3次失败后触发决策点 | `task_tracker.py` |
| **空闲检测** | 识别会话空闲状态，支持自动恢复 | `memory_ops.py` |
| **结果追踪** | JSONL格式记录任务执行历史 | `memory_ops.py` |
| **中断点恢复** | 支持从断点继续任务执行 | `memory_ops.py` |
| **周报/月报** | 生成任务统计和分析报告 | `memory_longterm.py` |

---

## 核心原则

> **Chat history is a BUFFER, not storage.**
> SESSION-STATE.md is your "RAM" — the ONLY place specific details are safe.

---

## 三层记忆架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: SESSION-STATE.md (工作内存)                        │
│  - 当前任务的所有细节                                        │
│  - 每条消息都更新关键信息                                    │
│  - 会话结束时提炼到 Layer 2                                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: memory/YYYY-MM-DD.md (每日日志)                   │
│  - 会话期间的所有活动记录                                    │
│  - 每日一个文件，可追溯历史                                  │
│  - 定期从中提炼到 Layer 3                                    │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: MEMORY.md (长期智慧)                              │
│  - 策划的长期经验和知识                                      │
│  - 从每日日志提炼的核心要点                                  │
│  - 持久化，可跨会话使用                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## WAL 协议 (Write-Ahead Logging)

### 触发条件 — 每条消息扫描

| 类型 | 示例 | 处理 |
|------|------|------|
| 修正信息 | "是X，不是Y" / "其实..." / "不，我意思是..." | 立即更新SESSION-STATE |
| 专有名词 | 人名、地名、公司名、产品名 | 记录到SESSION-STATE |
| 偏好 | "我喜欢X" / "不喜欢Y方式" | 记录到USER.md |
| 决策 | "用X方案" / "选择Y" / "用Z技术" | 记录SESSION-STATE+decision |
| 草稿修改 | 正在修改的文件内容 | 记录差异 |
| 具体数值 | 数字、日期、ID、URL | 记录精确值 |

### WAL 执行流程

```
每条用户消息
    ↓
扫描所有触发条件
    ↓
有匹配？
    ├── 否 → 直接响应
    └── 是 → STOP，不开始写响应
              ↓
         WRITE → 更新 SESSION-STATE.md
              ↓
         THEN → 响应用户
```

---

## SESSION-STATE.md 结构

```markdown
# Session State

> 最后更新: YYYY-MM-DD HH:mm

## 当前任务
- 任务描述: ...
- 阶段: THINKING / PLANNING / EXECUTING / REVIEWING
- 开始时间: ...

## 任务细节
- 用户目标: ...
- 约束条件: ...
- 技术栈: ...

## 关键信息 (从WAL协议收集)
### 修正记录
- [时间] 原始理解 → 正确理解

### 专有名词
- term: definition

### 用户偏好
- 风格偏好: ...
- 技术偏好: ...

### 决策记录
- [时间] 决策: ...

### 具体数值
- 日期: ...
- ID: ...
- URL: ...

## 上下文进度
- 已完成步骤: ...
- 当前步骤: ...
- 下一步: ...
```

---

## Working Buffer 协议

### 上下文生存机制

```markdown
## At 60% context (危险区)
- CLEAR 旧缓冲区，开始新鲜
- 60%之后的每条消息：同时附加用户的原始消息和你响应的摘要
- 上下文截断后：首先读取缓冲区，提取重要上下文
```

### 危险区协议

```markdown
当检测到上下文 > 60%：
1. 立即保存当前状态到 SESSION-STATE.md
2. 记录所有关键细节
3. 清空非必要上下文
4. 从 SESSION-STATE 恢复关键信息
```

---

## 记忆检索流程

### 任务开始前

```python
# 1. 读取 SESSION-STATE.md (当前任务上下文)
read("SESSION-STATE.md")

# 2. 读取 memory/YYYY-MM-DD.md (今日相关日志)
read("memory/" + today + ".md")

# 3. 检索长期记忆
memory_search(query=当前任务描述, namespace=agentic-workflow)
```

### 任务完成后

```python
# 1. 更新 SESSION-STATE.md 当前进度
update("SESSION-STATE.md", progress=...)

# 2. 记录到每日日志
append("memory/" + today + ".md", summary)

# 3. 如有关键经验，提炼到 MEMORY.md
if 有值得提炼的经验:
    distill_to_MEMORY()
```

---

## 与外部MCP记忆的关系

```
三层本地记忆                    MCP外部记忆
┌──────────────┐              ┌──────────────┐
│ SESSION-STATE│ ←──同步──→  │ agentic-workflow│
│ memory/      │              │ debugging      │
│ MEMORY.md    │              │ architecture  │
└──────────────┘              └──────────────┘
     ↓                              ↓
 本地快速访问              跨项目长期存储
 (本会话)                  (全局复用)
```

**互补策略**：
- 本地三层记忆：快速、细粒度、任务相关
- MCP外部记忆：跨会话、跨项目、全局复用
- 任务开始时同时检索两者

---

## 文件位置约定

```
agentic-workflow/
├── SESSION-STATE.md           # 当前会话工作内存（根目录）
├── MEMORY.md                  # 长期记忆（根目录）
└── memory/
    └── YYYY-MM-DD.md          # 每日日志
```

---

## 最佳实践

1. **WAL优先**：任何修正信息，先写SESSION-STATE再响应
2. **及时提炼**：会话结束时，将SESSION-STATE提炼到MEMORY.md
3. **上下文保护**：进入危险区时，先保存再截断
4. **双向同步**：关键决策同步到MCP外部记忆
5. **定期清理**：每周清理过时的daily memory，保留精华到MEMORY.md

---

## 断路器机制 (v4.10新增)

### 核心思想

循环停滞检测：当同一步骤失败3次时，触发断路器暂停并等待人类决策。

### 脚本支持

```bash
# 记录步骤失败
python scripts/task_tracker.py --op=step-failure --task-id=T001 --step=implement_auth

# 检查断路器状态
python scripts/task_tracker.py --op=circuit-check --task-id=T001 --step=implement_auth

# 重置断路器
python scripts/task_tracker.py --op=circuit-reset --task-id=T001 --step=implement_auth
```

### 断路器触发流程

```
EXECUTING 阶段:
    if step_failed:
        record_step_failure(task_id, step_name)
        if failure_count >= 3:
            → 触发断路器
            → 输出决策卡片:
                ┌─────────────────────────────────────┐
                │ ⚠️ 断路器触发                        │
                │ 任务: T001                          │
                │ 步骤: implement_auth                 │
                │ 失败次数: 3                          │
                │                                     │
                │ [1] 换方案继续                       │
                │ [2] 寻求帮助                         │
                │ [3] 中止任务                         │
                └─────────────────────────────────────┘
```

---

## 空闲检测机制 (v4.11新增)

### 核心思想

检测会话空闲状态，当用户长时间无活动时自动识别并提示恢复方案。

### 脚本支持

```bash
# 检查空闲状态
python scripts/memory_ops.py --op=idle-check --path=SESSION-STATE.md --idle-threshold=30
```

### 返回格式

```json
{
  "is_idle": false,
  "idle_minutes": 0,
  "last_active": "2026-03-20T10:30:00",
  "task_info": {"phase": "EXECUTING", "progress": 70}
}
```

### 空闲恢复流程

```
检测空闲 >= 30分钟:
    → 输出恢复卡片:
        ┌─────────────────────────────────────┐
        │ 💤 会话空闲检测                      │
        │                                     │
        │ 距离最后活动: 45分钟                  │
        │ 最后任务: 用户认证模块开发            │
        │ 进度: 70%                           │
        │                                     │
        │ [1] 继续任务                         │
        │ [2] 查看当前状态                     │
        │ [3] 新建会话                         │
        └─────────────────────────────────────┘
```

---

## 结果追踪 (v4.11新增)

### 核心思想

JSONL格式记录任务执行历史，支持后续分析和报告生成。

### 数据文件

```
.task_history.jsonl   # 任务历史记录（项目根目录）
```

### 记录格式

```json
{"timestamp": "2026-03-20T10:45:00", "task_id": "T001", "status": "success", "duration_seconds": 300, "lessons": ["使用tavily搜索更高效"], "next_actions": ["继续权限模块"]}
```

### 脚本支持

```bash
# 添加任务结果
python scripts/memory_ops.py --op=add-result \
    --task-id=T001 --status=success \
    --duration=300 --lessons="使用tavily搜索更高效" \
    --next-actions="继续权限模块"

# 查看周报
python scripts/memory_longterm.py --op=weekly-report --days=7

# 查看月报
python scripts/memory_longterm.py --op=monthly-report --days=30
```

---

## 中断点恢复 (v4.11新增)

### 核心思想

任务中断时保存断点信息，下次继续时快速恢复上下文。

### SESSION-STATE.md 断点字段

```markdown
## 当前任务
- **任务描述**: 用户认证模块开发
- **阶段**: EXECUTING
- **中断点**: implement_auth
- **进度**: 70
- **开始时间**: 2026-03-20 09:30:00
```

### 脚本支持

```bash
# 更新断点
python scripts/memory_ops.py --op=resume-point --phase=implement_auth --progress=70

# 查看当前状态
python scripts/memory_ops.py --op=show
```

---

## 周报/月报 (v4.11新增)

### 周报内容

```bash
python scripts/memory_longterm.py --op=weekly-report
```

输出:
```
============================================================
任务统计报告 (近7天)
============================================================
生成时间: 2026-03-20 10:50:00

## 总体统计
- 总任务数: 12
- 已完成: 8 (67%)
- 进行中: 3
- 失败: 1

## 任务类型分布
- 功能开发: 6
- Bug修复: 4
- 代码审查: 2

## 平均任务时长
- 平均完成时间: 245秒
- 最快: 45秒
- 最慢: 890秒

## 教训总结
- 搜索应优先使用tavily (出现3次)
- 决策点模式优于自动循环 (出现2次)
```

### 月报内容

```bash
python scripts/memory_longterm.py --op=monthly-report
```

输出包含:
- 趋势分析（与上周/上月对比）
- 模式识别（重复出现的任务类型）
- 效率指标（任务完成率、平均时长）
- 改进建议（基于历史数据）

