# 2. Publicación en GitHub Pages con una acción programada

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

La recomendación tiene que poder consultarla desde el móvil quien hace el
trayecto, sin ejecutar nada, y estar al día cada mañana y cada mediodía. Es
un repositorio público.

## Decisión

- Una acción de GitHub (`.github/workflows/previsio.yml`) pasa las pruebas,
  ejecuta `prevision.py` y despliega `web/` en GitHub Pages con
  `actions/deploy-pages`. Se programa cada media hora de 5:00 a 7:00 y de
  13:00 a 15:00 (hora local, en horario de verano y de invierno) y dos veces
  por la tarde para el día siguiente.
- `dades.json` no se guarda en el repositorio: se genera en cada ejecución.
  Así no hay commits automáticos.
- La web está en catalán, dirigida a quien hace el trayecto, sin su nombre.
  Lleva `noindex` para que los buscadores no la indexen.
- **Privacidad:** el repositorio no tiene la dirección de casa; las
  coordenadas van redondeadas a unos 500 m, que no cambian la previsión. La
  primera versión, con la dirección exacta, nunca se subió: se rehízo el
  historial local antes de crear el repositorio.
- El tema sigue al del dispositivo, con el mismo conmutador que Sirena.

## Alternativas descartadas

- **Página fija con la recomendación de hoy**: quedaría vieja al día
  siguiente.
- **Ejecutarlo en el NAS o en el ordenador de casa y subir el resultado**:
  depende de que esa máquina esté encendida y añade commits cada media hora.
- **Cinco idiomas**: es una herramienta para una sola persona, que la lee en
  catalán.

## Consecuencias

La página muestra la hora de la última actualización y avisa si los datos
tienen más de 3 horas o si ha fallado alguna fuente.

## Evidencia

- Ejecución local del 05-10-2026: `probar-web` sin errores en Chromium,
  Firefox y WebKit, escritorio y móvil, tema claro y oscuro; axe-core sin
  incidencias en las dos páginas.

## Riesgos y limitaciones

- GitHub puede retrasar las ejecuciones programadas (a veces más de 15
  minutos) o saltarse alguna en horas de mucha carga.
- GitHub desactiva las acciones programadas de un repositorio público tras 60
  días sin actividad. La acción se reactiva a sí misma por la API el día 1 de
  cada mes. **Hipótesis pendiente de validación**: que reactivar una acción
  que ya está activa reinicie el plazo de 60 días.
- meteo.cat podría bloquear las peticiones desde los servidores de GitHub; en
  ese caso falla solo el bloque de estaciones y la web lo avisa.

## Validación

Primera ejecución en GitHub el 05-10-2026 (ver el historial de la acción).
