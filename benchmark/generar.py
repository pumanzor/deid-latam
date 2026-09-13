#!/usr/bin/env python3
"""
Genera el set de evaluacion chileno: documentos sinteticos con gold standard exacto.

La gracia: las plantillas llevan marcadores {{TIPO:rol:clave}}. Al sustituir el valor se
registra el offset exacto, asi que la anotacion no se hace a mano y no tiene errores de
desplazamiento. Cada corrida con la misma semilla produce el mismo set.

Uso:  python3 eval/generar.py [--n 32] [--semilla 42]
Salida: eval/docs/<id>.txt y eval/gold/<id>.json
"""
import json, random, argparse, unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parent

# ---------------------------------------------------------------- catalogos
NOMBRES_F = ["Maria Fernanda","Camila Andrea","Ana Maria","Francisca Belen","Catalina Paz",
             "Maria Jose","Javiera Ignacia","Antonia Paz","Valentina Soledad","Rosa Elena",
             "Daniela Alejandra","Constanza Beatriz"]
NOMBRES_M = ["Juan Pablo","Jose Miguel","Luis Alberto","Sebastian Ignacio","Cristian Andres",
             "Matias Nicolas","Rodrigo Antonio","Felipe Ignacio","Hector Manuel","Diego Alonso",
             "Gonzalo Esteban","Patricio Hernan"]
APELLIDOS = ["Gonzalez Soto","Ovalle Ferrada","Rojas Miranda","Fuentes Cortes","Tapia Sandoval",
             "Zuniga Paredes","Navarro Espinoza","Riquelme Toledo","Herrera Campos","Vergara Lillo",
             "Munoz Alcayaga","Carrasco Bravo","Pizarro Leiva","Sepulveda Aguilera","Bustos Cifuentes",
             "Araya Quintana","Melo Sanhueza","Valdes Urrutia"]
CALLES = ["Pasaje Los Canelos","Avenida Las Torres","Calle Manuel Rodriguez","Pasaje El Peumo",
          "Avenida Los Aromos","Calle Arturo Prat","Pasaje Las Acacias","Camino El Roble",
          "Calle Baquedano","Pasaje Los Maitenes"]
VILLAS = ["Villa El Roble","Poblacion Santa Ana","Villa Los Presidentes","Condominio Altos del Sol",
          "Villa Las Rosas","Poblacion El Esfuerzo"]
COMUNAS = ["Puente Alto","La Florida","Maipu","Rancagua","Quilpue","Talagante","Buin","Melipilla",
           "San Bernardo","Los Andes","Curico","Chillan"]
ESTABLECIMIENTOS = ["Hospital Clinico Valle Verde","Clinica Santa Amelia","Hospital Regional del Maipo",
                    "Cesfam Los Aromos","Hospital San Gabriel","Clinica Cordillera",
                    "Centro Medico Puerta del Sol","Hospital Provincial Las Vertientes"]
DIAGNOSTICOS = [
 ("colecistitis aguda litiasica","dolor abdominal en hipocondrio derecho","colecistectomia laparoscopica"),
 ("neumonia adquirida en la comunidad","tos productiva y fiebre","tratamiento antibiotico endovenoso"),
 ("apendicitis aguda","dolor en fosa iliaca derecha","apendicectomia laparoscopica"),
 ("pielonefritis aguda","dolor lumbar y disuria","tratamiento antibiotico endovenoso"),
 ("crisis hipertensiva","cefalea occipital y vision borrosa","ajuste de terapia antihipertensiva"),
 ("descompensacion diabetica","poliuria, polidipsia y decaimiento","hidratacion e insulinoterapia"),
]
FARMACOS = ["losartan 50 mg cada 12 horas","metformina 850 mg cada 12 horas",
            "atorvastatina 20 mg cada 24 horas","levotiroxina 75 mcg cada 24 horas",
            "enalapril 10 mg cada 12 horas","omeprazol 20 mg cada 24 horas"]
ESPECIALIDADES = ["Cirugia General","Medicina Interna","Broncopulmonar","Nefrologia","Cardiologia",
                  "Traumatologia","Gastroenterologia"]
EXAMENES = ["hemograma con VHS","perfil bioquimico","ecografia abdominal","radiografia de torax",
            "creatinina plasmatica","hemoglobina glicosilada"]

# ---------------------------------------------------------------- utilidades
def dv_rut(n: int) -> str:
    s, m = 0, 2
    for d in reversed(str(n)):
        s += int(d) * m
        m = 2 if m == 7 else m + 1
    r = 11 - (s % 11)
    return {11: "0", 10: "K"}.get(r, str(r))

