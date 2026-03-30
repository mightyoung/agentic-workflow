# Scripts 目录 (v4.7更新)

> 可执行的脚本，用于自动化任务执行和环境操作。支持跨平台运行。

## 当前真实运行面

如果你只想知道仓库现在实际能跑什么，先看这几个脚本：

- `router.py`: 轻量关键词路由
- `memory_ops.py`: 维护项目内 `SESSION-STATE.md`
- `task_tracker.py`: 任务状态追踪
- `run_tracker.py`: 执行统计，输出 `.run_tracker.json`
- `step_recorder.py`: phase 记录，输出 `.step_records.json`

说明：
- 文档中提到的更完整 orchestration 能力并不都已在脚本层落地
- 命令示例以本目录脚本的真实 CLI 为准
- 如果环境没有 `python` 命令，请使用 `python3`

## 目录内容

### Python 脚本（跨平台）

| 脚本 | 功能 | 用途 |
|------|------|------|
| `wal_scanner.py` | WAL 触发扫描 | 检测用户消息中的修正/偏好/决策信息 |
| `memory_ops.py` | 记忆操作 | 更新 SESSION-STATE.md |
| `memory_daily.py` | 每日日志 | 管理 memory/YYYY-MM-DD.md |
| `memory_longterm.py` | 长期记忆 | 管理 MEMORY.md |
| `task_tracker.py` | 任务追踪 | 追踪任务进度和状态 |
| `router.py` | 路由决策 | 辅助判断用户意图和触发阶段 |
| `worktree_manager.py` | Git Worktree 管理 | 并行任务进程级隔离 |
| `run_tracker.py` | 执行追踪 | 追踪 steps, tokens, duration |
| `step_recorder.py` | 阶段记录 | 记录每个 phase 执行情况 |
| `reward_calculator.py` | 奖励计算 | 多维度奖励计算 (OpenYoung) |
| `experience_store.py` | 经验存储 | 经验存储与查询 (v5.7.1 增强) |
| `pattern_detector.py` | 模式检测 | 失败模式检测与建议 |

### Bash 脚本（Unix/Linux/macOS）

| 脚本 | 功能 | 用途 |
|------|------|------|
| `init_session.sh` | 初始化会话 | 创建 SESSION-STATE.md |
| `check_template.sh` | 检查模板 | 验证任务计划模板是否存在 |
| `quick_tdd.sh` | 快速 TDD | 执行 TDD 循环 (红-绿-重构) |
| `check_env.sh` | 环境检查 | 检查必需工具和环境变量 |
| `auto_commit.sh` | 自动提交 | 快捷 git 提交 |
| `create_plan.sh` | 创建计划 | 生成任务计划文件 |
| `quick_review.sh` | 快速审查 | 代码审查 (TODO/密码/空文件) |
| `watch_progress.sh` | 监控进度 | 监控 progress.md 变化 |

### Windows 批处理脚本（Windows）

位于 `win/` 子目录：

| 脚本 | 功能 | 用途 |
|------|------|------|
| `init_session.bat` | 初始化会话 | 创建 SESSION-STATE.md |
| `check_template.bat` | 检查模板 | 验证任务计划模板是否存在 |
| `check_env.bat` | 环境检查 | 检查必需工具和环境变量 |
| `create_plan.bat` | 创建计划 | 生成任务计划文件 |
| `quick_review.bat` | 快速审查 | 代码审查 (TODO/密码/空文件) |

### 跨平台脚本调用

Agent 应该自动检测操作系统并选择正确的脚本版本：

```python
import platform
import os

def get_script_path(script_name):
    """获取跨平台脚本路径"""
    system = platform.system().lower()

    if system == "windows" or os.name == "nt":
        # Windows: 使用 .bat 脚本
        base = "scripts/win"
        if script_name.endswith(".py"):
            return f"{base}/../{script_name}"  # Python 跨平台
        return f"{base}/{script_name}.bat"
    else:
        # Unix/Linux/macOS: 使用 .sh 或 .py 脚本
        base = "scripts"
        if script_name.endswith(".py"):
            return f"{base}/{script_name}"
        return f"{base}/{script_name}.sh"
```

## 使用方式

Agent 在需要时通过 Bash 工具调用这些脚本：

