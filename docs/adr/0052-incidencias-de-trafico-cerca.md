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
  carretera, puntos kilométricos, tipo, nivel, causa, «cap a» y la hora de su
  última actualización) y
  `incidenciesRSS.xml` (municipio y sentido escritos), cruzados por el
  identificador (`transit.py`). Sin el RSS, las incidencias salen igual, sin
  municipio. Sin el GML, el bloque no sale y el error queda en `errors`.
- **Qué se muestra**: las incidencias que empiezan a `TRANSIT_RADI_KM` o menos
  de Montflorit, en línea recta: AP-7, B-30, C-58, C-17, C-33, BV-1414 y
  BV-1415. Eran 6 km; desde la 3.33.0, 5 (Juanjo, 09-10-2026: «como máximo
  5km»), y cada incidencia dice a qué distancia está («Barcelona, a 4 km»):
  en metros, de 50 en 50, por debajo de 1 km («si está a menos de 1km en
  metros»), y si no, en km con un decimal; igual en la web y en `/transit`. Todas las retenciones (accidentes,
  averías, circulación) y, de las obras, solo las que desvían o cortan la vía
  (nivel 3 o más, o «tallada» o «tall total» en el texto). Las obras con un
  carril restringido (nivel 2) no: el 09-10-2026 eran 162 de 184 en toda
  Cataluña, duran semanas y taparían lo que importa; el enlace al Servei
  Català de Trànsit las tiene todas.
- **Obras sin ubicación precisa, fuera** (3.36.0): sin punto kilométrico o
  en un tramo de más de `TRANSIT_OBRES_TRAM_MAX_KM` (2 km) no dicen dónde está
  el corte. Juanjo, ante la BV-1414 del km 4 al 0 («incorporació a C-58
  tallada»): «no se sabe dónde está esa calzada cortada, si no hay ubicación
  precisa se elimina». Las retenciones siguen saliendo aunque sean largas: su
  tramo es la propia cola.
- **Dónde**: dentro de las fichas del coche y de la moto, plegado al final
  («Trànsit ara: N incidències»), con la carretera, el municipio, el estado con
  el color de su nivel (gris, 2; ámbar, 3 y 4; rojo, 5), la causa, el sentido,
  los puntos kilométricos; sin incidencias, una línea lo dice. **Sin hora por
  incidencia** (3.32.1): la del fichero es la de su última actualización, no
  la del inicio (el 09-10-2026 a las 11:11 la lista oficial daba la retención
  de la C-58 con «Inici» 06:29, y el fichero, 09:03), y vista sola parecía que
  el dato no estaba al día. Juanjo: «no aporta nada decir que empezó a las 6
  porque lo que interesa es ahora… lo que se muestra es lo que hay ahora». Lo
  que sale es lo que el Servei Català de Trànsit da como vigente a la hora de
  la consulta, que figura al pie.
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

- El fichero puede llegar cortado si se descarga mientras el Servei Català de
  Trànsit lo reescribe (09-10-2026, 12:27: «unclosed token»; las cinco
  descargas siguientes llegaron enteras). Desde la 3.35.1, si no se puede leer,
  se vuelve a pedir una vez a los 3 segundos.

- La distancia es en línea recta hasta el punto que da la fuente para el
  tramo, no la de todo el tramo ni por carretera: una incidencia larga que
  empiece lejos y llegue cerca no sale, y la misma puede salir a distancias
  algo distintas entre descargas (la BV-1414, a 3,1 y a 4,4 km el 09-10-2026),
  porque el punto cambia de un extremo del tramo al otro.
- Las obras pueden seguir «activas» en la fuente mucho después de acabar
  (hay alguna de abril); sin la fecha, no se nota. Se muestra lo que la fuente
  da por vigente, como su propia lista.
- Nivel y tipo vienen como números sin documentación pública: su significado
  se ha deducido de los textos que los acompañan (Evidencia).

## Validación

`tests/test_transit.py` (formato real del GML y del RSS, filtro, textos, sin
RSS, obras, municipios, puntos kilométricos, el mismo nivel que la página,
qué cortes avisan y el aviso al empezar, una sola vez, sin fuente y al acabar),
`tests/test_bot.py` (bloque de `/avisos_actius`) y
`tests/test_web.py` (consejo del coche y la moto ahora y más tarde). `probar-web` en Chromium, Firefox y WebKit, escritorio, móvil y tableta,
claro y oscuro, con los plegables abiertos, sin errores; el enlace
`sortir.html#trens` abre el plegable en Chromium y Firefox, en las dos
lenguas; axe-core sin fallos en «Si surts» (las dos lenguas, plegables
abiertos) y en «Fonts i crèdits».