def rut(rnd, formato=None):
    """RUT con DV valido, en alguno de los formatos que se ven en la practica."""
    n = rnd.randint(5_000_000, 24_999_999)
    d = dv_rut(n)
    f = formato or rnd.choice(["puntos", "guion", "pegado", "minuscula"])
    miles = f"{n:,}".replace(",", ".")
    if f == "puntos":    return f"{miles}-{d}"
    if f == "guion":     return f"{n}-{d}"
    if f == "pegado":    return f"{n}{d}"
    return f"{miles}-{d.lower()}"

def fecha(rnd, ini=2026, fin=2026):
    d, m = rnd.randint(1, 28), rnd.randint(1, 12)
    a = rnd.randint(ini, fin)
    return rnd.choice([f"{d:02d}/{m:02d}/{a}", f"{d:02d}-{m:02d}-{a}", f"{d} de {MESES[m-1]} de {a}"])

MESES = ["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre",
         "octubre","noviembre","diciembre"]

def telefono(rnd):
    return rnd.choice([f"+56 9 {rnd.randint(1000,9999)} {rnd.randint(1000,9999)}",
                       f"9{rnd.randint(10000000,99999999)}",
                       f"{rnd.randint(22,75)} {rnd.randint(200,999)} {rnd.randint(1000,9999)}"])

def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")

def correo(rnd, nombre):
    p = sin_tildes(nombre.lower()).split()
    return f"{p[0][0]}{p[-1]}@correo-ejemplo.cl"