```bash
# Python 脚本
python3 scripts/wal_scanner.py "用户消息文本"
python3 scripts/memory_ops.py --op=update --key=task --value="任务描述"
python3 scripts/memory_daily.py --op=create --date=2026-03-20
python3 scripts/memory_daily.py --op=add-task --task-id=T001 --desc="完成任务" --result=success
python3 scripts/memory_daily.py --op=distill  # 从SESSION-STATE蒸馏到每日日志
python3 scripts/memory_longterm.py --op=init
python3 scripts/memory_longterm.py --op=add-experience --exp="学到X"
python3 scripts/memory_longterm.py --op=refine --days=7  # 从7天日志提炼
python3 scripts/memory_longterm.py --op=search --query="关键词"
python3 scripts/task_tracker.py --op=create --task-id=T001 --desc="开发功能X"
python3 scripts/router.py "帮我搜索最佳实践"

# 评估与追踪 (v5.7)
python3 scripts/run_tracker.py --op=start --run-id=R001 --category=DEBUGGING
python3 scripts/run_tracker.py --op=step --run-id=R001 --step=THINKING --tokens=1500
python3 scripts/run_tracker.py --op=finish --run-id=R001 --status=success
python3 scripts/step_recorder.py --op=start --run-id=R001 --phase=EXECUTING --input-tokens=120
python3 scripts/step_recorder.py --op=end --run-id=R001 --phase=EXECUTING --output-tokens=500
python3 scripts/reward_calculator.py --success=1 --steps=15 --tokens=800 --json
python3 scripts/experience_store.py --op=stats
python3 scripts/experience_store.py --op=extract-patterns --category=DEBUGGING
python3 scripts/experience_store.py --op=suggest-skills
python3 scripts/pattern_detector.py --op=detect-failures --json

# Git Worktree 隔离 (v5.7.1)
python3 scripts/worktree_manager.py --op=create --task-id=T001 --branch=feature-x
python3 scripts/worktree_manager.py --op=list
python3 scripts/worktree_manager.py --op=completed --task-id=T001
python3 scripts/worktree_manager.py --op=merge --task-id=T001
python3 scripts/worktree_manager.py --op=cleanup

# Bash 脚本
bash scripts/init_session.sh                    # 初始化会话
bash scripts/check_template.sh                 # 检查模板
bash scripts/check_env.sh                      # 检查环境
bash scripts/quick_tdd.sh "npm test" "npm run build"  # TDD循环
bash scripts/create_plan.sh "新功能开发"        # 创建计划
bash scripts/quick_review.sh src/              # 快速审查
bash scripts/auto_commit.sh . "完成功能X"     # 提交代码
bash scripts/watch_progress.sh progress.md 5   # 监控进度
```

## 依赖

- Python 3.6+
- 无外部依赖（使用标准库）

## 与 SKILL.md 的关系

这些脚本是 SKILL.md 中描述的"可执行机制"的实际实现。

SKILL.md 定义了：
- 工作流程和阶段
- 触发条件和路由逻辑
- 核心原则和铁律

脚本负责：
- 实际的文件操作
- 状态追踪和更新
- 辅助决策计算

## 设计原则

### Python 脚本
1. **无外部依赖** - 只使用 Python 标准库
2. **复杂逻辑** - 处理数据结构和模式匹配
3. **结构化输出** - JSON 格式便于解析

### Bash 脚本
1. **快速执行** - 文件操作、管道组合
2. **确定性** - 相同输入产生相同输出
3. **Unix 哲学** - 单一职责，可组合

### 选择指南

| 场景 | 推荐 |
|------|------|
| 文件存在检查 | Bash/Windows (`test -f` / `if exist`) |
| 正则表达式匹配 | Python (`re`) |
| Git 操作 | Bash (`git add/commit`) |
| 复杂数据处理 | Python (`json`, `dict`) |
| 模板创建 | Bash/Windows (`cat <<EOF` / `echo`) |
| 进度追踪 | Python（跨平台） |
| 跨平台兼容 | Python（始终优先） |

### 跨平台支持

| 脚本类型 | Windows | macOS | Linux | 优先级 |
|-----------|---------|--------|-------|--------|
| Python (.py) | ✅ | ✅ | ✅ | 高 |
| Bash (.sh) | ❌* | ✅ | ✅ | 中 |
| Batch (.bat) | ✅ | ❌ | ❌ | 低 |

*在 Git Bash 或 WSL 环境下可运行

详见：`win/README.md`
