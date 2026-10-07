# 29. Página «Si surts» y estado de los trenes

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

La página del trayecto («Moto o cotxe?») recomendaba un medio para un viaje
fijo. Juanjo quiso generalizarla «para que fuese útil para todo el barrio»:
que cada uno ponga su hora de salida y de vuelta y reciba recomendaciones de
ropa, transporte y lo que haga falta. Al día siguiente de un temporal, con
Rodalies parado, preguntó además si se podía saber si funcionaban los trenes
y otros transportes.

## Decisión

- **Una página nueva en Temps a Montflorit**, «Si surts» (`web/sortir.html` y
  `web/sortir.js`), en catalán y castellano, con un menú «El temps ara · Si
  surts» con iconos. Todo se calcula en el navegador a partir de la previsión
  hora a hora que ya se publica; el servidor solo añade el índice UV y el
  estado de los trenes. No hay destino: los datos de Montflorit valen para
  moverse por la zona, y la página lo dice.
- **Dos selectores**: hora de salida («Ara» o cualquier hora de la tabla) y de
  vuelta (por defecto, 3 horas después).
- **Un veredicto por medio para toda la salida** (ida y vuelta, porque quien va
  en moto vuelve en moto): a pie, bici o patinete, moto, coche y transporte
  público, en verde, ámbar o rojo con el motivo. Coche y transporte público
  van por separado, porque uno puede ir bien y el otro no (Juanjo, 07-10-2026).
  Umbrales en `web/sortir.js`: los de lluvia son los del trayecto, comprobados
  con datos; los de viento y frío de bici y moto, una primera propuesta que la
  página declara sin comprobar.
- **Transporte público según los trenes**: «Bé» si circulan todos, «Amb
  incidències» si alguno no circula, va por carretera o tiene avisos, «Sense
  trens» si no circula ninguno; con un enlace al bloque «Trens ara» de debajo,
  para que la ficha no crezca.
- **Ropa por medio**, según la temperatura que se nota a la ida y a la vuelta:
  con la velocidad del medio en bici (18 km/h) y en moto (45 km/h), y con el
  viento previsto a pie, en coche y en transporte público (el rato a pie hasta
  el coche o la estación), con el índice de Environment Canada (10 °C o menos).
  A pie, ocho tramos, de «Màniga curta» (más de 24 °C) a «Abric, gorro, bufanda
  i guants» (0 °C o menos); en bici, manga corta desde 21 °C. Si la vuelta pide
  otra prenda, se dice aparte con su hora y temperatura, en lugar del antiguo
  «millor capes» (Juanjo pidió el 07-10-2026 distinguir manga corta y larga y
  que fuese «algo más completo… sin caer en tonterías»). En moto, una sola
  chaqueta para toda la salida, la del momento más frío, porque no se cambia por
  el camino. Se dejan fuera pantalón, calzado y humedad: dependen de cada
  persona y la previsión no trae humedad. **Consejos**: lluvia que empieza o
  acaba, cambio de temperatura, protector solar, gorra y gafas de sol (UV 3 o
  más), salida o vuelta de noche y calor (32 °C o más).
- **Cada uno elige qué medios ve**: casillas con icono, en verde (✓) o rojo
  (✕), guardadas en el navegador (`localStorage`); sin «Transport públic» no
  sale el bloque de los trenes. Una explicación corta desaparece tras la
  primera vez que se desmarca uno. En pantalla ancha, las fichas en columnas.
- **Trenes** (`trens.py`): R4, R7 y R8 de Rodalies y S2 de FGC, las que paran
  en el término de Cerdanyola (la S1 no). Avisos y posición en tiempo real de
  Renfe (GTFS-RT en JSON) y de FGC (GTFS-RT en protobuf, leído con un lector
  mínimo propio: el contenedor no tiene la biblioteca). Una línea circula si
  en la última hora se ha visto un tren suyo moviéndose a 6 km o menos de su
  estación: un tren parado también envía su posición, y el 07-10-2026 la R4
  circulaba solo por el tramo sur. Estados: «Sense incidències», «Amb
  incidències», «Servei per carretera», «Sense trens» y «Fora d'horari». Los
  avisos se muestran en el idioma en que los publica el operador, sin
  traducirlos (Juanjo, 07-10-2026); Renfe marca como castellano también el
  texto catalán, y se distinguen por el contenido.
