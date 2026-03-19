#!/bin/bash
# create_plan.sh - 创建任务计划文件
# 用法: bash scripts/create_plan.sh [任务名称] [项目路径]

TASK_NAME="${1:-新任务}"
PROJECT_DIR="${2:-.}"

TIMESTAMP=$(date '+%Y-%m-%d')
FILENAME="$PROJECT_DIR/task_plan_${TIMESTAMP}.md"

# 检查是否已存在
if [ -f "$FILENAME" ]; then
    echo "文件已存在: $FILENAME"
    exit 1
fi

# 创建任务计划文件
cat > "$FILENAME" << EOF
# 任务计划: $TASK_NAME

> 创建时间: $(date '+%Y-%m-%d %H:%M:%S')

## 目标
> 一句话描述要完成的任务

## 专家视角
> 这个问题谁最懂？TA会怎么说？

## 任务元数据

| 字段 | 值 |
|------|---|
| 优先级 | P0 / P1 / P2 / P3 |
| 估计时间 | X 分钟 |
| 依赖任务 | [task_id, ...] |
| 可独立测试 | true / false |

## 阶段

### Phase 1: [阶段名]
- [ ] 任务1 (P0, 5min, 依赖-)
- [ ] 任务2 (P1, 10min, 依赖-)

### Phase 2: [阶段名]
- [ ] 任务3 (P0, 15min, 依赖task1)
- [ ] 任务4 (P2, 5min, 依赖task2)

## 进度

| 阶段 | 状态 | 完成度 |
|------|------|--------|
| Phase 1 | 待开始 | 0% |
| Phase 2 | 待开始 | 0% |

## 决策记录

| 决策 | 理由 | VFM评分 | 日期 |
|------|------|---------|------|
| | | | |

## 遇到的问题

| 问题 | 尝试次数 | 解决方案 |
|------|----------|----------|
| | | |

## 自动追踪

| 任务ID | 状态变更 | 时间 | 备注 |
|--------|----------|------|------|
EOF

echo "已创建: $FILENAME"
