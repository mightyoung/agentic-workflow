#!/usr/bin/env python3
"""
WAL Scanner - WAL (Write-Ahead Logging) 触发扫描器 (v4.9)

检测用户消息中是否包含需要记忆的信息：
- 修正信息: "是X，不是Y" / "其实..." / "错了"
- 偏好: "我喜欢X" / "不喜欢Y方式"
- 决策: "用X方案" / "选择Y"
- 具体数值: 数字、日期、ID、URL

v4.9 新增: 3x 确认规则
- 同一模式被纠正3次时触发晋升确认
- 自动追踪模式出现次数
- 支持模式晋升到 PATTERNS.md

用法:
    python wal_scanner.py "用户消息文本"
    python wal_scanner.py --check-patterns    # 检查待晋升模式
    python wal_scanner.py --promote PATTERN_KEY  # 晋升指定模式
"""

import re
import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Tuple, Any

from safe_io import safe_write_json

# 默认模式存储文件
DEFAULT_PATTERNS_FILE = ".wal_patterns.json"

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
    (r'\d{4}-\d{2}-\d{2}', 'date'),  # 日期（去掉\b避免中文边界问题）
    (r'\b\d+\.\d+\.\d+\.\d+\b', 'ip'),  # IP地址
    (r'https?://[^\s]+', 'url'),  # URL
    (r'\b[A-Z0-9]{8,}\b', 'id'),  # 大写字母数字ID
    (r'\$\d+', 'money'),  # 金钱
]

# 晋升阈值
PROMOTION_THRESHOLD = 3


def _validate_path(path: str) -> bool:
    """验证路径安全（防止路径遍历攻击）"""
    try:
        # 解析符号链接，获取真实路径
        real_path = os.path.realpath(path)
        # 允许绝对路径（用户明确指定的位置，如临时文件）
        # 只阻止使用 .. 进行遍历的相对路径
        if os.path.isabs(path):
            return True
        # 相对路径：检查解析后是否在当前目录内
        cwd = os.getcwd()
        return real_path.startswith(cwd)
    except OSError:
        return False


def get_pattern_key(trigger_type: str, match: str) -> str:
    """生成稳定的模式键"""
    # 简化并标准化匹配文本作为键的一部分
    normalized = match.lower().strip()[:20]
    # 替换空格和特殊字符
    normalized = re.sub(r'[\s\-]+', '_', normalized)
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    return f"{trigger_type}_{normalized}"


def load_patterns(path: str = DEFAULT_PATTERNS_FILE) -> Dict:
    """加载已存储的模式数据"""
    if not _validate_path(path):
        return {
            "patterns": {},
            "version": "1.0"
        }
    default = {
        "patterns": {},
        "version": "1.0"
    }

    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Validate structure
            if "patterns" not in data:
                data["patterns"] = {}
            return data
        except (json.JSONDecodeError, IOError):
            # Invalid file - return default
            return default
    return default


def save_patterns(patterns: Dict, path: str = DEFAULT_PATTERNS_FILE) -> None:
    """保存模式数据"""
    if not _validate_path(path):
        return
    safe_write_json(path, patterns)


def increment_pattern_count(trigger_type: str, match: str, path: str = DEFAULT_PATTERNS_FILE) -> Tuple[int, bool]:
    """
    增加模式计数

    Returns:
        (count, should_promote): 当前计数和是否应该晋升
    """
    patterns = load_patterns(path)
    pattern_key = get_pattern_key(trigger_type, match)
    now = datetime.now().isoformat()

    if pattern_key not in patterns["patterns"]:
        patterns["patterns"][pattern_key] = {
            "count": 0,
            "first_seen": now,
            "last_seen": now,
            "type": trigger_type,
            "sample": match,
            "promoted": False
        }

    patterns["patterns"][pattern_key]["count"] += 1
    patterns["patterns"][pattern_key]["last_seen"] = now

    should_promote = patterns["patterns"][pattern_key]["count"] >= PROMOTION_THRESHOLD
    patterns["patterns"][pattern_key]["should_promote"] = should_promote

    save_patterns(patterns, path)

    return patterns["patterns"][pattern_key]["count"], should_promote


