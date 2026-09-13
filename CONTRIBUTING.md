# Contributing

The fastest way to help is to add your country.

## Adding a country

Three things, in this order:

1. **The check-digit validator** in `src/deid_latam/validators.py`, with a docstring that
   names the algorithm.
2. **The pattern** in `src/deid_latam/patterns.py`. If the identifier's shape alone is
   ambiguous (bare digits with no separator), set `needs_context=True` and add the words
   that introduce it in your country.
3. **Test vectors** in `tests/test_<country>.py`: at least five identifiers you know are
   valid, five invalid ones, and one test proving the pattern does not fire on invoice or
   record numbers from real documents in your country.

Without the third one the contribution cannot be merged. A pattern with no test is a
pattern that will silently redact the wrong thing in somebody's hospital.

## Reporting a leak

If you find text where `find_identifiers` misses an identifier, or redacts something it
should not, open an issue with the failing text. Use invented data, never a real person's
identifier. That is the single most useful contribution to this project.

## The benchmark

`benchmark/` is generated, not hand written. To add a document type, add a template to
`PLANTILLAS` in `benchmark/generar.py` using `{{TYPE|role|key}}` markers, and the gold
standard is produced with it. Do not edit files under `benchmark/gold/` by hand.

Never add real clinical documents to this repository, de-identified or not.
