# 48. Avisos en el navegador, sin Telegram

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Los avisos (riera, peligro, lluvia en unos minutos, trenes y la previsión
diaria) solo llegaban por el bot y el canal de Telegram (ADR 0034). Juanjo
quería que cualquiera pudiera recibirlos sin Telegram y pensó en una
aplicación para Android. Al ver lo que costaría Google Play (la cuenta, quizá
una prueba con 12 personas durante 14 días y rehacer el paquete cada año) y
que la app sería la misma web con su icono, decidió empezar por las
notificaciones de la propia web y dejar Play para más adelante, según cuánta
gente consiga instalarla («entonces igual con eso ya me vale, no?»). Si se
hace, el envoltorio irá en `android/` de este repositorio.

## Decisión

- **Página «Avisos»** (`web/avisos.html`, `web/avisos.js`), en catalán y
  castellano: las mismas opciones que el bot (peligro, riera, lluvia a punto
  de empezar, trenes y la previsión a las 6, 7, 8 o 20 h), con las mismas
  casillas que «Si surts»; «Activa els avisos» pide permiso al navegador y se
  suscribe; los cambios se guardan solos, de uno en uno y con lo último
  marcado; «Envia'm una prova» y «Desactiva», que borra la suscripción.
- **Que no se confunda con Telegram** (Juanjo, 08-10-2026): el enlace de
  arriba de cada página, antes «Avisos a Telegram», pasa a «Avisos al mòbil»
  («Avisos en el móvil»), con la campana que suena; la página empieza por
  «Nou:», destacado con una franja y color, no con negrita. Telegram sigue en
  su página, enlazada al final.
- **Cómo instalarla**: en iPhone y iPad, Apple solo deja recibir avisos a la
  web añadida a la pantalla de inicio y abierta como aplicación; en Safari, la
  página lo explica en vez de las opciones. En Android funcionan desde el
  navegador, pero la página aconseja añadirla a la pantalla de inicio (solo en
  Android y si no está ya instalada): Chrome puede dejar de mostrar los avisos
  de las webs que hace tiempo que no se abren, y no los de las instaladas.
- **Servidor en IONOS**, junto al bot, porque tiene que funcionar cuando la
  tormenta deja la casa sin luz (ADR 0034):
  - `bot/subscripcio.php` (PHP 8.4), que carga `app/meteo-local/subscripcio.php`
    desde la copia del repositorio, así que se pone al día con el `git pull`
    del bot. Da la clave pública y guarda, cambia o borra cada suscripción en
    `.temps-bot/push.json`. Solo acepta direcciones de los servicios de
    notificaciones de los navegadores (Google, Mozilla, Apple, Microsoft),
    claves con forma válida, cuerpos de 4 KB y 20.000 suscripciones; solo
    responde a la web publicada y, para probarla, a `localhost`.
  - `bot/push.py`, cada minuto con el entorno de Python de la reserva
    (pywebpush, MPL-2.0): reparte `avisos.json` y la previsión con las
    funciones del bot (`a_repartir`, `resum`), con estado propio
    (`push-estat.json`), reintentos mientras el aviso es vigente y el mismo
    tiempo de vida que en Telegram; borra las suscripciones que el servicio da
    por muertas (404 o 410). La notificación lleva como título la línea en
    negrita del mensaje del bot y abre la web en el idioma de cada uno (los
    trenes, en «Si surts»).
  - Claves VAPID en `.temps-bot/vapid.json`, creadas una vez por
    `bot/instalar.sh`; la web pide la pública al servidor, no la lleva escrita.
- **A Juanjo**, como en el bot: cada alta nueva con el total, y los
  dispositivos en el recuento de los lunes.
- **Privacidad**: de cada dispositivo solo se guarda la dirección que da su
  navegador y lo que elige; la página y los créditos lo dicen, y que las
  notificaciones pasan por el servicio del navegador.

## Alternativas descartadas

- **App en Google Play ahora**: la misma web con icono, a cambio de la cuenta,
  la posible prueba de 14 días, los formularios y rehacer el paquete cada año.
  Se decidirá según el uso.
