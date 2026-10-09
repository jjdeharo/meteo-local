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
