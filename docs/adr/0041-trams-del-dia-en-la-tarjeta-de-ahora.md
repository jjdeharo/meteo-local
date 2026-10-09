# 41. Tramos del día: resumen y tabla plegable

Fecha: 2026-10-08 (cambiado el 2026-10-09) · Estado: aceptado

## Contexto

Juanjo pidió ver «al principio, quizás debajo de los datos de ahora», la
probabilidad de lluvia con icono y cualquier fenómeno destacable (nieve,
temperaturas extremas…) por la mañana y por la tarde, para no tener que
leer la tabla de 24 horas. También que el botón «El temps ara» pasara a «El
temps», porque la página lleva además la previsión.

El 09-10-2026 pidió también partir la tabla de 24 horas, que hacía la
página muy larga, en desplegables por tramo: «se podría dividir la lista
del tiempo en mañana, tarde, noche como desplegables? […] con el primer
tramo desplegado por defecto». Con eso el resumen de la tarjeta repetía
lo mismo justo encima, y aprobó quitarlo de allí («vale, quítalo»). Al
verlo, pidió que el último tramo no quedara con pocas horas: «sería mejor
alargar la previsión»; y después, que el bot, el canal y la web dieran
completa la previsión de mañana («había predicciones incompletas creo
recordar, ahora se podrían completar»; «también en la web… la predicción
para mañana»).

## Decisión

- **La tabla de 24 horas va por tramos** (`resumTrams`, `resumTram` y
  `taulaTram`, en `web/casa.js`): matí (7–14 h), tarda (14–21 h) y nit
  (21–7 h), cada uno en un desplegable nativo (`<details>`) con su tabla.
  La cabecera de cada desplegable es el resumen del tramo descrito abajo,
  de modo que plegados se lee el día de un vistazo. Salen todos los tramos
  que toca la previsión, sin las horas ya pasadas: el tramo en curso dice
  «fins a les 21 h»; los que vienen, «21–7 h». Los de mañana se llaman
  «Demà matí», «Demà tarda» y «Demà nit», y por eso desaparecen las filas
  que separaban los días. La sección se titula «Previsió» («Previsión»),
  la palabra del resto de la web, en lugar de «Pròximes 24 hores», que ya
  no era exacto; se descartaron «Hora a hora» y «Predicció», que chocaba
  con «previsió».
- **La previsión llega a 24 horas como mínimo y hasta las 21 h de mañana**,
  acabando siempre con un tramo (`FI_TRAMS` y `FI_DEMA` en `casa.py`), para
  que mañana (la mañana y la tarde) salga siempre entero. «Mañana» es el día
  siguiente al del tramo en curso: de madrugada, la noche aún es de ayer.
  Son entre 24 y 38 filas: 38 a las 7 h; 33 a las 22 h, porque la noche
  dura 10 horas. Los modelos: el 09-10-2026 AROME y AROME HD llegaban a 45
  horas desde la última pasada, e ICON-EU y el ensemble más allá de lo que
  se pide (hasta el final de pasado mañana). Cuando AROME no llega, la
  lluvia sale de los otros modelos y la probabilidad, del ensemble, sin
  hueco. La probabilidad aprendida se entrenó con previsiones de hasta un
  día antes; por eso «Com es llegeix la taula» avisa, si la tabla pasa de
  24 horas, de que más allá es menos precisa. **Los riesgos y sus avisos**
  (`HORES_RISC` en `riscos.py`) y **el registro con el que se aprende**
  siguen con las 24 primeras horas, para no avisar antes ni cambiar el
  aprendizaje.
- **El bot y el canal** reciben mañana entero: el resumen de la noche (21 h,
  canal, bot y navegador) llegaba solo hasta las 20 h de mañana y lo decía
  («Previsió per a demà, dijous (fins a les 20 h)»); ahora llega a las 21 h
  y no lleva coletilla, que solo sale si los datos no llegan a las 21 h.
  `/dema` pedido por la mañana también sale entero. Los selectores de «Si
  surts» rotulan con el día de la semana lo que cae pasado mañana
  («dissabte 06:00») en lugar de llamarlo «demà».

- **Abiertos de entrada**: el primer tramo y cualquiera con aviso de AEMET
  o con un fenómeno de los de abajo, para que lo peligroso no quede
  plegado. Al imprimir se abren todos y después vuelven como estaban.
