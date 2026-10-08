# 34. Bot y canal de Telegram

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

Juanjo quiso que los vecinos pudieran recibir los avisos que eligieran
(riera, lluvia, lluvias fuertes, resumen del día), con un bot de Telegram, y
además un canal. La riera, «superimportante», debía entrar con un aviso de
que es orientativa. Al preguntar dónde vive el bot, propuso que el principal
fuera IONOS y no el NAS: el fallo más probable del NAS es un corte de luz o de
internet en casa, que suele llegar con las tormentas.

## Decisión

- **Bot `@TempsMontfloritBot`** («Bot Temps a Montflorit»), creado con @BotFather
  desde la cuenta de Juanjo; su clave, en
  `~/.config/credenciales/temps-montflorit-bot.json` y en IONOS
  (`~/.temps-bot/config.json`, 600). **Canal `@TempsMontflorit`** («Canal
  Temps a Montflorit»), de Juanjo, con el bot como administrador para publicar.
- **Que no se confundan**: nombres distintos (los dos se llamaban igual y
  Juanjo lo corrigió, 07-10-2026) e iconos distintos: el canal, el de la web
  (nube azul); el bot, la misma nube sobre verde con un robot pequeño de
  Lucide (`bot/icona/`; Juanjo pidió el robot). La descripción del bot dice
  que es personal y remite al canal para quien no quiera elegir.
- **El bot vive en IONOS** (`bot/bot.py`, solo biblioteca estándar): el cron lo
  arranca cada minuto y, durante unos 50 segundos, espera mensajes de Telegram
  (responde en uno o dos segundos) y reparte. Un candado evita dos a la vez.
  Se pone al día solo con `git pull` cada hora. Lo monta `bot/instalar.sh`.
- **Quien calcula decide los avisos públicos** (`avisos_bot.py`, en el NAS en
  cada publicación y en la reserva cuando la sustituye), con estado propio, y
  los deja en `avisos.json` junto a `montflorit.json`, en catalán y
  castellano, cada uno con un identificador: el bot no repite ninguno. Cada
  aviso empieza por lo que pasa en negrita («Atenció: possible desbordament de
  la riera de Sant Cugat») y lo explica sin dar nada por sabido (de dónde baja
  el agua, qué hacer), porque lo lee gente que no conoce la web (Juanjo,
  07-10-2026). El de peligro dice que lo calcula el programa y no es oficial.
  Tipos:
  - **riera**: atención y peligro (ADR 0027), siempre con «Avís en proves,
    orientatiu i no oficial: segueix les indicacions de Protecció Civil i de
    l'Ajuntament»; en el menú, «Desbordament de la riera de Sant Cugat (en
    proves)» (Juanjo, 07-10-2026);
  - **perill**: los umbrales de aviso de AEMET con lo medido o previsto
    (ADR 0018);
  - **pluja**: lluvia en Montflorit en unos 15 minutos según el radar
    (ADR 0022);
  - **trens**: una línea de Cerdanyola deja de circular o vuelve, si el cambio
    se repite en dos pasadas (ADR 0029).
  Un aviso que llega tarde no se manda (lluvia, a los 20 minutos; los demás, a
  las 3 horas).
- **Cada persona elige** en un menú con botones (al darse de alta, el menú
  empieza diciendo qué se le ha marcado ya: «Per començar, t'he activat els
  avisos de la riera i de perill»), con una sola marca: ✓ es
  «sí»; sin marca, «no» (Juanjo, 07-10-2026: con «·» para el no, «el check
  siempre es afirmación»). Los cuatro tipos (por
  defecto, riera y peligro), la previsión, un mensaje al día a las 6, 7 u
  8 h (el tiempo ahora y el resto del día) o a las 20 h (la de mañana: la
  noche solo si se espera lluvia, temperaturas, lluvia y avisos de AEMET de
  mañana; sin trenes), o «No vull rebre la previsió» (el menú lo explica), y el
  idioma (catalán o castellano, al principio el de su Telegram). Órdenes:
  /avisos, /resum, /ara y /baixa, que borra sus datos. Solo se guardan su
  identificador de Telegram y lo que elige; si bloquea el bot, se le da de
  baja. Solo en chats privados.
