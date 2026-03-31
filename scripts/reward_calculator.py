#!/usr/bin/env python3
"""
Reward Calculator - 多维度奖励计算器

基于 OpenYoung 的多维度 reward 设计：
- task_completion: 任务完成奖励
- efficiency: 基于 step/token 的效率奖励
- quality: 基于评估的质量奖励
- penalty: 错误惩罚

用法:
    python reward_calculator.py --success=1 --steps=15 --max-steps=20 --tokens=800 --max-tokens=1000 --errors=0
"""

import argparse
import json
import sys
from typing import Dict

# 配置
DEFAULT_MAX_STEPS = 20
DEFAULT_MAX_TOKENS = 1000

# 奖励权重
WEIGHTS = {
    "task_completion": 1.0,
    "efficiency": 0.2,
    "quality": 0.3,
    "token_efficiency": 0.1,
    "error_penalty": -0.1
}


def calculate_efficiency_reward(steps: int, max_steps: int = DEFAULT_MAX_STEPS) -> float:
    """计算效率奖励

    公式: 1 - (实际steps / 最大steps)
    范围: 0.0 - 1.0 (steps <= max_steps 时)
    """
    if max_steps <= 0:
        return 0.0
    ratio = steps / max_steps
    return max(0.0, 1.0 - ratio)


def calculate_token_efficiency(tokens: int, max_tokens: int = DEFAULT_MAX_TOKENS) -> float:
    """计算 Token 效率奖励

    公式: 1 - (实际tokens / 最大tokens)
    范围: 0.0 - 1.0
    """
    if max_tokens <= 0:
        return 0.0
    ratio = tokens / max_tokens
    return max(0.0, 1.0 - ratio)


def calculate_error_penalty(error_count: int) -> float:
    """计算错误惩罚

    公式: -0.1 * error_count
    """
    return WEIGHTS["error_penalty"] * error_count


def calculate_reward(
    success: bool,
    steps: int,
    tokens: int,
    max_steps: int = DEFAULT_MAX_STEPS,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    error_count: int = 0,
    quality_score: float = 0.0  # 0.0 - 1.0, from LLM judge
) -> Dict:
    """计算总奖励

    总奖励 = task_completion + efficiency + quality + token_efficiency + penalty

    Returns:
        包含各项奖励和总奖励的字典
    """
    # 1. 任务完成奖励
    task_completion = 1.0 if success else -0.5

    # 2. 效率奖励
    efficiency = calculate_efficiency_reward(steps, max_steps) * WEIGHTS["efficiency"]

    # 3. Token 效率奖励
    token_efficiency = calculate_token_efficiency(tokens, max_tokens) * WEIGHTS["token_efficiency"]

    # 4. 质量奖励
    quality = quality_score * WEIGHTS["quality"]

    # 5. 错误惩罚
    penalty = calculate_error_penalty(error_count)

    # 总奖励
    total = task_completion + efficiency + quality + token_efficiency + penalty

    return {
        "task_completion": task_completion,
        "efficiency": round(efficiency, 4),
        "token_efficiency": round(token_efficiency, 4),
        "quality": round(quality, 4),
        "penalty": round(penalty, 4),
        "total": round(total, 4),
        "details": {
            "success": success,
            "steps": steps,
            "tokens": tokens,
            "max_steps": max_steps,
            "max_tokens": max_tokens,
            "error_count": error_count,
            "quality_score": quality_score
        }
    }


def print_reward_breakdown(reward: Dict) -> None:
    """打印奖励分解"""
    print("\n" + "="*50)
    print("Reward Calculator - 奖励分解")
    print("="*50)
    print(f"任务完成: {'+' if reward['task_completion'] > 0 else ''}{reward['task_completion']:.2f}")
    print(f"效率奖励: {reward['efficiency']:+.4f}")
    print(f"Token效率: {reward['token_efficiency']:+.4f}")
    print(f"质量奖励: {reward['quality']:+.4f}")
    print(f"错误惩罚: {reward['penalty']:+.4f}")
    print("-"*50)
    print(f"总奖励:   {reward['total']:+.4f}")
    print("="*50)

    details = reward.get("details", {})
    if details:
        print("\n详情:")
        print(f"  成功: {details.get('success')}")
        print(f"  Steps: {details.get('steps')} / {details.get('max_steps')}")
        print(f"  Tokens: {details.get('tokens')} / {details.get('max_tokens')}")
        print(f"  Errors: {details.get('error_count')}")
        print(f"  Quality: {details.get('quality_score'):.2f}")


def main():
    parser = argparse.ArgumentParser(description='Reward Calculator - 多维度奖励计算')
    parser.add_argument('--success', type=lambda x: x.lower() == 'true' or x == '1',
                       required=True, help='任务是否成功 (true/false)')
    parser.add_argument('--steps', type=int, required=True, help='实际步数')
    parser.add_argument('--tokens', type=int, required=True, help='Token 数量')
    parser.add_argument('--max-steps', type=int, default=DEFAULT_MAX_STEPS,
                       help=f'最大步数 (默认: {DEFAULT_MAX_STEPS})')
    parser.add_argument('--max-tokens', type=int, default=DEFAULT_MAX_TOKENS,
                       help=f'最大 tokens (默认: {DEFAULT_MAX_TOKENS})')
    parser.add_argument('--errors', type=int, default=0, help='错误数量')
    parser.add_argument('--quality', type=float, default=0.0,
                       help='质量评分 (0.0-1.0, 默认: 0.0)')
    parser.add_argument('--json', action='store_true', help='输出 JSON 格式')

    args = parser.parse_args()

    reward = calculate_reward(
        success=args.success,
        steps=args.steps,
        tokens=args.tokens,
        max_steps=args.max_steps,
        max_tokens=args.max_tokens,
        error_count=args.errors,
        quality_score=args.quality
    )

    if args.json:
        print(json.dumps(reward, ensure_ascii=False, indent=2))
    else:
        print_reward_breakdown(reward)

    return 0


if __name__ == '__main__':
    sys.exit(main())
