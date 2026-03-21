---
name: Telemetry
description: 遥测模块 - 记录 skill 使用情况用于本地分析学习
version: 1.0.0
created: 2026-03-21
status: disabled
---

# Telemetry 遥测模块

## 价值和意义

Telemetry 是 agentic-workflow 的重要基础设施，用于：

1. **工作流分析** - 了解 skill 使用模式，识别瓶颈和优化点
2. **质量改进** - 通过阶段耗时数据发现低效环节
3. **学习进化** - 基于实际使用数据持续优化工作流设计
4. **问题诊断** - 记录错误和恢复过程，便于问题排查

## 记录内容

### 阶段事件

```yaml
phases:
  - phase_id: string          # 阶段唯一标识
    phase_name: string        # 阶段名称 (planning, coding, review, etc.)
    event: "enter" | "exit"  # 事件类型
    timestamp: ISO8601        # 事件时间
    duration_ms?: number      # 阶段耗时（exit 事件时）
    metadata?: object         # 阶段特定元数据
```

### 关键决策点

```yaml
decisions:
  - decision_id: string       # 决策唯一标识
    decision_type: string     # 决策类型 (agent_routing, tool_selection, etc.)
    context: string           # 决策上下文摘要
    choice: string           # 最终选择
    alternatives?: string[]    # 考虑的替代方案
    timestamp: ISO8601
```

### 错误和恢复

```yaml
errors:
  - error_id: string
    error_type: string       # 错误分类
    severity: "low" | "medium" | "high" | "critical"
    message: string          # 错误消息（不含敏感信息）
    recovery_action?: string  # 恢复措施
    recovered: boolean       # 是否成功恢复
    timestamp: ISO8601
```

### 性能指标

```yaml
metrics:
  - metric_name: string
    value: number
    unit: string            # ms, count, ratio, etc.
    timestamp: ISO8601
```

## 隐私保护原则

**严格保护以下信息永不记录：**

- 代码内容、文件路径、仓库名
- API 密钥、令牌、凭证
- 用户名、邮箱等个人身份信息
- 具体的业务数据或敏感内容

**允许记录的摘要信息：**

- 阶段名称和类型
- 决策类型和结果
- 耗时统计（数值）
- 错误类型和严重程度
- 操作频率统计

## 禁用机制

### 全局禁用

用户可通过设置环境变量禁用遥测：

```bash
export AGENTIC_TELEMETRY_ENABLED=false
```

### 会话级禁用

在 CLAUDE.md 或项目配置中设置：

```yaml
telemetry:
  enabled: false
```

### 运行时禁用

使用 skill 时传入参数：

```
/agentic-workflow --telemetry=false
```

## 简化实现

由于 agentic-workflow 是本地 skill，数据不发送到远程服务器，采用简化实现：

### 存储位置

遥测数据写入当前会话状态文件：

```
SESSION-STATE.md
```

### 记录格式

使用 YAML 格式的结构化日志，便于解析和分析：

```yaml
telemetry:
  session_id: string
  started_at: ISO8601
  events:
    - type: phase
      phase: planning
      event: enter
      timestamp: ISO8601
    - type: decision
      decision_type: agent_routing
      choice: coder
      timestamp: ISO8601
    - type: error
      error_type: timeout
      severity: medium
      recovered: true
      timestamp: ISO8601
  metrics:
    - name: total_duration_ms
      value: 45230
      unit: ms
  ended_at: ISO8601
```

### 分析工具

后续可使用简单脚本分析 SESSION-STATE.md 中的遥测数据：

```bash
# 统计各阶段耗时
grep -A 20 "telemetry:" SESSION-STATE.md | grep -E "(phase|duration_ms)"

# 分析错误频率
grep "error_type:" SESSION-STATE.md | sort | uniq -c
```

## 实现状态

- [x] 记录内容定义
- [x] 隐私保护原则
- [x] 禁用机制
- [x] 轻量级实现（写入 SESSION-STATE.md）
- [x] 集成到各 skill 阶段
- [x] 分析脚本工具