# ---------------------------------------------------------------- plantillas
# Los marcadores son {{TIPO|rol|clave}}. La misma clave repetida reusa el mismo valor,
# que es justo lo que pasa en un documento real (el medico aparece dos veces).
PLANTILLAS = {
"epicrisis": """EPICRISIS DE ALTA
(documento ficticio generado para evaluacion. Personas, establecimiento y direccion inventados)

Establecimiento: {{ESTABLECIMIENTO|institucion|est}}, {{COMUNA|institucion|com}}
Paciente: {{NOMBRE|paciente|pac}}
RUT: {{RUT|paciente|rutpac}}
Fecha de nacimiento: {{FECHA|paciente|fnac}} ({{EDAD|paciente|edad}} anos)
Domicilio: {{DIRECCION|paciente|dir}}, {{COMUNA|paciente|comdom}}
Telefono de contacto: {{TELEFONO|paciente|tel}}
Correo: {{EMAIL|paciente|mail}}
Ficha clinica N: {{ID_INTERNO|paciente|ficha}}
Prevision: {{PREVISION|paciente|prev}}
Fecha de ingreso: {{FECHA|paciente|fing}}    Fecha de alta: {{FECHA|paciente|falta}}

MOTIVO DE INGRESO
Paciente de {{EDAD|paciente|edad}} anos consulta en el servicio de urgencia por {{SINTOMA}} de
48 horas de evolucion, asociado a nauseas, vomitos y fiebre hasta 38,5 C.

ANTECEDENTES
Hipertension arterial en tratamiento con {{FARMACO1}}. Diabetes mellitus tipo 2 en tratamiento
con {{FARMACO2}}. Alergia a penicilina.

EVOLUCION
{{EXAMEN}} informada por el Dr. {{NOMBRE|profesional|med}} muestra hallazgos compatibles con
{{DIAGNOSTICO}}. Se inicia ceftriaxona 1 g cada 24 horas endovenoso y metronidazol 500 mg cada
8 horas.

Se realiza {{PROCEDIMIENTO}} el {{FECHA|paciente|fproc}} por el equipo de {{ESPECIALIDAD}} a cargo
del Dr. {{NOMBRE|profesional|med}}. Evolucion postoperatoria favorable, con buena tolerancia oral
al segundo dia.

INDICACIONES AL ALTA
Paracetamol 1 g cada 8 horas por 5 dias. Mantener {{FARMACO1}} en dosis habitual.
Control en 10 dias en policlinico de {{ESPECIALIDAD}}.

Medico tratante: Dr. {{NOMBRE|profesional|med}}, RUT {{RUT|profesional|rutmed}}
Contacto secretaria: {{TELEFONO|institucion|telsec}}
""",

"interconsulta": """SOLICITUD DE INTERCONSULTA

Origen: {{ESTABLECIMIENTO|institucion|est}}, comuna de {{COMUNA|institucion|com}}
Fecha de solicitud: {{FECHA|paciente|fsol}}
Folio: {{ID_INTERNO|paciente|folio}}

DATOS DEL PACIENTE
Nombre: {{NOMBRE|paciente|pac}}
RUN: {{RUT|paciente|rutpac}}
Edad: {{EDAD|paciente|edad}} anos
Direccion: {{DIRECCION|paciente|dir}}, {{COMUNA|paciente|comdom}}
Telefono: {{TELEFONO|paciente|tel}}
Prevision: {{PREVISION|paciente|prev}}
Ocupacion: {{PROFESION|paciente|prof}}

DERIVACION A: {{ESPECIALIDAD}}

RESUMEN CLINICO
Paciente con cuadro de {{SINTOMA}} en estudio. Se solicito {{EXAMEN}}, cuyo resultado muestra
alteraciones que requieren evaluacion por especialista. Actualmente en tratamiento con
{{FARMACO1}}.

Se solicita evaluacion para descartar {{DIAGNOSTICO}}.

Profesional solicitante: Dra. {{NOMBRE|profesional|med}}
RUT profesional: {{RUT|profesional|rutmed}}
Correo de contacto: {{EMAIL|profesional|mailmed}}
""",

"informe_lab": """INFORME DE LABORATORIO CLINICO
{{ESTABLECIMIENTO|institucion|est}} - Unidad de Laboratorio

Paciente: {{NOMBRE|paciente|pac}}
RUT: {{RUT|paciente|rutpac}}
Fecha de nacimiento: {{FECHA|paciente|fnac}}
N de orden: {{ID_INTERNO|paciente|orden}}
Fecha de toma de muestra: {{FECHA|paciente|ftoma}}
Servicio solicitante: {{ESPECIALIDAD}}
Medico solicitante: Dr. {{NOMBRE|profesional|med}}

RESULTADOS
Hemoglobina           13,4 g/dL       (12,0 - 16,0)
Leucocitos            14.200 /uL      (4.000 - 11.000)
Proteina C reactiva   86 mg/L         (menor a 5)
Creatinina            0,9 mg/dL       (0,6 - 1,1)
Glicemia              178 mg/dL       (70 - 100)

OBSERVACIONES
Leucocitosis con desviacion a izquierda y PCR elevada, compatible con proceso infeccioso agudo.
Se sugiere correlacionar con {{EXAMEN}} y cuadro clinico.

Validado por: TM {{NOMBRE|profesional|tec}}
Consultas: {{TELEFONO|institucion|tellab}}
""",

"receta": """RECETA MEDICA

{{ESTABLECIMIENTO|institucion|est}}
{{DIRECCION|institucion|direst}}, {{COMUNA|institucion|com}}
Telefono: {{TELEFONO|institucion|telest}}

Fecha: {{FECHA|paciente|frec}}

Paciente: {{NOMBRE|paciente|pac}}
RUT: {{RUT|paciente|rutpac}}
Edad: {{EDAD|paciente|edad}} anos
Prevision: {{PREVISION|paciente|prev}}

Rp.
1. {{FARMACO1}} por 30 dias
2. {{FARMACO2}} por 30 dias
3. Paracetamol 500 mg cada 8 horas en caso de dolor

Indicaciones: control en 30 dias. Dieta hiposodica. Consultar si presenta {{SINTOMA}}.

Dr. {{NOMBRE|profesional|med}}
{{ESPECIALIDAD}}
RUT {{RUT|profesional|rutmed}}
Correo {{EMAIL|profesional|mailmed}}
""",

"consentimiento": """CONSENTIMIENTO INFORMADO PARA PROCEDIMIENTO

Establecimiento: {{ESTABLECIMIENTO|institucion|est}}
Fecha: {{FECHA|paciente|fcons}}

Yo, {{NOMBRE|paciente|pac}}, cedula de identidad {{RUT|paciente|rutpac}}, domiciliado en
{{DIRECCION|paciente|dir}}, comuna de {{COMUNA|paciente|comdom}}, telefono {{TELEFONO|paciente|tel}},
declaro que he sido informado por el Dr. {{NOMBRE|profesional|med}} sobre el procedimiento
{{PROCEDIMIENTO}} indicado por diagnostico de {{DIAGNOSTICO}}.

Se me explicaron los riesgos del procedimiento y las alternativas disponibles. Autorizo su
realizacion en la fecha {{FECHA|paciente|fproc}}.

En caso de emergencia contactar a {{NOMBRE|tercero|fam}}, telefono {{TELEFONO|tercero|telfam}}.

Firma paciente: ______________________
Firma profesional: Dr. {{NOMBRE|profesional|med}}, RUT {{RUT|profesional|rutmed}}
Ficha: {{ID_INTERNO|paciente|ficha}}
""",

"ingreso_urgencia": """DATO DE ATENCION DE URGENCIA

{{ESTABLECIMIENTO|institucion|est}} - Servicio de Urgencia
Numero de atencion: {{ID_INTERNO|paciente|atencion}}
Fecha y hora de ingreso: {{FECHA|paciente|fing}}, 03:42 hrs

IDENTIFICACION
Nombre completo: {{NOMBRE|paciente|pac}}
RUT: {{RUT|paciente|rutpac}}
Edad: {{EDAD|paciente|edad}} anos
Domicilio: {{DIRECCION|paciente|dir}}, {{COMUNA|paciente|comdom}}
Telefono: {{TELEFONO|paciente|tel}}
Correo: {{EMAIL|paciente|mail}}
Prevision: {{PREVISION|paciente|prev}}
Acompanante: {{NOMBRE|tercero|fam}}, telefono {{TELEFONO|tercero|telfam}}

CATEGORIZACION: C3

MOTIVO DE CONSULTA
Paciente acude por {{SINTOMA}} de inicio subito. Se solicita {{EXAMEN}}.
Evaluado por Dr. {{NOMBRE|profesional|med}}, quien indica manejo por {{DIAGNOSTICO}}.

DESTINO: hospitalizacion en {{ESPECIALIDAD}}
""",

"informe_imagen": """INFORME DE IMAGENOLOGIA

Centro: {{ESTABLECIMIENTO|institucion|est}}, {{COMUNA|institucion|com}}
Paciente: {{NOMBRE|paciente|pac}}    RUT: {{RUT|paciente|rutpac}}
Fecha de examen: {{FECHA|paciente|fexam}}
Numero de estudio: {{ID_INTERNO|paciente|estudio}}
Medico derivante: Dr. {{NOMBRE|profesional|med}}

EXAMEN: {{EXAMEN}}

TECNICA
Estudio realizado sin medio de contraste, en cortes axiales.

HALLAZGOS
Se observan alteraciones en relacion al cuadro clinico descrito, con signos compatibles con
{{DIAGNOSTICO}}. No se observan colecciones ni aire libre.

CONCLUSION
Hallazgos compatibles con {{DIAGNOSTICO}}. Se sugiere correlacion clinica y control evolutivo.

Dr. {{NOMBRE|profesional|rad}}
Radiologo
Contacto: {{EMAIL|profesional|mailrad}} / {{TELEFONO|institucion|telimg}}
""",

"certificado": """CERTIFICADO MEDICO

{{ESTABLECIMIENTO|institucion|est}}
{{COMUNA|institucion|com}}, {{FECHA|paciente|fcert}}

Certifico que don/dona {{NOMBRE|paciente|pac}}, RUT {{RUT|paciente|rutpac}}, de
{{EDAD|paciente|edad}} anos de edad, con domicilio en {{DIRECCION|paciente|dir}}, comuna de
{{COMUNA|paciente|comdom}}, y que se desempena como {{PROFESION|paciente|prof}}, fue atendido en
este establecimiento por cuadro de {{DIAGNOSTICO}}.

Se indica reposo por 7 dias a contar de esta fecha y tratamiento con {{FARMACO1}}.

Se extiende el presente certificado a solicitud del interesado para los fines que estime
convenientes.

Dr. {{NOMBRE|profesional|med}}
{{ESPECIALIDAD}}
RUT {{RUT|profesional|rutmed}}
Registro contacto: {{TELEFONO|institucion|telcert}}
""",
}

