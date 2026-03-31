#!/usr/bin/env python3
"""
Experience Store - 经验存储

存储和查询执行经验：
- task_category: 任务类别
- reasoning_trace: 推理轨迹
- rewards: 奖励数据
- success_rate: 成功率

v5.7.1 增强：自进化模式
- 从成功经验中提取可复用模式
- 基于历史数据生成技能建议
- 支持轨迹分析

用法:
    python experience_store.py --op=add --category=DEBUGGING --success=1 --steps=10
    python experience_store.py --op=query --category=DEBUGGING
    python experience_store.py --op=stats
    python experience_store.py --op=extract-patterns --category=DEBUGGING
    python experience_store.py --op=suggest-skills
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional, Dict, List

from safe_io import safe_write_json

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
    safe_write_json(path, data)


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


def extract_success_patterns(
    category: Optional[str] = None,
    min_reward: float = 1.0,
    path: str = DEFAULT_EXPERIENCE_FILE
) -> List[Dict]:
    """从成功经验中提取可复用模式

    分析高奖励成功经验，提取共性模式：
    - 典型步骤数范围
    - 典型 token 消耗
    - 成功模式特征
    """
    store = load_store(path)
    experiences = store.get("experiences", [])

    # 过滤成功且高奖励的经验
    filtered = [
        e for e in experiences
        if e.get("success") and e.get("reward_total", 0) >= min_reward
    ]

    if category:
        filtered = [e for e in filtered if e.get("task_category") == category]

    if len(filtered) < 3:
        return []

    # 提取统计特征
    steps_list = [e.get("steps", 0) for e in filtered]
    tokens_list = [e.get("tokens", 0) for e in filtered]

    # 计算中位数和典型范围
    steps_list.sort()
    tokens_list.sort()

    median_steps = steps_list[len(steps_list) // 2]
    median_tokens = tokens_list[len(tokens_list) // 2]

    # 典型范围：25th - 75th percentile
    q1_steps = steps_list[len(steps_list) // 4]
    q3_steps = steps_list[3 * len(steps_list) // 4]
    q1_tokens = tokens_list[len(tokens_list) // 4]
    q3_tokens = tokens_list[3 * len(tokens_list) // 4]

    return [{
        "category": category or "ALL",
        "sample_count": len(filtered),
        "median_steps": median_steps,
        "steps_range": [q1_steps, q3_steps],
        "median_tokens": median_tokens,
        "tokens_range": [q1_tokens, q3_tokens],
        "success_rate": len([e for e in filtered]) / max(1, len(experiences))
    }]


def suggest_skill_improvements(
    category: Optional[str] = None,
    path: str = DEFAULT_EXPERIENCE_FILE
) -> List[Dict]:
    """基于历史数据生成技能改进建议

    分析低效模式，生成改进建议：
    - 效率低于中位数的经验特征
    - 常见错误模式
    - 优化建议
    """
    store = load_store(path)
    experiences = store.get("experiences", [])

    if category:
        experiences = [e for e in experiences if e.get("task_category") == category]

    if len(experiences) < 5:
        return [{"type": "insufficient_data", "message": "数据不足，无法生成建议"}]

    # 计算中位效率
    rewards = [e.get("reward_total", 0) for e in experiences]
    rewards.sort()
    median_reward = rewards[len(rewards) // 2]

    # 找出低效经验
    inefficient = [e for e in experiences if e.get("reward_total", 0) < median_reward]

    suggestions = []

    # 分析低效特征
    if inefficient:
        avg_steps_low = sum(e.get("steps", 0) for e in inefficient) / len(inefficient)
        avg_tokens_low = sum(e.get("tokens", 0) for e in inefficient) / len(inefficient)

        efficient = [e for e in experiences if e.get("reward_total", 0) >= median_reward]
        if efficient:
            avg_steps_high = sum(e.get("steps", 0) for e in efficient) / len(efficient)
            avg_tokens_high = sum(e.get("tokens", 0) for e in efficient) / len(efficient)

            if avg_steps_low > avg_steps_high * 1.2:
                suggestions.append({
                    "type": "step_optimization",
                    "issue": f"低效任务平均步骤数 ({avg_steps_low:.0f}) 高于高效任务 ({avg_steps_high:.0f})",
                    "recommendation": "考虑优化决策流程，减少不必要的步骤"
                })

            if avg_tokens_low > avg_tokens_high * 1.3:
                suggestions.append({
                    "type": "token_optimization",
                    "issue": f"低效任务平均 token ({avg_tokens_low:.0f}) 高于高效任务 ({avg_tokens_high:.0f})",
                    "recommendation": "考虑简化提示词或压缩上下文"
                })

    # 错误模式分析
    error_experiences = [e for e in experiences if e.get("error_count", 0) > 0]
    if error_experiences:
        avg_errors = sum(e.get("error_count", 0) for e in error_experiences) / len(error_experiences)
        suggestions.append({
            "type": "error_reduction",
            "issue": f"有错误的经验平均错误数: {avg_errors:.1f}",
            "recommendation": "加强错误处理和预防机制"
        })

    return suggestions


def analyze_category_improvement(
    category: str,
    path: str = DEFAULT_EXPERIENCE_FILE
) -> Dict:
    """分析特定类别的改进空间

    对比该类别与总体平均，识别改进方向
    """
    store = load_store(path)
    experiences = store.get("experiences", [])

    cat_exp = [e for e in experiences if e.get("task_category") == category]
    other_exp = [e for e in experiences if e.get("task_category") != category]

    if not cat_exp:
        return {"category": category, "status": "no_data"}

    # 计算该类别统计
    cat_reward = sum(e.get("reward_total", 0) for e in cat_exp) / len(cat_exp)
    cat_success = len([e for e in cat_exp if e.get("success")]) / len(cat_exp)

    # 计算其他类别统计
    other_reward = 0.0
    other_success = 0.0
    if other_exp:
        other_reward = sum(e.get("reward_total", 0) for e in other_exp) / len(other_exp)
        other_success = len([e for e in other_exp if e.get("success")]) / len(other_exp)

    return {
        "category": category,
        "sample_count": len(cat_exp),
        "reward": round(cat_reward, 3),
        "success_rate": round(cat_success, 3),
        "vs_average": {
            "reward_diff": round(cat_reward - other_reward, 3) if other_exp else 0,
            "success_diff": round(cat_success - other_success, 3) if other_success else 0
        },
        "status": "improving" if cat_reward >= other_reward else "needs_attention"
    }


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
    parser.add_argument('--op', choices=['add', 'query', 'stats', 'category-stats',
                                          'extract-patterns', 'suggest-skills', 'analyze-category'],
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

    elif args.op == 'extract-patterns':
        patterns = extract_success_patterns(
            category=args.category,
            min_reward=args.min_reward or 1.0,
            path=args.path
        )
        print(f"\n提取到 {len(patterns)} 个成功模式:")
        print(json.dumps(patterns, ensure_ascii=False, indent=2))

    elif args.op == 'suggest-skills':
        suggestions = suggest_skill_improvements(
            category=args.category,
            path=args.path
        )
        print(f"\n生成 {len(suggestions)} 条改进建议:")
        for i, s in enumerate(suggestions, 1):
            print(f"\n{i}. [{s.get('type', 'unknown')}]")
            print(f"   问题: {s.get('issue', 'N/A')}")
            print(f"   建议: {s.get('recommendation', 'N/A')}")

    elif args.op == 'analyze-category':
        if not args.category:
            print("错误: --category 必须指定")
            return 1
        analysis = analyze_category_improvement(args.category, args.path)
        print(f"\n类别分析: {args.category}")
        print(json.dumps(analysis, ensure_ascii=False, indent=2))

    return 0


if __name__ == '__main__':
    sys.exit(main())
