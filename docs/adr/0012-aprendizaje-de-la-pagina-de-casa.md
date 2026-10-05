# 12. Aprendizaje de la página de casa

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

La página de casa daba como probabilidad de lluvia la fracción de las 40
simulaciones de ICON-EU-EPS, sin calibrar (ADR 0007), y la temperatura del
modelo tal cual. No guardaba sus previsiones, así que no podía saber cuánto
acertaba. Juanjo pidió que el programa aprenda de sus predicciones («es
imperativo que lo haga») y aprobó la regresión logística, con un método de
aprendizaje automático también para casa.

## Decisión

- **Registro** (`registre.py`, llamado desde `casa.py`, solo en el NAS): en
  cada pasada, las horas completas de Montflorit (`montflorit.csv`: lluvia,
  temperatura y humedad en la hora en punto); una vez por hora, todo lo que
  daban los modelos para las 24 horas siguientes y lo que mostró la página
  (`casa-AAAA-MM.jsonl`).
- **Lluvia: regresión logística** (`aprenentatge.py`). Primer modelo ajustado
  con el archivo de 2024-2026 (`calibracio/pluja_casa.py`): lluvia de los tres
  modelos finos, antelación, hora y día del año, con la lluvia de Sabadell y
  Sant Cugat como verdad. Con 30 horas de lluvia propias, un modelo con
  Montflorit como verdad y dos señales más: la fracción del ensemble y la
  lluvia medida al prever.
- **Temperatura: regresión lineal ridge** del error del modelo en Montflorit,
  a partir de 14 días registrados.
- **Adopción** (`aprenentatge.py diari`, cada día tras la verificación de las
  16:00): validación cruzada en cuatro grupos de semanas; un método sustituye
  al que se usa solo si su error baja al menos un 5 %. Un cambio de método se
  avisa por Telegram y se aplica al día siguiente, salvo que exista
  `/estat/aprenentatge/atura`. Los pesos del mismo método se ponen al día sin
  avisar.
- **Lo medido sigue mandando**: «Plou ara» y la persistencia de las primeras
  horas sustituyen a la probabilidad calculada si dan más.
- La página dice de dónde sale la probabilidad y, si se corrige, la
  temperatura.
- Explicación completa para revisar: [docs/estadistica.md](../estadistica.md).

## Alternativas descartadas

- **Métodos más complejos** (árboles de decisión, redes neuronales): con
  pocos datos propios aprenden de memoria los casos vistos y fallan en los
  nuevos. Se podrán probar con un año de datos, con la misma comprobación.
- **Restar el error medio de la temperatura**: es la versión más pobre de la
  regresión; no distingue la noche del día ni el cielo despejado del cubierto.
- **Esperar a tener datos de Montflorit para todo**: la lluvia es rara y
  tardaría meses; el archivo ya mejora el ensemble.

## Consecuencias

El registro crece unos 10 KB por hora (unos 7 MB al mes). El aprendizaje no
usa IA ni servicios de pago: numpy en el NAS, segundos al día.

## Evidencia

- API de meteocerdanyola.com (05-10-2026): ignora todo parámetro de fechas
  (`range`, `from`, `to`, `from_ts`, `date`…) y devuelve siempre 24 horas.
- Comprobación del modelo del archivo con los 90 días que no se usaron para
  ajustarlo (06-07 a 04-10-2026, 4.368 horas-estación, 95 con lluvia): error
  de Brier 0,0122, frente a 0,0187 del ensemble y 0,0216 de la frecuencia
  habitual. Fiabilidad en `calibracio/pluja_casa.json`.
- Con previsiones de un día antes, 0,0198 frente a 0,0216: la mejora a 24
  horas es pequeña.

## Riesgos y limitaciones

- La verdad del primer modelo es Sabadell y Sant Cugat, a 5-6 km.
- El corto plazo del archivo une las primeras horas de cada pasada: es
  optimista para las horas lejanas de la tabla.
- Si el NAS está apagado más de 24 horas, se pierden esas horas de Montflorit.
- La validación con pocas semanas tiene mucho margen de error; el 5 % de
  mejora mínima evita cambiar por ruido.

## Validación

`tests/test_aprenentatge.py` (rasgos, modelo del archivo, propuesta y
aplicación al día siguiente, `atura`, sin cambio con pocos días o sin mejora)
y `tests/test_registre_casa.py` (horas de Montflorit, paso por medianoche).
