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
- Las actualizaciones programadas las hace el NAS (`nas/`, ADR 0005). Si cambias
  `nas/`, copia los archivos a `/volume1/docker/meteo-local` y reconstruye
  (`docker compose up -d --build`). Ver el estado: `docker logs meteo-local`.
- El registro está en el NAS, en `/volume1/docker/meteo-local/estat/registre`
  (`resultats.csv` y un `.jsonl` por mes). Resumen: `docker exec meteo-local
  python3 /proyecto/registre.py resum`.
