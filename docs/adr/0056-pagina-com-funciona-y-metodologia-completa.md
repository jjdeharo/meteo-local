# 56. Página «Com funciona» y metodología completa

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

Juanjo pidió una página de ayuda que explicara por qué nació la aplicación y
qué hace, y que destacara lo que la distingue: que todo aprende con el tiempo
(aprendizaje automático) y la gran cantidad de fuentes que usa. Debía abrirse
con un icono en la botonera de la cabecera, junto al idioma, y enlazar, para
profundizar, la metodología matemática, que había que revisar para ver si
estaba completa (09-10-2026).

## Decisión

- **Página `com-funciona.html`** («Com funciona» / «Cómo funciona»), en las
  dos lenguas, generada como las demás por `montflorit.py`
  (`CANVIS_COM_FUNCIONA`, traducción en `i18n/es.json`). Apartados: por qué
  nació, qué ofrece, una previsión que aprende, las fuentes que usa, lo que
  hay que tener en cuenta y para profundizar.
- **Lo personal no sale.** El proyecto nació para decidir un trayecto
  familiar en moto (ADR 0001), pero la web pública no habla de él (ADR
  0024): la página dice «un desplazamiento corto, a primera hora y a
  mediodía». Pasa la misma comprobación de palabras prohibidas que las
  demás páginas (`PROHIBIDES`).
- **Las cifras son las ya publicadas** en «D'on surt» o en los ADR: la
  probabilidad comprobada (15 % → 15 %, 40 % → 38 %), el error de la
  temperatura (1,5 → 1,0 °C), la lluvia con menos del 5 %, el 05-10-2026
  (AROME con 0,0 mm y más de 20 mm por hora en Montflorit, ADR 0007).
- **Los desbordamientos de la riera** del 29-09-2026 y del 04-10-2026, con el
  agua dentro de las casas, se citan como lo que hizo ver la utilidad de la
  web para el barrio (Juanjo, 09-10-2026), enlazados a las notas del
  Ayuntamiento de Cerdanyola que ya cita el ADR 0027.
- **Aprendizaje automático, sin IA generativa.** La página y la metodología
  dicen que son métodos estadísticos clásicos (regresiones) ajustados con lo
  que pasó, y que no interviene ningún modelo de lenguaje.
- **Icono «?» (`circle-help` de Lucide)** en la botonera de todas las
  páginas, entre el idioma y la campana.
- **`docs/estadistica.md` completado** tras una auditoría frente al código:
  introducción e índice para quien llega desde la web, y los métodos que
  faltaban (radar llevado hacia delante, final de la lluvia, aviso de antes
  de llover, riesgos, riera, «els models no encerten», «Si surts», calidad
  del aire), el horizonte de 24 a 38 horas y la operación interna aparte, al
  final. Fórmulas en LaTeX, que GitHub muestra. Está en castellano; la página
  lo dice al enlazarlo.

## Alternativas descartadas

- **La metodología como página de la web, con las fórmulas en KaTeX**: una
  biblioteca más que cargar para pocos lectores; GitHub ya muestra las
  fórmulas.
- **Contar el origen tal como fue** (el trayecto en moto): es de uso familiar
  y la web pública no lo nombra.

## Consecuencias

- Dos limitaciones de método que encontró la auditoría quedan escritas en
  la metodología, sin cambiar el código: la regla del final de la lluvia se
  elige y se mide con los mismos episodios y se cambia el mismo día, y la
  corrección del aire no se ha comprobado fuera de los datos con que se
  calcula.
- Una fuente o un método nuevos se añaden también a la página y a la
  metodología.

## Validación

`montflorit.py web` genera las dos páginas sin palabras prohibidas ni
bloques sin traducir; `probar-web` en Chromium, Firefox y WebKit, escritorio,
móvil y tableta, claro y oscuro, en las dos lenguas, y en el resto de
páginas con el icono nuevo (en «Avisos», sin WebKit, que se cuelga con las
notificaciones en Linux); axe-core sin incidencias; botonera completa a
320 px. En la metodología, las 117 fórmulas compilan con KaTeX en modo
estricto y los 18 enlaces del índice coinciden con las anclas de GitHub.
