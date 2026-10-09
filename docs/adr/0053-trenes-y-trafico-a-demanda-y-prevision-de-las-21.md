# 53. Trenes y tráfico a demanda, y la previsión de la noche a las 21 h

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

En la 3.31.0 (ADR 0052) una carretera cortada cerca avisaba con los de
«Situacions de perill», y los trenes tenían su propia categoría de avisos
(«Trens de Cerdanyola (si no circulen)», ADR 0029 y 0034). Juanjo, el mismo
día: «yo no las incluiría en situación de peligro, no lo son»; propuso una
orden para el tráfico como la de los trenes y quitar los trenes de los avisos:
«el que le interese lo mira en el menú. Lo mismo se aplica a la aplicación».
Pidió también pasar la previsión de mañana de las 20 h a las 21 h, «sin que
los usuarios tengan que hacer nada», porque a las 21 es mejor previsión.

## Decisión

- **Trenes y tráfico no avisan: se consultan.** Fuera la categoría «trens» del
  bot (`TIPUS`), de la página «Avisos» del navegador (`avisos.js`,
  `subscripcio.php`, `push.py`) y la lógica que generaba esos avisos en
  `avisos_bot.py`, con su estado (`trens`) y el de los cortes (`talls`). Fuera
  también el aviso de carreteras cortadas y su bloque de `/avisos_actius`
  (`es_tall`, `TRANSIT_AVIS_KM`, `TRANSIT_AVIS_CAUSES`).
- **Orden `/transit`** en el bot, como `/trens`: las incidencias de la ficha
  del coche de «Si surts» (ADR 0052), con la carretera, el municipio y los
  textos del Servei Català de Trànsit tal cual, y el enlace a su estado del
  tráfico. En el menú de Telegram, «El trànsit a prop» («El tráfico cerca»).
- **A quien tenía los avisos de trenes se le dice una sola vez**, en su idioma:
  «Els avisos de trens ja no s'envien automàticament. Pots consultar l'estat
  dels trens quan vulguis amb /trens.» (`bot.py`, `migra`). Si Telegram no lo
  acepta, se reintenta a la vuelta siguiente; la categoría se quita al
  entregarlo. El 09-10-2026 era un suscriptor del bot; en el navegador, nadie.
- **La previsión de la noche, a las 21 h** (`HORES_RESUM`, `HORES` del PHP y
  `HORES_PUSH`). Quien la tenía a las 20 h pasa a las 21 h sin hacer nada; una
  página vieja que aún mande «20» se guarda como «21».

## Alternativas descartadas

- **Una categoría propia para los cortes de carretera** («Carreteres
  tallades»): coherente con los trenes, pero Juanjo prefirió que el tráfico,
  como los trenes, se consulte.
- **Dejar la categoría de trenes para quien ya la tenía**: dos formas de hacer
  lo mismo, y una opción que nadie más podría elegir.

## Consecuencias

- Nadie recibe aviso de un corte de carretera ni de un tren parado: se ven en
  «Si surts» y con /transit y /trens.
- Hay que volver a ejecutar `bot/instalar.sh` para que Telegram muestre
  /transit en el menú y la descripción nueva.
- Las capturas de la página «Avisos a Telegram» siguen mostrando el menú
  antiguo (ya estaban pendientes de rehacer).

## Evidencia

- Open-Meteo (`/data/<modelo>/static/meta.json`, consultado el 09-10-2026):
  AROME France HD e ICON-EU se calculan cada 3 horas (pasadas de las 2, 5, 8,
  11, 14, 17, 20 y 23 h, hora local) y están disponibles unas 2 h 40 min y
  2 h 50 min después (la de las 5 h, a las 7:40 y 7:52). La de las 17 h llega,
  pues, hacia las 19:40-19:50; como el NAS publica cada 15 minutos, a las 20 h
  a menudo aún no ha entrado, y a las 21 h siempre. La siguiente, la de las
  20 h, no llega hasta hacia las 22:40.
- Suscriptores el 09-10-2026 (solo recuentos): bot, 4, uno con trenes y uno con
  la previsión de las 20 h; navegador, 4, ninguno con trenes ni previsión.

## Validación

`tests/test_bot.py`: el menú ya no tiene trenes y ofrece las 21 h; /transit en
catalán y castellano, sin incidencias y fuera de `/avisos_actius`; la
migración pasa las 20 h a las 21 h, avisa una sola vez a quien tenía trenes y
le quita la categoría; `avisos_bot.py` ya no avisa de trenes y borra el estado
viejo. `tests/test_push.py` y `tests/test_transit.py`, al día.