- **«Desplega-ho tot» / «Plega-ho tot»**, junto al título, se recuerda en el
  dispositivo (`localStorage`, `meteo.previsio-tot-obert`): quien quiere ver
  siempre el día entero lo pulsa una vez (Juanjo, 09-10-2026: «no debería
  ser persistente? si no cada vez que alguien abre la aplicación y quiere
  ver el día entero tiene que hacer lo mismo»). No se recuerda cada tramo,
  porque cambian de nombre a lo largo del día («Demà matí» pasa a ser
  «Matí»). Lo que se abre o cierra a mano no se guarda, pero se mantiene
  mientras la página está abierta, aunque se repinte con datos nuevos (antes
  de la 3.41.0, cada actualización lo volvía a plegar). El botón dice lo que
  hará: «Desplega-ho tot» si queda algún tramo plegado.
- **Las columnas miden lo mismo en todos los tramos** (`table-layout:
  fixed` y un `<colgroup>`), para que las cifras queden alineadas al abrir
  varios. Desde 640 px de ancho, los anchos van en proporción (hora y
  cuatro columnas de cifras al 13 %, el cielo con el resto), el reparto de
  la tabla anterior, y la cabecera, más baja, en una línea: con anchos fijos
  pensados para el móvil el cielo se quedaba casi todo el ancho del
  ordenador y las cifras se amontonaban a la derecha (Juanjo, 09-10-2026:
  «es muy distinto al actual, lo ves bien?»). Por debajo de 640 px, cada
  columna de cifras mide lo que ocupa de verdad (medido a 360 px) y el
  cielo se queda el resto; desde 400 px hacia abajo, el texto del cielo que
  no cabe al lado de su icono pasa debajo («Poc ennuvolat»), y el que cabe
  se queda al lado («Serè»). En la 3.40.0, en el móvil de Juanjo, «Cobert»
  se montaba sobre la temperatura («en movil se mezcla la prevision con la
  temperatura»): medido de 320 a 412 px, pasaba en todas las anchuras y en
  los dos idiomas, y las pruebas solo se habían mirado a 393 y 412 px. A
  320 px la tabla se desplaza un poco de lado, como antes.
  La barra de color de un aviso se corta en el límite de cada tramo y
  vuelve a empezar en el siguiente.
- **Las notas de la tabla** (asterisco, cruz, barra de aviso, viento, de
  dónde se aprende la probabilidad y, si pasa de 24 horas, que más allá es
  menos precisa) van plegadas en «Com es llegeix la taula», con el aspecto
  de «D'on surt».
- **La tarjeta de ahora ya no lleva el resumen**: desde la 3.40.0 está en
  las cabeceras de los desplegables, justo debajo. Entre el 08-10-2026 y la
  3.39.0 eran tres fichas al final de la tarjeta, después del radar.
- **Siempre**, en este orden: el cielo del tramo con su icono y su nombre
  (la media de las nubes de sus horas, con los nombres de Meteocat del
  ADR 0043; «Boira» si hay niebla en la mayoría de las horas; de noche, la
  luna) y la temperatura mínima–máxima con el termómetro («9 °C» si son
  iguales). El cielo no dice la lluvia: la dice el paraguas.
- **El paraguas, solo si va a llover** (Juanjo, 09-10-2026: «símbolo de
  lluvia solo si va a llover»): si alguna hora del tramo llega a «possible»
  (20 % o más, el mismo criterio que el cielo de la tabla), con la
  probabilidad máxima de sus horas y los milímetros sumados si llegan a 1
  («uns 5 mm»). Hasta la 3.28.0 salía siempre, también con un 0 %.
- **Solo cuando se dan**, en ámbar y con su icono: tempesta (código de
  tormenta de Open-Meteo, 95 o más, o aviso de AEMET por tormentas en la
  hora), pluja forta (40 mm en una hora) o torrencial (80), ratxes de vent
  (70 km/h), calor (36 °C), gel (0 °C o menos) y neu (0,1 cm o más en el
  tramo). La lluvia va con las palabras del manual de estilo de Meteocat
  (`INTENSITAT_PLUJA` en `web/casa.js`, ADR 0043; hasta entonces, 20 mm, el
  amarillo de AEMET); el viento y el calor, con los amarillos del Plan
  Meteoalerta que ya usa `config.RISC_LLINDARS` (ADR 0018). El
  hielo va a 0 °C, no al −4 del aviso amarillo de frío, porque lo que
  importa a quien sale es si puede helar.
