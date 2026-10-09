# 52. Incidencias de tráfico de cerca en «Si surts»

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

En el ADR 0029 las incidencias de tráfico quedaron fuera de «Si surts» como
«fuente nueva que mantener». El 09-10-2026 Juanjo preguntó si se podían poner
las que afectan a Montflorit; con la fuente comprobada, pidió hacerlo. Coche y
moto solo tenían en cuenta el tiempo.

## Decisión

- **Fuente: el Servei Català de Trànsit**, en el portal de datos abiertos de la
  Generalitat («Incidències viàries en temps real a Catalunya»), los mismos
  datos de su mapa: `incidenciesGML.xml` (punto de inicio del tramo,
  carretera, puntos kilométricos, tipo, nivel, causa, «cap a» y hora) y
  `incidenciesRSS.xml` (municipio y sentido escritos), cruzados por el
  identificador (`transit.py`). Sin el RSS, las incidencias salen igual, sin
  municipio. Sin el GML, el bloque no sale y el error queda en `errors`.
- **Qué se muestra**: las incidencias que empiezan a `TRANSIT_RADI_KM` (6 km)
  o menos de Montflorit: AP-7, B-30, C-58, C-17, C-33, BV-1414, BV-1415,
  BV-1462 y las rondas por el norte. Todas las retenciones (accidentes,
  averías, circulación) y, de las obras, solo las que desvían o cortan la vía
  (nivel 3 o más, o «tallada» o «tall total» en el texto). Las obras con un
  carril restringido (nivel 2) no: el 09-10-2026 eran 162 de 184 en toda
  Cataluña, duran semanas y taparían lo que importa; el enlace al Servei
  Català de Trànsit las tiene todas.
- **Dónde**: dentro de las fichas del coche y de la moto, plegado al final
  («Trànsit ara: N incidències»), con la carretera, el municipio, el estado con
  el color de su nivel (gris, 2; ámbar, 3 y 4; rojo, 5), la causa, el sentido,
  los puntos kilométricos y desde cuándo; sin incidencias, una línea lo dice.
  Abierto, la ficha ocupa todo el ancho. La primera versión, sin publicar, lo
  ponía en un bloque aparte debajo de los trenes con un enlace desde las
  fichas; Juanjo no quería saltar a otro sitio de la página («creo que
  debería estar todo junto») y eligió esta forma entre tres (también agrupar
  las listas bajo las fichas o abrir una ventana). Los trenes pasan igual a la
  ficha del transporte público (ADR 0029). Las dos fichas repiten la lista,
  pero plegada no ocupa sitio.
- **El consejo del coche y la moto**: si se sale ahora y hay una retención de
  nivel `TRANSIT_NIVELL_SORTIDA` (3) o más (retenciones, congestión o calzada
  cortada), pasan a «compte» con las carreteras y un enlace al bloque. La
  circulación intensa (2) y las obras solo se listan. Si la salida es más
  tarde, el tráfico de ahora no cuenta: un atasco dura minutos.
- **Los textos son los del Servei Català de Trànsit, en catalán**, también en
  la versión en castellano, como los avisos de Renfe y FGC. Solo los nombres
  de municipio pasan de mayúsculas a la forma normal.
- **Aviso a los vecinos de una carretera cortada** (Juanjo, 09-10-2026: «eso
  afecta a la circulación de los vecinos»). Retirado el mismo día, en la
  3.32.0 (ADR 0053): un corte no es una situación de peligro, y el tráfico se
  consulta con /transit. Lo que se hizo en la 3.31.0: una calzada cortada (el texto dice
  «tallada») a `TRANSIT_AVIS_KM` (4 km) o menos, un mensaje al empezar y otro
  al dejar de constar. Va con los de «Situacions de perill», como los
  incendios (ADR 0046): llega a todos los suscriptores que lo tienen por
  defecto, al canal y a los avisos del navegador, sin una categoría nueva a la
  que haya que apuntarse. De las obras, solo si el corte lo causa algo
  imprevisto (esllavissada, esfondrament, inundació, accident, arbre…,
  `TRANSIT_AVIS_CAUSES`): los cortes programados, como los nocturnos,
  avisarían cada noche y ya se ven en la ficha. La primera pasada solo apunta
  lo que hay, y si el Servei Català de Trànsit no responde no se da por
  acabado. Lo decide `transit.py` (campo `tall`) y `/avisos_actius` del bot los
  lista en un bloque «Carreteres tallades».

