"""
String Reverse - 字符串反转函数
"""


def string_reverse(s: str) -> str:
    """
    反转输入字符串。

    Args:
        s: 待反转的字符串

    Returns:
        str: 反转后的字符串

    Raises:
        ValueError: 当输入字符串为空时抛出
    """
    if not s:
        raise ValueError("字符串不能为空")
    return s[::-1]


def string_reverse_safe(s: str) -> str:
    """
    反转输入字符串（带验证的安全版本）。

    Args:
        s: 待反转的字符串

    Returns:
        str: 反转后的字符串

    Raises:
        ValueError: 当字符串为空时抛出
    """
    if not s:
        raise ValueError("字符串不能为空")
    return s[::-1]