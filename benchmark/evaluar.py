#!/usr/bin/env python3
"""
Evalua un pipeline de de-identificacion contra el gold standard de eval/gold/.

Metricas, en orden de importancia para el negocio:
  1. FUGA por documento: cuantos documentos quedan con al menos un identificador directo
     (RUT, NOMBRE de paciente, TELEFONO, EMAIL) sin redactar. Un documento con fuga no se
     puede enviar a ninguna parte.
  2. RECALL por tipo: de los identificadores que habia, cuantos detecto.
  3. PRECISION por tipo: de lo que marco, cuanto era identificador. Mide cuanto documento
     destruye de mas.

Criterio de acierto: solapamiento de caracteres. Una entidad del gold se considera detectada
solo si el pipeline cubre TODO su rango. Un nombre compuesto cubierto a medias cuenta como
fuga, porque "Rojas Miranda" sigue identificando.

Uso:
  python3 eval/evaluar.py --modelo small            # OpenMed Spanish SuperClinical Small
  python3 eval/evaluar.py --modelo small --con-rut  # + reconocedor de RUT propio
  python3 eval/evaluar.py --umbral 0.5
"""
import json, argparse, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DIRECTOS = {"RUT", "TELEFONO", "EMAIL"}          # identifican por si solos
MODELOS = {
    "small": "OpenMed/OpenMed-PII-Spanish-SuperClinical-Small-44M-v1",
    "large": "OpenMed/OpenMed-PII-Spanish-SuperClinical-Large-434M-v1",
}

# ------------------------------------------------------------------ deid-latam
# El benchmark mide la libreria publicada, no una copia del codigo.
sys.path.insert(0, str(RAIZ.parent / "src"))
from deid_latam import find_identifiers          # noqa: E402

def buscar_ruts(texto):
    """Spans de identificadores nacionales segun deid-latam."""
    return [(s.start, s.end, s.label) for s in find_identifiers(texto)]

# ------------------------------------------------------------------ pipeline
def spans_openmed(texto, modelo, umbral):
    """El resultado expone pii_entities (PIIEntity con .start/.end/.label)."""
    import openmed as om
    r = om.deidentify(texto, model_name=modelo, lang="es", confidence_threshold=umbral)
    fuera = []
    for e in (r.pii_entities or []):
        fuera.append((e.start, e.end, getattr(e, "label", "?")))
    return fuera, (r.metadata or {}).get("sentence_language")

def cobertura(span_gold, detectados):
    """Fraccion del rango del gold cubierta por los detectados (0.0 a 1.0)."""
    ini, fin = span_gold["inicio"], span_gold["fin"]
    rango = set(range(ini, fin))
    if not rango:
        return 1.0
    libres = set(rango)
    for a, b, _ in detectados:
        libres -= set(range(a, b))
    return 1.0 - len(libres) / len(rango)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", default="small", choices=list(MODELOS))
    ap.add_argument("--umbral", type=float, default=0.7)
    ap.add_argument("--con-rut", action="store_true", help="suma deid-latam")
    ap.add_argument("--solo-rut", action="store_true", help="mide solo deid-latam, sin modelo")
    args = ap.parse_args()

    golds = sorted((RAIZ / "gold").glob("*.json"))
    if not golds:
        sys.exit("No hay gold. Corre primero: python3 eval/generar.py")

    por_tipo = {}          # tipo -> [encontrados, total]
    docs_con_fuga, fugas_detalle, idiomas_vistos = 0, [], set()
    t0 = time.time()

    for g in golds:
        d = json.loads(g.read_text(encoding="utf-8"))
        texto = (RAIZ / "docs" / f"{d['id']}.txt").read_text(encoding="utf-8")

        detectados, idiomas = [], set()
        if not args.solo_rut:
            sp, idi = spans_openmed(texto, MODELOS[args.modelo], args.umbral)
            detectados += sp
            if idi: idiomas.add(idi)
        if args.con_rut or args.solo_rut:
            detectados += buscar_ruts(texto)

        fuga_doc = []
        for e in d["entidades"]:
            t = e["tipo"]
            par = por_tipo.setdefault(t, [0, 0, 0])
            par[1] += 1
            c = cobertura(e, detectados)
            if c >= 1.0:
                par[0] += 1
            else:
                if c > 0:
                    par[2] += 1
                directo = t in DIRECTOS or (t == "NOMBRE" and e["rol"] == "paciente")
                if directo:
                    fuga_doc.append(f"{t}:{e['texto']}")
        idiomas_vistos |= idiomas
        if fuga_doc:
            docs_con_fuga += 1
            fugas_detalle.append((d["id"], fuga_doc))

    dur = time.time() - t0
    etiqueta = "solo deid-latam" if args.solo_rut else \
               f"{args.modelo} umbral {args.umbral}" + (" + deid-latam" if args.con_rut else "")
    n = len(golds)

    print(f"\nSet: {n} documentos  ·  Pipeline: {etiqueta}  ·  {dur:.1f} s")
    if idiomas_vistos:
        print(f"Idioma detectado por la libreria: {', '.join(sorted(idiomas_vistos))}")
    print()
    print(f"{'tipo':16} {'completo':>9} {'parcial':>9}   {'total'}")
    print("-" * 52)
    for t in sorted(por_tipo, key=lambda x: -por_tipo[x][1]):
        ok, tot, par = por_tipo[t]
        print(f"{t:16} {ok/tot*100:8.1f}% {par/tot*100:8.1f}%   {tot}")

    tot_ok  = sum(v[0] for v in por_tipo.values())
    tot_all = sum(v[1] for v in por_tipo.values())
    tot_par = sum(v[2] for v in por_tipo.values())
    print("-" * 52)
    print(f"{'TOTAL':16} {tot_ok/tot_all*100:8.1f}% {tot_par/tot_all*100:8.1f}%   {tot_all}")
    print("  completo = todo el identificador redactado. parcial = quedo un trozo a la vista.\n")
    print(f"DOCUMENTOS CON FUGA: {docs_con_fuga} de {n}  ({docs_con_fuga/n*100:.0f}%)")
    print("  (fuga = queda al menos un RUT, telefono, correo o nombre de paciente sin redactar)\n")
    for did, f in fugas_detalle[:6]:
        print(f"  {did:24} {', '.join(f[:3])}{' ...' if len(f) > 3 else ''}")
    if len(fugas_detalle) > 6:
        print(f"  ... y {len(fugas_detalle)-6} documentos mas")

if __name__ == "__main__":
    main()