- **Canal**: los avisos de riera y peligro, y el resumen del día a las 7,
  solo en catalán (Juanjo, 08-10-2026). Hasta entonces iban en catalán y
  castellano en el mismo mensaje; Telegram no permite que cada lector de un
  canal vea una versión distinta, y dos canales por idioma eran más
  mantenimiento para un mensaje al día. Quien quiera el castellano lo tiene en
  el bot, que toma el idioma de su Telegram.
- **Ropa en la previsión** (Juanjo, 07-10-2026: que la indique «para todo el
  día», también en la de las 20 h para el día siguiente): la de ir a pie, con
  los tramos de «Si surts» (ADR 0029) y el viento previsto, entre las 7 y las
  21 h, al final del mensaje y separada del resto por una línea en blanco
  (Juanjo, 08-10-2026: con la ropa en medio, «la información está muy
  desordenada»). Si el momento más frío y el más caluroso piden prendas distintas, se
  dicen las dos por orden de hora («jaqueta a les 7 h (14 °C); màniga curta o
  màniga llarga fina a les 15 h (23 °C)»); si no, una sola. La tabla está
  repetida en `bot/bot.py`, porque el bot no usa el JavaScript de la web, y
  una prueba comprueba grado a grado que las dos dicen lo mismo. El cambio
  llega al bot con su `git pull` horario: las suscripciones están en
  `~/.temps-bot/subscriptors.json`, fuera del repositorio, y no se tocan.
- **Sin repetir el canal** (Juanjo, 07-10-2026): a quien sigue el canal, el
  bot no le manda lo que el canal ya le da (avisos de riera y peligro, y la
  previsión de las 7 si eligió esa hora), salvo que tenga el bot en
  castellano, porque el canal va en catalán; sí la lluvia, los trenes y la
  previsión a otra hora. El bot, administrador del canal, lo pregunta a
  Telegram (`getChatMember`) una vez por pasada y solo cuando hay algo que
  repartir. Si el canal no ha recibido el aviso o la pregunta falla, el bot lo
  manda igualmente: mejor repetido que perdido. El menú del bot lo dice, con
  el enlace al canal: «Si també ets al canal (@TempsMontflorit), no et repetiré
  el que ja t'arriba per allà…» (Juanjo pidió que el bot lo dijera claro; un
  aviso breve al marcar un botón no bastaba y se quitó). Antes, la página avisaba de que con los dos algunos
  avisos podían llegar repetidos; Juanjo prefirió evitarlo.
- **Nada se da por enviado hasta que Telegram lo acepta** (revisión del
  07-10-2026: antes, el aviso se apuntaba como repartido antes de enviarlo y
  un fallo pasajero lo perdía). Lo que falla (el canal o un chat) queda en
  `pendents` del estado y se reintenta cada minuto mientras el aviso esté
  vigente; si el canal falla, los suscriptores lo reciben igualmente por el
  bot y, cuando el canal lo acepte, quien está en él lo verá repetido. El
  resumen diario del canal y el de cada persona se reintentan dentro de su
  hora. Y si Renfe y FGC no dan datos, el resumen lo dice en vez de «sense
  incidències».
- **Altas**: cada alta nueva, una línea a Juanjo con el número total, sin
  nombres (Juanjo, 07-10-2026).
- **Altas en el canal**: cada persona que se apunta al canal, una línea a
  Juanjo con su nombre y el número total (Juanjo, 08-10-2026: «avísame por
  telegram cuando se apunte alguien nuevo»). Telegram solo cuenta las altas de
  un canal a sus administradores, y al bot si las pide (`chat_member` en
  `getUpdates`). El nombre no se guarda: va solo en el aviso, y Juanjo lo ve
  igualmente en la lista del canal. Las bajas no se avisan.
