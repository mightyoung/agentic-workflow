#!/bin/bash
# check_env.sh - 检查运行环境
# 用法: bash scripts/check_env.sh

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}=== 环境检查 ===${NC}"
echo ""

# 检查工具是否存在
check_tool() {
    local tool="$1"
    local package="${2:-$tool}"

    if command -v "$tool" &> /dev/null; then
        version=$(command -v "$tool" && $tool --version 2>&1 | head -1 || echo "")
        echo -e "✓ $tool: $version"
        return 0
    else
        echo -e "✗ $tool: 未安装 (需要安装 $package)"
        return 1
    fi
}

# 基础工具
echo "基础工具:"
check_tool "git"
check_tool "python3"
check_tool "node"
echo ""

# 可选工具
echo "可选工具:"
check_tool "gh" "GitHub CLI"
check_tool "cargo" "Rust"
check_tool "go"
echo ""

# 环境变量
echo "环境变量:"
[ -n "$TAVILY_API_KEY" ] && echo "✓ TAVILY_API_KEY 已设置" || echo "✗ TAVILY_API_KEY 未设置"
[ -n "$OPENAI_API_KEY" ] && echo "✓ OPENAI_API_KEY 已设置" || echo "✗ OPENAI_API_KEY 未设置"
echo ""

# Claude Code 检查
if command -v "claude" &> /dev/null; then
    claude_version=$(claude --version 2>&1 | head -1 || echo "未知")
    echo -e "${GREEN}✓ Claude Code: $claude_version${NC}"
else
    echo -e "${RED}✗ Claude Code: 未安装${NC}"
fi

echo ""
echo -e "${CYAN}=== 检查完成 ===${NC}"
