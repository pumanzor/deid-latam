"""OpenMed integration: the model finds the names, this finds the identifiers.

OpenMed ships clinical PII models for Spanish, and on the benchmark in this repository
they redact every email and every date. They also redact 5.8% of the RUTs, which is
the number that makes a Chilean document unpublishable no matter how good the rest of
the pipeline is. This module runs both over the same text and merges the result.

    from deid_latam.integrations.openmed import redact

    redact(text, model_name="OpenMed/OpenMed-PII-Spanish-SuperClinical-Small-44M-v1")

Why a merge and not OpenMed's own ``custom_recognizer`` hook: that hook takes deny-list
regexes, and a regex cannot run a check digit. Feeding it the bare RUT pattern would
redact one in eleven order numbers in the file. The validation has to happen in Python,
so the spans are computed here and merged afterwards.

Offsets are what gets merged, never text. OpenMed's masked output has different offsets
from the input, so the identifiers are located on the original text, combined there, and
the redaction is applied once at the end.

OpenMed is not a dependency of this package. Install it with::

    pip install "deid-latam[openmed]"
"""
from __future__ import annotations

from typing import Iterable

from .. import Span, find_identifiers

__all__ = ["find_all", "redact", "merge", "spans_from_openmed", "MODELS"]

# The two Spanish clinical models measured in benchmark/. The 434M one is slower and,
# on this set, slightly worse. Check the README table before paying for the inference.
MODELS = {
    "small": "OpenMed/OpenMed-PII-Spanish-SuperClinical-Small-44M-v1",
    "large": "OpenMed/OpenMed-PII-Spanish-SuperClinical-Large-434M-v1",
}
DEFAULT_MODEL = MODELS["small"]


def spans_from_openmed(result) -> list[Span]:
    """Convert a ``DeidentificationResult`` into ``Span`` objects.

    Model spans carry ``validated=False`` and an empty country: they come from a
    confidence score, not from a check digit, and the model does not say which country
    an entity belongs to.
    """
    text = getattr(result, "original_text", "") or ""
    out = []
    for entity in getattr(result, "pii_entities", None) or []:
        start, end = getattr(entity, "start", None), getattr(entity, "end", None)
        if start is None or end is None or end <= start:
            continue
        out.append(
            Span(
                start=start,
                end=end,
                text=text[start:end],
                label=str(getattr(entity, "label", "PII")),
                country="",
                validated=False,
            )
        )
    return out


def merge(*groups: Iterable[Span]) -> list[Span]:
    """Combine several groups of spans into one non-overlapping list.

    Overlapping spans are merged into the union of their ranges, not resolved in favour
    of one of them. A model span that covers half a RUT and a validated span that covers
    all of it must come out as one redaction over the whole thing; keeping the shorter
    one would leave digits on the page.

    The label of a merged span comes from the validated member when there is one, since
    a check digit says what the value is and a confidence score only says that it looked
    like something.
    """
    spans = sorted(
        (s for group in groups for s in group),
        key=lambda s: (s.start, -(s.end - s.start)),
    )
    merged: list[Span] = []
    for span in spans:
        if merged and span.start < merged[-1].end:
            previous = merged[-1]
            if span.end <= previous.end and span.label == previous.label:
                continue  # wholly contained, adds nothing
            winner = previous if previous.validated or not span.validated else span
            merged[-1] = Span(
                start=previous.start,
                end=max(previous.end, span.end),
                text="",  # rebuilt below, the union may cross both source texts
                label=winner.label,
                country=winner.country,
                validated=previous.validated or span.validated,
            )
        else:
            merged.append(span)
    return merged


def find_all(
    text: str,
    model_name: str = DEFAULT_MODEL,
    lang: str = "es",
    confidence_threshold: float = 0.7,
    country: str | None = None,
    **kwargs,
) -> list[Span]:
    """Run OpenMed and deid-latam over ``text`` and return the merged spans.

    Extra keyword arguments go straight to ``openmed.deidentify``.

    Note on ``lang``: OpenMed 2.3.0 accepts ``lang="es"`` for the model but its sentence
    segmenter stays on English, which is visible in ``result.metadata`` as
    ``sentence_language: "en"``. It is a known limitation of the library, not of the
    model, and it does not affect the spans this function returns.
    """
    import openmed as om

    result = om.deidentify(
        text,
        model_name=model_name,
        lang=lang,
        confidence_threshold=confidence_threshold,
        **kwargs,
    )
    spans = merge(spans_from_openmed(result), find_identifiers(text, country))
    return [
        s if s.text else Span(s.start, s.end, text[s.start:s.end], s.label, s.country, s.validated)
        for s in spans
    ]


def redact(
    text: str,
    model_name: str = DEFAULT_MODEL,
    lang: str = "es",
    confidence_threshold: float = 0.7,
    country: str | None = None,
    template: str = "[{label}]",
    **kwargs,
) -> str:
    """Replace everything both tools found, in one pass over the original text.

    The output is pseudonymised, not anonymous, and on the benchmark in this repository
    it still leaks a patient name in every document. Measure before trusting it.
    """
    spans = find_all(
        text,
        model_name=model_name,
        lang=lang,
        confidence_threshold=confidence_threshold,
        country=country,
        **kwargs,
    )
    out, last = [], 0
    for span in spans:
        out.append(text[last:span.start])
        out.append(template.format(label=span.label, country=span.country))
        last = span.end
    out.append(text[last:])
    return "".join(out)
