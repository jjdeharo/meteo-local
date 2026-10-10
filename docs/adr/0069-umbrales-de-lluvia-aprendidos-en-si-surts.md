# 69. Umbrales de lluvia de «Si surts» que se aprenden, según la antelación

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

Juanjo, 10-10-2026: el objetivo de la web es dar «predicciones fiables al
100 %, en la medida de lo posible», y «la web tiene que aprender de sus
errores, siempre y en todo lo que toca». Los umbrales de lluvia de «Si
surts» eran fijos (40 % y 10 % en bici y moto, ADR 0047; 20 % a pie; 50 % o
1 mm en coche) y distintos según el medio, aunque la lluvia es la misma.

Se propuso como acierto que con «millor no» lloviera al menos la mitad de las
veces; a Juanjo le pareció poco, y preguntó por qué no se usaban los datos
locales. Con la lluvia de su estación (un año, del 08-10-2025 al
04-10-2026, 8.458 horas y 324 con lluvia, con la regla de hora seca del
aprendizaje) y la probabilidad del archivo sin ver la semana juzgada:

| Antelación | Desde | Llueve | Horas |
|---|---|---|---|
| 1-3 h | 40 % | 71 % | 233 |
| 1-3 h | 50 % | 75 % | 179 |
| 1 día | 40 % | 57 % | 186 |
| 1 día | 60 % | 79 % | 56 |

Por debajo del 10 % llueve el 0,6 % de las horas (1 día antes, el 1,0 %),
pero del 10 al 15 % el 14 % y del 15 al 20 % el 27 %: el 20 % de ir a pie
daba «bé» a horas en que llueve 1 de cada 4. La probabilidad está bien
calibrada (con un 70-80 %, llueve el 85 %). Lo que más falla no son los
umbrales, sino la lluvia que llega con «bé»: el 15 % de las horas de lluvia
a corto plazo y el 24 % un día antes, que solo baja mejorando la
probabilidad.

## Decisión

- **Qué significa cada nivel** (Juanjo lo aprobó: «si, hazlo»): con «pluja
  probable» («millor no» en bici y moto, «compte» en coche) tiene que llover
  al menos 2 de cada 3 veces; con «bé», como mucho 1 de cada 100 y nunca más
  de 1 de cada 10 en ninguna franja de 5 puntos de probabilidad (para que las
  muchas horas secas no tapen las dudosas). Las dos primeras, con el margen
  de la muestra (cota de Wilson, z = 1,28).
- **Los mismos umbrales para todos los medios**, y solo la probabilidad (sin
  ella, los milímetros: 0,2 y 1 mm): «pluja» decide «millor no» en bici y
  moto y «compte» en coche; «risc», «compte» en bici y moto y el paraguas a
  pie. El coche ya no sube de nivel por un solo modelo con 1 mm si la
  probabilidad es baja.
- **Dos juegos según la antelación**: «curt», para dentro de 3 horas o menos
  (se juzga con la previsión de 1 a 3 h antes), y «llarg», para más tarde
  (con la de 6 a 10 h antes). La página sabe cuánto falta para cada hora.
- **De partida**, los del archivo local: curt, 40 % y 10 %; llarg, 60 % y
  10 % (`config.SORTIR_LLINDARS_PLUJA`). A pie, el paraguas pasa del 20 % al
  10 %; en coche, «pluja probable» del 50 % al 40 % o el 60 %.
- **Se aprenden solos** (`aprenentatge.aprén_sortir`, cada día): con 30
  horas de lluvia o más en `sortir.csv` para una banda, se buscan el umbral
  de «pluja» más bajo y el de «risc» más alto que cumplen; si no son los de
  ahora, se propone, se avisa a Juanjo por Telegram y se aplica al día
  siguiente (`llindars-sortir.json`), salvo que exista `atura`. La verdad es
  la lluvia de la estación de casa, con su cero confirmado (ADR 0058 y 0060).
- **La página los recibe en los datos** (`sortir_llindars`, de casa.py) y
  «Com es decideix» dice los de ahora; si no llegan, usa los de partida.

## Alternativas descartadas

- **«Millor no» con la mitad**: la regla de ahora ya da el 71 % en casa.
- **Subir «millor no» al 70 % o más**: acierta el 89 %, pero solo 1 de cada
  4 horas de lluvia lo recibe; el resto pasa a «compte», que no quita la moto.
- **«Bé» solo con el 1 de cada 100 del conjunto**: dejaba subir «compte» al
  15 % a corto plazo, con «bé» en horas en que llueve 1 de cada 7.

## Riesgos y limitaciones

- El archivo no tiene radar ni estaciones; la web, sí: a corto plazo
  debería acertar más. Por eso decide el registro propio en cuanto hay datos.
- La banda «llarg» de partida sale de la previsión de un día antes, más
  insegura que la de 6 a 10 horas: es prudente y el registro la ajustará.
- Con «llarg», ningún umbral de «risc» llega al 1 de cada 100 con el margen:
  se queda el 10 %.

## Validación

Pruebas: el aprendizaje con muestras sintéticas y con la forma del archivo
de casa (la franja del 10 al 15 % no puede ser «bé»), el ciclo de propuesta
y aplicación, y que la página y la comprobación dan el mismo nivel en las
dos bandas (`tests/test_web.py`, 91 casos por medio y banda). Cifras:
`calibracio` con la lluvia de casa, scripts de la sesión del 10-10-2026.
