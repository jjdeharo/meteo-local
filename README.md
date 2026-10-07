# meteo-local

Responde a una pregunta concreta: **¿lloverá en el trayecto en moto de
Cerdanyola del Vallès al Parc Taulí (Sabadell), a la ida (6:30-7:30) o a la
vuelta (15:00-15:30)?** Da **un solo medio para todo el día** (moto, moto con
impermeable o coche), porque quien va en moto vuelve en moto, y el riesgo de
lluvia de cada trayecto con sus motivos.

Web: <https://jjdeharo.github.io/meteo-local/> (en catalán, para quien hace
el trayecto). Al lado, [el tiempo en casa](https://jjdeharo.github.io/meteo-local/casa.html):
lo que miden ahora la estación de casa y la de Montflorit y la previsión hora
a hora para las 24 horas siguientes, actualizada cada media hora (ADR 0007).
La probabilidad de lluvia sale de una regresión logística ajustada con lo que
llovió de verdad y comprobada con todo el archivo (ADR 0021), y de ella sale
también el cielo de la tabla; la temperatura se corrige con un año de la estación de casa
(ADR 0017), y el NAS guarda cada hora lo previsto y lo medido para seguir
aprendiendo (ADR 0012; explicación en [docs/estadistica.md](docs/estadistica.md)).
Si lo que miden las estaciones o lo que prevé la página llega a los umbrales de
aviso de AEMET para el Vallès (lluvia, rachas, calor, frío o nieve), la página
lo marca como «Risc» y el NAS avisa a Juanjo por Telegram; los avisos de AEMET y
de Protección Civil por sí solos no lo hacen (ADR 0018). Las dos primeras horas
de la tabla y del trayecto tienen en cuenta hacia dónde va la lluvia del radar
(ADR 0019), y cuando ese radar dice que la lluvia llega a casa en unos 15
minutos, el NAS avisa a Juanjo por Telegram, una vez por episodio de lluvia
(ADR 0022).

La página de casa se publica además aparte, como web del tiempo del barrio:
[Temps a Montflorit](https://jjdeharo.github.io/meteo-montflorit/), sin la
página del trayecto, generada en cada publicación a partir de esta (ADR 0024),
en catalán y en [castellano](https://jjdeharo.github.io/meteo-montflorit/es/)
(ADR 0025).

## Cómo funciona

Un contenedor en el NAS de casa (`nas/`) ejecuta `publica.sh` cada cuarto de
hora (la página del trayecto, de 5:00 a 7:30 y de 13:00 a 15:30; la de casa,
todo el día; el horario está en `config.py` y la web lo muestra).
`publica.sh` calcula los datos con `prevision.py` y `casa.py` y los sube a
IONOS (`bilateria.org/app/meteo-local/`), de donde los lee la página. La web
entera va a la rama `gh-pages`, de la que sirve GitHub Pages, solo cuando
cambia el código, cada media hora como mucho o si IONOS falla: GitHub admite
unas 10 publicaciones por hora, y esa copia es la reserva si IONOS no
responde (ADR 0020). Al subir cambios a `main`, una acción de GitHub pasa las
pruebas, y el NAS, que mira cada minuto si hay código nuevo, publica. Solo
publica el NAS.

**Modo aviso:** con aviso de AEMET, plan de Protección Civil activado, lluvia
en las estaciones o en el radar a menos de 15 km, las dos páginas pasan a
actualizarse cada 6 minutos (:03, :09…), justo después de cada imagen nueva
del radar de Meteocat (ADR 0010). El horario lo decide `que_toca.py` con el
mismo dato que muestra la web. En `main` no hay commits automáticos.

A las 5:47 y a las 13:07, un agente con IA (Claude Sonnet 5.5) mira los datos y el
radar en imagen y escribe un comentario breve en catalán, que la página muestra
como «Valoració feta amb IA». Por la mañana puede hacer la recomendación más
prudente, nunca menos; el comentario caduca si el programa cambia los niveles
con que se escribió (`agent/`, ADR 0009).

**Riera de Sant Cugat.** En cada pasada de la página de casa se calcula la
lluvia de 3 horas en Sant Cugat (Meteocat) más la que el radar trae sobre la
cuenca en la hora siguiente. Con 35 mm llega un aviso de atención por
Telegram, y con 50, de peligro: la riera se desbordó en Montflorit con 53 mm
(29-04-2024) y con 67 (29-09-2026 y 04-10-2026). Cada episodio se apunta con
lo que midieron Sant Cugat, el Fabra (Collserola) y Montflorit, para ajustar
los umbrales (`riera.py`, ADR 0027).

Cada actualización queda apuntada en el NAS, y a las 16:00 se comprueba la
lluvia que cayó y si la recomendación acertó (`registre.py`). A los 28 días
llega un resumen por Telegram.

La página del trayecto solo informa dentro de sus franjas (5:00-7:30 y
13:00-15:30). Por la mañana recomienda un solo medio para el día y la ropa
(según el frío a 45 km/h, el calor y la lluvia; ADR 0013); por la tarde
solo da el tiempo de la vuelta (riesgo de lluvia, temperatura y viento). Fuera
de las franjas hace lo mismo para quien sale en ese momento: se elige la hora
de vuelta y dice el medio, la ropa y cómo cambiará el tiempo (ADR 0014).

Se puede instalar en el móvil como aplicación (manifiesto, iconos y service
worker que nunca guarda los datos; ADR 0015). Si Open-Meteo falla, la página de casa mantiene la
última previsión buena, de 6 horas como mucho, y lo avisa (ADR 0016). Las
dos páginas, si están abiertas, se ponen al día solas después de cada
actualización prevista (ADR 0011).

El riesgo de cada trayecto (bajo, moderado o alto) junta cinco fuentes y
manda la más desfavorable; el medio del día sale del trayecto con más riesgo:
alto, coche; moderado, moto con impermeable; bajo en los dos, moto. La
decisión se recalcula hasta el final de la ventana de ida (7:30) y desde
entonces se mantiene: cada ejecución lee los datos ya publicados (`--anterior`). Si
después empeora la vuelta, la web lo avisa sin cambiar el medio.

Fuentes, de la más a la menos decisiva:

1. **Avisos de AEMET** del Prelitoral de Barcelona (el Vallès): un aviso de
   lluvia o tormenta a la hora del trayecto, riesgo alto. **Planes de Protección
   Civil** de inundaciones, viento o nieve en alerta o emergencia: riesgo alto
   (ADR 0008).
2. **Radar** de Meteocat o, si su imagen va 10 minutos por detrás, de
   RainViewer; una comparación diaria decide cuál acierta más (ADR 0026). Hasta 2
   horas, la lluvia de ahora se lleva hacia delante con el movimiento de la
   advección de Meteocat, medido en la lluvia de cerca del trayecto (ADR 0019
   y 0023): probable (50 %) y de 1 mm/h, riesgo alto;
   posible (20 %), moderado. Entre 2 y 3 horas, la distancia: lluvia a menos
   de 15 km y creciendo, alto; a menos de 40 km, moderado.
3. **Estaciones**: Montflorit, de meteocerdanyola.com, minuto a minuto; la de
   casa (Ecowitt), solo cuando marca lluvia (ADR 0017), y las de Meteocat en Sabadell y Sant Cugat (página de meteo.cat o, si falla,
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
| `web/` | Las páginas: `index.html` y `app.js` (trayecto), `casa.html` y `casa.js` (casa), `comu.js` (lo común), `estil.css` y `fonts.html` (fuentes y créditos); `manifest.webmanifest`, `sw.js` e `icones/` para instalarla como aplicación |
| `calibracio/` | Descarga del histórico, análisis, `informe.md` y `calibracio.json` (los datos, en `dades/`, no se suben) |
| `tests/` | Pruebas de la regla, del horario, de la web y del aprendizaje, sin red |
| `casa.py` | Datos de la página de casa (`casa.json`) |
| `publica.sh` | Calcula y publica en la rama `gh-pages` (lo usa el NAS), y la web pública en su repositorio |
| `montflorit.py`, `montflorit/` | Genera la web pública «Temps a Montflorit» a partir de la página de casa, y sus datos sin el trayecto; manifiesto, iconos y README propios (ADR 0024), y `es.js`, los textos del programa en castellano (ADR 0025) |
| `i18n/` | `es.json`, la traducción de los textos fijos de la web pública, y `claus.js`, que saca del programa los textos por traducir (ADR 0025) |
| `nas/` | Contenedor del NAS: `compose.yml`, `Dockerfile` y `reloj.sh` |
| `agent/` | Agente diario: instrucciones, imagen del radar, ejecución y validación |
| `ecowitt.py` | La estación de casa con la API oficial de Ecowitt; las claves, fuera del repositorio (ADR 0017) |
| `pluviometre.py` | Comprueba una vez, tras limpiarlo, si el pluviómetro de casa marca la lluvia débil y avisa por Telegram (ADR 0017) |
| `nowcast.py` | La lluvia del radar (Meteocat o RainViewer) llevada hacia delante hasta 2 horas (ADR 0019 y 0023) |
| `riscos.py` | Situaciones de peligro de la página de casa y aviso por Telegram (ADR 0018) |
| `radar_fonts.py` | Apunta lo que daba cada radar en casa y, cada día, elige el que acierta más (ADR 0026) |
| `pluja_arriba.py` | Aviso por Telegram unos 15 minutos antes de que llueva en casa, según el radar, y registro de sus aciertos (ADR 0022) |
| `riera.py` | Lluvia en la cuenca de la riera de Sant Cugat y aviso por Telegram de atención o peligro de desbordamiento, con registro de episodios (ADR 0027) |
| `registre.py` | Registro en el NAS de cada actualización y del resultado de cada día (ADR 0006) |
| `aprenentatge.py` | Aprendizaje de la página de casa: regresiones, comprobación y cambio de método (ADR 0012, `docs/estadistica.md`) |
| `.github/workflows/previsio.yml` | Al subir a `main`: pruebas |
| `docs/adr/` | Registro de decisiones |

## Uso local

```sh
python3 prevision.py                        # resumen en la terminal
python3 prevision.py --json web/dades.json  # datos para ver la web en local
python3 -m unittest discover -s tests       # pruebas
```

Necesita Python 3 con `numpy` y `Pillow`. Tarda unos 15 s. La estación de
casa se lee si están las variables `ECOWITT_APPLICATION_KEY`,
`ECOWITT_API_KEY` y `ECOWITT_MAC` o el archivo
`~/.config/meteo-local/ecowitt.env`; sin ellas, todo funciona con Montflorit.
La corrección de la temperatura se rehace con `python3
calibracio/estacio_casa.py --descarrega`.

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
estación de casa con la [API de Ecowitt](https://doc.ecowitt.net/web/#/apiv3en?page_id=1),
radar y advección de [Meteocat](https://www.meteo.cat/observacions/radar) y,
de reserva, de [RainViewer](https://www.rainviewer.com/), y avisos de AEMET a través de
[Meteoalarm](https://meteoalarm.org/). Iconos de [Lucide](https://lucide.dev/)
(ISC).

Código bajo AGPL-3.0-or-later ([LICENSE](LICENSE)); contenidos bajo CC BY-SA
4.0 ([LICENSE-CONTINGUTS.md](LICENSE-CONTINGUTS.md)). Hecho con IA:
[nivel 4 del MIAE](https://jjdeharo.github.io/miae/?nivel=4).
