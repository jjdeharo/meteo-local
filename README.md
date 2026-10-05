# meteo-local

Responde a una pregunta concreta: **¿lloverá en el trayecto en moto de
Cerdanyola del Vallès al Parc Taulí (Sabadell), a la ida (6:30-7:30) o a la
vuelta (15:00-15:30)?** Da **un solo medio para todo el día** (moto, moto con
impermeable o coche), porque quien va en moto vuelve en moto, y el riesgo de
lluvia de cada trayecto con sus motivos.

Web: <https://jjdeharo.github.io/meteo-local/> (en catalán, para quien hace
el trayecto).

## Cómo funciona

Una acción de GitHub ejecuta `prevision.py` varias veces al día (cada media
hora de 5:00 a 7:00, también a las 6:15, y de 13:00 a 15:00, hora local), guarda el resultado en
`web/dades.json` y publica la carpeta `web/` en GitHub Pages. No se guarda
nada más ni se hacen commits automáticos.

El riesgo de cada trayecto (bajo, moderado o alto) junta cinco fuentes y
manda la más desfavorable; el medio del día sale del trayecto con más riesgo:
alto, coche; moderado, moto con impermeable; bajo en los dos, moto. La
decisión se recalcula hasta el final de la ventana de ida (7:30) y desde
entonces se mantiene: cada ejecución lee los datos ya publicados (`--anterior`). Si
después empeora la vuelta, la web lo avisa sin cambiar el medio.

Fuentes, de la más a la menos decisiva:

1. **Avisos de AEMET** del Prelitoral de Barcelona (el Vallès): un aviso de
   lluvia o tormenta a la hora del trayecto, riesgo alto.
2. **Radar** (RainViewer), solo para las 3 horas siguientes: lluvia a menos de
   15 km y creciendo, riesgo alto; a menos de 40 km, moderado.
3. **Estaciones**: Montflorit, de meteocerdanyola.com, minuto a minuto, y las
   de Meteocat en Sabadell y Sant Cugat (página de meteo.cat o, si falla,
   portal de datos abiertos de la Generalitat). Si llueve y falta menos de
   hora y media, riesgo alto.
4. **Modelos finos** (AROME HD, AROME e ICON-EU): 1 mm en una hora, alto;
   0,2 mm, moderado. Los globales (ECMWF, UKMO, GFS) se descargan pero no
   deciden: sus celdas de 10-25 km incluyen mar.
5. **Ensemble ICON-EU-EPS** (40 miembros): el 50 % o más con lluvia, alto; el
   20 %, moderado.

Umbrales y lugares, en `config.py`. El porqué, en los ADR.

**Calibración.** Los umbrales de los modelos se han comprobado con lo que
llovió de verdad entre 2024 y 2026 en Sabadell y Sant Cugat
(`calibracio/`). Cuando la regla dice moto, llovió el 1 % de los días; compte,
del 10 al 13 %; coche, del 37 al 52 %. Ajustar un modelo estadístico o añadir
el CAPE no la mejora de forma apreciable. La web muestra esas frecuencias junto
al motivo de los modelos. Para repetirla: `python3 calibracio/descarrega.py
--forzar` y `python3 calibracio/analitza.py`.

## Archivos

| Archivo | Para qué |
|---|---|
| `prevision.py` | Recoge los datos, decide y escribe `dades.json`; sin `--json`, imprime un resumen |
| `config.py` | Coordenadas, horario, estaciones, zonas de aviso, modelos y umbrales |
| `web/` | La página: `index.html`, `app.js`, `estil.css` y `fonts.html` (fuentes y créditos) |
| `calibracio/` | Descarga del histórico, análisis, `informe.md` y `calibracio.json` (los datos, en `dades/`, no se suben) |
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
- Tras la hora de salida, el medio no cambia aunque cambie la previsión.

## Fuentes y licencias

Previsión de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), observaciones
de [Meteocat](https://www.meteo.cat/observacions/xema) y del
[portal de datos abiertos de la Generalitat](https://analisi.transparenciacatalunya.cat/d/nzvn-apee), estación de Montflorit de
[meteocerdanyola.com](https://meteocerdanyola.com/2026/sites/cerdanyola_montflorit/index.html),
radar de [RainViewer](https://www.rainviewer.com/) y avisos de AEMET a través de
[Meteoalarm](https://meteoalarm.org/). Iconos de [Lucide](https://lucide.dev/)
(ISC).

Código bajo AGPL-3.0-or-later ([LICENSE](LICENSE)); contenidos bajo CC BY-SA
4.0 ([LICENSE-CONTINGUTS.md](LICENSE-CONTINGUTS.md)). Hecho con IA:
[nivel 4 del MIAE](https://jjdeharo.github.io/miae/?nivel=4).
