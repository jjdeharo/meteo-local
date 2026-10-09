# 41. Tramos del día en la tarjeta de ahora

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Juanjo pidió ver «al principio, quizás debajo de los datos de ahora», la
probabilidad de lluvia con icono y cualquier fenómeno destacable (nieve,
temperaturas extremas…) por la mañana y por la tarde, para no tener que
leer la tabla de 24 horas. También que el botón «El temps ara» pasara a «El
temps», porque la página lleva además la previsión.

## Decisión

- **Tres fichas por tramo** (`resumTrams` y `blocTrams`, en `web/casa.js`)
  al final de la tarjeta de ahora, después del radar y antes de
  «Actualitzat a les…»: matí (7–14 h), tarda (14–21 h) y nit (21–7 h). Se
  muestran los tres primeros tramos con horas por delante: el tramo en
  curso dice «fins a les 14 h»; los que vienen, «14–21 h»; a partir de las
  21 h salen «Nit», «Demà matí» y «Demà tarda» (la previsión llega a 24 h).
- **Siempre**, en este orden: el cielo del tramo con su icono y su nombre
  (la media de las nubes de sus horas, con los nombres de Meteocat del
  ADR 0043; «Boira» si hay niebla en la mayoría de las horas; de noche, la
  luna) y la temperatura mínima–máxima con el termómetro («9 °C» si son
  iguales). El cielo no dice la lluvia: la dice el paraguas.
- **El paraguas, solo si va a llover** (Juanjo, 09-10-2026: «símbolo de
  lluvia solo si va a llover»): si alguna hora del tramo llega a «possible»
  (20 % o más, el mismo criterio que el cielo de la tabla), con la
  probabilidad máxima de sus horas y los milímetros sumados si llegan a 1
  («uns 5 mm»). Hasta la 3.28.0 salía siempre, también con un 0 %.
- **Solo cuando se dan**, en ámbar y con su icono: tempesta (código de
  tormenta de Open-Meteo, 95 o más, o aviso de AEMET por tormentas en la
  hora), pluja forta (20 mm en una hora), ratxes de vent (70 km/h), calor
  (36 °C), gel (0 °C o menos) y neu (0,1 cm o más en el tramo). Los
  umbrales de lluvia, viento y calor son los amarillos del Plan Meteoalerta
  que ya usa `config.RISC_LLINDARS` (ADR 0018); no se inventan otros. El
  hielo va a 0 °C, no al −4 del aviso amarillo de frío, porque lo que
  importa a quien sale es si puede helar.
- **El botón de la página pública se llama «El temps» / «El tiempo»**
  (`PAGINES_PUBLIQUES` en `montflorit.py`); la privada sigue siendo «Temps a
  casa».

## Alternativas descartadas

- **Una línea de texto en vez de fichas**: con los fenómenos se hacía larga
  y no se leía de un vistazo en el móvil.
- **Umbrales propios para los fenómenos**: la página ya usa los de AEMET
  para el riesgo; repetirlos evita dos criterios distintos en la misma
  tarjeta.

## Validación

- `tests/test_web.py`, `test_resum_per_trams_del_dia`: tramos, horas,
  probabilidad, milímetros, temperaturas y los seis fenómenos, de día y de
  noche; `tests/test_montflorit.py`: traducciones y menú.
- Desde el 09-10-2026, `test_cel_de_cada_tram` (cielo, niebla, luna y lluvia
  que sube las nubes) y cuándo sale el paraguas; Firefox y Chromium con los
  datos reales y con lluvia simulada, y axe-core sin incidencias.
- `probar-web` en Chromium, Firefox y WebKit, escritorio, móvil y tableta,
  claro y oscuro, en catalán y castellano, y axe-core sin incidencias, el
  08-10-2026. Juanjo vio las capturas antes de publicar.
