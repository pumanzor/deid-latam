"""Presidio integration: a recognizer that speaks Latin American identifiers.

Microsoft Presidio ships recognizers for the US, the UK, Spain, Italy, Poland,
Singapore, Australia and India. There is no Chilean RUT among them, and the Spanish
pack covers the DNI, which is a different identifier with a different check digit.
This module plugs the gap.

    from presidio_analyzer import AnalyzerEngine
    from deid_latam.integrations.presidio import register

    analyzer = AnalyzerEngine()
    register(analyzer)
    analyzer.analyze(text="RUT 15.847.392-5", language="es")
    # [type: CL_RUT, start: 4, end: 16, score: 1.0]

The recognizer delegates to ``find_identifiers`` instead of handing Presidio a bare
``PatternRecognizer``. That is deliberate. A ``PatternRecognizer`` can carry the regex
but not the check digit, and Presidio's context words only raise a score, they never
require it. Both rules matter here: the check digit is what keeps invoice numbers out
of the results, and the context requirement is what keeps nine bare digits from being
redacted on a one-in-eleven coincidence. Delegating keeps a single implementation, so
the Presidio results and the standalone results are the same results.

Presidio is not a dependency of this package. Install it with::

    pip install "deid-latam[presidio]"
"""
from __future__ import annotations

from typing import Iterable, Optional

from presidio_analyzer import EntityRecognizer, RecognizerResult

from .. import find_identifiers
from ..patterns import PATTERNS, patterns_for

__all__ = ["DeidLatamRecognizer", "register", "supported_entities"]

# A match with a correct check digit is evidence, not a guess, so it takes the top
# score. A pattern still waiting for its validator gets a score that survives the
# default threshold without pretending to be certain.
SCORE_VALIDATED = 1.0
SCORE_UNVALIDATED = 0.6


def supported_entities(country: str | None = None) -> list[str]:
    """Entity labels this recognizer emits, e.g. ``["CL_RUT"]``."""
    return sorted({p.label for p in patterns_for(country)})


class DeidLatamRecognizer(EntityRecognizer):
    """Presidio recognizer for Latin American national identifiers.

    Args:
        country: ISO 3166-1 alpha-2 code to restrict the search. None searches all.
        supported_language: language code to register under. Presidio matches
            recognizers to the requested language, so a recognizer registered for
            "es" is skipped on an English run and vice versa.
        name: recognizer name reported in the results metadata.
    """

    def __init__(
        self,
        country: str | None = None,
        supported_language: str = "es",
        name: str = "DeidLatamRecognizer",
        version: str = "0.1.0",
    ) -> None:
        self.country = country
        entities = supported_entities(country)
        if not entities:
            raise ValueError(f"no patterns for country {country!r}")
        super().__init__(
            supported_entities=entities,
            name=name,
            supported_language=supported_language,
            version=version,
        )

    def load(self) -> None:
        """Nothing to load. No model, no lexicon, no network call."""

    def analyze(
        self,
        text: str,
        entities: Iterable[str],
        nlp_artifacts=None,
    ) -> list[RecognizerResult]:
        """Return one ``RecognizerResult`` per identifier found in ``text``.

        ``nlp_artifacts`` is accepted and ignored: the detection is regex plus check
        digit, so it needs no tokenisation and no language model.
        """
        wanted = set(entities or self.supported_entities)
        results = []
        for span in find_identifiers(text, self.country):
            if span.label not in wanted:
                continue
            results.append(
                RecognizerResult(
                    entity_type=span.label,
                    start=span.start,
                    end=span.end,
                    score=SCORE_VALIDATED if span.validated else SCORE_UNVALIDATED,
                    recognition_metadata={
                        _NAME_KEY: self.name,
                        _ID_KEY: self.id,
                    },
                )
            )
        return results


# Presidio added these metadata keys in 2.2.29 and older releases do not define them.
_NAME_KEY = getattr(RecognizerResult, "RECOGNIZER_NAME_KEY", "recognizer_name")
_ID_KEY = getattr(RecognizerResult, "RECOGNIZER_IDENTIFIER_KEY", "recognizer_identifier")


def register(
    target,
    country: str | None = None,
    languages: Iterable[str] = ("es", "en"),
) -> list[DeidLatamRecognizer]:
    """Add the recognizer to an ``AnalyzerEngine`` or a ``RecognizerRegistry``.

    A Presidio recognizer is bound to one language, so one instance is registered per
    entry in ``languages``. Clinical documents from the region are written in Spanish,
    but the text often reaches the pipeline tagged "en" by a language detector, and an
    identifier missed because of a language tag is still an identifier missed.

    Returns the recognizers that were registered.
    """
    registry = getattr(target, "registry", target)
    if not hasattr(registry, "add_recognizer"):
        raise TypeError(
            "register() takes an AnalyzerEngine or a RecognizerRegistry, "
            f"got {type(target).__name__}"
        )
    added = []
    for language in languages:
        recognizer = DeidLatamRecognizer(country=country, supported_language=language)
        registry.add_recognizer(recognizer)
        added.append(recognizer)
    return added
