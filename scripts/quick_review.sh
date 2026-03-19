#!/bin/bash
# quick_review.sh - 快速代码审查
# 用法: bash scripts/quick_review.sh [文件路径或目录]

TARGET="${1:-.}"

CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}=== 快速代码审查 ===${NC}"
echo "目标: $TARGET"
echo ""

# 统计信息
echo -e "${YELLOW}文件统计:${NC}"
if [ -d "$TARGET" ]; then
    echo "  文件数: $(find "$TARGET" -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.java" \) | wc -l | tr -d ' ')"
    echo "  代码行数: $(find "$TARGET" -type f \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.java" \) -exec cat {} \; | wc -l | tr -d ' ')"
elif [ -f "$TARGET" ]; then
    echo "  文件: $TARGET"
    echo "  行数: $(cat "$TARGET" | wc -l | tr -d ' ')"
fi
echo ""

# 检查常见问题
echo -e "${YELLOW}检查常见问题:${NC}"

# TODO/FIXME
todos=$(grep -r "TODO\|FIXME\|XXX" "$TARGET" 2>/dev/null | grep -v ".git" | head -5 || true)
if [ -n "$todos" ]; then
    echo "  ⚠ 发现 TODO/FIXME:"
    echo "$todos" | head -3 | sed 's/^/    /'
else
    echo "  ✓ 无 TODO/FIXME"
fi

# 硬编码密码
secrets=$(grep -rE "(password|api_key|secret|token)\s*=\s*['\"][^'\"]{8,}['\"]" "$TARGET" 2>/dev/null | grep -v ".git" || true)
if [ -n "$secrets" ]; then
    echo "  ⚠ 发现疑似硬编码凭据"
else
    echo "  ✓ 无硬编码凭据"
fi

# 空文件
empty=$(find "$TARGET" -type f -empty 2>/dev/null | grep -v ".git" | head -5 || true)
if [ -n "$empty" ]; then
    echo "  ⚠ 发现空文件:"
    echo "$empty" | sed 's/^/    /'
else
    echo "  ✓ 无空文件"
fi

echo ""
echo -e "${CYAN}=== 审查完成 ===${NC}"