- **Dónde lo explican los operadores**: «Estat del servei: Rodalies · FGC ·
  Busos de l'AMB», una sola vez, en el bloque de trenes. Rodalies publica las
  incidencias en su portada; FGC remite el estado del servicio a su cuenta de
  X.
- **Aviso de responsabilidad** junto a los trenes y en los créditos: los
  datos de terceros se consultan automáticamente y el autor no se hace
  responsable de su exactitud (Juanjo, 07-10-2026).

## Alternativas descartadas

- **Pedir el destino**: complica la página y, a esta distancia, apenas cambia
  la previsión.
- **Recomendar un solo medio**: cada vecino tiene medios distintos.
- **Autobuses urbanos de Cerdanyola (CV1, CV3, CV4)**: la AMB publica en
  abierto el tiempo real de sus autobuses, pero el 07-10-2026 las CV no
  aparecían. Un aviso de un solo uso del vigía del NAS
  (`busos-cv-temps-real`) comprueba hasta el 09-10-2026 si aparecen; si lo
  hacen, se añaden. Del B4 interurbano no se ha encontrado tiempo real.
- **Cruzar los viajes en tiempo real con el horario oficial** para saber si
  paran en Cerdanyola: el 07-10-2026 la R4 hacía solo el tramo sur con los
  identificadores de los viajes completos.
- **Retrasos**: Renfe los publica tren a tren, pero «Sense incidències» se
  refiere a los avisos; se añadirán si hace falta.
- **Incidencias de tráfico, polen y calidad del aire**: fuentes nuevas que
  mantener, fuera del núcleo.

## Consecuencias

- Los datos públicos llevan `trens` y, en cada hora, `uv`.
- Dos peticiones más a Renfe (unos 225 KB) y dos a FGC por pasada, y una a
  Open-Meteo para el índice UV.
- El NAS guarda las posiciones de la pasada anterior en
  `/estat/trens-posicions.json`.

## Evidencia

- Datos de Renfe y FGC con licencia CC BY 4.0 (metadatos de data.renfe.com y
  de dadesobertes.fgc.cat, consultados el 07-10-2026).
- 07-10-2026, 07:51: alerta de Renfe para R1-R8 «Per causes alienes a
  Rodalies no es pot garantir la prestació del servei», dos trenes de la R7
  quietos en Montcada Bifurcació y Cerdanyola Universitat, R8 con servicio por
  carretera y trenes de la R4 moviéndose solo en el tramo sur. Coincide con la
  prensa: toda la red parada por la negativa de los maquinistas a circular
  tras el temporal.
- El índice UV solo lo da el modelo por defecto de Open-Meteo; los de
  Météo-France, ECMWF e ICON lo dan vacío (07-10-2026).

## Riesgos y limitaciones

- Los umbrales de bici, patinete y a pie no están comprobados con datos, ni
  los tramos de ropa, que son orientativos: no hay fuente oficial que diga a
  qué temperatura se lleva cada prenda.
- Con trenes cada 30 minutos, una línea puede tardar hasta una hora en pasar a
  «Sense trens» tras parar.
- Si Renfe o FGC cambian el formato de sus datos, la línea queda «Sense dades».
- El lector de protobuf solo lee los campos de los avisos que se usan.

## Validación

`tests/test_web.py` (tramos de ropa, viento a pie, otra prenda a la vuelta, una
sola chaqueta en moto, bici), `tests/test_trens.py` (protobuf, idiomas, trenes parados, lejos de la estación,
vistos hace poco, estados y orden de los avisos) y `tests/test_montflorit.py`
(menú, página pública, palabras permitidas, castellano). La página, probada en
Chromium, Firefox y WebKit, en escritorio, móvil y tableta, con tema claro y
oscuro, y axe-core sin incidencias, con los datos reales del 07-10-2026 (R4 y
R7 sin trenes, R8 por carretera, S2 sin incidencias). Las casillas, probadas al
desmarcar, recargar y volver a marcar.
