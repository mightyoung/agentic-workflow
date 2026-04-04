"""
Benchmark 测试: 字符串全排列 - WITH Skill 流程 (v5.4)
TDD 驱动实现 + 代码审查
"""

import sys

import pytest


class TestStringPermutation:
    """字符串全排列测试套件"""

    def test_basic_permutation(self):
        """基础测试: 单字符"""
        result = string_permutation("a")
        assert result == ["a"]

    def test_two_chars(self):
        """基础测试: 两字符"""
        result = string_permutation("ab")
        assert set(result) == {"ab", "ba"}
        assert len(result) == 2

    def test_three_chars(self):
        """基础测试: 三字符"""
        result = string_permutation("abc")
        assert len(result) == 6
        assert set(result) == {"abc", "acb", "bac", "bca", "cab", "cba"}

    def test_duplicates_removed(self):
        """边界测试: 去重"""
        result = string_permutation("aba")
        # 3!/2! = 3 种排列
        assert len(result) == 3
        assert set(result) == {"aab", "aba", "baa"}

    def test_empty_string(self):
        """边界测试: 空字符串"""
        result = string_permutation("")
        assert result == []

    def test_single_char(self):
        """边界测试: 单字符"""
        result = string_permutation("x")
        assert result == ["x"]

    def test_result_is_list_of_strings(self):
        """类型测试: 返回类型"""
        result = string_permutation("abc")
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_all_results_same_length(self):
        """正确性测试: 所有排列长度一致"""
        result = string_permutation("abcd")
        n = len("abcd")
        for perm in result:
            assert len(perm) == n

    def test_no_missing_permutations(self):
        """正确性测试: 不遗漏任何排列"""
        result = string_permutation("xyz")
        # 3! = 6
        assert len(result) == 6
        assert set(result) == {"xyz", "xzy", "yxz", "yzx", "zxy", "zyx"}


# ============================================================================
# 实现代码 (将在 RED 阶段后填充)
# ============================================================================

def string_permutation(s: str) -> list[str]:
    """
    计算字符串的全排列。

    使用回溯法(Backtracking)实现：
    - 时间复杂度: O(n! * n)
    - 空间复杂度: O(n!) 用于存储结果

    Args:
        s: 输入字符串

    Returns:
        所有不重复的全排列列表
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
            # 去重: 同一层不使用相同字符
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


if __name__ == "__main__":
    # 运行测试
    exit_code = pytest.main([__file__, "-v"])
    sys.exit(exit_code)
