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

- **Bot `@TempsMontfloritBot`** («Temps a Montflorit»), creado con @BotFather
  desde la cuenta de Juanjo; su clave, en
  `~/.config/credenciales/temps-montflorit-bot.json` y en IONOS
  (`~/.temps-bot/config.json`, 600). **Canal `@TempsMontflorit`**, de Juanjo,
  con el bot como administrador para publicar.
- **El bot vive en IONOS** (`bot/bot.py`, solo biblioteca estándar): el cron lo
  arranca cada minuto y, durante unos 50 segundos, espera mensajes de Telegram
  (responde en uno o dos segundos) y reparte. Un candado evita dos a la vez.
  Se pone al día solo con `git pull` cada hora. Lo monta `bot/instalar.sh`.
- **Quien calcula decide los avisos públicos** (`avisos_bot.py`, en el NAS en
  cada publicación y en la reserva cuando la sustituye), con estado propio, y
  los deja en `avisos.json` junto a `montflorit.json`, en catalán y
  castellano, cada uno con un identificador: el bot no repite ninguno. Tipos:
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
- **Cada persona elige** en un menú con botones: los cuatro tipos (por
  defecto, riera y peligro), la previsión, un mensaje al día a las 6, 7 u
  8 h (el tiempo ahora y el resto del día) o a las 20 h (la de mañana: la
  noche solo si se espera lluvia, temperaturas, lluvia y avisos de AEMET de
  mañana; sin trenes), o «Sense previsió» (el menú lo explica), y el
  idioma (catalán o castellano, al principio el de su Telegram). Órdenes:
  /avisos, /resum, /ara y /baixa, que borra sus datos. Solo se guardan su
  identificador de Telegram y lo que elige; si bloquea el bot, se le da de
  baja. Solo en chats privados.
- **Canal**: los avisos de riera y peligro, y el resumen del día a las 7, en
  catalán y castellano en el mismo mensaje.
- **Recuento**: los lunes a las 9, una línea a Juanjo (con su bot de avisos)
  con los suscriptores del bot, qué eligen y los miembros del canal
  (`bot.py informe`). El canal tiene fijado un mensaje de presentación, solo en
  catalán (Juanjo, 07-10-2026).
- **En la web**: «Avisos a Telegram: bot · canal» bajo el menú, y en los
  créditos, qué guarda el bot.
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
pasadas), riera con el aviso orientativo y peligro en castellano.
