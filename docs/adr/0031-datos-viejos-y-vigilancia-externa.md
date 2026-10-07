# 31. Datos viejos y vigilancia externa

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

Juanjo preguntó qué pasa si el NAS deja de funcionar. La web (GitHub Pages)
y sus datos (IONOS) siguen en pie, pero congelados: la página avisaba a los 20
minutos de que faltaba una actualización y seguía mostrando debajo la
previsión, los veredictos de «Si surts» y el estado de los trenes como si
fueran de ahora. Para un vecino que no lea el aviso, eso puede llevar a
error. Además, si el NAS contesta pero el contenedor no publica, nadie avisaba
a Juanjo: el latido de IONOS solo mira si el NAS responde.

## Decisión

- **En la web** (`comu.js`, `dadesVelles` y `blocDadesVelles`): con datos de
  más de 2 horas (`DADES_VELLES_H`), las dos páginas dejan de mostrar la
  previsión, los avisos, los veredictos, las casillas y los trenes, y dicen de
  cuándo son los datos y dónde mirar mientras tanto: la previsión de Meteocat
  para Cerdanyola, su radar, Rodalies y FGC. Cuando llegan datos nuevos, todo
  vuelve.
- **En IONOS** (`ionos/latido.sh` de `vigilancia-nas`): en la misma vuelta de
  cada 10 minutos, si `montflorit.json` lleva más de 60 minutos sin renovarse,
  avisa a Juanjo por Telegram una vez, y otra cuando vuelve a renovarse.

## Alternativas descartadas

- **Ocultar antes** (20-30 minutos): un fallo pasajero de una fuente dejaría
  la página vacía; el aviso de retraso ya sale a los 20.
- **Una página de reserva calculada fuera del NAS**: es otra decisión, mayor;
  ver la conversación del 07-10-2026 y, si se hace, su propio ADR.

## Consecuencias

- Con el NAS caído, quien abra la web ve un aviso claro y enlaces oficiales,
  no una previsión vieja.
- Los avisos por Telegram de la página (peligro, lluvia, riera) siguen
  parándose con el NAS.

## Evidencia

- Enlace de Meteocat para Cerdanyola: código municipal 082665, sacado de la
  lista de municipios de su web (`/prediccio/municipal/082665`, 200 el
  07-10-2026).
- `date -r` funciona en la shell de IONOS; el `$HOME` del cron ya es `htdocs`.

## Riesgos y limitaciones

- La hora del archivo en IONOS es la de la subida, no la de los datos: si el
  NAS subiera datos viejos, el latido no lo vería (la web sí, por `generat`).

## Validación

`tests/test_web.py` (`dadesVelles` con 2 h 10 min y 1 h 50 min); las dos
páginas, en catalán y castellano, con datos de hace 3 horas en Firefox y WebKit
móvil; `latido.sh --probar` con un archivo de hace 2 horas (avisa) y con el
real (no avisa), en IONOS, el 07-10-2026.
