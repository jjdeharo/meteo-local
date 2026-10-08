# 49. Final de la lluvia según el radar: pendiente de datos

Fecha: 2026-10-08 · Estado: aceptado (se muestra o no cuando haya datos)

## Contexto

Cuando llueve, la tarjeta «Ara» dice «Pluja a sobre». Juanjo preguntó si
podía decir también cuándo se prevé que acabe. El radar llevado hacia
delante (ADR 0019) ya da, cada 5 minutos y hasta 2 horas, la probabilidad de
lluvia en casa; solo se usaba para la llegada.

## Decisión

- **Regla propuesta** (`fi_pluja.py`): el final previsto es el primer
  momento, desde la pasada, en que la probabilidad baja del 20 % durante 15
  minutos seguidos; si no pasa en las 2 horas del radar, «no s'acaba en 2
  hores».
- **No se muestra hasta comprobarla.** Desde el 08-10-2026 el NAS guarda la
  lluvia de Montflorit cada 5 minutos (`montflorit-5min.csv`, `registre.py`;
  la estación solo ofrece las últimas 24 horas). Cada día, con el ajuste del
  aprendizaje, `fi_pluja.py` compara la regla con lo que pasó en cada pasada
  registrada mientras llovía (`radar-fonts-*.jsonl`, con el radar que usaba la
  página). Con 5 episodios de lluvia, manda a Juanjo las cifras una vez
  (aciertos a 15 minutos o menos, demasiado pronto, demasiado tarde, error
  medio y aciertos de «no s'acaba en 2 hores») para que decida si se muestra.
  `python3 fi_pluja.py resum` las da en cualquier momento.

## Alternativas descartadas

- **Mostrarlo ya**: sería publicar un dato sin comprobar (ver Evidencia).
- **Comprobar con la estación de casa**: su pluviómetro no marca bien la
  lluvia débil (ADR 0017), que es justo la del final de un episodio.
- **Comprobar con las horas de Montflorit**: no dicen en qué minuto para.

## Consecuencias

`montflorit-5min.csv` crece unos 9 KB al día y va en la copia diaria del
registro (ADR 0044).

## Evidencia

Comprobación del 08-10-2026 con lo registrado (un solo episodio, el 6 de
octubre por la noche, 29 pasadas): con la estación de casa como verdad (lluvia
de 20:25 a 22:30 y de 23:30 a 23:45), el final previsto llegaba entre 40 y
90 minutos tarde; pero Montflorit recogió 0,8 mm de 22 a 23 h y otros 0,8 de
23 a 24 h, y el radar, desde las 21:57, daba el final entre las 23:12 y las
00:05. Con un solo episodio y sin la lluvia minuto a minuto de Montflorit no
se puede saber si acierta.

## Riesgos y limitaciones

- El radar solo desplaza la lluvia que hay: no ve que un chubasco crezca o se
  deshaga; acierta más con lluvia que pasa que con tormentas que nacen encima.
- El círculo que se mira crece con la antelación: puede adelantar el final a
  una hora vista.
- Cinco episodios dan una cifra orientativa.

## Validación

`tests/test_fi_pluja.py` (tramos de 5 minutos completos, episodios y pausas,
final previsto, cifras y aviso una sola vez).
