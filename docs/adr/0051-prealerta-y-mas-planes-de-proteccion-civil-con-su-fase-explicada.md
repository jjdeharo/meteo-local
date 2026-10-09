# 51. Prealerta y más planes de Protección Civil, con su fase explicada

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

La web solo mostraba los planes INUNCAT, VENTCAT y NEUCAT activados, en alerta
o emergencia. El 09-10-2026 Juanjo preguntó por las fases y pidió mostrar
también la prealerta, «para todos los planes», con «alguna forma fácil no
invasiva» de que se entienda qué es cada fase.

## Decisión

- **La prealerta se muestra.** El conjunto de datos oficial
  (`wj9c-j6vf`) la trae con `plaactivat` «NO», porque no activa el plan; la
  web la acepta igualmente (`planes_proteccion_civil`, en `prevision.py`).
  Si un plan sale repetido, se queda la fase más alta.
- **Planes**: INUNCAT, VENTCAT y NEUCAT, y del PROCICAT los riesgos de ola
  de calor, ola de frío, contaminación y viento (`C.PROCICAT_PC`). El riesgo
  de cada registro del PROCICAT lo dice su icono
  (`ico_PROCICAT_<RIESGO>.png`); sin riesgo reconocible, no se muestra. El
  filtro de zona de siempre (`afecta_la_zona`) se aplica a todos.
- **Fuera los planes de incidentes** (INFOCAT, TRANSCAT, PLASEQCAT, AEROCAT,
  CAMCAT, ALLAUCAT, RADCAT…) y el PROCICAT de pandemia y ferrocarril: los
  datos abiertos no dicen dónde ha pasado el incidente, y saldría uno de la
  otra punta de Cataluña igual que uno de al lado. Los incendios cercanos ya
  los dan Bombers y el Pla Alfa (ADR 0046); los trenes, «Si surts».
- **Franja del color de la fase**: gris (`--suau`) la prealerta, naranja la
  alerta y roja la emergencia. Antes, siempre roja.
- **Un «?» junto a la fase** (`ajudaFase`, en `web/comu.js`) despliega
  debajo una línea con lo que significa, resumida de la definición oficial del
  mismo conjunto de datos; sin ventana, igual con el dedo que con el ratón:
  - Prealerta: «Es preveu un risc a mitjà termini. El pla no està activat:
    només cal estar-ne pendent.»
  - Alerta: «El pla està activat: es preveu un risc important a curt termini,
    o hi ha afectacions que no són greus.»
  - Emergència: «El pla està activat per un risc greu per a la població:
    segueix les indicacions de Protecció Civil.»
- **La prealerta no avisa**: no pone la web en modo aviso, no cuenta en el
  riesgo ni en el aprendizaje (`pla_inuncat`) y no cambia los consejos de
  «Si surts»; ninguno de ellos la tenía en cuenta y siguen igual. En el bot
  solo sale si se pregunta (/avisos_actius), como en la web.
- Un plan del PROCICAT en alerta o emergencia pone la web en modo aviso, como
  ya lo hace cualquier aviso de la AEMET, también el de calor.

## Alternativas descartadas

- **Todos los planes del conjunto de datos**: ver arriba, sin zona fiable.
- **Leer el PDF de cada comunicado para saber la zona de los incidentes**:
  posible, pero más trabajo y frágil; queda para cuando haga falta.
- **Definiciones en un rótulo emergente**: en el móvil no se ven.

## Evidencia

- Descripción del conjunto de datos (API de Socrata,
  `api/views/wj9c-j6vf.json`, consultada el 09-10-2026): «Plans de protecció
  civil en fase de prealerta, alerta o emergència» y la definición de cada
  fase; `plaactivat` «Indica si el Pla està activat o no».
- Comunicados del CECAT de noviembre de 2024 al 08-10-2026 (listado del
  contenedor `documents.dadesobertes.gencat.cat/cecat`): 1.405, de 13 planes;
  INUNCAT 407, PROCICAT 292, VENTCAT 137, AEROCAT 125, INFOCAT 120, NEUCAT 55…
  Iconos del PROCICAT: contaminació, ferrocarril, onada de calor, onada de
  fred, pandèmia y vent.
- Pla INUNCAT (actualización de 2017, apartado 4.1): fases de prealerta,
  alerta y emergencia.
- Hipótesis pendiente: que los registros del PROCICAT lleven siempre el icono
  de su riesgo; si no, no se muestran (no se inventa el riesgo).

## Validación

- 264 pruebas: `tests/test_avisos.py` (prealerta no activada, PROCICAT por
  riesgo, fase más alta, zona) y `tests/test_web.py` (color por fase y texto
  del «?»).
- Firefox y Chromium, móvil y escritorio, claro y oscuro, catalán y
  castellano, con un plan simulado en cada fase: el «?» se abre, sin
  desbordamiento y axe-core sin incidencias. axe detectó que el título
  naranja no se leía en tema oscuro (también en los avisos naranjas de la
  AEMET): ahora usa `--taronja-text`, más claro en ese tema.