## Alternativas descartadas

- **DATEX II del Servei Català de Trànsit en el Punto de Acceso Nacional de la
  DGT** (`nap.dgt.es/datex2/sct/...`): mismos hechos, pero 1,1 MB por pasada
  en vez de 230 KB, solo con códigos (sin texto que leer) y sin licencia
  declarada en su ficha. La de la DGT para el resto de España excluye
  Cataluña.
- **Servicios comerciales** (TomTom, HERE, Waze para ciudades): de pago o con
  convenio, y fuera del criterio de no depender de terceros privados.
- **Calles de Cerdanyola**: los cortes por obras municipales o fiestas solo se
  anuncian en la web del Ajuntament, no como datos.

## Consecuencias

- `casa.json` y `montflorit.json` llevan `transit` (`hora` e `incidencies`),
  de 1 a 2 KB; nada se guarda en el registro.
- Dos descargas más por pasada (unos 170 KB y 65 KB), en el NAS y en la
  reserva de IONOS.
- Los avisos de corte dependen de que la fuente quite la incidencia al
  reabrir; si una se queda colgada, el «ya no consta» llega tarde.

## Evidencia

- Ficha oficial del conjunto: `analisi.transparenciacatalunya.cat/d/uyam-bs37`
  (Departament d'Interior i Seguretat Pública), que remite a
  `www.gencat.cat/transit/opendata/incidenciesGML.xml` y
  `incidenciesRSS.xml`; la página de datos abiertos del Servei Català de
  Trànsit la enlaza. Licencia: la abierta de uso de información de Cataluña,
  que pide citar «Generalitat de Catalunya. Departament de…» y la fecha de
  actualización (`web.gencat.cat/ca/generalitat/dades-indicadors/dades-obertes/llicencies`).
- Descargas del 09-10-2026 (10:00-10:20): 184 incidencias, todas del Servei
  Català de Trànsit, con estos niveles en dos descargas: tipo 2 (retención)
  con nivel 2 «Circulació intensa», 3 «Circulació amb retencions», 4
  «Circulació amb congestió» y 5 «Calçada tallada»; tipo 3 (obras) con nivel
  2 «Calçada restringida», 3 «… Desviaments», 4 «Calçada tallada.
  Desviaments» y 5 «Calçada tallada».
- A 6 km o menos salían ese día: retenciones en la C-58, la B-20 y la C-33
  (nivel 3), circulación intensa en la AP-7 en Cerdanyola por una avería y en
  Barberà (nivel 2), y la incorporación de la BV-1414 a la C-58 cortada por
  obras desde el 22-04-2026.

## Riesgos y limitaciones

- La distancia es la del punto de inicio del tramo, no la de todo el tramo:
  una incidencia larga que empiece lejos y llegue cerca no sale.
- Las obras pueden seguir «activas» en la fuente mucho después de acabar
  (hay alguna de abril); se muestran desde cuándo están para que se vea.
- Nivel y tipo vienen como números sin documentación pública: su significado
  se ha deducido de los textos que los acompañan (Evidencia).

## Validación

`tests/test_transit.py` (formato real del GML y del RSS, filtro, textos, sin
RSS, obras, municipios, puntos kilométricos, el mismo nivel que la página,
qué cortes avisan y el aviso al empezar, una sola vez, sin fuente y al acabar),
`tests/test_bot.py` (bloque de `/avisos_actius`) y
`tests/test_web.py` (consejo del coche y la moto ahora y más tarde, y «des
de»). `probar-web` en Chromium, Firefox y WebKit, escritorio, móvil y tableta,
claro y oscuro, con los plegables abiertos, sin errores; el enlace
`sortir.html#trens` abre el plegable en Chromium y Firefox, en las dos
lenguas; axe-core sin fallos en «Si surts» (las dos lenguas, plegables
abiertos) y en «Fonts i crèdits».
