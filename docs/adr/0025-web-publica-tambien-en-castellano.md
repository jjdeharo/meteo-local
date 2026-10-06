# 25. Web pública también en castellano

Fecha: 2026-10-06 · Estado: aceptado

## Contexto

La web pública «Temps a Montflorit» (ADR 0024) salió solo en catalán. El
mismo día Juanjo pidió tenerla también en castellano. La página no es solo
texto fijo: casi todo lo que se lee lo escribe su programa a partir de los
datos (el cielo de cada hora, las franjas de los avisos, el radar, los
riesgos), con gramática catalana dentro del código, y los datos traen
algunas palabras en catalán. Y tiene que seguir saliendo sola de la página
de casa, sin una segunda copia que mantener.

## Decisión

- **Dónde**: <https://jjdeharo.github.io/meteo-montflorit/es/>, con su
  página de fuentes en `es/fonts.html`. La de la raíz sigue en catalán. Cada
  una enlaza la otra junto al nombre del municipio («Castellano», «Català»).
- **Los textos del programa** (`web/comu.js` y `web/casa.js`) pasan por una
  función, `T`: `` T`Ara a ${lloc}` `` o `T('No plou')`. Sin diccionario
  devuelve el texto tal cual, así que la web de siempre y la pública en
  catalán no cambian. La página en castellano carga antes
  `montflorit/es.js`, que trae la traducción de cada texto (la clave es el
  texto catalán con `{0}`, `{1}`… donde van los valores; la traducción puede
  ser una función cuando el orden o las preposiciones cambian, como en
  «hoy hasta las 20:00»). Las palabras que vienen en los datos (niveles,
  tipos de aviso, planes, rumbos) pasan por `TD`. El texto de un riesgo, que
  `riscos.py` escribe en catalán, se vuelve a componer en castellano con los
  campos del propio riesgo.
- **Los textos fijos** de las dos páginas se traducen al generar la web
  (`montflorit.py`), bloque a bloque (títulos, párrafos, elementos de lista y
  rótulos), con la tabla `i18n/es.json`: la clave es el bloque en catalán.
- **Nada puede quedar sin traducir**: si aparece un bloque sin traducción,
  la generación falla; y las pruebas comparan los textos que pasan por `T`
  en el código (`i18n/claus.js` los saca) con los de `es.js`, en los dos
  sentidos, y las palabras de los datos con las que conoce.
- **Los archivos comunes no se duplican**: la página de `es/` usa los de la
  carpeta de arriba (`data-arrel="../"` para los datos de reserva y la
  instalación como aplicación).
- **La traducción es automática** y así se dice en «Fuentes y créditos».

## Alternativas descartadas

- **Una segunda copia de las páginas y del programa en castellano**: habría
  que acordarse de cambiar las dos en cada retoque.
- **Traducir el programa al generar la web**, sustituyendo cadenas: no
  distingue los textos de los nombres internos, y las frases compuestas
  (franjas, artículos) no salen sustituyendo.
- **Publicar los datos también en castellano**: lo que hay que traducir de
  ellos son una veintena de palabras; un segundo archivo en cada pasada no
  compensa.
- **Elegir el idioma por el del navegador**: muchos navegadores de aquí
  están en castellano y sus dueños leen en catalán. Se abre en catalán y
  hay un enlace a la vista.
- **`<base href="../">`** para no tocar las rutas: los iconos de la página
  son referencias internas (`<use href="#…">`) y con `<base>` dejan de verse
  en algunos navegadores.

## Consecuencias

- `comu.js` y `casa.js` cambian para todos: cada texto visible va con `T`.
  Un texto nuevo sin `T` saldría en catalán en la página en castellano; uno
  con `T` y sin traducción hace fallar las pruebas.
- Tres cosas más que mantener al cambiar un texto: `montflorit/es.js` (los
  del programa), `i18n/es.json` (los fijos) y, si cambia el vocabulario de
  los datos, `dades` de `es.js`.
- La aplicación instalada se sigue llamando «Temps a Montflorit» y se abre
  en catalán.
- De paso, las coordenadas que `casa.js` usa para saber si es de día
  quedan redondeadas a una décima de grado: el archivo se publica también en
  el repositorio de la web pública.

## Evidencia

- 84 textos del programa y 39 bloques fijos traducidos (06-10-2026).
- Los tipos de aviso que llegan en los datos son «pluja» y «tempestes»
  (`prevision.py`); los planes, los de `config.PLANES_PC`; los rumbos, los
  ocho de `nowcast.RUMBS`.

## Riesgos y limitaciones

- Traducción hecha con IA, sin revisión profesional.
- Con un día de la semana, las franjas no llevan artículo al empezar
  («viernes de 09:00 a 18:00»), para que valga la misma lógica que agrupa
  las del mismo día; después de «hasta» sí lo llevan.
- El comunicado de Protección Civil y las páginas enlazadas de Meteocat y
  de meteocerdanyola.com están en catalán.

## Validación

`tests/test_montflorit.py`: las páginas de `es/` se generan, enlazan la otra
versión y no dejan catalán a la vista; un bloque nuevo sin traducir falla;
no falta ni sobra ninguna traducción; avisos, cielo, presión, radar, horario
y riesgos en castellano; el catalán sigue igual (`tests/test_web.py`).
`probar-web` en Chromium, Firefox y WebKit, en escritorio, móvil y tableta,
con tema claro y oscuro, y axe-core.
