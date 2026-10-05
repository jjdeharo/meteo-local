# 1. Fuentes de datos y método para decidir moto o coche

Fecha: 2026-10-05 · Estado: aceptado (regla de decisión añadida el mismo día)

## Contexto

Hay que decidir cada mañana si el trayecto en moto de casa (Cerdanyola del
Vallès) al Parc Taulí (Sabadell), con llegada a las 7:30 y vuelta a las 15:00,
tendrá lluvia. El trayecto es corto (unos 8 km), de modo que lo que importa es
la lluvia local en dos ventanas de media hora, y en otoño buena parte de ella
es convectiva: chubascos que nacen y mueren en menos de una hora.

## Decisión

`prevision.py` junta cinco fuentes y da para cada ventana uno de tres
veredictos: moto, moto con impermeable («compte») o coche. **Manda la fuente
más desfavorable**, porque el coste de equivocarse no es simétrico: ir en
coche sin necesidad es una molestia; una tormenta en moto, un riesgo.

1. **Avisos de AEMET** (feed de Meteoalarm). Un aviso de lluvia o tormenta en
   el Prelitoral de Barcelona que toque la ventana: coche. Uno solo en el
   Litoral de Barcelona: compte.
2. **Radar** (RainViewer), solo si la ventana empieza en las 3 horas
   siguientes. Lluvia apreciable a menos de 15 km y creciendo (más de un 30 %
   de superficie en 50 km en la última hora): coche; a menos de 15 km sin
   crecer, o a menos de 40 km: compte.
3. **Estaciones** de Meteocat de Sabadell - Parc Agrari (XF) y Sant Cugat - CAR
   (XV), leídas de la página pública de meteo.cat. Si alguna registra lluvia en
   la última media hora y falta menos de hora y media: coche.
4. **Modelos finos** de Open-Meteo (AROME HD, AROME, ICON-EU), en los dos
   extremos del trayecto: máximo de 1 mm en una hora, coche; 0,2 mm, compte.
   Los globales (ECMWF, UKMO, GFS) no deciden: sus celdas incluyen mar.
5. **Ensemble ICON-EU-EPS** (40 miembros, horario): fracción de miembros con
   0,2 mm o más en la ventana. Un 50 % o más, coche; un 20 %, compte. Con el
   umbral de coche en el 40 %, un día sin aviso y con los modelos secos daba
   coche solo por el ensemble; se subió al 50 %.

La web da solo el día de hoy. Con `prevision.py` se puede pedir otro día
cambiando la fecha en el código; entonces no cuentan radar ni estaciones.

## Alternativas descartadas

- **API de Meteocat y AEMET OpenData**: piden clave; las páginas públicas y
  Meteoalarm dan lo necesario sin ella.
- **Portal de datos abiertos de la Generalitat** (Socrata, XEMA): el dominio
  `analisi.transparencia.gencat.cat` no resuelve desde la red de casa.
- **Calcular el desplazamiento de la lluvia por correlación entre fotogramas**:
  se probó y dio 22 km/h hacia el este en una ejecución y 2 km/h en la
  siguiente, con tormentas formándose en el mismo intervalo. Se sustituyó por
  la superficie de lluvia cercana, que sí distingue un sistema que crece.

## Consecuencias

La respuesta es una recomendación razonada, no una probabilidad calibrada. El
radar solo sirve para las 2-3 horas siguientes; la vuelta de las 15:00 se
decide sobre todo por avisos y modelos.

## Evidencia

- Prueba del 05-10-2026 a las 5:40: AROME HD (pasada de 00 UTC) ponía 11 mm
  entre las 4 y las 5 en Cerdanyola; XF y XV registraron 0,0 mm. El radar no
  mostraba ecos sobre el Vallès, pero sí tormentas formándose a 10-25 km al
  sur, en el mar, y AEMET tenía aviso amarillo de lluvia y tormentas en el
  Prelitoral de Barcelona de 5:00 a 20:00.
- La tabla de meteo.cat (`/observacions/xema/dades?codi=XX`) va en hora UTC.
- La precipitación horaria de Open-Meteo es la acumulada en la hora anterior.

## Riesgos y limitaciones

- La lectura de meteo.cat depende del HTML de su página (clase `tblperiode`).
- El umbral de intensidad del radar (transparencia del PNG mayor que 100) se
  ha fijado a ojo con la escala de colores 2 de RainViewer: hipótesis pendiente
  de contrastar con la lluvia medida en las estaciones.
- RainViewer limita el zoom gratuito a 7 (unos 0,9 km por píxel).

## Validación

Pruebas de la regla en `tests/test_decidir.py`, con datos inventados.

Ejecución completa el 05-10-2026 a las 5:45 (unos 16 s), comparada a mano con
las imágenes de radar y las tablas de las dos estaciones.
