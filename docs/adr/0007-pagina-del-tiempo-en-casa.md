# 7. Página del tiempo en casa

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

Juanjo pidió una página paralela con el tiempo en casa (Montflorit), sobre
todo la previsión hora a hora para las 24 horas siguientes.

## Decisión

- `web/casa.html`, en catalán como el resto del sitio, enlazada con la del
  trayecto por una navegación común en el mismo sitio de las dos páginas. El
  código común de las dos (tema, horario, versión) pasa a `web/comu.js`.
- **Ara a Montflorit:** la estación de meteocerdanyola.com (ADR 0004).
- **Avisos de AEMET** del Prelitoral de Barcelona aún vigentes.
- **Tabla de 24 tramos de una hora** («10–11»), calculada por `casa.py`:
  - temperatura, cielo, viento y rachas de `meteofrance_seamless` (AROME a
    1,5 km y, más allá de su alcance, ARPEGE);
  - lluvia: la mayor de los tres modelos finos (AROME HD, AROME e ICON-EU),
    porque un solo modelo puede fallar: la mañana del 05-10-2026 AROME daba
    0,0 mm mientras en Montflorit caían más de 20 mm/h;
  - probabilidad: fracción de los 40 miembros de ICON-EU-EPS con 0,2 mm o más
    en el tramo;
  - la descripción del cielo se deduce de esos mismos datos, para que no diga
    «serè» en un tramo con lluvia.
- **Se actualiza cada media hora, todo el día** (`HORARIO_CASA`,
  `INTERVALO_CASA_MIN`; cada hora hasta el 05-10-2026, cuando Juanjo pidió
  cada 30 minutos), desde el NAS. En esas pasadas solo se recalcula la
  página de casa (`SOLO_CASA=1` en `publica.sh`): los datos del trayecto se
  vuelven a publicar tal como estaban, para no alterar su horario ni su
  decisión. La página muestra su horario como la del trayecto.

### Corrección del 05-10-2026, 10:10

Con alerta de Protección Civil por lluvias torrenciales, la tabla decía
«pluja feble, 33 %» porque solo enseñaba los modelos (Juanjo: «esto es
claramente incorrecto»). Se añadió:

- **Persistencia:** si ha llovido en la última hora en Montflorit, las cuatro
  primeras filas no bajan de lo que pasó en casos parecidos en Sabadell y Sant
  Cugat entre 2024 y 2026 (`persistencia` en `calibracio/calibracio.json`):
  tras una hora con 1 mm o más, siguió lloviendo la hora siguiente el 78 % de
  las veces, y dos horas después el 56 %. La fila en curso, si llueve, dice
  «Plou ara». Estas cifras llevan asterisco.
- **Comprobación de los modelos:** si en las tres últimas horas han caído al
  menos 3 mm y más del triple de lo previsto más 1 mm, la página lo dice (el
  05-10-2026 a las 10:09, 27,4 mm medidos frente a 0,5 previstos).
- **Avisos por hora:** cada fila lleva los avisos de AEMET que la cubren; los
  planes de Protección Civil, sin hora de fin, van arriba (ADR 0008).
- Sin lluvia prevista pero con probabilidad del 30 % o más, el cielo dice
  «Possible pluja», no «serè».

### Corrección del 05-10-2026, 16:50: avisos con día y franja

La línea de avisos agrupaba por nivel y hora de fin, sin el día: un aviso de
hoy hasta las 20:00 y dos de mañana (9:00-18:00 y 22:00-24:00) salían como
tres avisos de hoy con finales distintos. Ahora hay una frase por nivel y
tipo, con cada franja y su día («avui fins a les 20:00; demà de 09:00 a 18:00
i de 22:00 a mitjanit»); las franjas seguidas se juntan y las acabadas no
salen (`textAvisos` en `web/casa.js`, `tests/test_web.py`).

## Alternativas descartadas

- **Iconos del tiempo:** la descripción en una palabra se lee igual y no
  depende de una biblioteca de iconos.
- **Un solo modelo para la lluvia:** ver arriba.

## Consecuencias

La tabla es ancha: las unidades van en la cabecera y, por debajo de 380 px de
ancho, la letra se reduce un poco para que quepa sin desplazamiento lateral.

## Evidencia

- Medido con Playwright en Chromium, Firefox y WebKit: a 360 y 390 px de ancho
  la tabla cabe en su contenedor.
- Aviso rojo de lluvia de AEMET en el Prelitoral de Barcelona de 7:00 a 10:00
  del 05-10-2026 (feed de Meteoalarm, severidad «Extreme»): la página lo
  muestra como «avís vermell».

## Riesgos y limitaciones

- La probabilidad del ensemble no está calibrada con datos locales.

## Validación

`probar-web` en los tres navegadores, móvil y escritorio, tema claro y oscuro.
