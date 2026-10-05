# meteo-local

Responde a una pregunta concreta: **¿lloverá en el trayecto en moto de
Cerdanyola del Vallès al Parc Taulí (Sabadell), a la ida (6:30-7:30) o a la
vuelta (15:00-15:30)?** Da una recomendación (moto, moto con impermeable o
coche) para hoy, con sus motivos.

Web: <https://jjdeharo.github.io/meteo-local/> (en catalán, para quien hace
el trayecto).

## Cómo funciona

Una acción de GitHub ejecuta `prevision.py` varias veces al día (cada media
hora de 5:00 a 7:00 y de 13:00 a 15:00, hora local), guarda el resultado en
`web/dades.json` y publica la carpeta `web/` en GitHub Pages. No se guarda
nada más ni se hacen commits automáticos.

La recomendación junta cinco fuentes y manda la más desfavorable:

1. **Avisos de AEMET** del Prelitoral de Barcelona (el Vallès): un aviso de
   lluvia o tormenta a la hora del trayecto decide por sí solo, coche.
2. **Radar** (RainViewer), solo para las 3 horas siguientes: lluvia a menos de
   15 km y creciendo, coche; a menos de 40 km, atención.
3. **Estaciones de Meteocat** de Sabadell y Sant Cugat: si llueve ahora y falta
   menos de hora y media, coche.
4. **Modelos finos** (AROME HD, AROME e ICON-EU): 1 mm en una hora, coche;
   0,2 mm, atención. Los globales (ECMWF, UKMO, GFS) se descargan pero no
   deciden: sus celdas de 10-25 km incluyen mar.
5. **Ensemble ICON-EU-EPS** (40 miembros): el 50 % o más con lluvia, coche; el
   20 %, atención.

Umbrales y lugares, en `config.py`. El porqué, en los ADR.

## Archivos

| Archivo | Para qué |
|---|---|
| `prevision.py` | Recoge los datos, decide y escribe `dades.json`; sin `--json`, imprime un resumen |
| `config.py` | Coordenadas, horario, estaciones, zonas de aviso, modelos y umbrales |
| `web/` | La página: `index.html`, `app.js`, `estil.css` y `fonts.html` (fuentes y créditos) |
| `tests/` | Pruebas de la regla de decisión, sin red |
| `.github/workflows/previsio.yml` | Programación, pruebas, cálculo y publicación |
| `docs/adr/` | Registro de decisiones |

## Uso local

```sh
python3 prevision.py                        # resumen en la terminal
python3 prevision.py --json web/dades.json  # datos para ver la web en local
python3 -m unittest discover -s tests       # pruebas
```

Necesita Python 3 con `numpy` y `Pillow`. Tarda unos 15 s.

## Comprobaciones tras cada cambio

- Pasan las pruebas.
- La web carga en Firefox, Chromium y WebKit, en móvil y escritorio, en tema
  claro y oscuro, sin desbordamiento horizontal (`probar-web`).
- axe-core no encuentra incidencias.
- Con una fuente caída, la web lo avisa y la recomendación sigue saliendo.
- Con datos de más de 3 horas, la web lo avisa.

## Fuentes y licencias

Previsión de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), observaciones
de [Meteocat](https://www.meteo.cat/observacions/xema), radar de
[RainViewer](https://www.rainviewer.com/) y avisos de AEMET a través de
[Meteoalarm](https://meteoalarm.org/). Iconos de [Lucide](https://lucide.dev/)
(ISC).

Código bajo AGPL-3.0-or-later ([LICENSE](LICENSE)); contenidos bajo CC BY-SA
4.0 ([LICENSE-CONTINGUTS.md](LICENSE-CONTINGUTS.md)). Hecho con IA:
[nivel 4 del MIAE](https://jjdeharo.github.io/miae/?nivel=4).
