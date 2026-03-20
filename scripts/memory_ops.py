#!/usr/bin/env python3
"""
Memory Operations - 记忆操作工具

提供 SESSION-STATE.md 的自动化操作：
- 更新当前任务
- 添加修正记录
- 添加偏好
- 添加决策
- 添加具体数值

用法:
    python memory_ops.py --op=update --key=task --value="任务描述"
    python memory_ops.py --op=add --type=correction --from="错误理解" --to="正确理解"
    python memory_ops.py --op=get --key=preferences
"""

import argparse
import os
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# 默认 SESSION-STATE 路径
DEFAULT_SESSION_STATE = "SESSION-STATE.md"


def ensure_session_state_exists(path: str = DEFAULT_SESSION_STATE) -> bool:
    """确保 SESSION-STATE.md 存在"""
    if not os.path.exists(path):
        # 确保父目录存在
        parent_dir = os.path.dirname(path)
        if parent_dir and not os.path.exists(parent_dir):
            return False
        # 创建默认模板
        default_content = f"""# SESSION-STATE.md

> 自动生成的工作内存文件

## 当前任务
- **任务描述**: (未设置)
- **阶段**: IDLE
- **开始时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
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
"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(default_content)
        return True
    return False


def update_task_info(path: str, task: str, phase: str = "PLANNING") -> bool:
    """更新任务信息"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新任务描述
    pattern = r'(\*\*任务描述\*\*: )(.*)(\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\1{task}\\3', content)
    else:
        content = re.sub(r'(\*\*任务描述\*\*: )', f'\\1{task}', content)

    # 更新阶段
    pattern = r'(\*\*阶段\*\*: )(.*)(\n)'
    content = re.sub(pattern, f'\\1{phase}\\3', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def add_correction(path: str, original: str, corrected: str) -> bool:
    """添加修正记录"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = f"| {timestamp} | {original} | {corrected} |\n"

    # 在表格末尾添加新行
    # 找到最后一个 | 结尾的行
    pattern = r'(\| .+ \| .+ \| .+ \|\n)(### )'
    if re.search(pattern, content):
        content = re.sub(pattern, f'{new_row}\\2', content)
    else:
        # 如果表格为空或格式不对，追加
        content += new_row

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def add_preference(path: str, preference_type: str, value: str) -> bool:
    """添加用户偏好"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if preference_type == 'style':
        new_pref = f"- **{preference_type}偏好**: {value}"
    else:
        new_pref = f"- **{preference_type}偏好**: {value}"

    # 查找对应偏好的行并更新
    escaped_type = re.escape(preference_type)
    pattern = f'(\\*\\*{escaped_type}偏好\\*\\*: )(.*)(\n)'
    if re.search(pattern, content):
        content = re.sub(pattern, f'\\g<1>{value}\\3', content)
    else:
        # 如果找不到，追加
        content += f"\n{new_pref}\n"

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def add_decision(path: str, decision: str, reason: str = "") -> bool:
    """添加决策记录"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_row = f"| {timestamp} | {decision} | {reason} |\n"

    # 在表格末尾添加新行
    pattern = r'(\| .+ \| .+ \| .+ \|\n)(### )'
    if re.search(pattern, content):
        content = re.sub(pattern, f'{new_row}\\2', content)
    else:
        content += new_row

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def add_value(path: str, value_type: str, value: str) -> bool:
    """添加具体数值"""
    if not ensure_session_state_exists(path) and not os.path.exists(path):
        return False

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_row = f"| {value_type} | {value} |\n"

    # 在表格末尾添加新行
    pattern = r'(\| .+ \| .+ \|\n)$'
    if re.search(pattern, content):
        content = re.sub(pattern, f'{new_row}', content)
    else:
        content += new_row

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def get_info(path: str, key: str) -> Optional[str]:
    """获取特定信息"""
    if not os.path.exists(path):
        return None

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    if key == 'task':
        pattern = r'\*\*任务描述\*\*: (.+)'
        match = re.search(pattern, content)
        return match.group(1) if match else None
    elif key == 'phase':
        pattern = r'\*\*阶段\*\*: (.+)'
        match = re.search(pattern, content)
        return match.group(1) if match else None
    elif key == 'preferences':
        pattern = r'### 用户偏好\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None
    elif key == 'decisions':
        pattern = r'### 决策记录\n(.*?)(?=\n##|\Z)'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1) if match else None

    return None


def show_session_state(path: str = DEFAULT_SESSION_STATE) -> None:
    """显示当前 SESSION-STATE 内容"""
    if not os.path.exists(path):
        print(f"SESSION-STATE.md 不存在: {path}")
        print("使用 --op=init 初始化")
        return

    with open(path, 'r', encoding='utf-8') as f:
        print(f.read())


def main():
    parser = argparse.ArgumentParser(description='Memory Operations - 记忆操作工具')
    parser.add_argument('--path', default=DEFAULT_SESSION_STATE, help='SESSION-STATE 路径')
    parser.add_argument('--op', choices=['update', 'add', 'get', 'show', 'init'], required=True, help='操作类型')
    parser.add_argument('--key', help='更新的键 (task, phase, preferences, decisions)')
    parser.add_argument('--value', help='更新值')
    parser.add_argument('--type', help='添加类型 (correction, preference, decision, value)')
    parser.add_argument('--from', dest='from_val', help='原始值 (用于 correction)')
    parser.add_argument('--to', dest='to_val', help='目标值 (用于 correction)')
    parser.add_argument('--reason', default='', help='决策理由')

    args = parser.parse_args()

    if args.op == 'show':
        show_session_state(args.path)
    elif args.op == 'init':
        ensure_session_state_exists(args.path)
        print(f"已初始化: {args.path}")
    elif args.op == 'update':
        if not args.key or not args.value:
            print("错误: --key 和 --value 必须指定")
            return 1
        if args.key == 'task':
            update_task_info(args.path, args.value)
        elif args.key == 'phase':
            # 特殊处理 phase
            ensure_session_state_exists(args.path)
            with open(args.path, 'r', encoding='utf-8') as f:
                content = f.read()
            pattern = r'(\*\*阶段\*\*: )(.*)(\n)'
            content = re.sub(pattern, f'\\1{args.value}\\3', content)
            with open(args.path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(f"未知key: {args.key}")
            return 1
        print(f"已更新: {args.key} = {args.value}")
    elif args.op == 'add':
        if args.type == 'correction':
            if not args.from_val or not args.to_val:
                print("错误: --from 和 --to 必须指定")
                return 1
            add_correction(args.path, args.from_val, args.to_val)
            print(f"已添加修正: {args.from_val} -> {args.to_val}")
        elif args.type == 'preference':
            if not args.key or not args.value:
                print("错误: --key 和 --value 必须指定")
                return 1
            add_preference(args.path, args.key, args.value)
            print(f"已添加偏好: {args.key} = {args.value}")
        elif args.type == 'decision':
            if not args.value:
                print("错误: --value 必须指定")
                return 1
            add_decision(args.path, args.value, args.reason)
            print(f"已添加决策: {args.value}")
        elif args.type == 'value':
            if not args.key or not args.value:
                print("错误: --key 和 --value 必须指定")
                return 1
            add_value(args.path, args.key, args.value)
            print(f"已添加数值: {args.key} = {args.value}")
        else:
            print(f"未知类型: {args.type}")
            return 1
    elif args.op == 'get':
        if not args.key:
            print("错误: --key 必须指定")
            return 1
        result = get_info(args.path, args.key)
        if result:
            print(result)
        else:
            print(f"未找到: {args.key}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
