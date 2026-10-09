# 26. Radar de Meteocat o de RainViewer según cuál acierta más

Fecha: 2026-10-06 · Estado: aceptado


**09-10-2026 (ADR 0058).** La observación es solo si llueve en casa; sin estación en la pasada, no se apunta observación y la pasada no entra en la comparación.

## Contexto

Juanjo vio en la página de casa, a las 19:39, la imagen del radar de Meteocat
de las 19:18, y preguntó si con tanto retraso no convenía usar la de
RainViewer. Meteocat publica cada imagen entre 14 y 17 minutos después de
tomarla (el 06-10-2026, 36 pasadas: retraso de 14 a 21 minutos, mediana
15). RainViewer (composición de AEMET) va a 1-3 minutos, pero marca más
lluvia de la que hay (ADR 0019). Hasta ahora se usaba RainViewer solo si su
imagen era más de 15 minutos más nueva que la de Meteocat.

## Decisión

- **RainViewer en cuanto su imagen es 10 minutos más nueva** que la de
  Meteocat (`nowcast.MARGES`). En la práctica, casi siempre que Meteocat va
  con su retraso habitual.
- **Las dos se comparan solas.** En cada pasada de la página de casa,
  `nowcast.fonts` calcula lo que daría para casa cada fuente con su última
  imagen y el mismo movimiento, y `radar_fonts.py` lo apunta en
  `registre/radar-fonts-AAAA-MM.jsonl` junto con si llovía en ese momento en
  Montflorit o en casa (en casa, solo cuenta el sí).
- **Cada día**, dentro del aprendizaje de la página de casa
  (`aprenentatge.diari`), se comparan las dos con lo que pasó, de 10 a 60
  minutos después de cada pasada, en los últimos 30 días, con la puntuación
  de Brier (docs/estadistica.md). Como el resto del aprendizaje: se cambia
  si hay al menos 30 casos con lluvia en 3 días distintos y la otra fuente
  tiene al menos un 5 % menos de error, salvo que exista el archivo de
  parada (`aprenentatge/atura`). El cambio se guarda en
  `aprenentatge/radar-font.json`, se aplica en la pasada siguiente y se
  avisa a Juanjo por Telegram. Con Meteocat como preferida, vuelve la regla
  de antes (más de 15 minutos).
- Afecta a las dos webs, la del trayecto y la de casa (también la pública),
  porque las dos usan el mismo radar llevado hacia delante.

## Alternativas descartadas

- **Seguir con 15 minutos**: con el retraso habitual de Meteocat, la página
  enseña lluvia de hace un cuarto de hora, y cuando la lluvia se está
  formando no la ve a tiempo.
- **Usar siempre RainViewer**: marca más lluvia de la que hay. La misma
  tarde dio una falsa alarma (a las 19:45 decía lluvia encima de casa y no
  llovía en Montflorit ni en casa).
- **Decidirlo con una sola tarde**: los casos eran pocos y con aciertos
  bajos. Por eso la decisión queda en manos de la comparación diaria.
- **Mover las horas de actualización**: con el retraso en una mediana de 15
  minutos, la página ya coge cada imagen casi en cuanto sale.

## Consecuencias

- La página enseña más a menudo «Radar de RainViewer». Más avisos de
  lluvia por Telegram, y algunos falsos, hasta que la comparación diga lo
  contrario.
- Unos 200 bytes más por pasada en los datos del trayecto y unos 400 en el
  registro (menos de 4 MB al mes). Ninguna petición más: las dos fuentes ya
  se descargaban en cada pasada.

## Evidencia

- Retraso de las imágenes del 06-10-2026: registro de las pasadas
  (`registre/2026-10.jsonl`): Meteocat, 14 a 21 minutos (mediana 15);
  RainViewer, 1 a 3. A las 19:47 la última de Meteocat era la de las 19:30.
- Comparación de esa tarde (17:40 a 18:50, 8 imágenes de RainViewer, las
  de Meteocat de la caché del NAS): la previsión de la página con cada
  imagen, con el mismo movimiento, contra lo que vio después Meteocat en 60
  km alrededor de casa. Acierto (CSI): a 30 minutos, Meteocat 0,08 y
  RainViewer 0,13; a 60 minutos, 0,01 y 0,05. La lluvia se formaba cerca;
  pocos casos.
- Hipótesis pendiente: que RainViewer acierte más en casa. La comparación
  diaria lo dirá.

## Riesgos y limitaciones

- La observación es puntual (lluvia en Montflorit o en casa) y la
  previsión es de un círculo alrededor de casa; vale para comparar las dos
  fuentes entre sí, no para dar su acierto absoluto.
- El pluviómetro de casa no marca la lluvia débil y en Montflorit solo
  cuenta la intensidad del momento: la lluvia muy débil puede quedar como
  «no llueve» para las dos fuentes por igual.
- Hasta tener 30 casos con lluvia en 3 días, manda RainViewer.

## Validación

`tests/test_radar_fonts.py`: margen de 10 minutos con RainViewer y regla de
antes con Meteocat; la preferida se lee del archivo; parejas a la hora
prevista; sin las dos fuentes no cuenta; cambia a la que acierta más y no
cambia con pocos casos ni si la mejora no llega al 5 %; registro de cada
pasada. Cálculo real del radar el
06-10-2026 con las dos series.
