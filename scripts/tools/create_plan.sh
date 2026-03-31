#!/bin/bash
# create_plan.sh - 创建项目内 task_plan.md
# 用法: bash scripts/create_plan.sh [任务名称] [项目路径]

TASK_NAME="${1:-新任务}"
PROJECT_DIR="${2:-.}"
TEMPLATE_FILE="$PROJECT_DIR/references/templates/task_plan.md"
FILENAME="$PROJECT_DIR/task_plan.md"
CREATED_AT=$(date '+%Y-%m-%d %H:%M:%S')

if [ -f "$FILENAME" ]; then
    echo "文件已存在: $FILENAME"
    exit 1
fi

if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "模板不存在: $TEMPLATE_FILE"
    exit 1
fi

sed \
    -e "s/{{TASK_NAME}}/$TASK_NAME/g" \
    -e "s/{{CREATED_AT}}/$CREATED_AT/g" \
    "$TEMPLATE_FILE" > "$FILENAME"

echo "已创建: $FILENAME"
