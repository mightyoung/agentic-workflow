"""
Palindrome checker - TDD implementation with agentic-workflow REVIEWING phase.

TDD Red Phase: All tests below are written BEFORE implementation.
"""

import pytest
from src.palindrome_with_skill import is_palindrome, is_palindrome_case_insensitive


# ===== 基本功能测试 (RED - 等待实现) =====

def test_simple_palindrome():
    """基本回文串：正向读和反向读完全相同"""
    assert is_palindrome("racecar") is True


def test_non_palindrome():
    """非回文串：正向读和反向读不同"""
    assert is_palindrome("hello") is False


# ===== 边界条件测试 (RED) =====

def test_empty_string():
    """空串是回文"""
    assert is_palindrome("") is True


def test_single_char():
    """单字符是回文"""
    assert is_palindrome("a") is True
    assert is_palindrome("Z") is True


def test_two_char_same():
    """两字符相同是回文"""
    assert is_palindrome("aa") is True
    assert is_palindrome("bb") is True


def test_two_char_different():
    """两字符不同不是回文"""
    assert is_palindrome("ab") is False
    assert is_palindrome("ba") is False


# ===== 特殊情况测试 (RED) =====

def test_palindrome_with_spaces():
    """带空格的回文串"""
    assert is_palindrome("race car") is False  # 严格模式：空格参与比较


def test_palindrome_with_numbers():
    """带数字的回文串"""
    assert is_palindrome("12321") is True
    assert is_palindrome("12345") is False


def test_palindrome_with_special_chars():
    """带特殊字符"""
    assert is_palindrome("a!a") is True
    assert is_palindrome("a#a") is True


def test_chinese_palindrome():
    """中文回文"""
    assert is_palindrome("上海自来水来自海上") is True


def test_case_sensitive():
    """大小写敏感：严格模式下大小写不同则非回文"""
    assert is_palindrome("Racecar") is False


def test_case_insensitive():
    """大小写不敏感版本"""
    assert is_palindrome_case_insensitive("RaceCar") is True
    assert is_palindrome_case_insensitive("Racecar") is True


# ===== 性能与边界测试 (RED) =====

def test_long_palindrome():
    """长回文串：1000个字符"""
    s = "a" * 500 + "b" + "a" * 500
    assert is_palindrome(s) is True


def test_palindrome_returns_bool():
    """返回值类型检查：必须返回布尔值"""
    result = is_palindrome("abc")
    assert isinstance(result, bool)


def test_palindrome_no_side_effects():
    """无副作用：输入字符串不应被修改"""
    original = "racecar"
    is_palindrome(original)
    assert original == "racecar"


# ===== 负向测试 (RED) =====

def test_none_input():
    """None 输入应抛出 TypeError"""
    with pytest.raises(TypeError):
        is_palindrome(None)


def test_non_string_input():
    """非字符串输入应抛出 TypeError"""
    with pytest.raises(TypeError):
        is_palindrome(123)

    with pytest.raises(TypeError):
        is_palindrome(["a", "b", "a"])

    with pytest.raises(TypeError):
        is_palindrome({"value": "aba"})


def test_palindrome_with_whitespace_only():
    """纯空格字符串"""
    assert is_palindrome("   ") is True  # 纯空格前后相同
