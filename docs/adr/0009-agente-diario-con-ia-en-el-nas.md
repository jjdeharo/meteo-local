# 9. Agente diario con IA en el NAS

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

La regla fija acierta bastante (ADR 0003), pero no tiene el juicio de quien
mira el radar en imagen o nota que los modelos no ven un episodio. Juanjo
pidió montar un agente diario en el NAS (05-10-2026), después de valorar que
el gasto de suscripción es el mismo que en la nube (ADR 0005).

## Decisión

- **Cuándo:** a las 6:07 (modo «mati») y a las 13:07 (modo «tarda»)
  (`AGENTE_HORAS`), después de la actualización de la hora en punto; después,
  el reloj vuelve a publicar con el comentario.
- **Qué recibe:** `dades.json` y `casa.json` ya calculados y una imagen del
  radar (`agent/radar.py`: tres fotogramas de la última hora, con el trayecto
  marcado). Instrucciones en `agent/instruccions.md`.
- **Qué puede hacer:** solo leer archivos (`--allowedTools "Read"`), con
  `--max-turns 6`. Ni comandos ni internet: no puede hacer nada fuera de su
  papel, y lo que hay en los datos no son instrucciones para él.
- **Qué devuelve:** un JSON con un comentario en catalán de una o dos frases
  cortas (35 palabras como máximo, sin repetir avisos ni niveles que la página
  ya muestra; simplificado el 05-10-2026 a petición de Juanjo),
  un nivel (`moto`, `compte`, `cotxe`) y su confianza. `agent/desa.py` lo
  valida y guarda en `/estat/comentari.json` con la hora y los niveles que daba
  el programa.
- **Cuánto pesa:** por la mañana puede hacer la recomendación más prudente,
  nunca menos que la regla («manda el más desfavorable», ADR 0001). Por la
  tarde solo comenta el tiempo de la vuelta, sin recomendar medio.
- **Caducidad:** el comentario deja de mostrarse si el programa cambia los
  niveles con que se escribió, para que la página nunca diga dos cosas
  contradictorias.
- **Etiqueta:** «Valoració feta amb IA (hh:mm)».
- **Modelo:** Claude Sonnet 5.5 (`claude-sonnet-5-5` en `AGENTE_MODELO`),
  suficiente para este juicio y más barato en uso de suscripción. Se fija por
  su nombre exacto y no con el alias `sonnet`, que pasaría solo al siguiente
  Sonnet y podría cambiar cómo escribe.
- **Acceso:** token de un año creado con `claude setup-token`, en
  `home/.config/meteo-local/claude.env` (`CLAUDE_CODE_OAUTH_TOKEN`), separado
  de la sesión del contenedor del boletín, porque compartir una sesión que se
  renueva sola puede invalidar la del otro.
- **Claude Code en la imagen**, con la versión común de los contenedores de
  agentes del NAS (`/volume1/docker/versiones/versiones.env`, enlazado como
  `.env`), que el actualizador semanal de vigilancia-nas pone al día con
  comprobación y vuelta atrás. El `Dockerfile` conserva la 2.1.289 por si falta.

## Alternativas descartadas

- **Que el agente escriba en cada actualización:** unas 25 ejecuciones al día
  y textos que podrían contradecirse.
- **Que pueda bajar la prudencia de la regla:** el coste de equivocarse no es
  simétrico.
- **Darle acceso a internet o a comandos:** no lo necesita.

## Consecuencias

El registro (ADR 0006) guarda el comentario de cada día con los datos, y a las
pocas semanas se podrá ver si el agente acierta más que la regla.

## Evidencia

Prueba del 05-10-2026 a las 10:18, con los datos reales y Sonnet: 15 s por
ejecución; los dos modos dieron textos correctos y concretos (lluvia medida,
banda de tormentas sobre el trayecto, plan de inundaciones). En la primera
prueba apareció una expresión sin sentido («aliments d'avís»); se añadió a
las instrucciones que relea el texto, y no volvió a salir en dos pruebas más.

## Riesgos y limitaciones

- El texto lo escribe un modelo: puede contener errores. La decisión nunca
  queda por debajo de la regla, y el comentario lleva la etiqueta de IA.
- El token caduca al año (octubre de 2027): habrá que repetir
  `claude setup-token`.

## Validación

Pruebas automáticas: el agente puede subir la prudencia, no bajarla, y el
comentario caduca si cambian los niveles (`tests/test_decidir.py`). Captura
de la página con el comentario en los dos modos.
