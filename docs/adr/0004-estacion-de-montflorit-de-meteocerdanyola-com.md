# 4. Estación de Montflorit de meteocerdanyola.com

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

El 05-10-2026 empezó a llover fuerte en Cerdanyola a las 6:28 (75 mm/h a las
6:54). A las 6:59, las estaciones de Meteocat (Sabadell y Sant Cugat, a 2,5 y
5 km) solo tenían datos hasta las 6:30, y la web decía que no registraban
lluvia. Juanjo señaló la estación de Montflorit de meteocerdanyola.com, en el
barrio donde empieza el trayecto, con datos minuto a minuto.

## Decisión

- La estación de Montflorit es la primera fuente de «¿llueve ahora?». Se lee de
  la API de las gráficas de la web
  (`/2026/api/graphs-series.php?slug=cerdanyola_montflorit`): una consulta por
  actualización, unos 380 KB con las últimas 24 horas minuto a minuto.
- Se calcula la lluvia de la última media hora con el acumulado del día
  (`PREC`, que vuelve a cero a medianoche) y se muestra la intensidad
  (`PINT`, mm/h).
- La web la cita, con enlace, en «Fonts i crèdits».
- Meteocat sigue detrás, para el extremo de Sabadell y como reserva.

## Alternativas descartadas

- **El archivo `latest.json` de la carpeta `/2026/data/`**, más ligero: el
  `robots.txt` de la web cierra esa carpeta a los programas. La API de las
  gráficas no está cerrada. Se le planteó a Juanjo pedir permiso al
  responsable (@meteocerdanyola); decidió leer la API de las gráficas
  («saca los datos de las graficas»).
- **Los canales de Meteoclimatic**, la red a la que pertenece la estación: su
  `robots.txt` cierra `/feed/` a los programas.
- **Las estaciones de Cerdanyola Centre y Ateneu** de la misma web: añadirían
  dos consultas más por actualización para un trayecto que ya cubre Montflorit.

## Consecuencias

La web detecta la lluvia en Cerdanyola en el minuto en que empieza, en lugar
de con media hora o una hora de retraso. No sirve para calibrar: la API solo
da las últimas 24 horas.

## Evidencia

- 05-10-2026, 7:02: Montflorit 19,2 mm en el día, 17,8 mm en la última media
  hora, 43,2 mm/h; Sabadell y Sant Cugat (Meteocat), 0,0 mm hasta las 6:30.
- `robots.txt` de meteocerdanyola.com (05-10-2026): `Disallow: /2026/data/`,
  entre otras; ninguna regla para `/2026/api/`.
- La API ignora el parámetro `hours`: siempre devuelve 24 horas.

## Riesgos y limitaciones

- Es una web particular sin API documentada: puede cambiar de formato o de
  dirección sin aviso. Si falla, se sigue con Meteocat.
- Su responsable no ha dado permiso expreso. Si lo pide, se quita.
- Pluviómetro de aficionado: no tiene los controles de calidad de Meteocat.

## Validación

Pruebas automáticas del cálculo de la última media hora, del paso por
medianoche y del motivo (`tests/test_decidir.py`).
