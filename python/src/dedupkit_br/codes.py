"""Product codes (EAN/GTIN, SKU) as stores really fill them in."""

from __future__ import annotations

PLACEHOLDERS = frozenset({"SEMGTIN", "SEMEAN", "NULL", "NONE", "NA", "N/A", "#N/A", "---", "-", "0", "1000000000000"})


def _ascii_digits(s: str) -> bool:
    return bool(s) and all("0" <= ch <= "9" for ch in s)


def clean_code(value: str) -> str:
    """ASCII letters in upper case, spaces, dashes and dots removed: ``" 789-1234 "`` → ``"7891234"``."""
    out = []
    for ch in value or "":
        if ch in " \t\r\n-.":
            continue
        out.append(chr(ord(ch) - 32) if "a" <= ch <= "z" else ch)
    return "".join(out)


def is_valid_gtin(code: str) -> bool:
    """GTIN-8, -12, -13 or -14 with a correct check digit."""
    c = clean_code(code)
    if len(c) not in (8, 12, 13, 14) or not _ascii_digits(c):
        return False
    digits = [ord(ch) - 48 for ch in c]
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits[:-1])))
    return (10 - total % 10) % 10 == digits[-1]


def is_placeholder(code: str) -> bool:
    """Values that stores type when they have no code: "SEM GTIN", "0", all zeros, "N/A",
    and numbers mangled by spreadsheets ("7.89E+12")."""
    c = clean_code(code)
    if not c:
        return True
    if c in PLACEHOLDERS or set(c) == {"0"}:
        return True
    return "E+" in c or "+" in c


def code_class(code: str) -> str:
    """``"long"``, ``"short"``, ``"placeholder"`` or ``"invalid"``.

    Long codes (GTINs, long SKUs) are specific enough to match on their own. Short codes
    (internal SKUs like ``"4521"``) are reused by many brands and only count together with
    the brand. A numeric code is long when it has 7 or more digits and at least 6 of them
    remain after leading zeros are removed.
    """
    c = clean_code(code)
    if is_placeholder(c):
        return "placeholder"
    if _ascii_digits(c):
        significant = len(c.lstrip("0"))
        if len(c) >= 7:
            return "long" if significant >= 6 else "short"
        return "short" if len(c) >= 4 else "invalid"
    if len(c) >= 5:
        return "long"
    return "short" if len(c) >= 3 else "invalid"
