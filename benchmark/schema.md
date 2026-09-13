# Esquema de anotación — set de evaluación chileno

Qué se marca como identificador y con qué criterio. Referencia: HIPAA Safe Harbor (18 categorías)
adaptado a Chile, más el test del considerando 26 que exige mirar el conjunto y no campo por campo.
Ver `~/projects/_meta/proteccion-datos/base-ley-21719.md`.

## Tipos de entidad

| Etiqueta | Qué incluye | Por qué importa |
|---|---|---|
| `RUT` | RUT o RUN en cualquier formato, con o sin puntos, DV numérico o K | Identifica por sí solo. Es el peor caso: quien tiene el número tiene a la persona. |
| `NOMBRE` | Nombre de pila y apellidos de personas | Con dos apellidos identifica en poblaciones chicas |
| `FECHA` | Nacimiento, ingreso, alta, procedimiento, control | Fecha exacta más comuna y diagnóstico reidentifica por combinación |
| `DIRECCION` | Calle, número, departamento, villa o población | Cuasi-identificador fuerte |
| `COMUNA` | Comuna o localidad | En comunas chicas es casi identificador |
| `TELEFONO` | Fijo o móvil, con o sin +56 | Identificador directo en la práctica |
| `EMAIL` | Correo electrónico | Identificador directo |
| `ID_INTERNO` | Ficha clínica, número de orden, folio, número de cama | Reidentifica contra el sistema de origen |
| `ESTABLECIMIENTO` | Hospital, clínica, cesfam, consulta | Reduce el universo de personas posibles |
| `EDAD` | Edad en años | HIPAA solo exige sobre 89. Acá se marca siempre, porque combina |
| `PREVISION` | Fonasa con tramo, isapre con plan | Cuasi-identificador débil, se marca para medirlo |
| `PROFESION` | Oficio u ocupación cuando aparece del paciente | Cuasi-identificador en contexto |

## Rol de la entidad

Cada marca lleva además el rol, porque el riesgo es distinto:

- `paciente` — el titular de los datos. Es lo que la ley protege.
- `profesional` — médico, enfermera, secretaria. Dato personal igual, pero el riesgo clínico es otro.
- `tercero` — familiar, acompañante, contacto de emergencia.
- `institucion` — el establecimiento.

## Qué NO se marca

Diagnósticos, medicamentos, dosis, exámenes y hallazgos clínicos. Son el contenido útil del
documento y deben sobrevivir intactos. Si el filtro los borra, eso se mide como falso positivo y
cuenta en contra: un documento destruido no sirve.

## Métricas

- **Recall por tipo**: de los identificadores que había, cuántos detectó. Es la métrica que manda,
  porque lo que no detecta se va fuera.
- **Precision por tipo**: de lo que marcó, cuánto era identificador. Mide cuánto documento destruye.
- **Fuga por documento**: cuántos documentos quedan con al menos un identificador directo
  (`RUT`, `NOMBRE` de paciente, `TELEFONO`, `EMAIL`) sin redactar. Es la métrica de negocio: un
  documento con fuga es un documento que no se puede enviar a ninguna parte.
- **Nombre parcial**: un nombre compuesto detectado a medias cuenta como fuga, no como acierto.
  "Juan Pablo Rojas Miranda" reducido a "Rojas Miranda" sigue identificando.

## Límite de este set

Es sintético. Los nombres, RUT, direcciones y establecimientos son inventados, y ningún documento
proviene de un paciente real. Sirve para medir cobertura de patrones y comportamiento del modelo,
no para afirmar desempeño sobre documentación clínica real de un hospital. Para eso hace falta un
convenio con datos reales y un comité de ética.
