# 54. Página «Consultes», y el sol, el aire y el polen en la web y en el bot

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

Juanjo preguntó cómo dar en la web lo mismo que el bot, para quien usa la
aplicación: «que el que use la app pueda acceder a la misma información que el
bot». Descartó un botón en la cabecera y una página con todo: quería una
tercera pestaña junto a «El temps» y «Si surts», aunque repita lo que ya está en
otras páginas, porque «es más fácil a veces ir a donde sabes que está», y que
funcione como el bot: «se elige lo que se quiere ver y entonces sale». Quitó
después «Ara», «Radar» y «Avisos actius», que ya se ven en «El temps», y pidió
añadir el polen, la calidad del aire y el sol, también en el bot.

## Decisión

- **Página «Consultes»** (`web/consultes.html` y `web/consultes.js`), con su
  pestaña en el menú de todas las páginas (icono «message-square-text» de
  Lucide); el nombre puede cambiar más adelante (Juanjo: «luego valoraremos si
  lo cambiamos»). Siete opciones, en el orden del bot: Avui, Demà, Sol, Aire,
  Pol·len, Trens y Trànsit. Se marca una y debajo sale solo su texto. Al
  entrar, la última vista en ese dispositivo o, la primera vez, «Avui»; cada
  opción tiene su dirección (`consultes.html#pollen`).
- **Los textos son los del bot**, hechos por sus mismas funciones en el NAS al
  publicar (`montflorit.py`, `consultes`): web y bot dicen siempre lo mismo,
  en catalán y en castellano. Llevan el HTML de Telegram (`<b>`, `<i>` y
  `<a>`); la página lo lee sin `innerHTML` y solo enlaza direcciones `https`.
  «Demà» llega hasta donde llega la previsión, 24 horas, como en el bot.
- **Polen** (`pollen.py`, `/pollen`): el nivel de la semana de cada tipo de
  polen y de espora en la estación de Bellaterra (campus de la UAB, a 3,1 km) y
  su tendencia, de la API del Punt d'Informació Aerobiològica
  (`aerobiologia.cat/api/v0/forecast/bellaterra/{ca,es}/xml`), guardada 3 horas.
  Se dicen los niveles de más a menos, los tipos en aumento aunque estén a
  cero y, si la semana ya ha pasado, que son los últimos publicados. Licencia
  CC BY-NC-SA 4.0, con el enlace a su página junto a los datos y en los
  créditos; se les avisó por correo el 09-10-2026, como piden.
- **Calidad del aire** (`aire.py`, `/aire`): el índice europeo de calidad del
  aire del modelo CAMS Europa de Copernicus, que sirve Open-Meteo, ahora y el
  peor momento de lo que queda de hoy, con los nombres del índice español
  (bona, raonablement bona, regular, desfavorable, molt desfavorable,
  extremadament desfavorable) y el contaminante que más pesa. El texto dice que
  es un modelo y no una medida, y enlaza la web de la Generalitat con las
  medidas de las estaciones.
- **Sol** (`casa.py`, `sol`, `/sol`): salida y puesta del sol, horas de luz e
  índice UV máximo de hoy, con el consejo de «Si surts» desde 3, y la salida y
  la puesta de mañana, de Open-Meteo.
- En el bot siguen `/ara`, `/radar` y `/avisos_actius`: en un chat no hay otra
  página donde verlos.

## Alternativas descartadas

- **Un botón en la cabecera** que desplegara las consultas, y **una página con
  todo a la vez**: Juanjo prefirió una pestaña y ver una sola cosa.
- **La calidad del aire medida por la Generalitat** (XVPCA, datos abiertos
  `tasf-thgu`), con estaciones en Barberà (3,5 km), Sant Cugat (3,9 km) y
  Montcada (4,4 km): el 09-10-2026 a las 11:40 sus datos llegaban hasta las 4
  h, con 7 u 8 horas de retraso, y no sirven para decir cómo está el aire ahora.
- **Polen en tiempo real** del equipo automático del campus (SwisensPoleno,
  ligado al proyecto AtPollenFluo, PID2020-117873RB-I00, que dirige el
  CIEMAT): publicó lecturas del ciprés en `aerobiologia.cat/tr` desde marzo de
  2023, «en desarrollo», pero esa dirección redirige a la portada (ya en julio
  de 2024) y el acceso está comentado en el código de la portada. Se les ha
  preguntado si volverán a publicarlas.

## Consecuencias

- `montflorit.json` pasa de unos 10,7 KB a unos 19 KB, con `consultes`, `sol`,
  `aire` y `pollen`.
- Tres consultas más por pasada a Open-Meteo (sol y aire) y, cada 3 horas, dos
  al Punt d'Informació Aerobiològica; la reserva de IONOS guarda también el
  polen (`POLLEN_DIR`).
- Los datos del polen no son CC BY-SA como el resto de contenidos: los créditos
  lo dicen.
- Hay que volver a registrar las órdenes en Telegram (`bot/instalar.sh`).

## Evidencia

- API del polen probada el 09-10-2026 (respuestas guardadas en `tests/dades`):
  semana del 5 al 11 de octubre, artemisa y compuestas en nivel medio,
  Alternaria y Cladosporium en máximo, cipreses a cero y en aumento. Su página
  `aerobiologia.cat/pia/ca/api` da la licencia y pide avisar por correo; la
  dirección (`aerobiologia.pia@uab.cat`) es la de `aerobiologia.cat/pia/ca/terms`.
- Open-Meteo, documentación de la API de calidad del aire: índice europeo por
  tramos de 0-20, 20-40, 40-60, 60-80, 80-100 y más de 100, del modelo CAMS
  Europa de 11 km; pide citar CAMS y Open-Meteo.

## Validación

`tests/test_consultes.py` (lectura de la API del polen, texto del polen y aviso
de semana pasada, categorías y texto del aire, texto del sol, que las consultas
de la web son las del bot, lectura del HTML de Telegram sin `innerHTML` y orden
de las opciones). `probar-web` de «Consultes» en Chromium y Firefox,
escritorio, móvil y tableta, claro y oscuro, en las dos lenguas; axe-core sin
fallos en «Consultes», «El temps» y «Fonts i crèdits».
