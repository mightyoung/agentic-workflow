"""
TestStringUtils - 字符串处理工具测试套件
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import unittest
from string_utils import string_reverse, string_compress, string_permutation


class TestStringReverse(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(string_reverse("hello"), "olleh")

    def test_empty(self):
        with self.assertRaises(ValueError):
            string_reverse("")

    def test_single_char(self):
        self.assertEqual(string_reverse("a"), "a")

    def test_palindrome(self):
        self.assertEqual(string_reverse("radar"), "radar")

    def test_unicode(self):
        self.assertEqual(string_reverse("中文"), "文中")

    def test_mixed(self):
        self.assertEqual(string_reverse("abc123"), "321cba")


class TestStringCompress(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(string_compress("aaabbb"), "a3b3")

    def test_single_run(self):
        self.assertEqual(string_compress("aaaaa"), "a5")

    def test_no_compression(self):
        self.assertEqual(string_compress("abc"), "abc")

    def test_empty(self):
        self.assertEqual(string_compress(""), "")

    def test_single_char(self):
        self.assertEqual(string_compress("a"), "a")

    def test_alternating(self):
        self.assertEqual(string_compress("ababab"), "ababab")

    def test_equal_length(self):
        # a2b2 == "aabb" (4 chars), not shorter
        self.assertEqual(string_compress("aabb"), "aabb")

    def test_complex(self):
        self.assertEqual(string_compress("aaabbbcc"), "a3b3c2")


class TestStringPermutation(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(set(string_permutation("ab")), {"ab", "ba"})

    def test_three_chars(self):
        result = string_permutation("abc")
        self.assertEqual(len(result), 6)

    def test_empty(self):
        self.assertEqual(string_permutation(""), [])

    def test_single_char(self):
        self.assertEqual(string_permutation("a"), ["a"])

    def test_duplicates(self):
        result = string_permutation("aba")
        self.assertEqual(len(result), 3)

    def test_all_same(self):
        result = string_permutation("aaa")
        self.assertEqual(len(result), 1)

    def test_returns_list_of_strings(self):
        result = string_permutation("xyz")
        self.assertIsInstance(result, list)
        for item in result:
            self.assertIsInstance(item, str)

    def test_correct_count_four_chars(self):
        result = string_permutation("abcd")
        self.assertEqual(len(result), 24)  # 4!


if __name__ == "__main__":
    unittest.main()
