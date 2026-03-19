#!/bin/bash
# watch_progress.sh - 监控进度文件变化
# 用法: bash scripts/watch_progress.sh [文件路径] [间隔秒数]

FILE="${1:-progress.md}"
INTERVAL="${2:-5}"

CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

if ! command -v inotifywait &> /dev/null && ! command -v fswatch &> /dev/null; then
    echo "警告: 未安装 inotifywait 或 fswatch，使用轮询模式"
    POLL_MODE=1
else
    POLL_MODE=0
fi

echo -e "${CYAN}监控进度: $FILE${NC}"
echo "间隔: ${INTERVAL}秒"
echo "按 Ctrl+C 退出"
echo ""

LAST_MD5=""

get_progress() {
    if [ -f "$FILE" ]; then
        # 提取完成的任务数量
        completed=$(grep -c "^\- \[x\]" "$FILE" 2>/dev/null || echo "0")
        total=$(grep -c "^\- \[" "$FILE" 2>/dev/null || echo "0")
        echo "$completed/$total"
    else
        echo "文件不存在"
    fi
}

show_progress() {
    clear
    echo -e "${CYAN}=== 进度监控 ===${NC}"
    echo "文件: $FILE"
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    echo -e "${YELLOW}当前进度: $(get_progress)${NC}"
    echo ""

    if [ -f "$FILE" ]; then
        echo "最近内容:"
        tail -10 "$FILE" | sed 's/^/  /'
    fi
}

if [ $POLL_MODE -eq 1 ]; then
    # 轮询模式
    while true; do
        show_progress
        sleep "$INTERVAL"
    done
else
    # inotify/fswatch 模式 (macOS/Linux)
    if command -v fswatch &> /dev/null; then
        # macOS
        fswatch -o "$FILE" | while read; do
            show_progress
        done
    else
        # Linux
        inotifywait -m -e modify "$FILE" | while read -r event; do
            show_progress
        done
    fi
fi