PREVISIONES = ["Fonasa tramo A","Fonasa tramo B","Fonasa tramo C","Fonasa tramo D",
               "Isapre Consalud plan 2C","Isapre Colmena plan Basico","Isapre Banmedica plan 4B"]
PROFESIONES = ["profesora basica","conductor de transporte escolar","tecnico en enfermeria",
               "comerciante","operario de bodega","contadora","agricultor","asistente social"]

# ---------------------------------------------------------------- generacion
def valor_para(tipo, rnd, cache, clave):
    if clave in cache:
        return cache[clave]
    if tipo == "NOMBRE":
        v = f"{rnd.choice(NOMBRES_F + NOMBRES_M)} {rnd.choice(APELLIDOS)}"
    elif tipo == "RUT":
        v = rut(rnd)
    elif tipo == "FECHA":
        v = fecha(rnd, 1945, 2026) if clave == "fnac" else fecha(rnd)
    elif tipo == "DIRECCION":
        v = f"{rnd.choice(CALLES)} {rnd.randint(100, 4999)}"
        if rnd.random() < 0.4:
            v += f", depto {rnd.randint(11, 99)}"
        if rnd.random() < 0.5:
            v += f", {rnd.choice(VILLAS)}"
    elif tipo == "COMUNA":       v = rnd.choice(COMUNAS)
    elif tipo == "TELEFONO":     v = telefono(rnd)
    elif tipo == "EMAIL":        v = correo(rnd, cache.get("pac", "juan perez"))
    elif tipo == "ID_INTERNO":
        v = rnd.choice([f"HC-{rnd.randint(2020,2026)}-{rnd.randint(100000,999999)}",
                        f"{rnd.randint(10000000,99999999)}",
                        f"F{rnd.randint(1000,9999)}-{rnd.randint(10,99)}"])
    elif tipo == "ESTABLECIMIENTO": v = rnd.choice(ESTABLECIMIENTOS)
    elif tipo == "EDAD":         v = str(rnd.randint(19, 91))
    elif tipo == "PREVISION":    v = rnd.choice(PREVISIONES)
    elif tipo == "PROFESION":    v = rnd.choice(PROFESIONES)
    else:
        raise ValueError(f"tipo desconocido: {tipo}")
    cache[clave] = v
    return v

