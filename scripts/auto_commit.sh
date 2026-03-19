#!/bin/bash
# auto_commit.sh - 自动提交更改到 git
# 用法: bash scripts/auto_commit.sh [文件路径] "提交消息"

FILE="${1:-.}"
MESSAGE="${2:-自动提交}"
STAGED=0

# 检查是否是 git 仓库
if ! git -C . rev-parse &> /dev/null; then
    echo "错误: 不是 git 仓库"
    exit 1
fi

# 添加文件
if [ "$FILE" = "." ]; then
    git add -A
    STAGED=1
elif [ -f "$FILE" ]; then
    git add "$FILE"
    STAGED=1
elif [ -d "$FILE" ]; then
    git add "$FILE"
    STAGED=1
fi

# 检查是否有更改
if [ $STAGED -eq 1 ]; then
    if git diff --cached --quiet; then
        echo "没有需要提交的内容"
        exit 0
    fi
fi

# 提交
git commit -m "$MESSAGE"

echo "已提交: $MESSAGE"

# 显示状态
git status --short
