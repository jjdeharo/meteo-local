# 21. Probabilidad de lluvia de casa comprobada con todo el archivo

Fecha: 2026-10-06 · Estado: aceptado

## Contexto

La probabilidad de lluvia de la página de casa sale de una regresión
logística ajustada con el archivo de 2024-2026 (ADR 0012). Se dio por fiable
con una sola comprobación: los últimos 90 días, con 95 horas de lluvia.

El 06-10-2026 Juanjo pidió examinar si la web predice lo que promete. Al
repetir la comprobación con todo el archivo (3.622 horas de lluvia) salieron
tres fallos:

- **La probabilidad se quedaba corta entre el 5 y el 50 %.** Cuando decía un
  7 % llovió el 25 % de las horas; con un 14 %, el 33 %; con un 24 %, el 44 %.
  La fórmula solo usaba la cantidad de lluvia de cada modelo como
  ln(1 + mm), que casi no cuenta las lluvias pequeñas: con un solo modelo
  dando 0,2 mm daba un 2 %, y en esos casos llovió una de cada diez horas.
- **La comparación con las simulaciones no valía.** Open-Meteo solo conserva
  unos días de ICON-EU-EPS: de las 4.368 muestras de la prueba, 96 tenían
  simulaciones y las otras 4.272 se contaron como «0 %». Las cifras «0,0187
  del ensemble» y «un 35 % menos de error» salían de ahí.
- **El cielo contradecía a la probabilidad.** La etiqueta («Pluja feble»,
  «Pluja») salía de los milímetros del modelo más lluvioso: la tabla ponía
  «Pluja feble» doce horas seguidas con probabilidades del 2 al 10 %.

Juanjo aprobó corregir la fórmula y que la etiqueta del cielo salga de la
probabilidad.

## Decisión

- **Señales nuevas en la regresión de lluvia** (`aprenentatge.py`,
  `RASGOS_ARXIU`), además de las que había:
  - si cada modelo da lluvia (0,1 mm o más, su décima), una por modelo;
  - si dan lluvia dos modelos o más, y si la dan los tres;
  - la cantidad de cada modelo multiplicada por la antelación, y lo mismo con
    «alguno da lluvia» y «la dan los tres»: lo previsto para dentro de un día
    se cumple menos.
- **La comprobación del modelo del archivo es con todo el archivo**
  (`calibracio/pluja_casa.py`): validación cruzada en cuatro grupos de
  semanas, a corto plazo y con previsiones de un día antes, con la tabla de
  fiabilidad de cada una. Se compara con la frecuencia habitual y con la
  fórmula anterior. La comparación con las simulaciones se retira.
- **Una prueba vigila la fiabilidad**: en cada tramo de probabilidad con 150
  horas o más, lo dado y lo que llovió no pueden separarse más de 5 puntos.
- **El cielo de la tabla sale de la probabilidad** (`web/casa.js`): «pluja»
  (o tormenta) con el 50 % o más, «possible pluja» desde el 20 %, y por debajo
  solo las nubes. Son los umbrales de `config.py` (`PROB_COCHE` y
  `PROB_ATENCION`). Los milímetros siguen siendo los del modelo más lluvioso
  y dicen cómo sería la lluvia, no si la habrá. Sin probabilidad, mandan los
  milímetros.
- La página dice cuánta lluvia llega con menos de un 5 %.

## Alternativas descartadas

- **Cambiar ln(1 + mm) por la raíz cúbica de los milímetros**: mejora el
  error un 8 %, pero sigue quedándose corta (un 7 % dado era un 14 %).
- **Solo «el modelo da lluvia», sin cuántos coinciden**: igual; la
  coincidencia no suma como dice la fórmula (un modelo solo, 10-20 %; los
  tres, 60 %).
- **Añadir el CAPE**: no mejora (error 0,0235 frente a 0,0231 a corto plazo).
- **Una corrección posterior de la probabilidad** (isotónica): otra pieza que
  mantener; con las señales nuevas ya no hace falta.
- **Quitar los milímetros cuando la probabilidad es baja**: la tabla enseña
  todos los datos; con la fórmula nueva, una hora con lluvia en algún modelo
  ya no se queda en un 1-2 %.

## Consecuencias

- Según la época del año, la hora y la antelación, una hora en que un solo
  modelo da poca lluvia (0,1-0,2 mm) pasa del 1-7 % al 4-21 %, y con los tres
  dando 0,2 mm, del 2-10 % al 18-43 %. En cambio, un solo modelo con mucha
  lluvia baja (ICON-EU con 3 mm, del 51-85 % al 28-56 %), y también lo más
  alto: antes un 89 % dado era un 77 % real.