import re
MARCA = re.compile(r"\{\{([A-Z_0-9]+)(?:\|([a-z]+)\|([a-z0-9]+))?\}\}")

def generar_doc(nombre_plantilla, rnd):
    txt = PLANTILLAS[nombre_plantilla]
    cache, libres = {}, {}
    dx = rnd.choice(DIAGNOSTICOS)
    libres["DIAGNOSTICO"]  = dx[0]
    libres["SINTOMA"]      = dx[1]
    libres["PROCEDIMIENTO"]= dx[2]
    libres["FARMACO1"]     = rnd.choice(FARMACOS)
    libres["FARMACO2"]     = rnd.choice([f for f in FARMACOS if f != libres["FARMACO1"]])
    libres["ESPECIALIDAD"] = rnd.choice(ESPECIALIDADES)
    libres["EXAMEN"]       = rnd.choice(EXAMENES)

    # primera pasada: fijar el nombre del paciente antes que el correo
    for m in MARCA.finditer(txt):
        if m.group(1) == "NOMBRE" and m.group(3) == "pac":
            valor_para("NOMBRE", rnd, cache, "pac"); break

    salida, spans, pos = [], [], 0
    for m in MARCA.finditer(txt):
        salida.append(txt[pos:m.start()])
        tipo, rol, clave = m.group(1), m.group(2), m.group(3)
        if rol is None:                      # texto clinico, no se marca
            valor = libres[tipo]
            salida.append(valor)
        else:
            valor = valor_para(tipo, rnd, cache, clave)
            ini = sum(len(s) for s in salida)
            salida.append(valor)
            spans.append({"inicio": ini, "fin": ini + len(valor),
                          "tipo": tipo, "rol": rol, "texto": valor})
        pos = m.end()
    salida.append(txt[pos:])
    return "".join(salida), spans

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=32)
    ap.add_argument("--semilla", type=int, default=42)
    args = ap.parse_args()

    (RAIZ / "docs").mkdir(parents=True, exist_ok=True)
    (RAIZ / "gold").mkdir(parents=True, exist_ok=True)
    rnd = random.Random(args.semilla)
    tipos = list(PLANTILLAS)
    resumen = {}

    for i in range(args.n):
        t = tipos[i % len(tipos)]
        texto, spans = generar_doc(t, rnd)
        did = f"{t}_{i//len(tipos)+1:02d}"
        (RAIZ / "docs" / f"{did}.txt").write_text(texto, encoding="utf-8")
        (RAIZ / "gold" / f"{did}.json").write_text(
            json.dumps({"id": did, "plantilla": t, "entidades": spans},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        for s in spans:
            resumen[s["tipo"]] = resumen.get(s["tipo"], 0) + 1

    total = sum(resumen.values())
    print(f"{args.n} documentos en eval/docs/, gold en eval/gold/  (semilla {args.semilla})")
    print(f"{total} identificadores marcados\n")
    for k in sorted(resumen, key=lambda x: -resumen[x]):
        print(f"  {k:16} {resumen[k]:4}")

if __name__ == "__main__":
    main()
