# meteo-local

Calcula y publica **Temps a Montflorit** (<https://meteo-montflorit.github.io/>),
la web del tiempo del barrio de Montflorit (Cerdanyola del Vallès), en catalán
y en [castellano](https://meteo-montflorit.github.io/es/). Tiene dos páginas:

- **El temps ara**: lo que miden ahora una estación particular del barrio y la
  de Montflorit, y la previsión hora a hora para las 24 horas siguientes, con
  los avisos de AEMET y los planes de Protección Civil (ADR 0007 y 0024).
- **Si surts**: para quien sale a una hora y vuelve a otra, cómo irá cada
  medio (a pie, bici o patinete, moto, coche y transporte público), qué ropa
  ponerse, consejos (lluvia, sol, noche, calor) y si circulan los trenes que
  paran en Cerdanyola (ADR 0029). Cada persona elige qué medios ve.

La probabilidad de lluvia sale de una regresión logística ajustada con lo que
llovió de verdad y comprobada con todo el archivo (ADR 0021); la temperatura se
corrige con un año de la estación particular (ADR 0017), y el NAS guarda cada
hora lo previsto y lo medido para seguir aprendiendo (ADR 0012; explicación en
[docs/estadistica.md](docs/estadistica.md)). Las dos primeras horas tienen en
cuenta hacia dónde va la lluvia del radar (ADR 0019).

Los vecinos pueden recibir avisos por Telegram: el «Bot Temps a Montflorit»
([@TempsMontfloritBot](https://t.me/TempsMontfloritBot)), donde cada uno elige
riera de Sant Cugat, peligro, lluvia en unos minutos, trenes y la previsión
del día, y el «Canal Temps a Montflorit»
([@TempsMontflorit](https://t.me/TempsMontflorit)), igual para todos, con la
riera, el peligro y la previsión de las 7. La web tiene una página de ayuda
con capturas, «Avisos a Telegram». El bot vive en IONOS (ADR 0034).

Además, solo para Juanjo, el NAS avisa por Telegram si lo medido o lo previsto
llega a los umbrales de aviso de AEMET (ADR 0018), unos 15 minutos antes de que
llueva en casa (ADR 0022) y si la lluvia en la cuenca de la riera de Sant Cugat
llega al umbral de atención o de peligro de desbordamiento (ADR 0027).

Hasta el 07-10-2026 el repositorio publicaba también la página «Moto o cotxe?»,
que recomendaba un medio para un trayecto fijo, con un agente diario con IA.
Se retiró: su dirección (<https://jjdeharo.github.io/meteo-local/>) lleva a «Si
surts», que hace lo mismo para cualquier salida, y la de «Temps a casa», a
Temps a Montflorit (ADR 0030).

## Cómo funciona

Un contenedor en el NAS de casa (`nas/`) ejecuta `publica.sh` cada cuarto de
hora, todo el día; en modo aviso (aviso de AEMET, plan de Protección Civil
activado o lluvia en las estaciones o en el radar a menos de 15 km), cada 6
minutos, justo después de cada imagen nueva del radar de Meteocat (ADR 0010 y
0020). El horario lo decide `que_toca.py` con el mismo dato que muestra la web.

`publica.sh` calcula los datos con `casa.py`, deja una copia en el NAS para los
avisos y sube los públicos (`montflorit.json`) a IONOS
(`bilateria.org/app/meteo-local/`), de donde los lee la página. La web, que
genera `montflorit.py` a partir de `web/`, va a su repositorio
(`meteo-montflorit/meteo-montflorit.github.io`, ADR 0028) solo cuando cambia
el código, cada media hora como mucho o si IONOS falla: GitHub admite unas 10
publicaciones por hora, y esa copia es la reserva si IONOS no responde. Las
direcciones antiguas (`jjdeharo.github.io/meteo-local/…`) las redirige el
repositorio aparte `jjdeharo/jjdeharo.github.io` (ADR 0035).

**Reserva en IONOS** (`reserva/`, ADR 0032): si el NAS lleva más de 35
minutos sin subir datos, el hosting de IONOS los calcula con el mismo programa,
los publica marcados como «reserva» y manda los avisos por Telegram en su
lugar; cuando el NAS vuelve, se aparta. Lo monta `reserva/instalar.sh`, y una
prueba diaria avisa si deja de funcionar.

Al subir cambios a `main`, una acción de GitHub pasa las pruebas, y el NAS, que
mira cada minuto si hay código nuevo, publica. Solo publica el NAS.

A las 16:00 el NAS rellena las horas que falten de la estación particular y la
previsión aprende de sus aciertos (`aprenentatge.py`). En `main` no hay commits
automáticos.

Fuentes de la previsión:

1. **Estaciones**: Montflorit (meteocerdanyola.com), minuto a minuto; la
   particular (Ecowitt), cuya lluvia solo cuenta cuando marca (ADR 0017), y las
   de Meteocat en Sabadell y Sant Cugat.
2. **Radar** de Meteocat o, si su imagen va 10 minutos por detrás, de
   RainViewer; una comparación diaria decide cuál acierta más (ADR 0026).
3. **Modelos** de Open-Meteo (AROME HD, AROME e ICON-EU, y el ensemble
   ICON-EU-EPS), con el índice UV del modelo por defecto.
4. **Avisos de AEMET** del Prelitoral de Barcelona y **planes de Protección
   Civil** (ADR 0008).
5. **Trenes**: avisos y posición en tiempo real de Renfe (R4, R7 y R8) y de FGC
   (S2), para «Si surts» (`trens.py`, ADR 0029).

Umbrales y lugares, en `config.py`. El porqué, en los ADR.

## Archivos

| Archivo | Para qué |
|---|---|
| `casa.py` | Datos de la web (`casa.json`): lo de ahora, la previsión hora a hora, el índice UV, los trenes y la riera |
| `prevision.py` | Recogida de datos que usa `casa.py` (avisos, planes, radar, estaciones); conserva aún la lógica de la página retirada del trayecto (ADR 0030) |
| `config.py` | Coordenadas, horario, estaciones, zonas de aviso, modelos y umbrales |
| `web/` | Las fuentes de la web pública: `casa.html` y `casa.js` (el tiempo ahora), `sortir.html` y `sortir.js` («Si surts»), `comu.js` (lo común), `estil.css`, `fonts.html` (fuentes y créditos), `manifest.webmanifest`, `sw.js` e `icones/` |
| `montflorit.py`, `montflorit/` | Genera la web pública a partir de `web/` y sus datos sin lo privado; manifiesto, iconos y README propios (ADR 0024), y `es.js`, los textos del programa en castellano (ADR 0025) |
| `i18n/` | `es.json`, la traducción de los textos fijos, y `claus.js`, que saca del programa los textos por traducir (ADR 0025) |
| `publica.sh` | Calcula y publica (lo usa el NAS) |
| `avisos_bot.py` | Decide los avisos públicos para el bot y el canal y los deja en `avisos.json` (ADR 0034) |
| `bot/` | El bot de Telegram, que vive en IONOS: `bot.py` (menú, suscripciones, reparto y resumen) e `instalar.sh` (ADR 0034) |
| `reserva/` | Servidor de reserva en IONOS: `reserva.py` (vigila, calcula y avisa si el NAS no publica), `avisar-juanjo` e `instalar.sh` (ADR 0032) |
| `que_toca.py` | Si toca actualizar en este minuto, según el horario publicado |
| `nas/` | Contenedor del NAS: `compose.yml`, `Dockerfile` y `reloj.sh` |
| `trens.py` | Estado de las líneas de tren de Cerdanyola con los datos en tiempo real de Renfe y FGC (ADR 0029) |
| `nowcast.py` | La lluvia del radar llevada hacia delante hasta 2 horas (ADR 0019 y 0023) |
| `ecowitt.py` | La estación particular con la API oficial de Ecowitt; las claves, fuera del repositorio (ADR 0017) |
| `pluviometre.py` | Comprueba una vez, tras limpiarlo, si el pluviómetro marca la lluvia débil y avisa por Telegram (ADR 0017) |
| `riscos.py` | Situaciones de peligro y aviso por Telegram (ADR 0018) |
| `pluja_arriba.py` | Aviso por Telegram unos 15 minutos antes de que llueva en casa, con registro de aciertos (ADR 0022) |
| `riera.py` | Lluvia en la cuenca de la riera de Sant Cugat y aviso de atención o peligro de desbordamiento, con registro de episodios (ADR 0027) |
| `radar_fonts.py` | Apunta lo que daba cada radar y, cada día, elige el que acierta más (ADR 0026) |
| `registre.py` | Registro en el NAS de lo medido en Montflorit y en la estación particular (ADR 0006) |
| `aprenentatge.py` | Aprendizaje de la previsión: regresiones, comprobación y cambio de método (ADR 0012, `docs/estadistica.md`) |
| `calibracio/` | Descarga del histórico, análisis y calibración (los datos, en `dades/`, no se suben) |
| `tests/` | Pruebas sin red |
| `.github/workflows/previsio.yml` | Al subir a `main`: pruebas |
| `docs/adr/` | Registro de decisiones |

## Uso local

```sh
python3 casa.py --json /tmp/casa.json          # los datos, con red
python3 montflorit.py web /tmp/web             # la web pública
python3 montflorit.py dades /tmp/casa.json /tmp/web/montflorit.json
python3 trens.py                               # el estado de los trenes
python3 riera.py ara                           # el índice de la riera
python3 -m unittest discover -s tests          # pruebas
```

Necesita Python 3 con `numpy` y `Pillow`, y Node para las pruebas de la web.
La estación particular se lee si están las variables `ECOWITT_APPLICATION_KEY`,
`ECOWITT_API_KEY` y `ECOWITT_MAC` o el archivo
`~/.config/meteo-local/ecowitt.env`; sin ellas, todo funciona con Montflorit.
Para ver la web en local, sírvela con un servidor (desde `localhost` no puede
leer los datos de IONOS y usa la copia de su carpeta).

## Comprobaciones tras cada cambio

- Pasan las pruebas.
- La web carga en Firefox, Chromium y WebKit, en móvil y escritorio, en tema
  claro y oscuro, sin desbordamiento horizontal (`probar-web`).
- Si cambia el HTML, el CSS o el JavaScript que crea o modifica elementos de
  la página, axe-core no encuentra incidencias.
- Con una fuente caída, la web lo avisa y sigue mostrando lo demás.
- Con datos de más de 2 horas, la web solo muestra el aviso y enlaces
  oficiales (ADR 0031); si los datos de IONOS llevan más de una hora sin
  renovarse, el vigía de IONOS avisa a Juanjo.

## Fuentes y licencias

Previsión de [Open-Meteo](https://open-meteo.com/) (CC BY 4.0), observaciones
de [Meteocat](https://www.meteo.cat/observacions/xema) y del
[portal de datos abiertos de la Generalitat](https://analisi.transparenciacatalunya.cat/d/nzvn-apee),
estación de Montflorit de
[meteocerdanyola.com](https://meteocerdanyola.com/2026/sites/cerdanyola_montflorit/index.html),
estación particular con la [API de Ecowitt](https://doc.ecowitt.net/web/#/apiv3en?page_id=1),
radar y advección de [Meteocat](https://www.meteo.cat/observacions/radar) y,
de reserva, de [RainViewer](https://www.rainviewer.com/), avisos de AEMET a
través de [Meteoalarm](https://meteoalarm.org/), y trenes de
[Renfe](https://data.renfe.com/) y de las
[dades obertes d'FGC](https://dadesobertes.fgc.cat/) (las dos, CC BY 4.0).
Iconos de [Lucide](https://lucide.dev/) (ISC). Los datos de terceros se
consultan automáticamente: el autor no se hace responsable de su exactitud.

Código bajo AGPL-3.0-or-later ([LICENSE](LICENSE)); contenidos bajo CC BY-SA
4.0 ([LICENSE-CONTINGUTS.md](LICENSE-CONTINGUTS.md)). Hecho con IA:
[nivel 4 del MIAE](https://jjdeharo.github.io/miae/?nivel=4).
