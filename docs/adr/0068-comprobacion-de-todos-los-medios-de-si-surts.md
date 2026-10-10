# 68. Comprobación diaria de todos los medios de «Si surts»

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

Desde el 08-10-2026 (ADR 0047) se apuntaba cada día en `moto.csv` qué nivel
de lluvia daba la regla de la moto y si llovió. Al preguntar Juanjo por el
coche y por ir a pie, se vio que nada más se comprobaba: ni la lluvia de los
otros medios ni el viento ni el frío. Juanjo, 10-10-2026: «si un medio como
la moto falla, es de suponer que el resto también lo hará ya que se rigen por
las mismas reglas, por eso es necesario no poner parches a un elemento sino
buscar que todo funcione bien», y «la web tiene que aprender de sus errores,
siempre y en todo lo que toca».

(Ese día también se aclaró por qué `moto.csv` no estaba por la mañana: se
borró el 09-10-2026 al retirar la estación de meteocerdanyola.com, de la que
salía su lluvia medida, y se rehízo solo a las 16:00 del 10-10, ADR 0058.)

## Decisión

- **`sortir.csv` sustituye a `moto.csv`** (que `verifica_sortir` borra): de
  cada hora pasada de 7 a 22 h y con las dos antelaciones de antes (al salir,
  de 1 a 3 horas; la vuelta decidida por la mañana, de 6 a 10), lo que mostró
  la página (probabilidad, milímetros, lluvia ahora, aviso de la AEMET, racha
  y temperatura) y lo que se midió (la lluvia, con las reglas de hora seca
  del aprendizaje, ADR 0058 y 0060; la racha máxima de la hora en Sant Cugat,
  `C.VENT_ESTACIO`, de `vent-mitges-hores.csv`; la temperatura de casa). Se
  rehace solo a partir del registro, que guarda todo desde el 08-10-2026.
- **Se guardan las entradas, no los niveles**: el resumen juzga con las
  reglas de ahora, así que si una regla cambia, se reevalúa todo lo
  registrado.
- **Las reglas, en Python como en la página**: `nivells_sortir` da para cada
  medio (a pie, bici o patinete, moto y coche; el transporte público no
  depende del tiempo) el nivel por lluvia, por racha y por frío, con los
  umbrales de `config.py` (`MOTO_*`, `SORTIR_*`). Una prueba
  (`tests/test_web.py`) ejecuta `avalua()` de `web/sortir.js` con 77 casos
  por medio y comprueba que da el mismo nivel; otra, que las constantes son
  las mismas.
- **El resumen** (`aprenentatge.py sortir`, y por Telegram una vez a los 28
  días): de cada medio y regla, cuántas horas dio cada nivel y en cuántas
  pasó (llovió, o la racha o el frío llegaron al umbral de «compte»); la
  moto, también con su regla de lluvia de antes del 08-10-2026.
- Desde hoy el registro guarda también la racha que mostró la página
  (`mostrat.ratxa`); antes se usa `wind_gusts_10m`, que es la misma.

## Pendiente: que aprenda

Esto mide; aún no corrige. Lo siguiente, a decidir con Juanjo: qué cuenta
como acierto en cada nivel (cuántas veces puede llover con «bé» o no llover
con «millor no») para que los umbrales se ajusten solos con el patrón de
siempre (propuesta, aviso y aplicación al día siguiente); y una corrección
aprendida de la racha del modelo con la medida, como la de la temperatura.

## Riesgos y limitaciones

- La racha medida es la de Sant Cugat, a unos kilómetros y con otra
  exposición: compara, pero no es la del barrio.
- Con pocos días de viento o de frío, el resumen dirá poco de esas reglas.
- La lluvia del coche (20 y 40 mm en una hora) es tan rara que tardará en
  haber casos.

## Validación

`tests/test_aprenentatge.py` (registro sintético: lluvia, una racha de 60
km/h, el registro viejo sustituido, una sola vez por hora, el resumen y su
aviso) y `tests/test_web.py` (mismas reglas que la página). Con una copia del
registro real del NAS del 10-10-2026: 61 horas de los cuatro medios.
