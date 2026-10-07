# 3. Calibración con datos reales: se mantiene la regla

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

Los umbrales de la regla (ADR 0001) se pusieron con criterio, sin comprobar.
Juanjo pidió tener en cuenta los datos del portal de la Generalitat y valorar
una predicción propia más fina. El portal tiene la lluvia semihoraria de las
estaciones desde 2009, y Open-Meteo archiva las previsiones pasadas de AROME
HD, AROME e ICON-EU desde principios de 2024.

## Decisión

- **Se mantienen los umbrales de la regla** (1 mm, coche; 0,2 mm, moto con
  impermeable). Ajustados con los datos, dan casi lo mismo.
- **No se añade la regresión logística ni el CAPE.** No mejoran la regla de
  forma apreciable y añaden complejidad.
- **Se muestra la frecuencia real de lluvia** de cada nivel de la regla junto
  al motivo de los modelos («des del 2024, quan els models deien això, a l'hora
  del trajecte ha plogut 6 de cada 58 dies»). Sale de
  `calibracio/calibracio.json`, que genera `calibracio/analitza.py`.
- Los scripts y el informe (`calibracio/informe.md`) se suben; los datos
  descargados (`calibracio/dades/`), no.

## Alternativas descartadas

- **Regresión logística** con lluvia prevista por modelo, CAPE y época del
  año. Comprobada con validación cruzada por meses: mejora el error cuadrático
  de la probabilidad un 38 % sobre la frecuencia habitual en la ida (la regla,
  un 30 %) y un 22 % en la vuelta (la regla, un 21 %); con la previsión de 24 h
  antes, empata o queda por debajo. Con solo la lluvia prevista ya se obtiene
  casi todo (36 % y 15 %).
- **CAPE como señal de tormenta.** Cuando los modelos no dan lluvia, llovió en
  el trayecto el 0,8 % de los días de ida; con CAPE de 800 J/kg o más, el
  2,6 % (38 días). En la vuelta, el 0,6 % y el 1,2 %. No compensa.

## Consecuencias

La regla queda respaldada con datos, y quien hace el trayecto ve en cada motivo cuántas veces
llovió de verdad con previsiones parecidas. La calibración se puede repetir
cuando haya más datos: `python3 calibracio/descarrega.py --forzar` y
`python3 calibracio/analitza.py`.

## Evidencia

Datos del 01-01-2024 al 04-10-2026 (1.003 días de ida y 1.006 de vuelta con
datos completos). Lluvia en el trayecto: 0,2 mm o más en alguna media hora de
la ventana en Sabadell (XF) o en Sant Cugat (XV).

| Nivel de la regla (previsión a corto plazo) | Ida: llovió | Vuelta: llovió |
|---|---|---|
| moto (menos de 0,2 mm) | 7 de 897 días (1 %) | 5 de 853 (1 %) |
| compte (0,2 a 1 mm) | 6 de 58 (10 %) | 12 de 90 (13 %) |
| cotxe (1 mm o más) | 25 de 48 (52 %) | 23 de 63 (37 %) |

El día entero, con un solo medio: llovió en algún trayecto 69 de 1.001 días
(7 %). La regla habría mandado el coche 91 días; 42 de ellos llovió. De los
27 días de lluvia en que no mandó coche, en 18 había avisado de llevar el
impermeable. Detalle completo en `calibracio/informe.md`.

## Riesgos y limitaciones

- Pocos casos: unas 40 lluvias por ventana. Las cifras tienen bastante
  margen de error.
- Solo se calibran los modelos. No hay historial de avisos de AEMET, ni de
  radar, ni del ensemble, que siguen con su regla del ADR 0001.
- La previsión «a corto plazo» del archivo une las primeras horas de cada
  pasada. Para la ida, decidida a las 6:00, se parece a la real; para la
  vuelta, decidida con unas 9 horas de antelación, es optimista. La previsión
  de 24 h antes da el límite pesimista; las dos están en el informe.
- Dos estaciones a 2,5 y 5 km del trayecto: un chubasco puede mojar la
  carretera sin pasar por ellas, o al revés.

## Validación

Validación cruzada en cinco grupos de meses enteros: los meses con que se
comprueba no se usan para ajustar. Prueba automática de que el motivo de los
modelos incluye la frecuencia real (`tests/test_decidir.py`).
