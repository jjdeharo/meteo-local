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
- **Si cambias una clave del NAS o de IONOS** (claves SSH, `ecowitt.env`,
  `ionos.env`, `claude.env`, el token de un bot o el usuario de IONOS),
  vuelve a cifrar el archivo correspondiente (`claus/claus-nas.tar.gz.gpg` o
  `claus/claus-ionos.tar.gz.gpg`) en el repositorio privado
  `meteo-montflorit/meteo-local-registre` y súbelo, con la misma orden de
  `RESTAURAR.md` al revés (`tar czf - … | gpg --symmetric --cipher-algo AES256`).
  La contraseña la escribe Juanjo en la ventana de gpg; avísale antes. Nada
  lo hace solo (ADR 0044 y 0045). Los suscriptores del bot no se copian.
- Si cambia un umbral, actualiza `config.py`, el texto «Com es decideix» de
  `web/sortir.html` (o «D'on surt» de `web/casa.html`), el README, las pruebas
  y el ADR.
- Pasa las pruebas y `probar-web` antes de publicar; sube `VERSION` en
  `config.py` y etiqueta la versión. Pasa también axe-core si cambia el HTML,
  el CSS o el JavaScript que crea o modifica elementos de la página; no hace
  falta si el cambio es solo de cálculo, de datos, del bot o de textos dentro
  de elementos que ya existen.
- Los datos públicos (`montflorit.json`) se publican en IONOS
  (`bilateria.org/app/meteo-local/`) y la web, cada media hora como mucho
  (ADR 0020). Este repositorio no publica ninguna web: las direcciones
  antiguas (`jjdeharo.github.io/meteo-local/…`) las redirige
  `jjdeharo/jjdeharo.github.io` (ADR 0035). La clave del NAS para IONOS solo
  puede ejecutar `reserva/rep-dades.sh` (orden fija en el `authorized_keys` de
  IONOS, instalado en `.meteo-reserva/bin/rep-dades` por `reserva/instalar.sh`),
  que solo acepta `montflorit.json` y `avisos.json` como archivos normales con
  JSON válido y de 2 MB como mucho, también descomprimidos (ADR 0038 y 0057); la carpeta tiene un `.htaccess` que permite leer los
  datos desde `meteo-montflorit.github.io`.
- La web pública (repositorio `meteo-montflorit/meteo-montflorit.github.io`;
  ADR 0024, 0028 y 0029) la genera `montflorit.py` a partir de
  `web/casa.html`, `web/sortir.html` y `web/fonts.html`, y no puede decir
  «casa» ni nada del trayecto (en «Si surts» sí «moto» y «cotxe»; los créditos
  y el README enlazan este repositorio y sus ADR). Si cambias
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
- El bot de Telegram vive en IONOS (`bot/`, ADR 0034). Estado: `ssh
  ionos-webspace 'python3 .meteo-reserva/repo/bot/bot.py estat'`; tras cambiar
  sus órdenes o descripción, `bot/instalar.sh`. Los suscriptores son datos
  personales: no se copian fuera de IONOS ni se publican. Los avisos en el
  navegador (página «Avisos», ADR 0048) también viven allí: `bot/push.py`
  envía cada minuto y `bot/subscripcio.php` guarda las suscripciones en
  `.temps-bot/push.json`, igual de personales. Estado: `ssh ionos-webspace
  '.meteo-reserva/v/bin/python .meteo-reserva/repo/bot/push.py estat'`.
- Los automatismos de este proyecto figuran en el inventario del NAS
  (`vigilancia-nas/config/automatismos.json`, ficha «Automatismos» de
  bilateria.org/nas). Si se añade, cambia o retira uno, se actualiza allí.
- El registro está en el NAS, en `/volume1/docker/meteo-local/estat/registre`
  (avisos de lluvia, episodios de la riera y lo medido). Resúmenes:
  `docker exec meteo-local python3 /proyecto/pluja_arriba.py resum`,
  `docker exec meteo-local python3 /proyecto/riera.py resum` y, lo que dijo
  «Si surts» de cada medio y lo que pasó, `docker exec meteo-local python3
  /proyecto/aprenentatge.py sortir` (ADR 0047 y 0068); el final de la lluvia según el
  radar, `docker exec meteo-local python3 /proyecto/fi_pluja.py resum`
  (ADR 0049).
