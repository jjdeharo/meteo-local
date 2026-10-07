# Instrucciones para agentes

Este repositorio calcula y publica «Temps a Montflorit»
(<https://meteo-montflorit.github.io/>): el tiempo en el barrio y «Si surts»
(medios, ropa, consejos y trenes para quien sale). Lugares, horario, fuentes y
umbrales: [README.md](README.md), `config.py` y `docs/adr/`. La página del
trayecto «Moto o cotxe?» y su agente con IA se retiraron el 07-10-2026 (ADR
0030): su dirección redirige a «Si surts».

Al preguntar por el tiempo, ejecuta `python3 casa.py --json /tmp/casa.json`
y **mira el radar en imagen**, no solo los números. Si falla alguna fuente,
consúltala a mano: no la des por vacía.

Al cambiar algo:

- La web está en catalán y castellano y va dirigida a cualquier vecino.
- **El repositorio es público**: nada de direcciones exactas ni nombres. Las
  coordenadas van redondeadas.
- Si cambia un umbral, actualiza `config.py`, el texto «Com es decideix» de
  `web/sortir.html` (o «D'on surt» de `web/casa.html`), el README, las pruebas
  y el ADR.
- Pasa las pruebas, `probar-web` y axe-core antes de publicar; sube `VERSION`
  en `config.py` y etiqueta la versión.
- Los datos públicos (`montflorit.json`) se publican en IONOS
  (`bilateria.org/app/meteo-local/`) y la web, cada media hora como mucho
  (ADR 0020). La rama `gh-pages` de este repositorio solo tiene
  `redireccions/`. La clave del NAS para IONOS solo puede dejar `.json` en esa
  carpeta (orden fija en el `authorized_keys` de IONOS); la carpeta tiene un
  `.htaccess` que permite leer los datos desde `meteo-montflorit.github.io`.
- La web pública (repositorio `meteo-montflorit/meteo-montflorit.github.io`;
  ADR 0024, 0028 y 0029) la genera `montflorit.py` a partir de
  `web/casa.html`, `web/sortir.html` y `web/fonts.html`, y no puede decir
  «casa» ni nada del trayecto (en «Si surts» sí «moto» y «cotxe»). Si cambias
  un texto que esté en sus listas de cambios, cámbialo también allí; las
  pruebas avisan. En ese repositorio no se edita nada a mano.
- La web pública está también en castellano (ADR 0025). Todo texto visible de
  `web/comu.js`, `web/casa.js` y `web/sortir.js` va con `T` (o `TD` si viene
  en los datos) y tiene su traducción en `montflorit/es.js`; los textos fijos
  de las páginas, en `i18n/es.json`. Los avisos de Renfe y FGC no se traducen:
  van en el idioma en que los publican. Si añades o cambias
  uno, tradúcelo: las pruebas fallan si falta.
- Las actualizaciones programadas las hace el NAS (`nas/`, ADR 0005). Si cambias
  `nas/`, copia los archivos a `/volume1/docker/meteo-local` y reconstruye
  (`docker compose up -d --build`). Ver el estado: `docker logs meteo-local`.
- Si el NAS no publica, lo hace la reserva de IONOS (`reserva/`, ADR 0032).
  Estado: `ssh ionos-webspace '.meteo-reserva/v/bin/python
  .meteo-reserva/repo/reserva/reserva.py estat'`; tras cambiar `reserva/`,
  `reserva/instalar.sh` (se pone al día sola cada hora con `git pull`).
- Los automatismos de este proyecto figuran en el inventario del NAS
  (`vigilancia-nas/config/automatismos.json`, ficha «Automatismos» de
  bilateria.org/nas). Si se añade, cambia o retira uno, se actualiza allí.
- El registro está en el NAS, en `/volume1/docker/meteo-local/estat/registre`
  (avisos de lluvia, episodios de la riera y lo medido). Resúmenes:
  `docker exec meteo-local python3 /proyecto/pluja_arriba.py resum` y
  `docker exec meteo-local python3 /proyecto/riera.py resum`.
