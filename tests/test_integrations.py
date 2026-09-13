"""Tests for the Presidio and OpenMed adapters.

The merge logic is tested without either library installed, because it is the part that
decides what ends up redacted. The adapters themselves are tested only where the
dependency is present.
"""
import pytest

from deid_latam import Span, find_identifiers
from deid_latam.integrations.openmed import merge, spans_from_openmed

TEXTO = "Paciente Juan Rojas Miranda, RUT 15.847.392-5, ingresa por dolor abdominal."
RUT_INICIO, RUT_FIN = TEXTO.index("15.847.392-5"), TEXTO.index("15.847.392-5") + 12


def span(start, end, label="PII", validated=False):
    return Span(start, end, TEXTO[start:end], label, "CL" if validated else "", validated)


# ------------------------------------------------------------------------- merge
def test_merge_conserva_ambos_cuando_no_se_tocan():
    modelo = [span(9, 27, "NAME")]
    propios = find_identifiers(TEXTO)
    salida = merge(modelo, propios)
    assert [(s.start, s.end, s.label) for s in salida] == [
        (9, 27, "NAME"),
        (RUT_INICIO, RUT_FIN, "CL_RUT"),
    ]


def test_merge_cubre_la_union_cuando_el_modelo_toma_la_mitad():
    """Un RUT medio detectado por el modelo no puede acortar la redaccion."""
    mitad = [span(RUT_INICIO, RUT_INICIO + 6, "ID")]
    salida = merge(mitad, find_identifiers(TEXTO))
    assert len(salida) == 1
    assert (salida[0].start, salida[0].end) == (RUT_INICIO, RUT_FIN)
    assert salida[0].label == "CL_RUT"      # gana el que tiene digito verificador
    assert salida[0].validated


def test_merge_extiende_hacia_adelante():
    """Si el modelo se pasa de largo, la union tambien se extiende."""
    largo = [span(RUT_INICIO + 3, RUT_FIN + 10, "ID")]
    salida = merge(find_identifiers(TEXTO), largo)
    assert (salida[0].start, salida[0].end) == (RUT_INICIO, RUT_FIN + 10)
    assert salida[0].label == "CL_RUT"


def test_merge_descarta_contenidos_del_mismo_tipo():
    duplicado = [span(RUT_INICIO, RUT_FIN, "CL_RUT", validated=True)]
    assert len(merge(find_identifiers(TEXTO), duplicado)) == 1


def test_merge_vacio():
    assert merge([], []) == []


# ---------------------------------------------------------------------- openmed
class _Entidad:
    def __init__(self, start, end, label):
        self.start, self.end, self.label = start, end, label


class _Resultado:
    def __init__(self, texto, entidades):
        self.original_text, self.pii_entities = texto, entidades


def test_spans_from_openmed_lee_el_texto_del_resultado():
    salida = spans_from_openmed(_Resultado(TEXTO, [_Entidad(9, 27, "NAME")]))
    assert len(salida) == 1
    assert salida[0].text == "Juan Rojas Miranda"
    assert salida[0].validated is False


@pytest.mark.parametrize("entidad", [
    _Entidad(None, 5, "NAME"),   # sin offsets
    _Entidad(5, 5, "NAME"),      # rango vacio
    _Entidad(9, 5, "NAME"),      # invertido
])
def test_spans_from_openmed_ignora_rangos_invalidos(entidad):
    assert spans_from_openmed(_Resultado(TEXTO, [entidad])) == []


def test_spans_from_openmed_sin_entidades():
    assert spans_from_openmed(_Resultado(TEXTO, None)) == []


# --------------------------------------------------------------------- presidio
def test_presidio_recognizer():
    pytest.importorskip("presidio_analyzer")
    from deid_latam.integrations.presidio import DeidLatamRecognizer, supported_entities

    rec = DeidLatamRecognizer()
    rec.load()
    salida = rec.analyze(TEXTO, entities=supported_entities())
    assert len(salida) == 1
    assert (salida[0].start, salida[0].end) == (RUT_INICIO, RUT_FIN)
    assert salida[0].entity_type == "CL_RUT"
    assert salida[0].score == 1.0


def test_presidio_respeta_la_lista_de_entidades_pedidas():
    pytest.importorskip("presidio_analyzer")
    from deid_latam.integrations.presidio import DeidLatamRecognizer

    assert DeidLatamRecognizer().analyze(TEXTO, entities=["US_SSN"]) == []


def test_presidio_register_rechaza_un_objeto_cualquiera():
    pytest.importorskip("presidio_analyzer")
    from deid_latam.integrations.presidio import register

    with pytest.raises(TypeError):
        register(object())
