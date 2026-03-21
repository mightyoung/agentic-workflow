---
name: preamble
version: 1.0.0
description: |
  标准化 Preamble - 每个 skill 启动时必须运行
  包含更新检查、会话追踪、任务进度和时间戳记录
---

## Preamble (v1.0)

### 1. 更新检查
> 调用 gstack-update-check 检查是否有新版本

```bash
# 检查 skill 更新
npx @claude-flow/cli@latest skills check-update --skill agentic-workflow
```

### 2. 会话追踪
> 维护 ~/.gstack/sessions/ 目录下的会话状态

```bash
# 会话状态文件路径
SESSION_STATE_FILE="${HOME}/.gstack/sessions/${SESSION_ID:-default}/state.md"

# 确保会话目录存在
mkdir -p "$(dirname "$SESSION_STATE_FILE")"
```

**SESSION-STATE.md 格式：**
```markdown
# Session State

## 元数据
- session_id: {SESSION_ID}
- started_at: {TIMESTAMP}
- last_active: {TIMESTAMP}

## 贡献者模式
- contributor_mode: {true|false}
- gstack_contributor: {配置值}

## 主动建议
- proactive_mode: {true|false}
```

### 3. 任务进度
> 读取或初始化任务进度追踪

```bash
TASK_PROGRESS_FILE="${HOME}/.gstack/sessions/${SESSION_ID:-default}/progress.md"

# 读取当前进度（如果存在）
if [ -f "$TASK_PROGRESS_FILE" ]; then
  source "$TASK_PROGRESS_FILE"
else
  # 初始化进度
  CURRENT_PHASE="initialization"
  PHASE_START_TIME=$(date +%s)
  TOTAL_PHASES=8
fi
```

**进度状态：**
- `initialization` - 初始化
- `router` - 路由选择
- `research` - 研究阶段
- `thinking` - 思考阶段
- `planning` - 规划阶段
- `executing` - 执行阶段
- `reviewing` - 审查阶段
- `debugging` - 调试阶段
- `complete` - 完成阶段

### 4. 时间戳记录
> 记录各阶段进入时间，用于性能分析

```bash
FUNCTION timestamp_record() {
  local phase="$1"
  local elapsed_ms=$(($(date +%s%N) / 1000000 - PHASE_START_MS))
  echo "[$(date +%H:%M:%S)] $phase: ${elapsed_ms}ms"
  PHASE_START_MS=$(date +%s%N | cut -b1-13)
}
```

**时间戳格式：** `HH:MM:SS PHASE: duration`

### 循环引用检测

```
# Phase 依赖图（有向无环图）
declare -A PHASE_DEPS=(
    [ROUTER]="OFFICE-HOURS RESEARCH THINKING PLANNING EXECUTING REVIEWING DEBUGGING COMPLETE"
    [OFFICE-HOURS]="THINKING PLANNING"
    [RESEARCH]="THINKING PLANNING"
    [THINKING]="PLANNING"
    [PLANNING]="EXECUTING"
    [EXECUTING]="REVIEWING"
    [REVIEWING]="DEBUGGING COMPLETE"
    [DEBUGGING]="REVIEWING"
    [COMPLETE]=""
)

# 检测循环依赖
detect_cycle() {
    local phase=$1
    local visited=()
    local stack=()

    function dfs {
        local current=$1
        if [[ " ${stack[@]} " =~ " ${current} " ]]; then
            echo "ERROR: Circular dependency detected: ${stack[@]} -> ${current}"
            return 1
        fi
        if [[ " ${visited[@]} " =~ " ${current} " ]]; then
            return 0
        fi

        stack+=($current)
        for dep in ${PHASE_DEPS[$current]}; do
            dfs $dep || return 1
        done
        stack=(${stack[@]/$current})
        visited+=($current)
        return 0
    }

    dfs $phase
}
```

**Phase 依赖规则**:
- ROUTER 可转向任何阶段
- REVIEWING 可转向 DEBUGGING 或 COMPLETE
- 其他阶段只能转向后续阶段（不允许回退）

---

## 执行流程

1. **进入 skill 时** → 执行更新检查
2. **更新会话状态** → 记录 last_active
3. **检查/创建进度** → 确定当前阶段
4. **记录阶段时间戳** → 进入新阶段

## 配置检查

| 配置项 | 来源 | 默认值 |
|--------|------|--------|
| `gstack_contributor` | 环境变量 | false |
| `telemetry_consent` | 会话状态 | null（已禁用）|
| `proactive_mode` | 环境变量 | false |
| `update_check` | 环境变量 | true |
