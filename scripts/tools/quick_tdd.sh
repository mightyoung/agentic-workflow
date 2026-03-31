#!/bin/bash
# quick_tdd.sh - 快速执行 TDD 循环
# 用法: bash scripts/quick_tdd.sh [测试命令] [实现命令]

TEST_CMD="${1:-echo 'No test command provided'}"
IMPL_CMD="${2:-echo 'No implementation command provided'}"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== TDD 循环 ===${NC}"
echo ""

# Step 1: 写测试 (RED)
echo -e "${YELLOW}1. 写测试 (RED)${NC}"
echo "命令: $TEST_CMD"
echo ""

# Step 2: 运行测试
echo -e "${YELLOW}2. 运行测试${NC}"
eval "$TEST_CMD"
TEST_RESULT=$?
echo ""

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${RED}测试通过！需要先让测试失败${NC}"
    exit 1
fi

echo -e "${GREEN}测试失败 ✓ (预期行为)${NC}"
echo ""

# Step 3: 实现 (GREEN)
echo -e "${YELLOW}3. 实现 (GREEN)${NC}"
echo "命令: $IMPL_CMD"
eval "$IMPL_CMD"
IMPL_RESULT=$?
echo ""

if [ $IMPL_RESULT -ne 0 ]; then
    echo -e "${RED}实现失败${NC}"
    exit 1
fi

echo -e "${GREEN}实现完成 ✓${NC}"
echo ""

# Step 4: 再运行测试
echo -e "${YELLOW}4. 运行测试验证${NC}"
eval "$TEST_CMD"
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}测试通过 ✓${NC}"
    echo -e "${CYAN}=== TDD 循环完成 ===${NC}"
    exit 0
else
    echo -e "${RED}测试失败 ✗${NC}"
    exit 1
fi
