# Instrucciones para agentes

Este repositorio responde a preguntas sobre el tiempo en el trayecto en moto
Cerdanyola → Parc Taulí y publica la recomendación en
<https://jjdeharo.github.io/meteo-local/>. Lugares, horario, fuentes y regla:
[README.md](README.md), `config.py` y `docs/adr/`.

Al preguntar:

1. Ejecuta `python3 prevision.py`. Si falla alguna fuente, consúltala a mano:
   no la des por vacía.
2. **Mira el radar en imagen**, no solo los números: compón el mosaico de
   RainViewer sobre el mapa y ábrelo. Las tormentas se forman en minutos.
3. Responde con **un solo medio para todo el día** (quien va en moto vuelve
   en moto), el riesgo de cada trayecto y, en pocas frases, el porqué.

Al cambiar algo:

- La web está en catalán y va dirigida a quien hace el trayecto.
- **El repositorio es público**: nada de direcciones exactas ni nombres. Las
  coordenadas van redondeadas.
- Si cambia la regla o un umbral, actualiza `config.py`, el texto «Com es
  decideix» de `web/index.html`, el README, las pruebas y el ADR.
- Pasa las pruebas, `probar-web` y axe-core antes de publicar; sube `VERSION`
  en `config.py` y etiqueta la versión.
- Los datos se publican en IONOS (`bilateria.org/app/meteo-local/`) y la web
  en la rama `gh-pages` cada media hora como mucho (ADR 0020). La clave del NAS
  para IONOS solo puede dejar `.json` en esa carpeta (orden fija en el
  `authorized_keys` de IONOS); la carpeta tiene un `.htaccess` que permite leer
  los datos desde `jjdeharo.github.io` y `meteo-montflorit.github.io`.
- La página de casa se publica también como web pública, «Temps a Montflorit»
  (repositorio `meteo-montflorit/meteo-montflorit.github.io`, en
  <https://meteo-montflorit.github.io/>; ADR 0024 y 0028): la genera
  `montflorit.py` y no puede decir «casa» ni nada del trayecto. Si cambias un texto de `web/casa.html` o
  `web/fonts.html` que esté en sus listas de cambios, cámbialo también allí;
  las pruebas avisan. En ese repositorio no se edita nada a mano.
- La web pública está también en castellano (ADR 0025). Todo texto visible de
  `web/comu.js` y `web/casa.js` va con `T` (o `TD` si viene en los datos) y
  tiene su traducción en `montflorit/es.js`; los textos fijos de
  `web/casa.html` y `web/fonts.html`, en `i18n/es.json`. Si añades o cambias
  uno, tradúcelo: las pruebas fallan si falta.
- Las actualizaciones programadas las hace el NAS (`nas/`, ADR 0005). Si cambias
  `nas/`, copia los archivos a `/volume1/docker/meteo-local` y reconstruye
  (`docker compose up -d --build`). Ver el estado: `docker logs meteo-local`.
- El agente diario (`agent/`, ADR 0009) se prueba en local con
  `DADES=web/dades.json CASA=web/casa.json COMENTARI=/tmp/c.json CLAUDE_ENV=/nonexistent agent/executa.sh mati`.
- Los automatismos de este proyecto figuran en el inventario del NAS
  (`vigilancia-nas/config/automatismos.json`, ficha «Automatismos» de
  bilateria.org/nas). Si se añade, cambia o retira uno, se actualiza allí.
- El registro está en el NAS, en `/volume1/docker/meteo-local/estat/registre`
  (`resultats.csv` y un `.jsonl` por mes). Resumen: `docker exec meteo-local
  python3 /proyecto/registre.py resum`.
