# 67. Avisos de peligro de Meteocat para el Vallès Occidental, junto a los planes

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

Un plan de Protección Civil en alerta («Pla d'inundacions (INUNCAT) en fase
d'alerta») no dice a qué zona afecta, y el vecino no sabe si va con él (ADR
0066). Juanjo preguntó qué se podía hacer y aprobó esta vía (10-10-2026:
«de acuerdo hazlo así»).

Lo comprobado ese día:

- Los datos abiertos de los planes (conjunto `wj9c-j6vf`) solo traen plan,
  fase, si está activado, una descripción corta («Emergència INUNCAT 3-7
  Octubre») y el PDF del comunicado. En el catálogo de datos abiertos de la
  Generalitat no hay ningún conjunto con la zona de cada activación.
- El comunicado (PDF del 08-10-2026, I-127743) describe la zona en texto
  libre y no siempre con nombres («comarques del litoral i prelitoral nord i
  central»): leerlo daría errores.
- Los avisos de peligro de Meteocat (situació meteorològica de perill, SMP)
  son por comarca, y el propio comunicado se apoya en ellos.
- **La API de Meteocat no sirve**: sus condiciones de uso dicen «No difondre
  a tercers, total ni parcialment, la informació rebuda de l'SMC», el alta
  pide el NIF y la suscripción gratuita dura como mucho un año.
- **Las páginas públicas de meteo.cat llevan los mismos avisos**, con la
  estructura de `/smp/episodis-oberts` de la API, en la llamada
  `Meteocat.avisosSMP({… avisos: [...] …})` (la portada y
  <https://www.meteo.cat/prediccio/general>, unos 310 KB). Su aviso legal
  (<https://www.meteo.cat/wpweb/avis-legal/>) permite reutilizar lo que
  publica en abierto sin alterarlo, sin desnaturalizarlo, citando la fuente
  e indicando la fecha: la misma base que el radar (ADR 0019).
- En `script.min.js` de meteo.cat (`_crearAvisosCombinatsLayer`) el grado de
  peligro va de 1 a 6: 1-2 moderado, 3-4 alto, 5-6 muy alto, y el mapa solo
  pinta los avisos vigentes que no son preavisos. El Vallès Occidental es la
  comarca 40 (`IDComarca` de `comarquesAmbMar.json`, el mapa de la web).

## Decisión

- **Con un plan a la vista** (los que no se ocultan por el ADR 0062), cada
  pasada lee la página de predicción general de meteo.cat (`smp.py`) y se
  queda con los avisos vigentes, no preavisos, que afectan a la comarca 40.
  Sin plan, no se lee: no se muestra en ningún otro sitio.
- **Junto al plan** (web, /avisos_actius y el aviso del plan nuevo por
  Telegram y el navegador) va una línea por aviso, con el círculo de su grado
  (ADR 0065):
  «Meteocat: avís de perill alt per «Intensitat de pluja» al Vallès
  Occidental, dissabte 10 de 12 a 24 h (Intensitat > 20 mm / 30 minuts; emès
  a les 10:09).» El meteoro y el umbral, tal como los publica Meteocat, en
  catalán también en la versión castellana (lo oficial ajeno, en su idioma);
  las franjas, las suyas, juntas si son seguidas; los días, por su nombre,
  para que no caduquen al pasar la medianoche.
- **Sin aviso**: «Meteocat no té cap avís de perill per al Vallès Occidental
  (dades de les 19:00)», con un círculo blanco.
- **Si la lectura falla**, no se dice nada: ni que hay aviso ni que no.
  El error queda en `errors` («smp: …»), que no avisa en la página.
- **Prueba diaria** (`aprenentatge.diari`, a la hora de verificación): si la
  página deja de traer los avisos, se le dice una vez a Juanjo por Telegram,
  y otra cuando vuelven (marca `smp-falla` en el directorio de aprendizaje).
- «Fonts i crèdits» cita a Meteocat como fuente de estos avisos.

## Riesgos y limitaciones

- No es una API: si Meteocat cambia su página, la lectura falla hasta que se
  arregle (lo detecta la prueba diaria).
- **Hipótesis sin comprobar**: que las franjas («12-18») son horas locales,
  como las muestra meteo.cat; se reproducen tal cual, sin convertir. Que
  `auxiliar` no cambia nada: se cuentan todas las afectaciones de la
  comarca. No había ningún aviso vigente el 10-10-2026 para verlo con datos
  reales: las pruebas usan el ejemplo de la documentación de la API.
- Cada lectura pesa unos 310 KB; con un plan activo y el modo vigilancia,
  cada 6 minutos.

## Validación

`tests/test_smp.py`: lectura de la página, filtro de comarca y de
preavisos, grado, franjas juntas, textos en los dos idiomas, la línea en
/avisos_actius y en el aviso del plan, sin lectura nada, y la prueba diaria.
Contra meteo.cat real el 10-10-2026 a las 19:25: lee la lista (vacía) y da
«Meteocat no té cap avís de perill per al Vallès Occidental». En la web, con
un plan y un aviso simulados, `probar-web` en Chromium y Firefox, escritorio
y móvil, catalán y castellano.
