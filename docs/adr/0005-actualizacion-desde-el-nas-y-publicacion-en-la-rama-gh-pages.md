# 5. Actualización desde el NAS y publicación en la rama gh-pages

Fecha: 2026-10-05 · Estado: aceptado · Sustituye en parte al ADR 0002

## Contexto

La web debe decir en qué horario se actualiza, y tiene que ser verdad. El
ADR 0002 programaba las actualizaciones en GitHub Actions, pero el 05-10-2026
GitHub no lanzó ninguna de las programadas (de 4:00 a 7:15 UTC, cada 15-30
minutos): todas las ejecuciones fueron de subidas. Juanjo ya había elegido el
NAS para el agente diario.

## Decisión

- **El NAS hace las actualizaciones.** Un contenedor `meteo-local` en
  `/volume1/docker/meteo-local` (archivos en `nas/`) mira cada minuto si la
  hora local es de actualización y, si toca, pone al día su copia del
  repositorio y ejecuta `publica.sh`.
- **El horario está en un solo sitio**, `config.py` (`HORARIO`,
  `INTERVALO_MIN`): de 5:00 a 7:30 y de 13:00 a 15:30, cada 30 minutos. El
  reloj del NAS y la web lo leen de ahí.
- **Se publica en la rama `gh-pages`**, de la que sirve GitHub Pages, con un
  solo commit que se rehace cada vez. La rama `main` no recibe commits
  automáticos.
- **GitHub Actions ya no programa nada:** en cada subida a `main` pasa las
  pruebas y publica con el mismo `publica.sh`.
- **El NAS empuja con una clave de despliegue** que solo da acceso a este
  repositorio («NAS meteo-local», de escritura), no con la sesión de GitHub de
  Juanjo.
- **La decisión del día se lee del archivo `estat/dades.json` del NAS**, no de
  la web, que puede tardar unos minutos en ponerse al día.
- **Desde las 7:30 la web no recomienda medio**: muestra solo el tiempo de la
  vuelta (riesgo de lluvia, temperatura y rachas de viento), que se actualiza
  de 13:00 a 15:30 (Juanjo, 05-10-2026).

## Alternativas descartadas

- **Seguir con la programación de GitHub:** no fue puntual ni una vez.
- **Que el NAS lance la acción de GitHub:** necesitaría un token de la API, con
  más permisos que una clave de despliegue, y añade el retraso de arrancar la
  máquina de GitHub.
- **Commits de datos en `main` cada media hora:** unos 12 al día que no
  aportan nada al historial.

## Consecuencias

Si el NAS está apagado, la web no se actualiza y lo dice: avisa cuando una
actualización prevista lleva más de 20 minutos sin llegar. Los cambios de
código salen al subirlos (acción de GitHub) y el NAS los recoge en la pasada
siguiente.

## Evidencia

- Lista de ejecuciones del 05-10-2026: ninguna con evento `schedule`.
- La huella ED25519 de github.com en el `known_hosts` del NAS coincide con la
  publicada en `api.github.com/meta`.
- Pasada manual desde el NAS a las 7:18 y la primera automática a las
  7:30:13, publicada en la web en menos de un minuto.
- Esa pasada de las 7:30 mantuvo la decisión de las 7:18 en lugar de
  recalcular, porque el corte era a las 7:30 en punto. Se añadió un margen de
  cinco minutos para que la última pasada de la mañana aún recalcule.

## Riesgos y limitaciones

- La rama `gh-pages` la pueden reescribir a la vez el NAS y la acción de
  GitHub; gana la última, y las dos calculan con los mismos datos.
- GitHub Pages tarda alrededor de un minuto en servir cada publicación.

## Validación

Prueba con el reloj del navegador simulado a las 6:50, 13:40 y 16:00 en
Chromium y Firefox: modo recomendación, modo vuelta y aviso de actualización
que no ha llegado.
