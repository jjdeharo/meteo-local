# 6. Registro de aciertos y de todas las señales

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

La regla combina las fuentes con umbrales y deja mandar a la más desfavorable
(ADR 0001). Un método estadístico que pese cada fuente según lo que acierta
sería mejor, pero solo hay historial de los modelos y de las estaciones de
Meteocat: el de las simulaciones de ICON-EU llega a tres meses atrás, el radar
gratuito no lo tiene, Montflorit solo da 24 horas y el archivo de avisos de
AEMET pide una clave. Juanjo aprobó guardar desde ya todo lo necesario y pedir
la clave (05-10-2026).

## Decisión

- `prevision.py` guarda en cada trayecto, además de los motivos, las
  **señales en números** (`senyals`): avisos del Vallès y de la costa, distancia
  y crecimiento del radar, lluvia de cada estación, lluvia máxima de cada
  modelo (finos y globales), CAPE y fracción de simulaciones con lluvia.
- `registre.py`, ejecutado por el reloj del NAS sin IA:
  - después de cada actualización apunta todos los datos publicados en
    `/estat/registre/AAAA-MM.jsonl`;
  - a las 16:00 (`HORA_VERIFICACION`) mide la lluvia que cayó en la ida y la
    vuelta en Montflorit, Sabadell y Sant Cugat, y clasifica el día en
    `resultats.csv`: acierto, coche sin lluvia, lluvia en moto, o lluvia en moto
    habiendo avisado del impermeable;
  - a los 28 días (`REGISTRO_DIAS_AVISO`) manda un resumen a Juanjo por
    Telegram, una sola vez. Si hay menos de 5 días de lluvia
    (`REGISTRO_LLUVIAS_MINIMAS`), el resumen dice que aún no se puede juzgar.
- Los datos se quedan en el NAS: son material de trabajo, no se publican.

## Alternativas descartadas

- **Que Juanjo revise los aciertos:** el registro y la clasificación son
  mecánicos.
- **Entrenar ya un modelo con todas las fuentes:** no hay historial de varias
  de ellas, y la lluvia en el trayecto es rara (unos 25 días al año).

## Consecuencias

Cuando haya bastantes días se podrá entrenar un modelo con todas las fuentes y
compararlo con la regla con días que no haya visto. La elección del medio pasaría
a ser una probabilidad con un umbral que decide Farners.

## Evidencia

- Prueba del 05-10-2026 (a mano, a las 9:30): coche; en la ida, 24,6 mm en
  Montflorit, 22,5 en Sant Cugat y 1,0 en Sabadell; resultado, acierto.
- API de simulaciones de Open-Meteo: «start_date out of allowed range from
  2026-07-04» (05-10-2026).
- El aviso por Telegram usa el `avisar-juanjo` y la configuración del
  contenedor del boletín, copiados al de meteo-local.

## Riesgos y limitaciones

- La lluvia de Montflorit sale de su API de las últimas 24 horas: si el NAS
  está apagado a las 16:00, ese día se queda sin verificar (se puede verificar
  a mano antes de que pasen 24 horas).
- Las dos estaciones de Meteocat salen de la tabla del día de meteo.cat, con
  el mismo límite.

## Validación

Prueba manual de `apunta`, `verifica` y `resum` con los datos del 05-10-2026.
