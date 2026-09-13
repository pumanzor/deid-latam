# deid-latam

**Latin American national identifiers for PII detection pipelines, plus the benchmark
nobody had written.**

No de-identification tool on the market detects the Chilean RUT. Not the free ones, not
the paid ones. The tools that advertise Spanish support cover Spain, where the national
identifier is the DNI. Run a Chilean discharge summary through any of them and it comes
out with the RUT intact, which is the primary patient key in every health system in the
country, and the document still presents itself as de-identified.

This package fixes the identifier half of that problem, and measures the other half
honestly.

```python
from deid_latam import find_identifiers, redact

text = "Paciente Juan Rojas Miranda, RUT 15.847.392-5, colecistitis aguda."

redact(text)
# 'Paciente Juan Rojas Miranda, RUT [CL_RUT], colecistitis aguda.'
```

Note what that does **not** do: the name is still there. This package covers national
identifiers, not names. For names you need a NER model, and the benchmark below shows
exactly how well the available ones do.

## Install

```bash
pip install deid-latam
```

No model download, no GPU, no network call. It is regular expressions and check digits.

## Coverage

| Country | Identifier | Check digit | Status |
|---|---|---|---|
| 🇨🇱 Chile | RUT / RUN | modulus 11 | **done**, 100% on the benchmark |
| 🇦🇷 Argentina | DNI, CUIL / CUIT | modulus 11 | help wanted |
| 🇧🇷 Brazil | CPF, CNPJ | two digits | help wanted |
| 🇨🇴 Colombia | cédula, NIT | modulus 11 | help wanted |
| 🇪🇨 Ecuador | cédula | modulus 10 | help wanted |
| 🇲🇽 Mexico | CURP, RFC | homoclave | help wanted |
| 🇵🇪 Peru | DNI, RUC | modulus 11 | help wanted |
| 🇺🇾 Uruguay | cédula de identidad | modulus 10 | help wanted |

One open issue per country. A contribution needs three things: the pattern, the
check-digit validator, and test vectors. See [CONTRIBUTING.md](CONTRIBUTING.md).

### Why check digits matter

A bare regex for "eight digits and a letter" fires on invoice numbers, order ids and
concatenated dates. One in eleven random numbers passes modulus 11 by chance, so
validation is what separates a tool you can run over a hospital archive from one that
shreds the documents.

Chilean RUTs are handled in two tiers. When the value carries thousand separators or a
hyphen (`15.847.392-5`, `15847392-5`), a valid check digit is enough. When it is eight
or nine bare digits (`158473925`), the check digit alone is not evidence, so a context
word such as `RUT`, `RUN` or `cédula` must appear right before it. That distinction is
the difference between 100% recall with zero false positives and a tool that redacts
every order number in the file.

## The benchmark

`benchmark/` holds the first public evaluation set for de-identification of Chilean
clinical documents. 32 synthetic documents across 8 real document types, with 428
annotated identifiers.

```bash
python benchmark/generar.py            # regenerate the set, seeded and reproducible
python benchmark/evaluar.py --solo-rut # measure deid-latam alone
```

The gold standard is exact by construction: documents are generated from templates with
markers, so offsets are recorded as values are substituted, with no hand annotation and
no drift.

### Results

Model measured: `OpenMed/OpenMed-PII-Spanish-SuperClinical-Small-44M-v1`, threshold 0.7.
An identifier counts as **complete** only when the whole span is redacted. A name cut in
half counts as a leak, because "Rojas Miranda" still identifies a person.

| Entity | Model alone | Model + deid-latam | Count |
|---|---|---|---|
| NAME | 0.0% | 0.0% | 92 |
| DATE | 100% | 100% | 52 |
| **RUT** | **5.8%** | **100%** | 52 |
| PHONE | 79.5% | 79.5% | 44 |
| CITY | 90.0% | 90.0% | 40 |
| FACILITY | 3.1% | 3.1% | 32 |
| AGE | 0.0% | 0.0% | 24 |
| ADDRESS | 29.2% | 29.2% | 24 |
| RECORD ID | 4.2% | 4.2% | 24 |
| EMAIL | 100% | 100% | 20 |
| **TOTAL** | **36.2%** | **47.7%** | 428 |
| **Documents with a leak** | **32/32** | **32/32** | 32 |

Three things worth reading twice.

**The RUT goes from 5.8% to 100%.** That is what this package does.

**Names sit at 0% complete, and 76% partial.** The model is not blind to names, it
detects a fragment of 76% of them and never covers the whole thing. Spanish
speaking Latin America uses two surnames, and the model tags one token and stops.

**Fixing the RUT saves no document at all.** Both columns leak in 32 of 32, because the
patient name is still exposed. The national identifier is half the problem. The other
half is open, and it needs a model, not a regex. If you want to work on something that
matters, that is the thing.

### Limits of this set

It is synthetic. Every name, RUT, address and facility is invented and no document comes
from a real patient. It measures pattern coverage and model behaviour, not performance on
a hospital's real archive. For that you need a data agreement and an ethics committee.

## Use with Presidio and OpenMed

```python
# Presidio
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern as PPattern
from deid_latam.patterns import patterns_for

# OpenMed
import openmed as om
from deid_latam import find_identifiers
spans = find_identifiers(text)   # merge with om.deidentify(...).pii_entities
```

Both integrations live in `src/deid_latam/integrations/`.

## Pseudonymisation, not anonymisation

`redact()` removes identifiers and keeps no mapping. That is **pseudonymisation**, not
anonymisation, and the distinction is legal, not cosmetic: a pseudonymised document is
still personal data, with every obligation attached. The remaining text can identify a
person by combination, an exact date plus a small town plus an uncommon diagnosis being
the textbook case.

Under Chile's Law 21.719, in full force on 1 December 2026, health data is sensitive
personal data. Do not describe the output of this tool as anonymised in a contract.

## License

Apache 2.0. The benchmark set is released under CC BY 4.0.

## Citation

If you use the benchmark in academic work, cite the repository. If you find a leak this
package misses, open an issue with the failing text; that is the most useful contribution
there is.
