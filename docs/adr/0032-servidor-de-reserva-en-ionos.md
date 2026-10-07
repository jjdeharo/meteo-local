# 32. Servidor de reserva en IONOS

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

Si el NAS deja de funcionar, la web se queda sin datos (ADR 0031) y se paran
los avisos por Telegram, también el de la riera (ADR 0027). El caso más
probable es un corte de luz en casa durante una tormenta: justo cuando más
hacen falta. Juanjo preguntó si se podía montar un servicio alternativo, por
ejemplo en IONOS, y aprobó la propuesta («sí, hazlo»).

## Decisión

- **Dónde**: en el hosting de IONOS, fuera de casa, en `~/.meteo-reserva`
  (dentro de `htdocs`, con `.htaccess` que impide servirla): un clon de este
  repositorio, un entorno de Python con numpy y Pillow, el estado y el
  registro. Lo monta `reserva/instalar.sh` desde el portátil.
- **Cuándo actúa** (`reserva/reserva.py vigila`, cron cada 5 minutos): si los
  datos que sube el NAS (`montflorit.json`) tienen más de 35 minutos, calcula
  con el mismo programa (`casa.py`), al ritmo de la página (15 minutos, o 6 en
  modo aviso), y publica los datos marcados con `"reserva": true`. Si el NAS
  publica mientras la reserva calcula, no pisa sus datos. Cuando el NAS vuelve
  a subir datos, la reserva se aparta.
- **Avisos**: al activarse y al apartarse, un mensaje a Juanjo. Mientras está
  activa, manda los avisos de peligro, lluvia inminente y riera en lugar del
  NAS, con el mismo bot (credenciales del vigía de IONOS), marcados como
  «reserva».
- **En la web**: la línea de actualización añade «Dades del servidor de
  reserva».
- **Prueba diaria** (`reserva.py prova`, 4:30): calcula sin publicar ni avisar
  y, si falla, avisa: una reserva rota no se descubre el día que hace falta.
- **Sin**: la estación de casa (sus claves se quedan en el NAS) y el modelo
  aprendido (usa el del archivo, en el repositorio). numpy con un solo hilo:
  el hosting limita la memoria.

## Alternativas descartadas

- **GitHub Actions programadas**: nube de terceros, con retrasos de minutos
  en los cron y sin estado entre ejecuciones; IONOS es de Juanjo y ya tiene
  el vigía.
- **Calcular siempre en los dos sitios**: el doble de peticiones a las fuentes
  y avisos repetidos.
- **Copiar a IONOS las claves de la estación de casa**: más secretos fuera de
  casa para una mejora pequeña en un modo de emergencia.

## Consecuencias

- Unos 100 MB en IONOS y, solo con el NAS caído, alrededor de un minuto de
  cálculo cada 15 minutos.
- El registro de aprendizaje no sigue durante la caída.
- Al volver el NAS, sus avisos parten de su propio estado: puede repetir un
  aviso que ya mandó la reserva.

## Evidencia

- IONOS (07-10-2026): Python 3.13, `venv`, `pip`, `git`, `curl` y cron;
  numpy 2.5.3 y Pillow 12.3.0 se instalan sin permisos de administrador y
  funcionan con `OPENBLAS_NUM_THREADS=1` (con varios hilos, OpenBLAS no
  consigue memoria); salida a Open-Meteo, Renfe y Telegram; límite de 1800 s
  de CPU por proceso.

## Riesgos y limitaciones

- Un cambio del hosting (Python, memoria) puede romper la reserva: la prueba
  diaria lo avisa.
- Si cae también IONOS, no hay reserva.
- La hora del archivo es la de la subida: si el NAS subiera datos viejos, la
  reserva no actuaría (la web los ocultaría a las 2 horas).

## Validación

Ensayo en local con un entorno aislado y un aviso falso (07-10-2026): con
datos de hace una hora, calcula, publica marcado y avisa; repetido enseguida,
espera; con datos nuevos del NAS, se aparta y avisa. En IONOS: prueba diaria
correcta y simulacro sobre los datos reales (ver el registro de instalación).
