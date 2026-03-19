#!/bin/bash
# check_template.sh - 检查任务计划模板是否存在
# 用法: bash scripts/check_template.sh [项目路径]

PROJECT_DIR="${1:-.}"

TEMPLATES=(
    "references/templates/task_plan.md"
    "references/templates/findings.md"
    "references/templates/progress.md"
)

check_file() {
    local file="$1"
    if [ -f "$PROJECT_DIR/$file" ]; then
        echo "✓ $file"
        return 0
    else
        echo "✗ $file (缺失)"
        return 1
    fi
}

echo "检查项目模板..."
echo "项目目录: $PROJECT_DIR"
echo ""

missing=0
for template in "${TEMPLATES[@]}"; do
    check_file "$template" || ((missing++))
done

echo ""
if [ $missing -eq 0 ]; then
    echo "所有模板文件完整 ✓"
    exit 0
else
    echo "缺少 $missing 个模板文件"
    exit 1
fi