- El modelo propio (`RASGOS_PROPIS`) hereda las señales nuevas: tiene 22
  pesos, así que tardará más en ganar al del archivo con pocos datos. Solo
  sustituye si mejora un 5 % en semanas no vistas, como antes.
- Las líneas ya guardadas en el registro sirven: guardan la lluvia de cada
  modelo, y las señales se calculan al ajustar.
- La página del trayecto no cambia: sigue con su regla (ADR 0001 y 0003).

## Evidencia

`python3 calibracio/pluja_casa.py` (06-10-2026; archivo del 01-01-2024 al
05-10-2026, 94.380 muestras). Resultado en `calibracio/pluja_casa.json`.

Error de Brier en semanas no vistas:

| | Frecuencia habitual | Fórmula anterior | Fórmula nueva |
|---|---|---|---|
| Corto plazo (47.676 muestras, 1.825 con lluvia) | 0,0368 | 0,0251 | 0,0225 (−10 %) |
| Un día antes (46.704 muestras, 1.797 con lluvia) | 0,0370 | 0,0296 | 0,0271 (−8 %) |

Fiabilidad a corto plazo (probabilidad media dada → lo que llovió):

| Tramo | Fórmula anterior | Fórmula nueva |
|---|---|---|
| 0-5 % | 1,7 → 1,1 % | 0,6 → 0,6 % |
| 5-10 % | 7 → 25 % | 8 → 8 % |
| 10-20 % | 14 → 33 % | 14 → 15 % |
| 20-30 % | 24 → 44 % | 24 → 27 % |
| 30-50 % | 39 → 50 % | 40 → 38 % |
| 50-70 % | 59 → 56 % | 59 → 62 % |
| 70-100 % | 89 → 77 % | 82 → 79 % |

Con previsiones de un día antes, la nueva da 1 → 1, 8 → 9, 15 → 14, 24 → 27,
39 → 37, 59 → 58 y 79 → 81 %.

Comprobaciones hechas a mano el mismo día, con otros repartos:

- ocho grupos de semanas: 0,0250 → 0,0225 y 0,0295 → 0,0270;
- ajustada hasta 2025 y comprobada con todo 2026: 0,0192 → 0,0175 y
  0,0248 → 0,0224;
- ajustada sin los últimos 90 días y comprobada en ellos: 0,0123 → 0,0118 y
  0,0200 → 0,0169.

Lluvia real según qué modelos la daban (0,2 mm o más), a corto plazo:
ninguno, 0,8 %; solo AROME, 23 %; solo ICON-EU, 21 %; los tres, 66 %. Con
solo ICON-EU dando 0,2 mm (729 horas), el 10 %.

Contraste con una estación que no se usó para ajustar
(`python3 calibracio/estacio_casa.py`): con la lluvia de la estación de casa
como verdad (08-10-2025 a 31-08-2026, 297 horas de lluvia), el error del
modelo del archivo baja de 0,0263 a 0,0236.

Simulaciones: la API de Open-Meteo devolvió datos de ICON-EU-EPS en 48 de las
2.184 horas pedidas (06-07 a 04-10-2026), todas de octubre.

## Riesgos y limitaciones

- **Lluvia que ningún modelo ve**: el 13 % de las horas de lluvia a corto
  plazo y el 24 % un día antes llegaron con menos de un 5 %. Ninguna fórmula
  hecha con estos modelos lo arregla.
- La verdad sigue siendo Sabadell y Sant Cugat, a 5-6 km, y el corto plazo
  del archivo une las primeras horas de cada pasada (ADR 0012).
- El archivo solo tiene dos antelaciones (corto plazo y un día antes): entre
  una y otra, la fórmula interpola. El registro propio lo medirá.
- Las señales de casa (radar, persistencia) siguen pudiendo subir la
  probabilidad por encima de la fórmula, y no están comprobadas con historial.

## Validación

`tests/test_aprenentatge.py` (señales nuevas, un solo modelo con poca lluvia,
fiabilidad guardada) y `tests/test_web.py` (el cielo según la probabilidad).
Página de casa calculada en local con los datos del 06-10-2026 y vista con
`probar-web` en Chromium, Firefox y WebKit, en escritorio, móvil y tableta, en
claro y oscuro; axe-core sin infracciones.
