# 10. Modo aviso: actualización cada 10 minutos

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

La página de casa se actualizaba cada hora y la del trayecto cada media hora.
El 05-10-2026 la lluvia en Montflorit pasó de casi nada a 26 mm/h en veinte
minutos (de 9:00 a 9:20). Juanjo preguntó si en situaciones de riesgo no
convendría actualizar más a menudo.

## Decisión

- **Modo aviso** cuando se da cualquiera de estas cosas
  (`motivos_modo_aviso` en `prevision.py`): aviso de AEMET vigente en el
  Vallès, plan de Protección Civil en alerta o emergencia, lluvia en alguna
  estación (Montflorit o Meteocat) o lluvia en el radar a menos de 15 km
  (`RADAR_AVISO_KM`).
- **En modo aviso, cada 10 minutos** (`MODO_AVISO_INTERVALO_MIN`): la página de
  casa todo el día (hasta las 23:50) y la del trayecto dentro de sus franjas.
  Más deprisa no sirve: el radar da una imagen cada 10 minutos.
- **En el minuto 1** (:01, :11, :21…; `MODO_AVISO_DESFASE_MIN`), para coger
  siempre la imagen nueva del radar. Propuesta de Juanjo («puedes actualizar
  un minuto después de que se actualice»), en lugar de pasar a 11 minutos, que
  habría ido desplazándose respecto a las imágenes.
- **El horario lo decide un solo sitio:** cada publicación escribe su horario
  en los datos (`horari`, con `cada_min`, `desfase_min` y `mode_avis`), la web
  lo muestra («Mode avís: dades cada 10 min») y el reloj del NAS lo lee con
  `que_toca.py` para decidir qué hacer en cada minuto. Lo que dice la página y
  lo que se hace no pueden separarse.
- **La decisión de la mañana** se sigue recalculando en la pasada de las 7:31:
  el corte es el final de la ida más el desfase y dos minutos.

## Alternativas descartadas

- **Cada 11 minutos:** el minuto de actualización iría cambiando respecto a
  las imágenes del radar; unas veces cogería la nueva y otras no.
- **Cada 10 minutos siempre:** sin riesgo no aporta y multiplica las consultas.

## Consecuencias

En un día de aviso, la estación de Montflorit pasa de 24 a hasta 144
consultas (unos 380 KB cada una), y el registro guarda más líneas. Con un plan
de Protección Civil activado sin hora de fin, el modo aviso dura hasta que lo
desactivan.

## Evidencia

- Medida del 05-10-2026: la imagen de las 11:10 ya estaba disponible a las
  11:10:47; el archivo de RainViewer indicaba la de las 11:00 generada a las
  11:00:23.

## Riesgos y limitaciones

- Si RainViewer se retrasa más de un minuto, esa pasada coge la imagen
  anterior; la siguiente, diez minutos después, ya tiene la nueva.

## Validación

Pruebas automáticas del horario normal, del modo aviso con desfase, del paso
por las 23:50 y de las razones que activan el modo aviso
(`tests/test_horario.py`).
