"""
Palindrome checker tests for WITHOUT Skill version.
"""

import pytest
from src.palindrome_without_skill import is_palindrome, is_palindrome_case_insensitive


def test_simple_palindrome():
    assert is_palindrome("racecar") is True


def test_non_palindrome():
    assert is_palindrome("hello") is False


def test_empty_string():
    assert is_palindrome("") is True


def test_single_char():
    assert is_palindrome("a") is True


def test_chinese_palindrome():
    assert is_palindrome("上海自来水来自海上") is True


def test_case_sensitive():
    assert is_palindrome("Racecar") is False


def test_case_insensitive():
    assert is_palindrome_case_insensitive("RaceCar") is True


def test_none_input():
    with pytest.raises(TypeError):
        is_palindrome(None)


def test_non_string_input():
    with pytest.raises(TypeError):
        is_palindrome(123)
