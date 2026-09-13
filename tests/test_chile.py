"""Tests for Chilean RUT / RUN detection and validation."""
import pytest

from deid_latam import find_identifiers, redact
from deid_latam.validators import is_valid_rut, rut_check_digit

# Check digits computed by hand from the modulus 11 rule, cross-checked against
# four widely published examples.
CHECK_DIGITS = [
    ("12345678", "5"),
    ("11111111", "1"),
    ("22222222", "2"),
    ("15847392", "5"),
    ("6635037", "1"),
]


@pytest.mark.parametrize("body,expected", CHECK_DIGITS)
def test_check_digit(body, expected):
    assert rut_check_digit(body) == expected


@pytest.mark.parametrize("value", [
    "12.345.678-5",     # thousand separators and hyphen
    "12345678-5",       # hyphen only
    "123456785",        # no separators at all
    "15.847.392-5",
    "15847392-5",
])
def test_valid_formats(value):
    assert is_valid_rut(value)


@pytest.mark.parametrize("value", [
    "12.345.678-9",     # wrong check digit
    "15.847.392-K",     # wrong check digit, the K is the giveaway
    "1234",             # too short
    "",                 # empty
    "abcdefgh-1",       # not digits
])
def test_invalid(value):
    assert not is_valid_rut(value)


def test_lowercase_k_is_accepted():
    # 13.000.007 has check digit K. Both cases must validate.
    assert rut_check_digit("13000007") == "K"
    assert is_valid_rut("13.000.007-K")
    assert is_valid_rut("13.000.007-k")


def test_finds_rut_in_clinical_text():
    text = "Paciente Juan Rojas Miranda, RUT 15.847.392-5, ingresa por dolor abdominal."
    spans = find_identifiers(text)
    assert len(spans) == 1
    assert spans[0].text == "15.847.392-5"
    assert spans[0].label == "CL_RUT"
    assert spans[0].validated is True


def test_does_not_fire_on_record_numbers():
    """The whole point of validating the check digit: internal ids are not RUTs."""
    text = (
        "Ficha clinica N: HC-2026-448127\n"
        "Numero de orden: 20260904\n"
        "Telefono: +56 9 8473 2910\n"
        "Folio: F5374-99\n"
    )
    assert find_identifiers(text) == []


def test_redact_leaves_clinical_content_intact():
    text = "RUT 15.847.392-5, diagnostico de colecistitis aguda litiasica."
    out = redact(text)
    assert "15.847.392-5" not in out
    assert "colecistitis aguda litiasica" in out
    assert "[CL_RUT]" in out


def test_bare_digits_need_context():
    """A bare 8 digit number is only a RUT when a context word introduces it."""
    assert find_identifiers("Numero de orden: 20260904") == []
    hallados = find_identifiers("RUT: 20260904")
    assert len(hallados) == 1 and hallados[0].text == "20260904"


def test_multiple_ruts_in_one_document():
    text = "Paciente RUT 15.847.392-5. Medico tratante RUT 12.345.678-5."
    spans = find_identifiers(text)
    assert [s.text for s in spans] == ["15.847.392-5", "12.345.678-5"]
