# meteo-local

Calcula y publica **Temps a Montflorit** (<https://meteo-montflorit.github.io/>),
la web del tiempo del barrio de Montflorit (Cerdanyola del Vallès), en catalán
y en [castellano](https://meteo-montflorit.github.io/es/). Tiene dos páginas:

- **El temps**: lo que miden ahora una estación particular del barrio y la
  de Montflorit, un resumen de la mañana, la tarde y la noche (probabilidad
  de lluvia, temperaturas y fenómenos destacables; ADR 0041) y la previsión
  hora a hora para las 24 horas siguientes, con los avisos de AEMET y los
  planes de Protección Civil (ADR 0007 y 0024).
- **Si surts**: para quien sale a una hora y vuelve a otra, cómo irá cada
  medio (a pie, bici o patinete, moto, coche y transporte público), qué ropa
  ponerse, consejos (lluvia, sol, noche, calor), si circulan los trenes que
  paran en Cerdanyola (ADR 0029) y las incidencias de tráfico de cerca (ADR
  0052). Cada persona elige qué medios ve.

La probabilidad de lluvia sale de una regresión logística ajustada con lo que
llovió de verdad y comprobada con todo el archivo (ADR 0021); la temperatura se
corrige con un año de la estación particular (ADR 0017), y el NAS guarda cada
hora lo previsto y lo medido para seguir aprendiendo (ADR 0012; explicación en
[docs/estadistica.md](docs/estadistica.md)). Las dos primeras horas tienen en
cuenta hacia dónde va la lluvia del radar (ADR 0019).

Los vecinos pueden recibir los avisos como notificaciones del móvil o del
ordenador, sin Telegram, desde la página «Avisos» de la web («Avisos al mòbil»;
ADR 0048): riera de Sant Cugat, peligro, lluvia en unos minutos, trenes y la
previsión del día, lo que elija cada uno. También por Telegram: el «Bot Temps a Montflorit»
([@TempsMontfloritBot](https://t.me/TempsMontfloritBot)), donde cada uno elige
riera de Sant Cugat, peligro, lluvia en unos minutos, trenes y la previsión
del día, y el «Canal Temps a Montflorit»
([@TempsMontflorit](https://t.me/TempsMontflorit)), igual para todos, con la
riera, el peligro y la previsión de las 7. La web tiene una página de ayuda
con capturas, «Avisos a Telegram». El bot y el envío de las notificaciones
viven en IONOS (ADR 0034 y 0048).

Los avisos de peligro (umbrales de AEMET con lo medido o lo previsto, ADR
0018), de lluvia en unos 15 minutos (ADR 0022) y de la riera de Sant Cugat (ADR
0027) los recibe todo el mundo igual, por las notificaciones, el bot o el canal.
Hasta el 08-10-2026 el NAS los mandaba además a Juanjo por Telegram; ahora solo
le escribe para lo que es de mantenimiento.

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
   particular (Ecowitt), cuya lluvia solo cuenta cuando marca (ADR 0017) y cuya
   presión se reduce al nivel del mar (ADR 0037), y las de Meteocat en Sabadell
   y Sant Cugat. El viento de ahora es el de Sant Cugat, por medias horas: el
   anemómetro de Montflorit marca casi siempre 0 (ADR 0037).
2. **Radar** de Meteocat o, si su imagen va 10 minutos por detrás, de
   RainViewer; una comparación diaria decide cuál acierta más (ADR 0026).
3. **Modelos** de Open-Meteo (AROME HD, AROME e ICON-EU, y el ensemble
   ICON-EU-EPS), con el índice UV del modelo por defecto.
4. **Avisos de AEMET** del Prelitoral de Barcelona y **planes de Protección
   Civil** (ADR 0008).
5. **Trenes**: avisos y posición en tiempo real de Renfe (R4, R7 y R8) y de FGC
   (S2), para «Si surts» (`trens.py`, ADR 0029), con el horario de cada línea
   en Cerdanyola sacado de sus GTFS (ADR 0038).
6. **Tráfico**: las incidencias del Servei Català de Trànsit a 6 km o menos
   (retenciones, accidentes, averías y obras que desvían o cortan la vía), de
   los datos abiertos de la Generalitat (`transit.py`, ADR 0052).

Umbrales y lugares, en `config.py`. El porqué, en los ADR.

## Archivos

| Archivo | Para qué |
|---|---|
| `casa.py` | Datos de la web (`casa.json`): lo de ahora, la previsión hora a hora, el índice UV, los trenes, el tráfico y la riera |
| `prevision.py` | Recogida de datos que usa `casa.py`: avisos de AEMET, planes de Protección Civil, radar, lluvia y viento de las estaciones, y el modo aviso |
| `config.py` | Coordenadas, horario, estaciones, zonas de aviso, modelos y umbrales |
| `web/` | Las fuentes de la web pública: `casa.html` y `casa.js` (el tiempo ahora), `sortir.html` y `sortir.js` («Si surts»), `avisos.html` y `avisos.js` (avisos en el navegador), `telegram.html` (ayuda de Telegram), `comu.js` (lo común), `estil.css`, `fonts.html` (fuentes y créditos), `manifest.webmanifest`, `sw.js` e `icones/` |
| `montflorit.py`, `montflorit/` | Genera la web pública a partir de `web/` y sus datos sin lo privado; manifiesto, iconos y README propios (ADR 0024), y `es.js`, los textos del programa en castellano (ADR 0025) |
| `i18n/` | `es.json`, la traducción de los textos fijos, y `claus.js`, que saca del programa los textos por traducir (ADR 0025) |
| `publica.sh` | Calcula y publica (lo usa el NAS) |
| `entorn.py` | Incendios forestales en curso cerca (Bombers) y nivel del Pla Alfa de Cerdanyola (Agents Rurals), para la web y los avisos de peligro (ADR 0046) |
| `desplegament.py` | Pone al día la copia del repositorio (NAS, reserva y bot) hasta el último commit con las pruebas de GitHub en verde; si GitHub no responde o las pruebas llevan más de 20 minutos sin acabar, despliega igualmente y lo apunta (ADR 0038) |
| `avis_privat.py` | Avisos de mantenimiento a Juanjo por Telegram con cola de reintento si Telegram no los acepta (ADR 0038) |
| `avisos_bot.py` | Decide los avisos públicos para el bot y el canal y los deja en `avisos.json` (ADR 0034) |
| `bot/` | Lo que vive en IONOS para repartir avisos: el bot de Telegram, `bot.py` (menú, suscripciones, reparto y resumen, ADR 0034); los avisos en el navegador, `push.py` (envío) y `subscripcio.php` (altas y bajas, ADR 0048); e `instalar.sh` |
| `reserva/` | Servidor de reserva en IONOS: `reserva.py` (vigila, calcula y avisa si el NAS no publica), `avisar-juanjo`, `rep-dades.sh` (recibe los datos que sube el NAS: la orden fija de su clave, ADR 0038) e `instalar.sh` (ADR 0032) |
| `que_toca.py` | Si toca actualizar en este minuto, según el horario publicado |
| `nas/` | Contenedor del NAS: `compose.yml`, `Dockerfile` y `reloj.sh`; `copia-registre.sh`, la copia diaria del registro en el repositorio privado `meteo-local-registre`, (ADR 0044) |
| `RESTAURAR.md` | Cómo volver a montarlo todo en otro NAS o en otro hosting, con las claves y el registro de la copia privada (ADR 0044 y 0045) |
| `trens.py` | Estado de las líneas de tren de Cerdanyola con los datos en tiempo real de Renfe y FGC (ADR 0029) |
| `transit.py` | Incidencias de tráfico de cerca, del Servei Català de Trànsit (ADR 0052) |
| `nowcast.py` | La lluvia del radar llevada hacia delante hasta 2 horas (ADR 0019 y 0023) |
| `ecowitt.py` | La estación particular con la API oficial de Ecowitt; las claves, fuera del repositorio (ADR 0017) |
| `pluviometre.py` | Comprueba una vez, tras limpiarlo, si el pluviómetro marca la lluvia débil y avisa por Telegram (ADR 0017) |
| `riscos.py` | Situaciones de peligro según lo medido y lo previsto, que usan la página y los avisos (ADR 0018) |
| `fi_pluja.py` | Comprueba a qué hora para la lluvia según el radar, antes de enseñarlo (ADR 0049) |
| `pluja_arriba.py` | Cuándo llegará la lluvia que ve el radar (la usa el aviso público de lluvia) y registro de sus aciertos (ADR 0022) |
| `riera.py` | Lluvia en la cuenca de la riera de Sant Cugat y aviso de atención o peligro de desbordamiento, con registro de episodios (ADR 0027) |
| `radar_fonts.py` | Apunta lo que daba cada radar y, cada día, elige el que acierta más (ADR 0026) |
| `registre.py` | Registro en el NAS de lo medido en Montflorit y en la estación particular, y de lo que daban los modelos, para aprender (ADR 0006 y 0012) |
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
python3 transit.py                             # las incidencias de tráfico de cerca
python3 riera.py ara                           # el índice de la riera
python3 calibracio/regla_moto.py               # la regla de lluvia de la moto, con el archivo
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
  renovarse, el vigía de IONOS avisa a Juanjo (desde que existe la reserva,
  ADR 0032, eso solo pasa si fallan el NAS y la reserva: una caída del NAS
  sola la avisa la propia reserva a los 35 minutos).

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
[dades obertes d'FGC](https://dadesobertes.fgc.cat/) (las dos, CC BY 4.0), e
incidencias de tráfico del
[Servei Català de Trànsit](https://transit.gencat.cat/es/informacio-viaria/estat-transit/)
(Generalitat de Catalunya, Departament d'Interior i Seguretat Pública), de los
[datos abiertos de la Generalitat](https://analisi.transparenciacatalunya.cat/d/uyam-bs37),
con la [licencia abierta de uso de información de Cataluña](https://web.gencat.cat/es/generalitat/dades-indicadors/dades-obertes/llicencies).
Iconos de [Lucide](https://lucide.dev/) (ISC). Los datos de terceros se
consultan automáticamente: el autor no se hace responsable de su exactitud.

Código bajo AGPL-3.0-or-later ([LICENSE](LICENSE)); contenidos bajo CC BY-SA
4.0 ([LICENSE-CONTINGUTS.md](LICENSE-CONTINGUTS.md)). Hecho con IA:
[nivel 4 del MIAE](https://jjdeharo.github.io/miae/?nivel=4).
