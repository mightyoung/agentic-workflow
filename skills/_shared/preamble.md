---
name: preamble
version: 1.1.0
description: |
  标准化 Preamble - 每个 skill 启动时的最小共享约定
  当前版本对齐项目内状态文件，而不是 ~/.gstack 会话目录
---

## Preamble

## 1. Current Storage Model

当前仓库的共享状态默认保存在项目目录，而不是 `~/.gstack/sessions/...`。

标准文件：

- `SESSION-STATE.md`: 当前任务、决策、偏好、上下文进度
- `progress.md`: 阶段进度概览
- `task_plan.md`: 规划阶段生成的任务计划

如果这些文件不存在，应优先使用仓库内现有脚本初始化或创建，而不是假定外部会话系统已经存在。

## 2. Session State

推荐使用项目内状态文件：

```bash
SESSION_STATE_FILE="${PWD}/SESSION-STATE.md"
```

如果需要初始化状态，使用真实脚本：

```bash
bash scripts/init_session.sh .
python3 scripts/memory_ops.py --op=show
```

## 3. Progress Tracking

项目内进度文件约定为：

```bash
TASK_PROGRESS_FILE="${PWD}/progress.md"
```

如果 `progress.md` 不存在，可以手动创建，或从模板目录复制最小模板：

```bash
cp references/templates/progress.md ./progress.md
```

## 4. Planning File

规划阶段的标准计划文件约定为：

```bash
TASK_PLAN_FILE="${PWD}/task_plan.md"
```

创建方式：

```bash
bash scripts/create_plan.sh "任务名称" .
```

## 5. Time Tracking

如果需要记录阶段耗时，使用当前仓库已存在的轻量追踪脚本，而不是假定 phase telemetry API：

```bash
python3 scripts/run_tracker.py --op=start --run-id=R001 --category=PLANNING
python3 scripts/step_recorder.py --op=start --run-id=R001 --phase=PLANNING
python3 scripts/step_recorder.py --op=end --run-id=R001 --phase=PLANNING --output-tokens=300
python3 scripts/run_tracker.py --op=finish --run-id=R001 --status=success
```

## Execution Flow

1. 确认当前工作目录
2. 检查 `SESSION-STATE.md` 是否存在
3. 检查或创建 `progress.md`
4. 如进入规划阶段，检查或创建 `task_plan.md`
5. 如需统计执行情况，调用 `run_tracker.py` / `step_recorder.py`

## Notes

- `~/.gstack` 相关路径目前应视为历史设计或外部集成方向
- 当前仓库中的 phase 文档应优先引用项目内文件
- 不要把未实现的 telemetry、session daemon 或 preload 检查写成既有能力
