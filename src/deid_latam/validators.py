"""Check-digit validators for Latin American national identifiers.

Every function takes the identifier as written by a human, in any of the formats
people actually use, and returns True only if the check digit is correct.

Why this matters for PII detection: a bare regex for "8 digits and a letter" fires on
invoice numbers, internal record ids and phone numbers. Validating the check digit
turns a noisy pattern into a precise one, which is the difference between a tool you
can run over a hospital's archive and one that destroys the documents.

Implemented and covered by tests:
    Chile      RUT / RUN           modulus 11

Patterns without check-digit validation live in ``patterns.py`` and are marked
experimental. Contributions for other countries are welcome, see CONTRIBUTING.md.
"""
from __future__ import annotations

import re

__all__ = ["clean", "rut_check_digit", "is_valid_rut"]

_NON_ALNUM = re.compile(r"[^0-9A-Za-z]")


def clean(value: str) -> str:
    """Strip dots, hyphens, spaces and any other separator."""
    return _NON_ALNUM.sub("", value or "")


# --------------------------------------------------------------------------- Chile
def rut_check_digit(body: int | str) -> str:
    """Return the check digit for a Chilean RUT/RUN body.

    Modulus 11 with the weight series 2,3,4,5,6,7 repeating from the rightmost digit.

    >>> rut_check_digit(15847392)
    '5'
    >>> rut_check_digit("6.635.037")
    '1'
    """
    digits = clean(str(body))
    if not digits.isdigit():
        raise ValueError(f"RUT body must be digits, got {body!r}")

    total, weight = 0, 2
    for digit in reversed(digits):
        total += int(digit) * weight
        weight = 2 if weight == 7 else weight + 1

    remainder = 11 - (total % 11)
    if remainder == 11:
        return "0"
    if remainder == 10:
        return "K"
    return str(remainder)


def is_valid_rut(value: str) -> bool:
    """True if ``value`` is a well formed RUT with a correct check digit.

    Accepts every format seen in the wild: with or without thousand separators,
    with or without the hyphen, upper or lower case K.

    >>> is_valid_rut("15.847.392-5")
    True
    >>> is_valid_rut("15847392-5")
    True
    >>> is_valid_rut("158473925")
    True
    >>> is_valid_rut("15.847.392-K")
    False
    """
    raw = clean(value)
    if len(raw) < 2:
        return False
    body, given = raw[:-1], raw[-1].upper()
    if not body.isdigit() or not (given.isdigit() or given == "K"):
        return False
    # A RUT body below 1.000.000 is possible but vanishingly rare in living people;
    # allowing it here would fire on 4 digit invoice numbers.
    if len(body) < 7:
        return False
    return rut_check_digit(body) == given
