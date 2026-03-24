#!/usr/bin/env python3
"""
Experience Store - 经验存储

存储和查询执行经验：
- task_category: 任务类别
- reasoning_trace: 推理轨迹
- rewards: 奖励数据
- success_rate: 成功率

用法:
    python experience_store.py --op=add --category=DEBUGGING --success=1 --steps=10
    python experience_store.py --op=query --category=DEBUGGING
    python experience_store.py --op=stats
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List
from pathlib import Path

# 默认经验文件
DEFAULT_EXPERIENCE_FILE = ".experience_store.json"

# 任务类别
TASK_CATEGORIES = [
    "CODE_GENERATION",
    "CODE_REVIEW",
    "DEBUGGING",
    "REFACTORING",
    "DOCUMENTATION",
    "DATA_ANALYSIS",
    "RESEARCH",
    "PLANNING",
    "GENERAL"
]


def _validate_path(path: str) -> bool:
    """验证路径安全（防止路径遍历攻击）"""
    try:
        real_path = os.path.realpath(path)
        if os.path.isabs(path):
            return True
        cwd = os.getcwd()
        return real_path.startswith(cwd)
    except OSError:
        return False


def load_store(path: str = DEFAULT_EXPERIENCE_FILE) -> Dict:
    """加载经验存储"""
    if not _validate_path(path):
        return {"experiences": [], "version": "1.0"}
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"experiences": [], "version": "1.0"}


def save_store(path: str, data: Dict) -> None:
    """保存经验存储"""
    if not _validate_path(path):
        return
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_experience(
    task_category: str,
    success: bool,
    steps: int,
    tokens: int,
    duration_ms: int,
    error_count: int = 0,
    reward_total: float = 0.0,
    description: str = "",
    path: str = DEFAULT_EXPERIENCE_FILE
) -> bool:
    """添加经验记录"""
    store = load_store(path)

    experience = {
        "id": f"exp_{len(store['experiences']) + 1:04d}",
        "task_category": task_category,
        "success": success,
        "steps": steps,
        "tokens": tokens,
        "duration_ms": duration_ms,
        "error_count": error_count,
        "reward_total": reward_total,
        "description": description,
        "created_at": datetime.now().isoformat()
    }

    store["experiences"].append(experience)
    save_store(path, store)

    print(f"添加经验: {experience['id']} [{task_category}] "
          f"reward={reward_total:.2f} success={success}")
    return True


def query_experiences(
    category: Optional[str] = None,
    min_reward: Optional[float] = None,
    limit: int = 10,
    path: str = DEFAULT_EXPERIENCE_FILE
) -> List[Dict]:
    """查询经验"""
    store = load_store(path)

    results = store.get("experiences", [])

    # 按类别过滤
    if category:
        results = [e for e in results if e.get("task_category") == category]

    # 按最小奖励过滤
    if min_reward is not None:
        results = [e for e in results if e.get("reward_total", 0) >= min_reward]

    # 按创建时间倒序
    results = sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)

    # 限制数量
    return results[:limit]


def get_category_stats(path: str = DEFAULT_EXPERIENCE_FILE) -> Dict:
    """获取各类别的统计"""
    store = load_store(path)

    stats = {}
    for cat in TASK_CATEGORIES:
        cat_experiences = [e for e in store.get("experiences", [])
                          if e.get("task_category") == cat]

        if not cat_experiences:
            continue

        total = len(cat_experiences)
        success = len([e for e in cat_experiences if e.get("success")])
        avg_steps = sum(e.get("steps", 0) for e in cat_experiences) / total
        avg_tokens = sum(e.get("tokens", 0) for e in cat_experiences) / total
        avg_reward = sum(e.get("reward_total", 0) for e in cat_experiences) / total

        stats[cat] = {
            "count": total,
            "success_rate": success / total if total > 0 else 0,
            "avg_steps": round(avg_steps, 1),
            "avg_tokens": round(avg_tokens, 0),
            "avg_reward": round(avg_reward, 4)
        }

    return stats


def get_overall_stats(path: str = DEFAULT_EXPERIENCE_FILE) -> Dict:
    """获取总体统计"""
    store = load_store(path)

    experiences = store.get("experiences", [])
    total = len(experiences)

    if total == 0:
        return {
            "total_experiences": 0,
            "categories": 0
        }

    success = len([e for e in experiences if e.get("success")])
    total_steps = sum(e.get("steps", 0) for e in experiences)
    total_tokens = sum(e.get("tokens", 0) for e in experiences)
    total_reward = sum(e.get("reward_total", 0) for e in experiences)

    return {
        "total_experiences": total,
        "success_rate": round(success / total, 4),
        "avg_steps": round(total_steps / total, 1),
        "avg_tokens": round(total_tokens / total, 0),
        "avg_reward": round(total_reward / total, 4),
        "categories": len(set(e.get("task_category") for e in experiences))
    }


def main():
    parser = argparse.ArgumentParser(description='Experience Store - 经验存储')
    parser.add_argument('--path', default=DEFAULT_EXPERIENCE_FILE, help='存储文件路径')
    parser.add_argument('--op', choices=['add', 'query', 'stats', 'category-stats'],
                       required=True, help='操作类型')
    parser.add_argument('--category', help='任务类别')
    parser.add_argument('--success', type=lambda x: x.lower() == 'true' or x == '1',
                       help='是否成功')
    parser.add_argument('--steps', type=int, help='步数')
    parser.add_argument('--tokens', type=int, help='Token 数量')
    parser.add_argument('--duration-ms', type=int, dest='duration_ms', help='耗时(ms)')
    parser.add_argument('--errors', type=int, default=0, help='错误数量')
    parser.add_argument('--reward', type=float, dest='reward', default=0.0, help='奖励值')
    parser.add_argument('--desc', help='描述')
    parser.add_argument('--min-reward', type=float, dest='min_reward', help='最小奖励')
    parser.add_argument('--limit', type=int, default=10, help='返回数量')

    args = parser.parse_args()

    if args.op == 'add':
        if not all([args.category, args.success is not None,
                    args.steps, args.tokens, args.duration_ms is not None]):
            print("错误: --category, --success, --steps, --tokens, --duration-ms 必须指定")
            return 1
        add_experience(
            task_category=args.category,
            success=args.success,
            steps=args.steps,
            tokens=args.tokens,
            duration_ms=args.duration_ms,
            error_count=args.errors,
            reward_total=args.reward,
            description=args.desc or "",
            path=args.path
        )

    elif args.op == 'query':
        experiences = query_experiences(
            category=args.category,
            min_reward=args.min_reward,
            limit=args.limit,
            path=args.path
        )
        print(f"找到 {len(experiences)} 条经验:")
        for exp in experiences:
            print(f"  [{exp['id']}] {exp['task_category']} "
                  f"success={exp['success']} reward={exp.get('reward_total', 0):.2f} "
                  f"steps={exp['steps']}")

    elif args.op == 'stats':
        stats = get_overall_stats(args.path)
        print("\n总体统计:")
        print(json.dumps(stats, ensure_ascii=False, indent=2))

        print("\n各类别统计:")
        cat_stats = get_category_stats(args.path)
        print(json.dumps(cat_stats, ensure_ascii=False, indent=2))

    elif args.op == 'category-stats':
        cat_stats = get_category_stats(args.path)
        print(json.dumps(cat_stats, ensure_ascii=False, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
