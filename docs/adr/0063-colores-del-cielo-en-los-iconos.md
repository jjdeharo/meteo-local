# 63. Colores del cielo en los iconos del tiempo, y lo seleccionado en azul

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

El 10-10-2026 Juanjo comparó la web con las aplicaciones del tiempo: «tienen
el sol amarillo, las nubes azules o rellenas de blanco… nuestra web es toda
gris y no solo da un aspecto demasiado uniforme sino que cuesta más de leer».
Pidió color en los iconos «manteniendo el estilo sobrio y profesional».

Hasta entonces los iconos de Lucide eran de un solo trazo: grises en la tabla
por horas y, en «Ara a Montflorit» y en la cabecera de cada tramo, del azul
de los enlaces, igual que la temperatura grande. Ese azul no distinguía un
sol de una nube y podía leerse como algo que se pulsa. La barra de la columna
«Prob.» existía desde la primera versión, pero con un 22 % de azul apenas se
veía.

## Decisión

- **Cada pieza del icono con el color que tiene en la realidad**, con los
  mismos iconos de Lucide separados en piezas: sol ámbar con relleno amarillo,
  nube gris azulada con relleno gris muy claro, lluvia y gotas en azul, nieve
  y granizo en celeste, luna gris violácea con relleno suave, rayo en ámbar.
  Se aplica a la tabla por horas, a la cabecera de cada tramo y a «Ara a
  Montflorit». La paleta son variables `--c-*` de `estil.css`, una por tema.
- **Lo que no tiene color natural queda en gris neutro**: termómetro,
  presión, viento, radar, y la temperatura grande, en el color del texto. Los
  botones, las pestañas y el conmutador de tema usan los mismos símbolos
  (`i-sun`, `i-cloud-sun`) y siguen del color del texto: los colores solo se
  activan dentro de `.taula-hores`, `.tram-hores > summary` y `.dades-ara`.
- **Un fenómeno destacado del tramo (tempestad, calor, rachas…) es un aviso**:
  su icono sigue entero del color de aviso, sin los colores del cielo.
- **La mínima en azul y la máxima en rojo** en el «16–21 °C» de cada tramo,
  como hace Meteocat (ADR 0043).
- **La probabilidad**: la barra pasa al 30 % del azul de la lluvia, y el
  número va en azul desde «possible» (20 %) y en negrita desde «pluja» (50 %),
  los mismos umbrales con que ya se coloreaba el texto del cielo
  (`PROB_POSSIBLE` y `PROB_PLUJA` de `casa.js`). Ese texto pasa también del
  azul de los enlaces al azul de la lluvia.
- **Lo seleccionado, en el azul de la web** (`--enllac`, el del icono de la
  aplicación y de la barra del navegador) en lugar de negro: las pestañas de
  página, las de «Consultes», el selector CA/ES y la campana en la página de
  avisos. Juanjo, al verlo con los iconos ya de color: «los colores de las
  pestañas El temps, Si surts, etc. son negros, ¿se puede mejorar?». Es la
  misma combinación de los botones de la ayuda (fondo azul, letra del color
  del fondo); en el tema oscuro, azul claro con letra oscura.
- **No cambian** los avisos (ya tienen su amarillo, naranja y rojo), los
  fondos, las tarjetas ni las páginas «Si surts» y «Consultes»: allí los
  iconos marcan categorías de una lista, no el tiempo. La regla del 09-10 que
  pone el icono encima del texto en pantallas de 400 px o menos (ADR 0041) se
  mantiene.

El color nunca es lo único que informa: el texto sigue diciendo «Serè»,
«Pluja feble» o la cifra.

## Evidencia y validación

- Contraste de los contornos sobre la tarjeta (mínimo 3:1 para elementos
  gráficos, WCAG 1.4.11). Tema claro sobre blanco: sol `#c76f00` 3,7; nube
  `#64748b` 4,8; lluvia `#2563eb` 5,2; nieve `#0284c7` 4,1; luna `#5b61b8` 5,5.
  Tema oscuro sobre `#1b2129`: todos por encima de 6, menos la máxima `#f87171`,
  5,9. El ámbar de Tailwind (`#d97706`) se quedaba en 3,0 sobre el fondo de
  la página y se oscureció.
- Texto sobre la barra de probabilidad (mínimo 4,5:1): con la barra al 30 %,
  el azul de la lluvia de los iconos daba 3,3 en claro y 3,6 en oscuro; por eso
  el texto usa `--c-aigua-text`, `#1e40af` (5,6) y `#93c5fd` (5,1).
- Lo seleccionado: letra `#f6f7f9` sobre `#1d4ed8`, 6,3:1; en oscuro,
  `#12161c` sobre `#8ab4ff`, 8,7:1.
- axe-core 4.13 (WCAG 2.1 AA) sobre la vista previa (página del tiempo en
  catalán y castellano, «Consultes» y avisos), en los dos temas, con los
  tramos abiertos y lluvia simulada: sin infracciones.
- Visto en Chromium, Firefox y WebKit en móvil, en claro y oscuro.
- Prueba `test_icones_del_cel_amb_els_seus_colors`: cada icono del cielo que
  usa `casa.js` lleva sus colores en `casa.html`, y la paleta está en los dos
  temas.

## Consecuencias

- Unos 12 símbolos de `casa.html` llevan ahora las piezas separadas, con
  `style="stroke:var(--ic-…,currentColor)"`. Fuera de las zonas con color, el
  valor por defecto es el de antes (trazo del color del texto y sin relleno).
- Un icono nuevo del cielo tiene que llevar sus piezas con las variables
  `--ic-*`; la prueba lo exige para los que use `casa.js`.
- La página crece 4,7 KB sin comprimir, unos 0,9 KB con la compresión con que se sirve (gzip).
