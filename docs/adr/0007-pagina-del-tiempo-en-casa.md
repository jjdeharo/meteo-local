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
- **Se actualiza cada hora en punto, todo el día** (`HORARIO_CASA`,
  `INTERVALO_CASA_MIN`), desde el NAS. En esas pasadas solo se recalcula la
  página de casa (`SOLO_CASA=1` en `publica.sh`): los datos del trayecto se
  vuelven a publicar tal como estaban, para no alterar su horario ni su
  decisión. La página muestra su horario como la del trayecto.

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
