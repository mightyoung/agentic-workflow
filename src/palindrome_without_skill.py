"""
Simple palindrome checker - direct implementation without workflow.
"""

def is_palindrome(s):
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s == s[::-1]


def is_palindrome_case_insensitive(s):
    if not isinstance(s, str):
        raise TypeError("Input must be a string")
    return s.lower() == s[::-1].lower()
