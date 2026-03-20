#!/usr/bin/env python3
"""
Long-term Memory Operations - 长期记忆操作工具

管理 MEMORY.md 长期记忆文件：
- 初始化长期记忆
- 添加核心经验
- 添加模式记录
- 搜索记忆
- 从每日日志提炼

用法:
    python memory_longterm.py --op=init
    python memory_longterm.py --op=add-experience --exp="核心经验描述"
    python memory_longterm.py --op=add-pattern --pattern="模式名称" --desc="模式描述"
    python memory_longterm.py --op=search --query="关键词"
    python memory_longterm.py --op=refine --days=7
"""

import argparse
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

# 默认长期记忆文件
DEFAULT_MEMORY_FILE = "MEMORY.md"


def ensure_memory_exists(filepath: str = DEFAULT_MEMORY_FILE) -> bool:
    """确保长期记忆文件存在"""
    if not os.path.exists(filepath):
        template = f"""# MEMORY.md - 长期记忆

> 自动生成的最后手段记忆

## 核心经验
- (从每日日志和工作会话中提炼)

## 模式记录
- (重复出现的模式)

## 项目知识
- (特定项目的关键信息)

## 技术栈
- (使用的技术栈和偏好)

## 偏好设置
- (用户偏好和技术偏好)

---
最后更新: {datetime.now().strftime('%Y-%m-%d')}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(template)
        return True
    return False


def add_experience(experience: str, filepath: str = DEFAULT_MEMORY_FILE) -> bool:
    """添加核心经验"""
    ensure_memory_exists(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 在核心经验章节添加
    new_exp = f"- {experience}\n"

    if "## 核心经验" in content:
        # 检查是否有默认占位符
        if "(从每日日志和工作会话中提炼)" in content:
            content = content.replace("(从每日日志和工作会话中提炼)", new_exp)
        else:
            # 追加到现有经验
            pattern = r'(## 核心经验\n)(.*?)(\n## |\n---)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                content = content.replace(match.group(0), match.group(1) + match.group(2) + new_exp + match.group(3))
    else:
        content += f"\n## 核心经验\n{new_exp}"

    # 更新最后更新时间
    content = re.sub(r'最后更新: .+', f'最后更新: {datetime.now().strftime("%Y-%m-%d")}', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"已添加核心经验: {experience[:50]}...")
    return True


def add_pattern(pattern_name: str, description: str, filepath: str = DEFAULT_MEMORY_FILE) -> bool:
    """添加模式记录"""
    ensure_memory_exists(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_pattern = f"- **{pattern_name}**: {description}\n"

    if "## 模式记录" in content:
        if "(重复出现的模式)" in content:
            content = content.replace("(重复出现的模式)", new_pattern)
        else:
            pattern = r'(## 模式记录\n)(.*?)(\n## |\n---)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                content = content.replace(match.group(0), match.group(1) + match.group(2) + new_pattern + match.group(3))
    else:
        content += f"\n## 模式记录\n{new_pattern}"

    content = re.sub(r'最后更新: .+', f'最后更新: {datetime.now().strftime("%Y-%m-%d")}', content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"已添加模式: {pattern_name}")
    return True


def search_memory(query: str, filepath: str = DEFAULT_MEMORY_FILE) -> List[str]:
    """搜索记忆内容"""
    if not os.path.exists(filepath):
        print(f"长期记忆文件不存在: {filepath}")
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    results = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        if query.lower() in line.lower():
            # 获取上下文
            start = max(0, i - 1)
            end = min(len(lines), i + 2)
            context = '\n'.join(lines[start:end])
            results.append(context)

    return results


def show_memory(filepath: str = DEFAULT_MEMORY_FILE) -> None:
    """显示长期记忆"""
    if not os.path.exists(filepath):
        print(f"长期记忆文件不存在: {filepath}")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        print(f.read())


def refine_from_daily_logs(days: int = 7, memory_dir: str = "memory",
                          output_file: str = DEFAULT_MEMORY_FILE) -> bool:
    """从每日日志提炼到长期记忆"""
    if not os.path.exists(memory_dir):
        print(f"每日日志目录不存在: {memory_dir}")
        return False

    # 收集最近N天的日志
    recent_logs = []
    end_date = datetime.now()

    for i in range(days):
        date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
        log_file = os.path.join(memory_dir, f"{date}.md")
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                recent_logs.append(f.read())

    if not recent_logs:
        print(f"没有找到最近 {days} 天的日志")
        return False

    # 提取教训
    lessons = []
    for log in recent_logs:
        lesson_matches = re.findall(r'## 教训\s*\n(.*?)(?=\n## |\n---|\Z)', log, re.DOTALL)
        for match in lesson_matches:
            lines = match.strip().split('\n')
            for line in lines:
                if line.startswith('- '):
                    lessons.append(line[2:])

    # 添加到长期记忆
    ensure_memory_exists(output_file)
    for lesson in set(lessons):  # 去重
        if lesson:
            add_experience(f"[提炼] {lesson}", output_file)

    print(f"已从 {days} 天的日志中提炼 {len(set(lessons))} 条经验到长期记忆")
    return True


def main():
    parser = argparse.ArgumentParser(description='Long-term Memory Operations - 长期记忆操作工具')
    parser.add_argument('--file', default=DEFAULT_MEMORY_FILE, help='长期记忆文件路径')
    parser.add_argument('--dir', default='memory', help='每日日志目录')
    parser.add_argument('--op', choices=['init', 'add-experience', 'add-pattern', 'search', 'show', 'refine'],
                       required=True, help='操作类型')
    parser.add_argument('--exp', help='核心经验内容')
    parser.add_argument('--pattern', help='模式名称')
    parser.add_argument('--desc', help='模式描述')
    parser.add_argument('--query', help='搜索关键词')
    parser.add_argument('--days', type=int, default=7, help='提炼最近N天的日志')

    args = parser.parse_args()

    if args.op == 'init':
        ensure_memory_exists(args.file)
        print(f"已初始化长期记忆: {args.file}")
    elif args.op == 'add-experience':
        if not args.exp:
            print("错误: --exp 必须指定")
            return 1
        add_experience(args.exp, args.file)
    elif args.op == 'add-pattern':
        if not args.pattern or not args.desc:
            print("错误: --pattern 和 --desc 必须指定")
            return 1
        add_pattern(args.pattern, args.desc, args.file)
    elif args.op == 'search':
        if not args.query:
            print("错误: --query 必须指定")
            return 1
        results = search_memory(args.query, args.file)
        if results:
            print(f"找到 {len(results)} 条匹配:")
            for i, result in enumerate(results, 1):
                print(f"\n--- 结果 {i} ---")
                print(result)
        else:
            print(f"没有找到与 '{args.query}' 相关的记忆")
    elif args.op == 'show':
        show_memory(args.file)
    elif args.op == 'refine':
        refine_from_daily_logs(args.days, args.dir, args.file)

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