## 数据结构定义 (YAML)

### 阶段事件 (Phase Events)

```yaml
phase_event:
  type: "phase"
  phase: string                    # 阶段名称: router, research, thinking, planning, executing, reviewing, debugging, complete
  event: "enter" | "exit"          # 事件类型
  timestamp: ISO8601               # 事件时间
  duration_ms?: number             # 阶段耗时（exit 事件时）
  metadata?:                        # 阶段特定元数据
    complexity?: "high" | "medium" | "low"
    route_layer?: "L0" | "L1" | "L2" | "L3"
    issue_count?: number
    severity_distribution?:
      fatal?: number
      serious?: number
      suggestion?: number
```

### 关键决策点 (Decision Points)

```yaml
decision_event:
  type: "decision"
  decision_type: string            # 决策类型: agent_routing, tool_selection, complexity_assessment, vbr_check
  context: string                  # 决策上下文摘要（不含敏感信息）
  choice: string                   # 最终选择
  alternatives?: string[]           # 考虑的替代方案
  timestamp: ISO8601
```

### 错误和恢复 (Errors and Recovery)

```yaml
error_event:
  type: "error"
  error_type: string               # 错误分类: timeout, validation_failed, skill_not_found, execution_error
  severity: "low" | "medium" | "high" | "critical"
  message: string                  # 错误消息 (不含敏感信息)
  recovery_action?: string         # 恢复措施
  recovered: boolean               # 是否成功恢复
  phase?: string                   # 发生错误的阶段
  timestamp: ISO8601
```

### 性能指标 (Performance Metrics)

```yaml
metric:
  name: string                      # 指标名称: task_duration_ms, vbr_pass_rate, issues_found
  value: number                    # 指标值
  unit: string                    # 单位: ms, count, ratio, percent
  phase?: string                  # 关联阶段
  timestamp: ISO8601
```

## SESSION-STATE.md 写入示例

### 遥测数据区块

```yaml
## 遥测数据

### 阶段事件
- [22:30:15] router: enter
- [22:30:16] router → research (L2, reason: "最佳实践搜索")
- [22:30:20] research: enter
- [22:31:05] research: exit (duration: 45000ms)
- [22:31:10] thinking: enter
- [22:32:30] thinking: exit (duration: 80000ms)

### 关键决策
- [22:30:16] agent_routing: research (alternatives: [thinking, planning])
- [22:31:10] complexity_assessment: high (factors: ["3+ 步骤", "多文件", "新技术栈"])

### 错误记录
- [22:45:30] timeout: skill execution timeout (recovered: true, action: "retry")

### 性能指标
- total_duration_ms: 45230
- vbr_pass_rate: 1.0
- issues_found: {fatal: 0, serious: 2, suggestion: 5}
```

### 写入函数伪代码

```bash
# 写入遥测事件的函数
telemetry_record() {
  local event_type="$1"
  local phase="$2"
  local event="$3"
  local timestamp=$(date +%H:%M:%S)
  local duration_ms="${4:-}"

  # 检查遥测是否启用
  if [ "$AGENTIC_TELEMETRY_ENABLED" = "false" ]; then
    return 0
  fi

  # 追加到 SESSION-STATE.md
  local telemetry_entry="[$timestamp] $phase: $event"
  if [ -n "$duration_ms" ]; then
    telemetry_entry="$telemetry_entry (duration: ${duration_ms}ms)"
  fi

  # 使用 sed 或 heredoc 追加
  sed -i '' "/## 遥测数据/a\\
### 阶段事件\\
- $telemetry_entry" "$SESSION_STATE_FILE"
}
```

## 轻量级记录格式

在进入/退出每个阶段时，向 SESSION-STATE.md 写入：

```yaml
## 阶段记录
- [22:30:15] router: enter
- [22:30:16] router → research (reason: "最佳实践搜索")
- [22:30:20] research: enter
- [22:31:05] research: exit (duration: 45s)
```
