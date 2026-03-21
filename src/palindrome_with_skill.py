"""
Palindrome checker - TDD-driven implementation with full review coverage.

遵循 TDD 红-绿-重构循环，每个测试用例对应一个具体需求。
"""

from __future__ import annotations


def is_palindrome(s: str) -> bool:
    """
    判断字符串是否为严格回文串（区分大小写，所有字符参与比较）。

    回文串定义：正向读与反向读完全相同的字符串。

    Args:
        s: 待检测的字符串

    Returns:
        bool: 是回文串返回 True，否则返回 False

    Raises:
        TypeError: 当输入不是字符串类型时抛出

    Examples:
        >>> is_palindrome("racecar")
        True
        >>> is_palindrome("hello")
        False
        >>> is_palindrome("")
        True
        >>> is_palindrome("Racecar")
        False
    """
    if not isinstance(s, str):
        raise TypeError("输入必须是字符串类型")

    # 边界条件：空串和单字符无需比较，默认视为回文
    if len(s) <= 1:
        return True

    # 双指针从两端向中间比较，O(n) 时间复杂度
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            return False
        left += 1
        right -= 1
    return True


def is_palindrome_case_insensitive(s: str) -> bool:
    """
    判断字符串是否为忽略大小写的回文串。

    比较前先将字符串统一转为小写。

    Args:
        s: 待检测的字符串

    Returns:
        bool: 是回文串返回 True，否则返回 False

    Raises:
        TypeError: 当输入不是字符串类型时抛出

    Examples:
        >>> is_palindrome_case_insensitive("RaceCar")
        True
        >>> is_palindrome_case_insensitive("ABBA")
        True
        >>> is_palindrome_case_insensitive("Racecar")
        True
    """
    if not isinstance(s, str):
        raise TypeError("输入必须是字符串类型")

    if len(s) <= 1:
        return True

    left, right = 0, len(s) - 1
    while left < right:
        # 两侧字符同时转小写后比较
        if s[left].lower() != s[right].lower():
            return False
        left += 1
        right -= 1
    return True
