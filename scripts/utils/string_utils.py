"""
String Utilities - 字符串处理工具
包含: 反转、压缩、全排列
"""



def string_reverse(s: str) -> str:
    """字符串反转 - O(n) 时间复杂度"""
    if not s:
        raise ValueError("Empty string not allowed")
    return s[::-1]


def string_compress(s: str) -> str:
    """
    字符串压缩 - aaabbb → a3b3
    如果压缩后不比原字符串短，返回原字符串
    """
    if not s:
        return s

    result = []
    count = 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            count += 1
        else:
            result.append(s[i - 1])
            result.append(str(count))
            count = 1
    # 处理最后一组
    result.append(s[-1])
    result.append(str(count))

    compressed = "".join(result)
    return compressed if len(compressed) < len(s) else s


def string_permutation(s: str) -> list[str]:
    """
    字符串全排列 - 使用回溯法
    时间复杂度: O(n! * n)
    """
    if not s:
        return []
    chars = list(s)
    n = len(chars)
    result = []
    used = [False] * n

    def backtrack(path: list[str]):
        if len(path) == n:
            result.append("".join(path))
            return
        seen = set()
        for i in range(n):
            if used[i]:
                continue
            if chars[i] in seen:
                continue
            seen.add(chars[i])
            used[i] = True
            path.append(chars[i])
            backtrack(path)
            path.pop()
            used[i] = False

    backtrack([])
    return result
