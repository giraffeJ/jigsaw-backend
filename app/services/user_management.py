"""
User management helpers

Contains utility functions related to Users that are useful across the codebase,
kept separate to improve maintainability and testability.

Current exports:
- normalize_workplace(s: str) -> str
"""

from typing import Optional


def normalize_workplace(s: Optional[str]) -> str:
    """
    Normalize workplace/company strings for comparison.

    - Lowercases input
    - Removes common Korean corporate markers and parentheses like "㈜", "(주)", "주식회사" etc.
    - Removes any character that is not alphanumeric or whitespace
    - Collapses multiple spaces
    - Returns empty string for falsy inputs
    """
    if not s:
        return ""
    s2 = s.lower()
    for token in ["㈜", "(주)", "주식회사", "주)", "주(", "주식", "주."]:
        s2 = s2.replace(token, " ")
    s2 = "".join(ch for ch in s2 if ch.isalnum() or ch.isspace())
    s2 = " ".join(s2.split())
    return s2.strip()
