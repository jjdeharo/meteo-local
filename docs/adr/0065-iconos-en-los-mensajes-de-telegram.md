# 65. Iconos en los mensajes de Telegram, solo donde ayudan a leer

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

Tras dar color a los iconos de la web (ADR 0063), Juanjo preguntó si los
mensajes del bot y del canal de Telegram podían llevar «algún icono que le dé
algo de color, parecido a lo que hemos hecho en la web». A la primera
propuesta, que ponía un icono en cada línea (termómetro, ropa, trenes…),
respondió: «que sirvan para leer y entender mejor los mensajes, no poner por
poner», y aprobó la segunda.

Telegram no muestra SVG ni colores en el texto: solo emojis, que cada sistema
dibuja a su manera. No pueden ser los iconos de Lucide de la web, pero sí el
mismo criterio.

## Decisión

- **Un emoji solo donde dice algo que el texto no dice o deja ver de un
  vistazo lo que habría que leer línea a línea.** Nada de iconos de tema: cada
  línea ya empieza por su rótulo, y quien pide /pollen sabe lo que ha pedido.
  Siempre al principio de la línea o delante del elemento que califica, nunca
  dentro de la negrita.
- **El cielo de ahora**, en «Ara mateix» (resumen de hoy y /ara): el de la
  hora en curso, con la misma regla que la tabla de la web (`cel` de
  `web/casa.js`), pasada a Python en `bot/bot.py` (`icona_cel`); una prueba
  compara las dos con decenas de horas de día, de noche, con lluvia, nieve,
  tormenta y niebla. Si llueve, el paraguas ☔, como la web. Correspondencias:
  ☀️ despejado, 🌤️ poco nuboso, ⛅ medio nuboso de día (☁️ de noche), ☁️ muy
  nuboso o cubierto, 🌙 despejado o poco nuboso de noche (no hay emoji de luna
  con nube), 🌫️ niebla, 🌦️ lluvia posible de día, 🌧️ lluvia, 🌨️ nieve,
  ⛈️ tormenta o granizo.
- **La lluvia, solo cuando hay**: delante de «Pluja: possible de…» y de
  «Aquesta nit: pluja…», el icono de la hora con la lluvia peor del tramo.
  «Sense pluja prevista» va sin icono, para que la línea destaque solo cuando
  importa.
- **Los niveles, con una sola escala de círculos en todos los mensajes**:
  ⚪ nulo o sin datos, 🟢 bajo o normal, 🟡 medio, 🟠 alto, 🔴 máximo y 🟣 por
  encima (UV extremo, aire extremadamente desfavorable). Se aplica a:
  - los avisos (`avisos_bot.py`): peligro y AEMET por su nivel (amarillo,
    naranja, rojo), riera (atención 🟠, peligro 🔴), Protección Civil (alerta
    🟠, emergencia 🔴), y 🟢 cuando se acaban. Delante del título, para ver la
    gravedad antes de leerlo, también en la notificación del móvil y del
    navegador (`bot/push.py` toma la primera línea);
  - los avisos de AEMET del resumen y de /avisos_actius, el tiempo
    excepcional, los planes y el Pla Alfa (nivel 3 🟠, 4 🔴);
  - cada línea de tren: 🟢 circula, 🟡 dice que circula pero no se ha visto
    ningún tren, 🟠 con incidencias, 🔴 sin trenes o por carretera, ⚪ sin datos
    o fuera de horario;
  - el polen, con los colores de las barras de la web (nulo ⚪, bajo 🟢,
    medio 🟡, alto 🟠, máximo 🔴);
  - el índice UV (bajo 🟢, moderado 🟡, alto 🟠, muy alto 🔴, extremo 🟣);
  - la calidad del aire (buena y razonablemente buena 🟢, regular 🟡,
    desfavorable 🟠, muy desfavorable 🔴, extremadamente desfavorable 🟣).
    La web usa los colores de la escala europea; aquí manda la escala única.
- **Sin icono**: el aviso de lluvia en unos minutos y el de incendio, cuyo
  título ya lo dice todo y que no tienen nivel; las notas («no és oficial»),
  los enlaces y los títulos de las consultas.
- Los círculos están en `CERCLE` de `bot/bot.py` y de `avisos_bot.py` (el bot
  no importa el resto del programa); una prueba comprueba que coinciden.

## Consecuencias

- El canal y los suscriptores reciben los mismos cambios: los textos salen de
  las mismas funciones.
- Si cambia la regla del cielo de la web, hay que cambiar también
  `icona_cel`; la prueba de `tests/test_web.py` avisa.
- Cada sistema dibuja los emojis a su manera: el aspecto exacto no se puede
  fijar, pero el significado sí.