- **Enviar desde el NAS**: el corte de luz que llega con la tormenta lo
  pararía justo cuando hace falta (el mismo motivo que el bot, ADR 0034).
- **Enviar desde `bot.py`**: el bot solo usa la biblioteca estándar y el
  sistema de IONOS no tiene pywebpush; un fallo del envío tampoco debe parar
  Telegram. `push.py` aparte, con el entorno de la reserva.
- **Copiar el PHP a la carpeta web en cada cambio**: se quedaría atrás; el
  que hay allí solo carga el del repositorio.
- **Hacer copia de las claves VAPID**: las suscripciones tampoco se copian
  (son datos personales, como los suscriptores del bot), así que sin ellas
  las claves no sirven; si se pierden, cada uno vuelve a activar
  (RESTAURAR.md).

## Consecuencias

- `app/meteo-local/.htaccess` pone el permiso de lectura para la web con
  `setifempty`, para no pisar el de `subscripcio.php`.
- El enlace «Avisos a Telegram» de las dos páginas lleva ahora a «Avisos».
- Un cron más en IONOS; `bot/instalar.sh` instala pywebpush, las claves, el
  PHP y el cron.

## Evidencia

- IONOS, 08-10-2026: PHP 8.4.26 en la web, con el mismo usuario que la
  cuenta, escribe en una carpeta privada; pywebpush 2.5.0 en
  `.meteo-reserva/v`.
- Prueba completa con Google Chrome, en una pantalla virtual y un perfil
  temporal (08-10-2026): alta, cambios guardados, prueba pedida desde la
  página, `push.py` la envía y la notificación aparece (Juanjo la vio en su
  escritorio). Primero se descubrió que pywebpush no acepta el PEM como texto
  (se le pasa la clave cargada) y que dos guardados seguidos podían llegar
  desordenados (ahora van de uno en uno).
- Chrome sin ventana no mantiene la conexión con el servicio de Google y no
  recibe nada; Playwright abre Chromium en incógnito, donde Chrome no admite
  notificaciones; su Firefox no tiene servicio de notificaciones.
- El WebKit de Playwright para Linux se cuelga en
  `pushManager.getSubscription()`, también en una página mínima: no sirve para
  probar Safari. En WebKit, registrar el service worker dos veces a la vez
  bloqueaba la página; ahora lo registra solo `comu.js`.
- iOS: avisos solo en la web añadida a la pantalla de inicio, desde iOS 16.4
  ([Pushpad](https://pushpad.xyz/blog/ios-special-requirements-for-web-push-notifications));
  desde iOS 26 se añade como aplicación salvo que se desactive
  ([heise](https://heise.de/-10749652)). Chrome y su limpieza de permisos de
  webs no visitadas, según la prensa
  ([Tom's Guide](https://www.tomsguide.com/computing/browsers/google-finally-adds-a-way-to-tame-notifications-on-chrome-heres-how-it-works));
  no comprobado en la documentación de Google.

## Riesgos y limitaciones

- Safari (iPhone, iPad y Mac) y la recepción en Firefox no se han podido
  probar aquí: pendiente de probar en un iPhone tras publicar.
- En el ordenador, los avisos suelen llegar solo con el navegador abierto.
- Los servicios de notificaciones pueden retrasar o perder alguna; las de
  riera, peligro y lluvia van con urgencia alta.
- `push.json` crece con cada dispositivo; se limpia con las bajas y con las
  suscripciones muertas.

## Validación

`tests/test_push.py` (texto de la notificación y su página en cada idioma,
cada aviso a quien lo eligió y una vez, reintentos y caducidad, suscripciones
muertas, previsión a su hora, prueba y altas a Juanjo) y las de la web
(`tests/test_montflorit.py`: traducciones de la página y de sus textos).
Página probada con `probar-web` en Chromium y Firefox, escritorio, móvil y
tableta, claro y oscuro, en los dos idiomas; WebKit no (ver Evidencia).
