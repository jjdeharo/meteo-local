# 22. Aviso por Telegram antes de que llueva en casa

Fecha: 2026-10-06 · Estado: aceptado; el envío a Juanjo, retirado el 08-10-2026

**08-10-2026:** Juanjo recibía este aviso dos veces, por Telegram y como
notificación del navegador (ADR 0048), que sale de la misma cuenta
(`avisos_bot.py` usa `pluja_arriba.compara`). Pidió quitar el de Telegram.
`pluja_arriba.py` ya no lo manda; sigue apuntando cada episodio y si acertó.
Lo que sigue describe cómo se decidía el aviso, que es el mismo de los
suscriptores.

## Contexto

Juanjo pidió «un aviso por telegram 10 minutos antes de llover». La página
de casa ya calcula en cada pasada cuándo llegaría a casa la lluvia que ve el
radar (ADR 0019) y lo enseña en «Ara a casa», pero no avisa.

Lo que limita la antelación es el propio radar: Meteocat publica cada imagen
unos 13 minutos después de tomarla, y en modo aviso el NAS hace una pasada
cada 6 minutos, justo después de cada imagen. Lo más reciente que se sabe
tiene, pues, unos 15 minutos, y entre una pasada y la siguiente pasan 6.

Al explicarle que los 10 minutos no podían ser exactos, respondió: «no pasa
nada si el aviso es 15 minutos antes, la idea es recibir una alerta con
antelación». Lo que importa es el margen, no el minuto.

## Decisión

- **Qué lo dispara** (`pluja_arriba.py`, tras publicar la página de casa): la
  llegada que da el radar llevado hacia delante para casa (primer momento con
  la mitad o más del círculo con lluvia, `radar.arriba` de `casa.json`). Se
  avisa cuando faltan `AVIS_PLUJA_MIN` (15) minutos más una pasada (6) o
  menos: el aviso sale entre 15 y 21 minutos antes de la hora prevista, para
  que siga llegando con margen si la lluvia se adelanta. Si
  el radar ya la ve encima y las estaciones aún no marcan, el aviso dice que
  puede empezar en cualquier momento.
- **Si ya llueve, no se avisa**: llueve cuando Montflorit o la estación de
  casa lo marcan.
- **Un aviso por episodio**: un episodio empieza cuando el radar anuncia la
  lluvia o cuando empieza a llover, y acaba tras `AVIS_PLUJA_REPOS_MIN` (60)
  minutos sin lluvia medida ni anunciada. Los chubascos seguidos no repiten
  el aviso.
- **A cualquier hora**, también de noche: no se pidió otra cosa.
- **El mensaje**, en catalán y en una línea: cuántos minutos faltan, la hora,
  si sería débil, moderada o fuerte (menos de 1, de 1 a 4 o más de 4 mm/h en
  la media hora siguiente a la llegada) y de qué imagen del radar sale.
- **Registro para saber cuánto acierta**
  (`/estat/registre/avisos-pluja.csv`): al acabar cada episodio se apunta si
  se avisó, para cuándo, cuándo empezó a llover de verdad y el resultado:
  «encert» (llovió en `AVIS_PLUJA_VERIFICA_MIN`, 45, minutos desde el
  aviso), «avís sense pluja» o «pluja sense avís». `python3 pluja_arriba.py
  resum` da el recuento.
- No interviene ninguna IA: es un programa en el NAS, sin coste.

## Alternativas descartadas

- **Apuntar a 10 minutos** (aviso entre 10 y 16 antes), como en la versión
  2.13.0: si la lluvia se adelanta unos minutos, el aviso llega justo o
  tarde, y eso es lo que Juanjo quiere evitar.

- **Avisar con lluvia «posible»** (un 20 % del círculo): más avisos en
  falso. Queda en el registro la base para decidirlo con datos.
- **Avisar desde los modelos o la probabilidad de la tabla**: dicen si
  lloverá en la hora, no en qué minuto.
- **Dentro de `riscos.py`**: aquello son situaciones de peligro, con otra
  lógica (niveles, fin del riesgo).
- **Un proceso aparte que mire el radar cada minuto**: el radar no da nada
  nuevo entre imagen e imagen.

## Consecuencias

- Hay que copiar `nas/reloj.sh` al NAS y reconstruir el contenedor.
- `casa.json` lleva un dato más, `radar.arriba_mm_h`.
- Cuando el registro tenga bastantes episodios se podrán ajustar el umbral
  y los minutos; hasta entonces son una hipótesis.

## Evidencia

- Retraso del radar: la imagen de las 09:42 UTC se publicó a las 09:54:24
  (ADR 0019); el 06-10-2026 a las 13:42, la última era la de las 13:30.
- Cadencia: `config.py` (`MODO_AVISO_INTERVALO_MIN = 6`); el modo aviso se
  activa con lluvia en el radar a menos de 15 km o que llegue a casa en la
  hora siguiente (`prevision.motivos_modo_aviso`).
- **Hipótesis sin comprobar**: que la llegada del radar acierte el momento
  con un margen de minutos. No hay archivo del radar para comprobarlo hacia
  atrás; lo dirá el registro.

## Riesgos y limitaciones

- **La lluvia que nace encima de casa no se avisa**: el radar solo lleva
  hacia delante la que ya existe. Tampoco ve la que crece o se deshace por
  el camino, y usa un solo movimiento para toda la zona.
- Los minutos son los de la hora prevista, no los reales: si la lluvia se
  adelanta o se retrasa, el margen cambia. Con más antelación, el radar se
  lleva más lejos (unos 30-36 minutos desde la imagen) y acierta algo menos.
- Si el radar de Meteocat se para, se usa RainViewer, con imágenes cada 10
  minutos: el aviso puede salir con menos margen.
- Fuera del modo aviso las pasadas son cada 15 minutos; el modo aviso se
  activa con lluvia a una hora de casa, así que solo afecta a la lluvia que
  aparece de golpe en el radar.
- Si el NAS o la publicación fallan, no hay aviso. Con datos de más de 15
  minutos no se avisa.

## Validación

`tests/test_pluja_arriba.py`: aviso entre 15 y 21 minutos antes, sin
repetir; acierto, aviso sin lluvia y lluvia sin aviso en el registro;
chubascos seguidos; lluvia encima según el radar; datos viejos; sin radar.
Prueba con los datos reales del 06-10-2026 a las 13:42 (sin lluvia
acercándose: no avisa). Pendiente de ver un aviso real.
