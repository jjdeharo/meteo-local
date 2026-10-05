# 16. Previsión de reserva si falla Open-Meteo

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

El 05-10-2026 a las 19:37, Open-Meteo respondió «503 Service Unavailable» y
esa pasada publicó la página de casa sin previsión: ni tabla ni recomendación
de salida fuera de las franjas (ADR 0014) hasta la pasada siguiente. Juanjo
aprobó mantener la última previsión buena avisando de que es de antes.

## Decisión

- Si fallan los modelos, `casa.py` reutiliza la última `casa.json`
  publicada (`--anterior`, que `publica.sh` le pasa: en el NAS,
  `/estat/casa.json`), solo con las horas que aún no han pasado.
- Lo que sigue llegando se pone al día: los avisos de AEMET de cada hora y,
  si ahora llueve en Montflorit, «Plou ara» en la primera hora. Las salidas
  fuera de las franjas se recalculan con esas horas.
- `previsio_de` guarda la hora de la previsión buena, también si la reserva
  se encadena en varias pasadas. Con más de 6 horas
  (`CASA_PREVISION_ANTERIOR_MAX_H`) no se usa: ya no sería fiable.
- Las dos páginas lo dicen arriba, con los avisos: «Open-Meteo, d'on surten
  els models, ara no respon: la previsió és la de les HH:MM». El aviso
  genérico de fuentes que fallan no se repite por la misma causa.
- La reserva no se apunta en el registro de aprendizaje (ADR 0012): no es una
  previsión nueva.

## Alternativas descartadas

- **Publicar sin previsión** (lo de antes): deja sin respuesta justo cuando
  se consulta.
- **Reintentar en la misma pasada:** la caída puede durar minutos; la pasada
  siguiente, a los 10 o 30 minutos, ya vuelve a intentarlo.

## Riesgos y limitaciones

- La probabilidad aprendida y la temperatura de la reserva son las de la hora
  en que se calcularon; solo la lluvia de ahora y los avisos están al día.

## Validación

`tests/test_previsio_anterior.py` (horas que quedan, lluvia de ahora,
encadenado y caducidad) y prueba de principio a fin con un fallo 503 simulado:
las dos páginas muestran la reserva y su aviso; `probar-web` y axe-core.
