#!/bin/bash
# init_session.sh - 初始化会话状态
# 用法: bash scripts/init_session.sh [项目路径]

set -e

PROJECT_DIR="${1:-.}"

# 创建会话状态目录
mkdir -p "$PROJECT_DIR"

# 检查是否已存在 SESSION-STATE.md
if [ -f "$PROJECT_DIR/SESSION-STATE.md" ]; then
    echo "SESSION-STATE.md 已存在"
    echo "如需重新初始化，请先删除现有文件"
    exit 0
fi

# 获取当前时间
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 创建 SESSION-STATE.md
cat > "$PROJECT_DIR/SESSION-STATE.md" << EOF
# SESSION-STATE.md

> 自动生成的工作内存文件 - $(date '+%Y-%m-%d')

## 当前任务
- **任务描述**: (未设置)
- **阶段**: IDLE
- **开始时间**: $TIMESTAMP
- **优先级**: P2

## 关键信息 (WAL协议收集)

### 修正记录
| 时间 | 原始理解 | 正确理解 |
|------|----------|----------|

### 用户偏好
- **风格偏好**:
- **技术偏好**:

### 决策记录
| 时间 | 决策内容 | 理由 |
|------|----------|------|

### 具体数值
| 类型 | 值 |
|------|---|

## 上下文进度

### 已完成步骤
- [ ]

### 当前步骤
-

### 遇到的问题
| 问题 | 尝试次数 | 解决方案 |
|------|----------|----------|
EOF

echo "已初始化: $PROJECT_DIR/SESSION-STATE.md"
