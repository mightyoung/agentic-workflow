---
name: preamble
version: 2.0.0
description: |
  标准化 Preamble - 每个 skill 启动时的最小共享约定
  当前版本只引用实际存在的文件
---

## Preamble

## 1. Current Storage Model

仓库的共享状态保存在项目目录的标准文件中：

- `.workflow_state.json` — 唯一真实状态数据源（session_id, task, phase, trigger_type）
- `progress.md` — 阶段进度概览
- `task_plan.md` — 规划阶段生成的任务计划
- `findings.md` — 研究阶段生成的调研结果

## 2. Session State

当前任务的会话状态存储在：

```bash
WORKFLOW_STATE_FILE="${PWD}/.workflow_state.json"
```

读取当前状态：

```bash
python3 scripts/unified_state.py --op validate --workdir .
```

## 3. Progress Tracking

进度文件约定为：

```bash
TASK_PROGRESS_FILE="${PWD}/progress.md"
```

## 4. Planning File

规划阶段的标准计划文件：

```bash
TASK_PLAN_FILE="${PWD}/task_plan.md"
```

## Execution Flow

1. 确认当前工作目录
2. 读取 `.workflow_state.json` 确认当前 phase 和 session
3. 如需进度信息，读取或创建 `progress.md`
4. 如进入规划阶段，读取或创建 `task_plan.md`
5. 完成后调用 `python3 scripts/workflow_engine.py --op advance --phase NEXT`

## Notes

- `~/.gstack` 路径已废弃，不再使用
- `SESSION-STATE.md` 已废弃，使用 `.workflow_state.json`
- 不要引用不存在的脚本或文件
