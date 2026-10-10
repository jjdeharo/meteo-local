# 64. Viento de ahora con las estaciones vecinas, en prueba

Fecha: 2026-10-10 · Estado: aceptado (la página aún no lo muestra)

## Contexto

El viento de «Ara a Montflorit» es el de la estación de Meteocat de Sant
Cugat (ADR 0037), porque el anemómetro de la estación de casa no funciona
bien. El 10-10-2026 Juanjo preguntó por qué no se toma de una estación más
cercana y, ante la respuesta, pidió: «¿no se podría hacer la media de las
estaciones vecinas? o una media ponderada… o lo que quieras pero que las
tengan en cuenta».

Las cuatro vecinas de Weather Underground (ADR 0060) están a menos de un
kilómetro y dan una lectura cada cinco minutos; Sant Cugat da
una media cada media hora y llega con retraso: hacia las 14:00 del 10-10 la
última era la de 13:00 a 13:30. Pero los anemómetros de las vecinas no están
a 10 m ni en campo abierto, como pide la norma y como están los de Meteocat.
Del 3 al 10-10-2026, en medias horas (`vent_veines.py omple` y `apren`):

| Estación | Factor hasta Sant Cugat | Correlación | Medias horas a cero cuando en Sant Cugat sopla |
|---|---|---|---|
| Puig de la Guàrdia (ICERDA18) | 1,29 | 0,82 | 3 % |
| A 600 m al nord-est (ICERDA48) | 1,87 | 0,75 | 4 % |
| A 400 m al nord (ICERDA28) | 3,26 | 0,67 | 36 % |
| A 1 km a l'est (ICERDA6) | 3,70 | 0,45 | 68 % |

Una media simple daría menos de la mitad del viento real: dos vecinas están
resguardadas y casi siempre marcan cero.

## Decisión

- **`vent_veines.py` estima el viento de ahora con las vecinas que sirven**:
  cada una, multiplicada por el factor que la lleva a Sant Cugat (mínimos
  cuadrados por el origen), y la media de todas, con un peso inverso a su
  error cuadrático. Solo cuentan las que tienen dos días de datos, una
  correlación de 0,6 o más y como mucho un 25 % de ceros cuando en Sant Cugat
  sopla (5 km/h o más). Hoy salen el Puig de la Guàrdia y la del nordeste.
  La racha, igual, con las rachas.
- **Se aprende cada día** dentro de `aprenentatge.py diari`, con los últimos
  60 días del registro `vent-mitges-hores.csv` (medias horas de las cuatro
  vecinas, de Sant Cugat y de Sabadell; cada pasada apunta las de hoy y el
  aprendizaje completa Meteocat con el portal de datos abiertos). Lo aprendido
  va a `estat/aprenentatge/vent-veines.json`.
- **Se comprueba dejando fuera cada día**: error medio contra Sant Cugat de la
  estimación, de Sabadell (otra estación oficial a 5 km) y de Sant Cugat de la
  media hora anterior (lo que enseña hoy la página, que llega con retraso).
- **La página sigue con Sant Cugat** hasta que Juanjo lo decida
  (`config.VENT_VEINES_ACTIU`, falso). La estimación se calcula en cada pasada
  y va en `vent_veines` de los datos, para compararla. Si se activa, la
  tarjeta dice «estacions veïnes» en lugar del nombre de la estación.
- **Aviso único**: cuando la comprobación tenga 12 medias horas con 15 km/h o
  más en Sant Cugat, el NAS envía a Juanjo las tres cifras y si la estimación
  acierta tanto o más (Juanjo: «¿te acordarás de mirar los resultados para
  tomar una decisión?»).

## Evidencia y validación

- Primera comprobación, del 3 al 10-10-2026, semana de calma (ninguna media
  hora con 15 km/h en Sant Cugat): error medio de la estimación 1,6 km/h; de
  Sabadell, 3,3; de Sant Cugat media hora antes, 1,0. Con poco viento, la
  estimación se parece más a Sant Cugat que Sabadell, pero menos que el dato
  anterior de la propia Sant Cugat. Falta viento de verdad para decidir.
- Pasada completa en el NAS el 10-10-2026 hacia las 14:00: estimación 9,9 km/h y
  rachas de 19,7, con las vecinas hasta las 13:59; Sant Cugat, 10,8 y 18,4,
  de 13:00 a 13:30.
- Pruebas: `tests/test_vent_veines.py` (medias horas completas, registro por
  columnas, portal en km/h, elección de vecinas, pesos, validación, aviso
  único y estimación de ahora).

## Riesgos e hipótesis

- **Hipótesis**: el factor de una vecina es estable con viento fuerte. Si los
  obstáculos frenan más el viento flojo que el fuerte, el factor cambiará; la
  comprobación con viento lo dirá.
- La dirección del viento importa: una vecina resguardada por el norte lo
  estará solo con viento del norte. El método no lo tiene en cuenta.
- Si una vecina cambia de sitio o de altura, su factor cambia; el aprendizaje
  diario lo recoge en unos días, y la correlación la deja fuera mientras tanto.
- Medir contra Sant Cugat supone que es la referencia buena; Sabadell sirve
  de contraste.

## Alternativas descartadas

- **Media simple de las vecinas.** Daría menos de la mitad del viento real.
- **Una sola vecina.** Si deja de enviar (el Puig de la Guàrdia lo hizo el
  9-10 por la noche), no hay dato; con dos, la otra sigue.
- **Activarlo ya.** Una semana de calma no basta para fiarse del factor.
