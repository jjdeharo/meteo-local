# 30. Retirada de la página del trayecto

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

La página «Moto o cotxe?» (<https://jjdeharo.github.io/meteo-local/>)
recomendaba cada día un medio para un trayecto fijo, con un agente con IA que
escribía una valoración (ADR 0009). Con «Si surts» (ADR 0029), que hace lo
mismo para cualquier salida y cualquier medio, Juanjo decidió que la página
del trayecto llevara a «Si surts» y la del tiempo en casa a Temps a
Montflorit, «por lo tanto ya no usará IA».

## Decisión

- **Redirecciones** (desde el 07-10-2026, en el repositorio
  `jjdeharo/jjdeharo.github.io`, ADR 0035; antes, `redireccions/` en la rama
  `gh-pages` de este repositorio): `index.html` (trayecto) y `sortir.html` llevan a
  <https://meteo-montflorit.github.io/sortir.html>; `casa.html` y cualquier
  otra dirección, a <https://meteo-montflorit.github.io/>; `fonts.html`, a sus
  créditos. Con `meta refresh`, `location.replace` y `link rel="canonical"`.
  Quitan el service worker antiguo y su magatzem, solo los de esta web, y
  `sw.js` se sustituye por uno que hace lo mismo y se da de baja.
- **El NAS ya no calcula el trayecto**: `publica.sh` solo calcula la página del
  tiempo (`casa.py`) y sube a IONOS `montflorit.json`; `que_toca.py` solo
  conoce su horario. Se retiran el registro de aciertos del trayecto, su
  resumen por Telegram y el agente diario con IA (`agent/`).
- **Se borran** la página del trayecto (`web/index.html`, `web/app.js`), el
  agente y las «salidas» que solo usaba esa página (`casa.py`, `sortides`).
- **IONOS** solo admite ya la lectura desde `meteo-montflorit.github.io`, y se
  borran `dades.json` y `casa.json`, que ya no lee nadie.
- **Siguen**: la página del tiempo, sus avisos por Telegram (peligro, lluvia
  inminente y riera) y el aprendizaje de la previsión.

## Alternativas descartadas

- **Mantener la página del trayecto** junto a «Si surts»: dos sitios que
  dicen lo mismo con reglas parecidas.
- **Borrar la dirección antigua** sin redirigir: ya estaba instalada en el
  móvil de quien la usaba.

## Consecuencias

- Hay que copiar `nas/reloj.sh` al NAS y reconstruir el contenedor.
- El contenedor sigue teniendo Claude Code y el token, que usan otros
  automatismos del NAS; meteo-local ya no los usa.
- **Pendiente**: `prevision.py` y `registre.py` conservan la lógica del
  trayecto (decisión, ropa, registro de aciertos) mezclada con la recogida de
  datos que usa la página del tiempo. Se retirará en un cambio aparte; mientras
  tanto, no se ejecuta.
- ADR 0001, 0003, 0006, 0009, 0011, 0013 y 0014 describen piezas retiradas;
  quedan como historia.

## Evidencia

Ensayo de `publica.sh` en local con `ESTAT_DIR` (07-10-2026): calcula
`casa.json`, lo deja en la carpeta de estado y genera `montflorit.json`.

## Riesgos y limitaciones

- Quien tenga la página antigua instalada como aplicación la abrirá y pasará a
  la nueva; para instalarla con la dirección nueva, tiene que volver a
  hacerlo.

## Validación

Pruebas (`tests/test_horario.py` con el horario único); redirecciones
comprobadas en el navegador tras publicar; registro del NAS sin pasadas del
trayecto ni del agente.
