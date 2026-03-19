#!/usr/bin/env python3
"""
WAL Scanner - WAL (Write-Ahead Logging) 触发扫描器

检测用户消息中是否包含需要记忆的信息：
- 修正信息: "是X，不是Y" / "其实..." / "错了"
- 偏好: "我喜欢X" / "不喜欢Y方式"
- 决策: "用X方案" / "选择Y"
- 具体数值: 数字、日期、ID、URL

用法:
    python wal_scanner.py "用户消息文本"
"""

import re
import sys
import json
from typing import List, Dict, Optional

# WAL 触发模式
WAL_PATTERNS = [
    # 修正信息
    (r'(?:不是|其实|错了|不对|更正)', 'correction'),
    # 偏好 - 正面
    (r'(?:我喜欢|我想要|我倾向|我更喜欢)', 'preference_positive'),
    # 偏好 - 负面
    (r'(?:我不喜欢|我不想|我讨厌|不要用)', 'preference_negative'),
    # 决策
    (r'(?:用|选择|决定|采用|确定|敲定)', 'decision'),
    # 专有名词模式 (需要上下文判断)
    (r'(?:叫|名叫|称为|是[A-Z])', 'proper_noun'),
]

# 具体数值模式
VALUE_PATTERNS = [
    (r'\b\d{4}-\d{2}-\d{2}\b', 'date'),  # 日期
    (r'\b\d+\.\d+\.\d+\.\d+\b', 'ip'),  # IP地址
    (r'https?://[^\s]+', 'url'),  # URL
    (r'\b[A-Z0-9]{8,}\b', 'id'),  # 大写字母数字ID
    (r'\$\d+', 'money'),  # 金钱
]


def scan_wal_triggers(text: str) -> Dict[str, List[str]]:
    """
    扫描文本中的WAL触发条件

    Args:
        text: 用户消息文本

    Returns:
        触发结果字典 {trigger_type: [matches]}
    """
    triggers = {}
    text_lower = text.lower()

    # 检查WAL模式
    for pattern, trigger_type in WAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            triggers[trigger_type] = matches

    # 检查具体数值
    value_matches = {}
    for pattern, value_type in VALUE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            value_matches[value_type] = matches

    if value_matches:
        triggers['values'] = value_matches

    return triggers


def should_update_session_state(triggers: Dict) -> bool:
    """
    判断是否需要更新 SESSION-STATE

    Args:
        triggers: scan_wal_triggers 的结果

    Returns:
        True 如果需要更新
    """
    # 有任何触发类型就返回True
    return len(triggers) > 0


def format_output(triggers: Dict, format: str = 'json') -> str:
    """
    格式化输出

    Args:
        triggers: 扫描结果
        format: 输出格式 ('json' | 'text' | 'simple')

    Returns:
        格式化后的字符串
    """
    if format == 'json':
        return json.dumps(triggers, ensure_ascii=False, indent=2)
    elif format == 'simple':
        if not triggers:
            return "NO_TRIGGERS"
        parts = []
        for trigger_type, matches in triggers.items():
            if isinstance(matches, list):
                parts.append(f"{trigger_type}: {', '.join(matches)}")
            else:
                parts.append(f"{trigger_type}: {matches}")
        return "; ".join(parts)
    else:  # text
        if not triggers:
            return "未检测到WAL触发条件"
        lines = ["检测到WAL触发条件:"]
        for trigger_type, matches in triggers.items():
            if isinstance(matches, list):
                lines.append(f"  - {trigger_type}: {matches}")
            else:
                lines.append(f"  - {trigger_type}: {matches}")
        return "\n".join(lines)


def main():
    # 从命令行读取文本
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        # 交互式模式
        print("WAL Scanner - 输入消息进行扫描 (Ctrl+C 退出)")
        print("-" * 50)
        while True:
            try:
                text = input("\n> ")
                if not text.strip():
                    continue

                triggers = scan_wal_triggers(text)
                print(format_output(triggers, 'text'))

                if should_update_session_state(triggers):
                    print("\n>>> 建议更新 SESSION-STATE.md")
            except KeyboardInterrupt:
                print("\n退出")
                break
    return 0


if __name__ == '__main__':
    # 非交互式模式：直接扫描
    if len(sys.argv) > 1:
        text = sys.argv[1]
        triggers = scan_wal_triggers(text)
        needs_update = should_update_session_state(triggers)

        # 输出结果
        print(format_output(triggers, 'simple'))

        # 如果需要更新，输出标记
        if needs_update:
            print("WAL_UPDATE_NEEDED=true")
        else:
            print("WAL_UPDATE_NEEDED=false")

        sys.exit(0)
    else:
        sys.exit(main())