def get_pending_promotions(path: str = DEFAULT_PATTERNS_FILE) -> List[Dict]:
    """获取待晋升的模式列表"""
    patterns = load_patterns(path)
    pending = []

    for key, data in patterns["patterns"].items():
        if data.get("should_promote") and not data.get("promoted"):
            pending.append({
                "key": key,
                "count": data["count"],
                "type": data["type"],
                "sample": data["sample"],
                "first_seen": data["first_seen"],
                "last_seen": data["last_seen"]
            })

    return pending


def promote_pattern(pattern_key: str, path: str = DEFAULT_PATTERNS_FILE) -> bool:
    """标记模式为已晋升"""
    patterns = load_patterns(path)

    if pattern_key in patterns["patterns"]:
        patterns["patterns"][pattern_key]["promoted"] = True
        patterns["patterns"][pattern_key]["promoted_at"] = datetime.now().isoformat()
        save_patterns(patterns, path)
        return True

    return False


def extract_correction_context(text: str) -> List[Tuple[str, str]]:
    """
    提取修正上下文

    Returns:
        [(trigger_type, match)] 列表
    """
    results = []

    for pattern, trigger_type in WAL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            results.append((trigger_type, match))

    return results


def scan_wal_triggers(text: str) -> Dict[str, Any]:
    """
    扫描文本中的WAL触发条件

    Args:
        text: 用户消息文本

    Returns:
        触发结果字典 {trigger_type: [matches] 或 {values_dict}}
    """
    triggers: Dict[str, Any] = {}

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
    import argparse

    parser = argparse.ArgumentParser(description='WAL Scanner - WAL 触发扫描器 (v4.9)')
    parser.add_argument('text', nargs='?', help='要扫描的文本')
    parser.add_argument('--check-patterns', action='store_true', help='检查待晋升模式')
    parser.add_argument('--promote', metavar='PATTERN_KEY', help='晋升指定模式')
    parser.add_argument('--patterns-file', default=DEFAULT_PATTERNS_FILE, help='模式存储文件路径')

    args = parser.parse_args()

    # 检查待晋升模式
    if args.check_patterns:
        pending = get_pending_promotions(args.patterns_file)
        if not pending:
            print("没有待晋升的模式")
            return 0

        print(f"发现 {len(pending)} 个待晋升模式:")
        print("-" * 60)
        for p in pending:
            print(f"  [{p['key']}]")
            print(f"    类型: {p['type']}")
            print(f"    次数: {p['count']}x")
            print(f"    示例: {p['sample']}")
            print(f"    首次: {p['first_seen']}")
            print(f"    最近: {p['last_seen']}")
            print()
        print("使用 --promote PATTERN_KEY 来晋升模式")
        return 0

    # 晋升模式
    if args.promote:
        if promote_pattern(args.promote, args.patterns_file):
            print(f"模式已晋升: {args.promote}")
        else:
            print(f"模式未找到: {args.promote}")
        return 0

    # 扫描文本
    if args.text:
        triggers = scan_wal_triggers(args.text)
        needs_update = should_update_session_state(triggers)

        # 输出结果
        print(format_output(triggers, 'simple'))

        # 如果检测到触发，增加模式计数并检查晋升
        if needs_update:
            print("WAL_UPDATE_NEEDED=true")

            # 更新模式计数
            corrections = extract_correction_context(args.text)
            for trigger_type, match in corrections:
                count, should_promote = increment_pattern_count(trigger_type, match, args.patterns_file)
                if should_promote:
                    pattern_key = get_pattern_key(trigger_type, match)
                    print(f"\n⚠️  模式 '{pattern_key}' 已达到 {PROMOTION_THRESHOLD} 次纠正")
                    print("    使用 --check-patterns 查看详情")
                    print("    使用 --promote {pattern_key} 晋升该模式")
        else:
            print("WAL_UPDATE_NEEDED=false")

        return 0

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
    sys.exit(main())
