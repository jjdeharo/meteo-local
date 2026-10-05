# 11. Páginas que se ponen al día solas; el trayecto, solo en su franja

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

Las páginas leían los datos una sola vez, al abrirlas: quien las tenía
abiertas veía datos viejos aunque el NAS ya hubiera publicado otros. Además, la
página del trayecto enseñaba la decisión de la mañana o el tiempo de la vuelta
a cualquier hora, también de noche, cuando no se actualiza. Juanjo pidió que
la página se actualice sola en el periodo en que cambia y que la del trayecto
solo informe en su horario: fuera de él, que diga cuándo vuelve a
actualizarse y enlace al tiempo en casa.

## Decisión

- **Lectura según el horario de los datos** (`carrega` en `web/comu.js`): tras
  cada actualización prevista (`horari` de los datos, el mismo que sigue el
  NAS, ADR 0010), la página vuelve a leer el JSON dos minutos después
  (`ESPERA_PUBLICACIO_MIN`). Si aún no ha llegado, lo intenta cada minuto
  hasta diez veces. Fuera del horario no lee nada. Al volver a una pestaña
  oculta (el móvil para los temporizadores), lee si ya tocaba.
- **Trayecto solo en franja** (`franjaActiva` en `web/app.js`): de 5:00 a
  7:30 y de 13:00 a 15:30, más el desfase y la espera de publicación. Fuera de
  ellas, o con datos anteriores al inicio de la franja, la página dice
  «Propera actualització: avui/demà a les HH:MM», las franjas y un enlace a
  `casa.html`. Al acabar la franja cambia sola.

## Alternativas descartadas

- **Consultar el JSON cada minuto siempre:** 1.440 lecturas al día por
  pestaña para unas 30-80 publicaciones; seguir el horario da lo mismo.
- **Recargar la página entera:** pierde el desplegable abierto y la posición.

## Consecuencias

Con el plan de Protección Civil activado fuera de franja, la página del
trayecto no lo enseña; lo enseña la de casa, a un clic.

## Evidencia

- Registro del NAS del 05-10-2026: la publicación acaba a los 10-21 s del
  minuto previsto (p. ej. «15:01:21 publicado»).
- API de GitHub Pages (`pages/builds`): las compilaciones de esa tarde tardan
  entre 22 y 44 s. Con dos minutos, los datos nuevos ya están servidos.

## Riesgos y limitaciones

- Si una compilación de GitHub Pages falla (hubo una a las 15:51 del
  05-10-2026), la página reintenta diez minutos y espera a la siguiente.

## Validación

`tests/test_web.py` (próxima lectura, también tras la última del día) y
`probar-web` en Chromium, Firefox y WebKit, dentro y fuera de franja.
