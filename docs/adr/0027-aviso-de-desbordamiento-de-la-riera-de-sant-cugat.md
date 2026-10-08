# 27. Aviso de desbordamiento de la riera de Sant Cugat

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

La riera de Sant Cugat nace en Collserola, en la zona de Les Planes, cruza
Sant Cugat y pasa por Montflorit. Su cuenca tiene unos 50 km²
([Wikipedia](https://es.wikipedia.org/wiki/Riera_de_San_Cugat)). Se ha
desbordado otras veces, pero en dos semanas de 2026 lo hizo dos veces con más
fuerza que nunca. Juanjo preguntó si se podía prever «mirando los registros
de Sant Cugat y los locales de Montflorit», con un margen de horas, y aprobó
la propuesta: «prepáralo así y lo vamos ajustando».

La ACA no mide el nivel de la riera: su aforo más cercano está en el Ripoll,
en Montcada, aguas abajo. Solo queda la lluvia.

## Decisión

- **El índice** (`riera.py`, calculado en cada pasada de la página de casa y
  guardado en `casa.json`, fuera de la web pública): la lluvia de 3 horas más
  alta que se alcanzará en la hora siguiente en Sant Cugat. Junta la lluvia
  semihoraria de la estación de Meteocat de Sant Cugat (XV), en la página de
  meteo.cat, y la que el radar ve y lleva hacia delante sobre el centro de la
  cuenca (nowcast.py, ADR 0019; lugar «conca»). El radar cubre también la
  media hora que la estación va por detrás.
- **Umbrales** (`config.py`): desde 20 mm en 3 horas se abre un episodio y
  se apunta; con 35 mm, aviso de **atención** por Telegram, y con 50 mm en 3
  horas y 60 en 6 (el mismo índice, con 6 horas), de **peligro**. La
  condición de 6 horas se añadió el mismo día (versión 2.19.0) al saber que
  el 13-09-2025, con 52 mm en 3 horas y nada antes, la riera no se desbordó.
  Hay un aviso por nivel y episodio. El episodio acaba tras 3 horas por debajo
  de 20 mm, y entonces se apunta en `/estat/registre/riera.csv` con sus
  máximos y una columna `desbordament` que se rellena a mano con lo que pasó.
- **El final se dice** (Juanjo, 08-10-2026: «para quitar la ansiedad», sin
  que «se convierta en una sucesión de mensajes de alerta y contraalerta»):
  cuando se cierra un episodio en el que hubo aviso, se manda un solo
  mensaje, por los mismos medios (`missatge_fi` en `riera.py` para Juanjo,
  `text_riera_fi` en `avisos_bot.py` para el canal y el bot): «ha passat el
  perill de desbordament» si llegó a peligro, «ja no hi ha risc de
  desbordament» si solo hubo atención, con la lluvia de las últimas 3 horas
  y «si torna a ploure fort, tornarà l'avís». Las 3 horas de calma del
  cierre son las que evitan el vaivén: mientras el episodio sigue abierto no
  se repite ningún nivel, y si después vuelve a llover fuerte es un episodio
  nuevo, con sus avisos. Un episodio que solo llegó al registro (20-35 mm)
  no manda nada, tampoco al acabar.
- **Lo que se dice pero no decide**: la lluvia de 3 horas del Observatori
  Fabra (D5), en la cresta de Collserola junto a Les Planes, donde nace la
  riera, y la de Montflorit (meteocerdanyola.com), minuto a minuto y sin
  retraso, en la parte baja. Ninguna tiene aún casos para fijarle un umbral.
- **El mensaje**, en catalán: lo medido en Sant Cugat y hasta qué hora, lo que
  añade el radar, el Fabra y Montflorit, y la referencia de los desbordamientos
  conocidos.
- A cualquier hora, como el aviso de lluvia (ADR 0022). Lo hace el programa en
  el NAS, sin IA y sin coste.

## Alternativas descartadas

- **Solo lo medido**: el aviso llega tarde (ver Evidencia).
- **Lluvia de la cuenca como media de Sant Cugat y el Fabra**: el 29-04-2024
  llovió sobre todo en Sant Cugat (53 mm frente a 22 en el Fabra) y la media
  no llegaba al umbral; Sant Cugat solo marca los tres casos.
- **Peligro solo con la lluvia de 3 horas** (versión 2.18.0): habría avisado
  en falso el 13-09-2025.
- **Peligro con la lluvia de 24 horas o del Fabra**: también separan los
  cuatro casos, pero el 29-09-2026 casi toda la lluvia cayó en 2 horas; la de
  6 horas es la que menos retrasa el aviso.
- **Que Montflorit decida**: es la única estación sin retraso, pero recoge la
  lluvia de la parte baja y no hay historial para saber qué umbral le toca. El
  29-09-2026 la estación de casa marcó unos 120 mm en dos horas, frente a 67
  en Sant Cugat. Se apunta para decidirlo con datos.
- **Un modelo con la humedad del suelo o la lluvia de días antes**: con tres
  casos no se puede ajustar. El registro dirá si hace falta.
- **Publicarlo en la web pública**: el umbral es una hipótesis; un aviso de
  inundación para el barrio necesita estar comprobado.

## Consecuencias

- Hay que copiar `nas/reloj.sh` al NAS y reconstruir el contenedor.
- Dos o cuatro peticiones más a meteo.cat por pasada (Sant Cugat y el Fabra,
  hoy y, de madrugada, ayer).
- `casa.json` lleva `riera`, y el nowcast, un lugar más («conca»).

## Evidencia

Lluvia de Sant Cugat (XV) y del Fabra (D5) del portal de datos abiertos de la
Generalitat (conjunto `nzvn-apee`), 2013-2026, por medias horas.

| Desbordamiento | Qué pasó | XV 3 h | XV 6 h | D5 3 h | Fin de las 3 h más lluviosas |
|---|---|---|---|---|---|
| 29-04-2024 | El agua llegó a la puerta de las casas (vídeo de Juanjo, 20:30) | 53 | 75 | 22 | 20:30 |
| 29-09-2026 | Entró en las casas; el Ayuntamiento cita el desbordamiento en Canaletes | 67 | 67 | 76 | 12:30 |
| 04-10-2026 | Entró en las casas a la 1-2; el Ayuntamiento lo cita en Montflorit | 67 | 104 | 43 | 02:00 |
| 13-09-2025 | **No se desbordó**: una foto de Juanjo del día 14 muestra que llovió, sin rastro de desbordamiento | 52 | 52 | 17 | 17:30 |

Lo que separa el 13-09-2025 de los desbordamientos es la lluvia de antes: fue
un chaparrón de 3 horas sobre suelo seco, con poca lluvia en Collserola (18 mm
en 24 horas en el Fabra, frente a 64 o más). Los tres desbordamientos tenían
67 mm o más en 6 horas. Del 11-05-2025 (48 mm en 3 horas) y del 06-11-2025
(38) no hay fotos; con la regla, ninguno de los dos daría peligro.

En los tres, el desbordamiento coincide con el final de las 3 horas más
lluviosas: la cuenca responde enseguida.

**Simulación con lo medido** (cada media hora desde 2013, con los 30 minutos
de retraso de la tabla de meteo.cat, sin radar porque no hay archivo):

- 51 episodios de 20 mm o más; 13 con atención y 5 con peligro en 13 años
  (con solo la condición de 3 horas eran 7). Los de peligro: 28-09-2014,
  15-11-2018, 29-04-2024, 29-09-2026 y 04-10-2026. De los dos primeros no se
  sabe si hubo desbordamiento.
- Margen en los tres casos: la atención habría llegado a las 20:00 (30 minutos
  antes del vídeo), a las 12:00 (con el desbordamiento ya en marcha) y a las
  0:30 (de 30 a 90 minutos antes). El peligro, siempre después.
- Con la hora siguiente conocida (el radar perfecto), la atención habría
  llegado a las 18:30, a las 10:30 y a las 23:00: de 1 a 3 horas antes. El
  radar real queda entre los dos extremos.

Fuentes del desbordamiento: notas del Ayuntamiento de Cerdanyola del
[29-09-2026](https://www.cerdanyola.cat/actualitat/els-serveis-municipals-treballen-recuperar-la-normalitat-despres-de-lepisodi-de-pluges)
y del [04-10-2026](https://www.cerdanyola.cat/node/20295).

## Riesgos y limitaciones

- **Cuatro casos** (tres desbordamientos y uno sin desbordamiento): los
  umbrales son una hipótesis. No se sabe qué pasó en la mayoría de los
  episodios de la simulación.
- El margen depende del radar: la lluvia que nace encima de la cuenca no se
  ve venir, y la relación de Marshall-Palmer suele quedarse corta con los
  chaparrones fuertes.
- Si meteo.cat no responde o la estación va más de 2 horas atrasada, no hay
  índice ni aviso.
- La estación de Sant Cugat está en el centro de la cuenca; una tormenta solo
  en la cabecera la ve el Fabra, que no decide.

## Validación

`tests/test_riera.py`: acumulados por medias horas enteras con datos del
04-10-2026, índice sin radar, el radar que adelanta el peligro, los niveles
de los cuatro casos conocidos, el chaparrón sobre suelo seco que solo da
atención, el hueco entre
estación e imagen, estación atrasada, un aviso por nivel, peligro sin
atención previa, cierre y registro del episodio, lluvia débil, y que la web
pública no lleve la riera. Prueba real el 07-10-2026 sin lluvia: índice 0.
Simulación de 2013-2026 (arriba). Pendiente de ver un aviso real.
