"""deid-latam: Latin American national identifiers for PII detection pipelines.

No de-identification tool on the market covers Latin American national identifiers.
The ones that claim Spanish support cover Spain, where the identifier is the DNI.
A Chilean discharge summary comes out of them with the RUT intact, which is the
primary patient key in every health system in the country.

This package is the missing piece: patterns plus check-digit validators, usable
standalone or plugged into Presidio and OpenMed.

    >>> from deid_latam import find_identifiers
    >>> text = "Paciente Juan Rojas, RUT 15.847.392-5, ingresa por dolor abdominal."
    >>> for span in find_identifiers(text):
    ...     print(span.label, span.text)
    CL_RUT 15.847.392-5

    >>> from deid_latam import redact
    >>> redact(text)
    'Paciente Juan Rojas, RUT [CL_RUT], ingresa por dolor abdominal.'

Note what the second example does not do: it leaves the name untouched. This package
covers identifiers, not names. Pair it with a NER model for the rest, and measure the
result with the benchmark in this repository before trusting it with real documents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Optional

from .patterns import PATTERNS, PENDING, Pattern, patterns_for
from .validators import clean, is_valid_rut, rut_check_digit

__version__ = "0.1.0"
__all__ = [
    "Span",
    "find_identifiers",
    "redact",
    "Pattern",
    "PATTERNS",
    "PENDING",
    "patterns_for",
    "is_valid_rut",
    "rut_check_digit",
    "clean",
]


@dataclass(frozen=True)
class Span:
    """One identifier found in a text."""

    start: int
    end: int
    text: str
    label: str
    country: str
    validated: bool


def find_identifiers(text: str, country: str | None = None) -> list[Span]:
    """Find every national identifier in ``text``.

    Args:
        text: the document, as plain text.
        country: ISO 3166-1 alpha-2 code to restrict the search. None searches all.

    Returns:
        Spans sorted by position. Overlapping matches keep the longest one.
    """
    found: list[Span] = []
    for pattern in patterns_for(country):
        for start, end, value in pattern.finditer(text):
            found.append(
                Span(start, end, value, pattern.label, pattern.country, pattern.validated)
            )

    found.sort(key=lambda s: (s.start, -(s.end - s.start)))
    kept: list[Span] = []
    for span in found:
        if kept and span.start < kept[-1].end:
            continue  # overlaps a longer match already kept
        kept.append(span)
    return kept


def redact(text: str, country: str | None = None, template: str = "[{label}]") -> str:
    """Replace every identifier with ``template``, formatted with the label.

    The replacement is not reversible and no mapping is kept. That makes the output
    pseudonymised, not anonymous: the remaining text can still identify a person by
    combination. See the README section on what this does and does not give you.
    """
    out, last = [], 0
    for span in find_identifiers(text, country):
        out.append(text[last:span.start])
        out.append(template.format(label=span.label, country=span.country))
        last = span.end
    out.append(text[last:])
    return "".join(out)