- **El botón de la página pública se llama «El temps» / «El tiempo»**
  (`PAGINES_PUBLIQUES` en `montflorit.py`); la privada sigue siendo «Temps a
  casa».

## Alternativas descartadas

- **Una línea de texto en vez de fichas**: con los fenómenos se hacía larga
  y no se leía de un vistazo en el móvil.
- **Mantener el resumen en la tarjeta y poner en los desplegables solo el
  nombre y las horas**: la página habría dicho lo mismo dos veces seguidas.
- **Una sola tabla con filas que se ocultan**: las columnas cambian de ancho
  al abrir y cerrar, y sin `<details>` hay que rehacer a mano el teclado y
  la accesibilidad de un desplegable.
- **Dejar el último tramo cortado** («Demà tarda (14–17 h)»): fue la
  primera versión, el 09-10-2026; el resumen de un tramo de tres horas no
  dice cómo será esa tarde.
- **Umbrales propios para los fenómenos**: la página ya usa los de AEMET
  para el riesgo; repetirlos evita dos criterios distintos en la misma
  tarjeta.

## Validación

- `tests/test_web.py`, `test_resum_per_trams_del_dia`: tramos, horas,
  probabilidad, milímetros, temperaturas y los seis fenómenos, de día y de
  noche; `tests/test_montflorit.py`: traducciones y menú.
- Desde el 09-10-2026, `test_cel_de_cada_tram` (cielo, niebla, luna y lluvia
  que sube las nubes) y cuándo sale el paraguas; Firefox y Chromium con los
  datos reales y con lluvia simulada, y axe-core sin incidencias.
- `probar-web` en Chromium, Firefox y WebKit, escritorio, móvil y tableta,
  claro y oscuro, en catalán y castellano, y axe-core sin incidencias, el
  08-10-2026. Juanjo vio las capturas antes de publicar.
- Tabla plegable, 09-10-2026: `test_resum_per_trams_del_dia` con todos los
  tramos y el último cortado («7–8 h»); `probar-web` en los tres
  navegadores, escritorio, móvil y tableta, claro y oscuro, con los datos
  reales y con un aviso amarillo y una racha de 78 km/h simulados (los dos
  tramos afectados salen abiertos y la barra se corta entre ellos); en
  Firefox del móvil el cielo se montaba sobre la temperatura con la columna
  de avisos, corregido dejando que pase de línea. axe-core sin incidencias
  con todo desplegado, en catalán y castellano, claro y oscuro.
- Previsión alargada, 09-10-2026: `test_acaba_el_tram_del_dia` (a las 7,
  11, 16, 20, 21, 22 y 0.30 h: 38, 34, 29, 25, 24, 33 y 31 filas, siempre
  acabando a las 7, 14 o 21 h y nunca antes de las 21 h de mañana),
  `test_nomes_les_24_primeres_hores` (una racha en la hora 27 no da
  riesgo), `test_hores_de_si_surts_amb_el_dia` y
  `test_dema_sencer_sense_fins_a_les`; datos reales con `casa.py` (28
  filas, de 17 h a las 21 h de mañana) y, simulando las 7.03 h de mañana
  con los modelos de las 17 h, 38 filas sin ninguna temperatura ni
  probabilidad vacía, con 7 horas sin AROME HD; `probar-web` de las dos
  páginas y axe-core sin incidencias.
- Móvil, 09-10-2026: medido en Chromium y Firefox a 320, 340, 360, 375,
  393, 412 y 430 px, en catalán y castellano, con todos los tramos
  abiertos, que ninguna celda se desborda ni el cielo se monta sobre la
  columna de al lado (antes de la corrección pasaba de 320 a 412 px);
  `probar-web` y axe-core sin incidencias.
- «Desplega-ho tot», 09-10-2026: `test_trams_oberts_de_sortida` (de serie,
  con la preferencia guardada y con lo abierto a mano) y, en Firefox y
  Chromium a 360 px, pulsar, recargar (todo abierto), plegar y recargar
  (solo el primero).
