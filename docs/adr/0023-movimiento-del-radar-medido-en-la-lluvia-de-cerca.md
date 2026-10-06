# 23. Movimiento del radar medido en la lluvia de cerca

Fecha: 2026-10-06 · Estado: aceptado

## Contexto

La tarde del 06-10-2026 la página anunció varias veces lluvia en casa que no
llegó: la hora prevista se iba retrasando. Juanjo preguntó si el fallo estaba
en llevar la lluvia en línea recta y si una parábola iría mejor.

El radar llevado hacia delante (ADR 0019) usa una sola flecha para toda la
zona, que sale de comparar la primera y la última imagen de la advección de
Meteocat en un cuadro de unos 300 km. Con las imágenes de esa tarde
(Evidencia) se vio que:

- La lluvia se movió en línea recta y con rumbo estable (de 62° a 79° toda la
  tarde, a unos 37 km/h): no había curva que seguir.
- La flecha de la página estaba desviada: 25 km/h hacia 52°, unos 16 km de
  error a una hora. En el cuadro de 300 km entraban tormentas lejanas que se
  movían de otra manera.
- La advección de Meteocat sí llevaba el movimiento bueno: su imagen a 60
  minutos coincidía con la real tanto como la mejor traslación posible.

## Decisión

El movimiento se mide **primero en la lluvia que hay a 60 km o menos del
trayecto** (`desplacament_local` en `nowcast.py`): la traslación con la que
más coinciden la primera y la última imagen de la advección de Meteocat (lo
que comparten las dos manchas de lluvia entre lo que ocupan las dos). Solo se
prueban saltos de hasta 60 km.

Si cerca hay poca lluvia (menos de 50 píxeles en alguna de las dos imágenes),
si las manchas coinciden menos de un 30 % o si el mejor salto queda en el
borde de la búsqueda, se mide como antes, en el cuadro de 300 km.

Lo demás no cambia: una sola flecha, línea recta, el círculo que crece y los
umbrales (ADR 0019). El resumen guarda además el rumbo en grados (`graus`),
para comprobarlo con el registro.

## Alternativas descartadas

- **Trayectoria parabólica** (velocidad más aceleración): esa tarde el
  movimiento real fue recto, y la aceleración estimada con imágenes seguidas
  es casi todo ruido. En la prueba, peor que la recta (acierto de 0,13 frente
  a 0,21 a 60 minutos; con velocidades medidas entre imágenes reales, que son
  ruidosas, así que la comparación no es del todo justa).
- **Usar la imagen de la advección de Meteocat tal cual en la primera hora**
  y seguir desde ella en la segunda: en la zona acierta parecido a 60 minutos
  (Brier 0,136 frente a 0,126 de la flecha de cerca) y peor a 120 (0,257
  frente a 0,214), y obliga a pedir a Meteocat más teselas en cada pasada.
- **Correlación de fase en un cuadro más pequeño** (150 km): con poca lluvia
  salta (rumbos de 331°, 145°, 183° en la misma tarde); 19 km de error.
- **Medir a 40 o a 100 km**: a 40 km, igual que a 60 (7,8 y 8,0 km de error)
  pero con menos lluvia para medir; a 100 km, peor (10,3 km).
- **Buscar saltos de hasta 120 km/h**: en la imagen de las 16:24 una tormenta
  lejana coincidía más (0,52) que la lluvia de cerca (0,47) y daba 120 km/h
  hacia el noroeste. Por eso solo saltos de hasta 60 km.

## Consecuencias

- La flecha, la hora de llegada y la línea «cap a…» de la página de casa
  salen de la lluvia que puede llegar al trayecto.
- Unas 0,25 segundos más de cálculo por pasada; ninguna petición más a
  Meteocat.
- Lluvia a más de unos 67 km/h (60 km en los 54 minutos entre las dos
  imágenes): se mide en el cuadro de 300 km, como antes.

## Evidencia

Las 29 imágenes del radar de Meteocat de 13:24 a 16:18 del 06-10-2026 y las
26 advecciones (previsiones a 6 y 60 minutos), sacadas de la caché del NAS.
Están en `calibracio/dades/`, fuera del repositorio. La prueba se repite con
`calibracio/moviment_radar.py`.

- Movimiento real: la traslación que mejor lleva cada imagen a la de 60
  minutos después, en 60 km alrededor de casa. Media, 37 km/h hacia 69°.
- Flecha según dónde se mida la advección (16 casos, error a 60 minutos):
  cuadro de 300 km, 16,3 km; lluvia a 60 km o menos, 8,0 km.
- Coincidencia entre las dos imágenes de la advección con el salto elegido:
  de 0,56 a 0,79 en las 25 primeras.
- Acierto en 97 puntos, cada 10 km a menos de 55 km de casa (probabilidad de
  la página contra si llovió en el punto; Brier, mejor cuanto más bajo):

  | A 60 minutos (n = 1.552) | Brier | Aciertos | Falsas alarmas | Lluvias sin anunciar |
  |---|---|---|---|---|
  | Lluvia quieta | 0,179 | 64 | 122 | 213 |
  | Cuadro de 300 km (antes) | 0,184 | 113 | 223 | 164 |
  | Lluvia de cerca (ahora) | 0,126 | 184 | 173 | 93 |

  | A 120 minutos (n = 582) | Brier | Aciertos | Falsas alarmas | Lluvias sin anunciar |
  |---|---|---|---|---|
  | Lluvia quieta | 0,194 | 8 | 32 | 97 |
  | Cuadro de 300 km (antes) | 0,279 | 18 | 118 | 87 |
  | Lluvia de cerca (ahora) | 0,214 | 37 | 105 | 68 |

  Aciertos, falsas alarmas y lluvias sin anunciar, con probabilidad del 50 %
  o más. Llovió en el 18 % de los casos.
- En casa no llovió. A 60 minutos, la página daba el 50 % o más en 2 de 16
  casos con la flecha de antes; con la de ahora serían 6, y con el movimiento
  real, 4: la lluvia iba hacia casa y se deshizo por el borde norte antes de
  llegar.

## Riesgos y limitaciones

- **No arregla el anuncio fallido de esa tarde en casa**, que no fue un error
  de trayectoria: la lluvia que se deshace o que nace no se ve llevando la
  imagen hacia delante, con ninguna flecha.
- A 120 minutos, llevar la lluvia hacia delante acertó menos que dejarla
  quieta (0,214 frente a 0,194), y ni con el movimiento real (0,158) mejoró a
  decir siempre la frecuencia media (0,148). Una sola tarde: se revisará con
  el registro.
- Una sola tarde y un solo episodio, con los casos de puntos vecinos
  parecidos entre sí. Los umbrales (60 km, 30 %) salen de esa tarde.
- Sigue siendo una sola flecha: con corrientes distintas dentro de los 60 km,
  se equivoca en una de ellas.

## Validación

`tests/test_nowcast.py`: la lluvia de cerca manda sobre una masa lejana mayor
que va en otra dirección; con poca lluvia cerca, lluvia demasiado rápida o
manchas que no se parecen, se vuelve al cuadro de 300 km. Y la prueba de
Evidencia, con el código definitivo.
