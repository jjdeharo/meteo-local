# 40. Cabecera compacta y bloque único de avisos

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Con el INUNCAT en emergencia y un aviso amarillo de AEMET a la vez, la parte
alta de «El temps ara» y de «Si surts» acumulaba, en líneas separadas, el
título, los botones de página, el enlace de Telegram, dos cajas de aviso con
borde y fondo de color y la línea «Actualitzat a les…». En un móvil, la
temperatura quedaba al borde de la pantalla y la previsión no se veía sin
desplazarse. Juanjo trajo una propuesta de ChatGPT con una maqueta y pidió
aplicarla «sin pérdida de datos».

## Decisión

- **Navegación y Telegram en una fila** (`.barra`): los botones de página a
  la izquierda y, a la derecha, el enlace «Avisos a Telegram» con la campana
  de Lucide delante (Juanjo, 08-10-2026: «la campanita… es muy visual»). La
  palabra se queda porque el icono solo no se lee ni se entiende; lo que
  sobra es «com funciona». En móvil el enlace baja debajo de los botones.
  Modificado por el ADR 0050: desde la 3.28.0, «Avisos al mòbil» es la
  campana de la botonera de la cabecera y la fila solo lleva el menú.
- **Un solo bloque «Avisos actius»** (`blocAvisos`, en `web/comu.js`) con
  borde fino y sin fondo de color, y dentro cada aviso con la franja lateral
  de su nivel: roja para Protecció Civil, naranja o amarilla para la AEMET
  según el nivel. El título de cada aviso va en negrita (en color, el rojo y
  el naranja). El texto oficial de la AEMET sigue citado, en castellano y sin
  traducir (ADR 0033); se quita el «L'AEMET hi afegeix — avui:» y el día solo
  se dice si hay avisos de más de un día. El bloque no existe si no hay nada
  vigente. El risc calculado (`blocRiscos`) entra en el mismo bloque.
- **«Actualitzat a les… · propera…»** al pie de la tarjeta de ahora, en
  pequeño y con el «Mode avís» (la página tiene que decir cuándo se actualiza
  de verdad: Juanjo, 05-10-2026). En «Si surts», que no tiene esa tarjeta,
  sigue sobre los selectores, también en pequeño.
- **La tarjeta de ahora pierde la franja azul** y conserva todos los datos:
  lluvia de hoy, humedad, presión, viento con estación y hora, radar con
  fuente y hora.
- **La nota de Protecció Civil sobre los consejos de «Si surts»** se reduce a
  una línea que no repite el plan («sale repetido», Juanjo, 08-10-2026) y
  dice lo que importa: «El consell de cada mitjà surt només de la pluja i el
  vent previstos: no té en compte l'emergència de Protecció Civil (vegeu
  l'avís de dalt)». Sin «veredictes» («suena a decisión judicial»). El plan
  no entra nunca en el cálculo de los consejos: se muestra para que la
  persona decida (ADR 0038, punto 12).

## Alternativas descartadas

- **Acortar el texto de la AEMET** como en la maqueta («Hasta 20 mm en una
  hora»): parafrasea el aviso oficial; se mantiene la cita literal.
- **Un solo color para todo el bloque**: dos avisos de nivel distinto se
  verían iguales; la franja por aviso conserva el nivel.
- **La tarjeta de ahora de la maqueta** quitaba la lluvia del día, la presión,
  la estación del viento y daba «Radar Meteocat» (es RainViewer): no se sigue.

## Validación

- 214 pruebas (`tests/test_web.py`: la nota de Protecció Civil y
  `textAvisos`, que no cambia; `tests/test_montflorit.py`: traducciones y
  construcción de la web con el menú dentro de `.barra`).
- `probar-web` en Chromium, Firefox y WebKit, escritorio, móvil y tableta,
  claro y oscuro, en catalán y castellano (64 combinaciones), y axe-core sin
  incidencias en las cuatro páginas, el 08-10-2026. Juanjo vio las capturas
  antes de publicar.