- **Recuento**: los lunes a las 9, una línea a Juanjo (con su bot de avisos)
  con los suscriptores del bot, qué eligen y los miembros del canal
  (`bot.py informe`). El canal tiene fijado un mensaje de presentación, solo en
  catalán (Juanjo, 07-10-2026).
- **En la web**: «Avisos a Telegram: com funciona» bajo el menú,
  y en los créditos, qué guarda el bot. «Com funciona» lleva a una página de
  ayuda breve (`web/telegram.html`, también en castellano). Dice que se puede
  usar solo el canal (en catalán), solo el bot o los dos, y que con los dos, y el bot en catalán, no repite
  lo que ya da el canal. Tiene un bloque
  para el canal (igual para todos, como un tablón; azul) y otro para el bot
  (personal; verde, como su icono y su botón). Cada bloque lleva su
  descripción, su botón, el nombre con que se busca en Telegram
  (@TempsMontflorit, @TempsMontfloritBot) y sus pasos con capturas reales,
  marcadas en rojo donde hay que tocar. En el ordenador, los pasos van en fila
  y los dos bloques comparten columnas; en el móvil, uno debajo de otro
  (Juanjo, 07-10-2026: «lo vertical puede estar bien para móvil, pero no para
  web»). Al pulsar una captura, en el ordenador se amplía sobre la propia
  página, tan grande como quepa, con una X arriba a la derecha y sin descarga, que en unas
  capturas de ayuda no tiene sentido (Juanjo, 07-10-2026) (visor de
  `web/comu.js`, sirve para cualquier enlace con la clase `amplia`); en el
  móvil se abre sola, donde se amplía con los dedos (Juanjo: la ventana nueva
  «quizás sea mejor para móvil… pero para web no»). Juanjo pidió que se entienda sin saber Telegram y que sea
  breve, porque «la gente no lee». Las capturas se hicieron con Telegram Web en
  un perfil de navegador temporal, con el bot parado y la suscripción de Juanjo
  guardada y restaurada después.
- Los avisos personales de Juanjo siguen como estaban.

## Alternativas descartadas

- **Bot en el NAS**: se para con un corte de luz en casa.
- **Solo canal**: no deja elegir ni preguntar.
- **Reutilizar los mensajes de los avisos de Juanjo**: están pensados para él
  («casa») y solo en catalán.

## Consecuencias

- IONOS ejecuta un proceso cada minuto que casi siempre espera (el límite es
  de CPU, 1800 s, no de tiempo).
- Datos personales mínimos en IONOS (`~/.temps-bot/subscriptors.json`).
- Si el NAS y la reserva callan, el bot sigue contestando, pero no hay avisos
  nuevos, y el resumen dice que los datos no se actualizan.

## Evidencia

- IONOS deja un proceso esperando 55 s (07-10-2026); límites: 1800 s de CPU,
  768 MB de memoria virtual, 42 procesos.
- Nombres libres comprobados con la API de Telegram antes de crearlos.

## Riesgos y limitaciones

- Los umbrales de la riera son una hipótesis con cuatro casos: de ahí el aviso
  de que es orientativo.
- Un cambio de NAS a reserva puede repetir un aviso (cada uno lleva su estado).

## Validación

`tests/test_bot.py`: alta con valores por defecto e idioma, botones, /start,
/baixa, grupos ignorados, resumen (y con datos viejos), reparto según lo que
elige cada uno, canal, una sola vez, aviso caducado, baja de quien bloquea,
resumen a la hora de cada uno y del canal; avisos públicos de trenes (dos
pasadas), riera con el aviso orientativo y peligro en castellano, con su
titular en negrita; ropa del día en la previsión (dos prendas por orden de hora,
viento, una sola prenda, fuera de 7 a 21 h) y tabla igual a la de la web
(`tests/test_web.py`); quien está en el canal no recibe repetido lo que el canal
da (y sí lo recibe si el canal falla), y el menú lo explica; un alta al canal
avisa a Juanjo con el nombre, y una baja, un cambio de papel o un alta en otro
chat, no. La página de ayuda pasa por las pruebas de la web pública
(traducción completa), `probar-web` y axe-core.
