# 10. Modo aviso: actualización al ritmo del radar

Fecha: 2026-10-05 · Estado: aceptado · Actualizado el 06-10-2026 (ADR 0020):
cada 6 minutos, al ritmo del radar de Meteocat

## Contexto

La página de casa se actualizaba cada hora y la del trayecto cada media hora.
El 05-10-2026 la lluvia en Montflorit pasó de casi nada a 26 mm/h en veinte
minutos (de 9:00 a 9:20). Juanjo preguntó si en situaciones de riesgo no
convendría actualizar más a menudo.

## Decisión

- **Modo aviso** cuando se da cualquiera de estas cosas
  (`motivos_modo_aviso` en `prevision.py`): aviso de AEMET vigente en el
  Vallès, plan de Protección Civil en alerta o emergencia, lluvia en alguna
  estación (Montflorit o Meteocat), lluvia en el radar a menos de 15 km
  (`RADAR_AVISO_KM`) o lluvia que el radar llevado hacia delante ve llegar a
  casa en la próxima hora (ADR 0019).
- **En modo aviso, cada 6 minutos** (`MODO_AVISO_INTERVALO_MIN`): la página de
  casa todo el día y la del trayecto dentro de sus franjas. Es el ritmo del
  radar de Meteocat, la imagen principal desde el ADR 0019; más deprisa no
  sirve. Hasta el 06-10-2026 era cada 10 minutos, el ritmo de RainViewer, y
  no se podía bajar porque GitHub Pages admite unas 10 publicaciones por hora;
  ahora los datos van a IONOS (ADR 0020).
- **Con 3 minutos de desfase** (:03, :09, :15…; `MODO_AVISO_DESFASE_MIN`), para
  coger siempre la imagen nueva: Meteocat la saca a :00, :06, :12… y la publica
  unos 13-14 minutos después. Es la misma idea que propuso Juanjo con
  RainViewer («puedes actualizar un minuto después de que se actualice»), con
  un intervalo fijo que no se desplaza respecto a las imágenes.
- **El horario lo decide un solo sitio:** cada publicación escribe su horario
  en los datos (`horari`, con `cada_min`, `desfase_min` y `mode_avis`), la web
  lo muestra («Mode avís: dades cada 6 min») y el reloj del NAS lo lee con
  `que_toca.py` para decidir qué hacer en cada minuto. Lo que dice la página y
  lo que se hace no pueden separarse.
- **La decisión de la mañana** se sigue recalculando en la pasada de las 7:31:
  el corte es el final de la ida más el desfase y dos minutos.

## Alternativas descartadas

- **Cada 11 minutos:** el minuto de actualización iría cambiando respecto a
  las imágenes del radar; unas veces cogería la nueva y otras no.
- **Cada 10 minutos siempre:** sin riesgo no aporta y multiplica las consultas.

## Consecuencias

En un día de aviso, la estación de Montflorit pasa de 24 a hasta 144
consultas (unos 380 KB cada una), y el registro guarda más líneas. Con un plan
de Protección Civil activado sin hora de fin, el modo aviso dura hasta que lo
desactivan.

## Evidencia

- Medida del 05-10-2026: la imagen de las 11:10 ya estaba disponible a las
  11:10:47; el archivo de RainViewer indicaba la de las 11:00 generada a las
  11:00:23.

## Riesgos y limitaciones

- Si RainViewer se retrasa más de un minuto, esa pasada coge la imagen
  anterior; la siguiente, diez minutos después, ya tiene la nueva.

## Validación

Pruebas automáticas del horario normal, del modo aviso con desfase, del paso
por las 23:50 y de las razones que activan el modo aviso
(`tests/test_horario.py`).

## Cambio del 09-10-2026: cómo se dice en la página

Desde la 3.41.0, la línea de actualización (arriba en las tres páginas, ADR
0040) dice solo «Mode avís» con un «?» al lado, el mismo de los planes de
Protección Civil (`botoAjuda` en `web/comu.js`). Al pulsarlo, debajo: «Quan
hi ha un avís de l'AEMET, un pla de Protecció Civil en alerta o emergència,
pluja a Montflorit o pluja al radar a menys de 15 km, la pàgina s'actualitza
més sovint: cada 6 minuts en lloc de cada 15, al ritme de les imatges del
radar.» Los 15 km y los 15 minutos van en los datos (`radar_km` y
`normal_min` del horario, `prevision.horario`), para que el texto siga a
`config.py`. Juanjo, 09-10-2026: «como la gente no sabe qué es modo aviso,
un ? que al pulsarlo salga la descripción». Antes decía «Mode avís: dades
cada 6 min.», y fuera del modo aviso, «Dades en directe cada 15 min.», que
se quita porque la próxima hora ya lo dice.

## Cambio del 10-10-2026: «Seguiment de prop»

En la página, el modo aviso se llama «Seguiment de prop» («Seguimiento de
cerca»), con el mismo «?» que explica cuándo y por qué. Juanjo: «modo aviso
no me gusta, ¿qué tal modo alerta Montflorit?». «Alerta» se descartó porque
es el nombre de una fase de los planes de Protección Civil que la misma
página muestra, y se habría leído como una alerta oficial. En el código y en
los datos sigue siendo `mode_avis`. Desde la 3.49.0, un plan sin motivo
meteorológico a la vista no lo activa (ADR 0062).

## Cambio del 10-10-2026, por la tarde: «Mode normal» y «Mode vigilància»

Juanjo: «no me gusta de prop, no dice nada», y pidió que la línea de la
actualización empezara por el modo, con un «?» que explicara la diferencia
entre los dos y, en el modo aviso, el motivo entre paréntesis. Los nombres
son «Mode normal» y «Mode vigilància» («Modo normal», «Modo vigilancia»):
vigilancia dice qué pasa (hay algo cerca y la página lo mira más a menudo).

- **Una línea propia para el modo**, encima de «Actualitzat a les… ·
  propera…», igual en los dos modos, para que la página no dé un salto al
  cambiar de uno a otro. Medido en el móvil (360-412 px): con el modo delante
  de la hora, la línea ocupaba dos en cualquier forma que conservara
  «actualitzat»; así son siempre dos, partidas por el sitio que toca.
- **El motivo entre paréntesis**, con los nombres de `motivos_modo_aviso`
  traducidos («Mode vigilància (pluja al radar)»; varios, separados por
  comas). El «?» va pegado a la última palabra para que no baje solo.
- **El «?» en los dos modos**, con el mismo texto: «Mode normal: la pàgina
  s'actualitza cada 15 minuts. Mode vigilància: s'actualitza cada 6 minuts,
  just després de cada imatge nova del radar de Meteocat. La pàgina es posa
  en mode vigilància quan hi ha un avís de l'AEMET, un pla de Protecció Civil
  en alerta o emergència, pluja a Montflorit o pluja al radar a menys de
  15 km. Quan ja no hi ha res d'això, torna al mode normal.» Juanjo corrigió
  la primera redacción («hi passa sola no queda bien… ninguno se entiende»):
  se nombra cada modo con todas las letras, sin pronombres.
- **El horario de los datos lleva siempre los dos ritmos** (`normal_min`,
  `avis_min`) y la distancia del radar (`radar_km`), también en modo normal,
  para que el «?» pueda explicarlos; con datos de antes, los valores de
  siempre.
- Sustituye a la decisión del 09-10-2026 de no decir nada en el ritmo normal.
