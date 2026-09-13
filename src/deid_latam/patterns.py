"""Regex patterns for Latin American personal identifiers.

Each pattern is paired with a validator where one exists. A pattern without a
validator is a candidate generator, not a detector: on its own it will fire on
invoice numbers and internal record ids, so it is marked ``validated=False`` and
should be used with surrounding context.

The goal is not to have many countries. It is to have each country right.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional

from .validators import is_valid_rut

__all__ = ["Pattern", "PATTERNS", "patterns_for"]


@dataclass(frozen=True)
class Pattern:
    """One identifier pattern for one country."""

    country: str            # ISO 3166-1 alpha-2
    label: str              # entity label, e.g. "CL_RUT"
    name: str               # human name, e.g. "RUT / RUN"
    regex: re.Pattern
    validator: Optional[Callable[[str], bool]] = None
    validated: bool = False      # True when a check digit makes the match reliable
    needs_context: bool = False  # True when the shape alone is ambiguous

    def finditer(self, text: str):
        """Yield (start, end, matched_text) for every valid occurrence."""
        text = text or ""
        for m in self.regex.finditer(text):
            value = m.group(0)
            if self.validator is not None and not self.validator(value):
                continue
            if self.needs_context:
                antes = text[max(0, m.start() - VENTANA_CONTEXTO):m.start()]
                if not _CONTEXTO.search(antes):
                    continue
            yield m.start(), m.end(), value


# --------------------------------------------------------------------------- Chile
# Covers every spelling seen in clinical documents, in two tiers on purpose:
#   15.847.392-5   15847392-5   15.847.392-k   158473925
#
# Tier 1, self-evident: the value carries thousand separators or a hyphen before the
# check digit. Nothing else in a clinical document looks like that, so a valid check
# digit is enough.
_RUT_SEPARADO = re.compile(
    r"(?<![0-9kK.\-])"
    r"(?:\d{1,2}(?:\.\d{3}){2}|\d{7,8})"
    r"\s*-\s*[0-9kK]"
    r"(?![0-9kK])"
)
# Tier 2, ambiguous: 8 or 9 bare digits. One in eleven random numbers passes modulus 11,
# so an order number or a concatenated date validates by chance. These only count when a
# context word sits right before them.
_RUT_PEGADO = re.compile(r"(?<![0-9kK.\-])\d{7,8}[0-9kK](?![0-9kK\-])")
_CONTEXTO = re.compile(
    r"(?:\bRUT\b|\bRUN\b|\bR\.?U\.?T\.?|c[eé]dula(?:\s+de\s+identidad)?|"
    r"carn[eé]\s+de\s+identidad|\bC\.?I\.?)\s*[:\-n°#]*\s*$",
    re.IGNORECASE,
)
VENTANA_CONTEXTO = 40   # characters looked at before a bare number

PATTERNS: list[Pattern] = [
    Pattern(
        country="CL",
        label="CL_RUT",
        name="RUT / RUN (con separador)",
        regex=_RUT_SEPARADO,
        validator=is_valid_rut,
        validated=True,
    ),
    Pattern(
        country="CL",
        label="CL_RUT",
        name="RUT / RUN (sin separador, requiere contexto)",
        regex=_RUT_PEGADO,
        validator=is_valid_rut,
        validated=True,
        needs_context=True,
    ),
]

# Countries still missing. Each one needs its pattern, its check-digit validator and
# test vectors before it lands here. See CONTRIBUTING.md, there is one open issue
# per country.
PENDING = {
    "AR": "DNI, CUIL / CUIT",
    "BR": "CPF, CNPJ",
    "CO": "cedula de ciudadania, NIT",
    "EC": "cedula",
    "MX": "CURP, RFC",
    "PE": "DNI, RUC",
    "UY": "cedula de identidad",
}


def patterns_for(country: str | None = None) -> list[Pattern]:
    """Patterns for one country, or all of them when ``country`` is None."""
    if country is None:
        return list(PATTERNS)
    code = country.strip().upper()
    return [p for p in PATTERNS if p.country == code]
