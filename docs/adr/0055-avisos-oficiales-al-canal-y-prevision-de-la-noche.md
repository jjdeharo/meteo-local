# 55. Avisos oficiales nuevos al canal, y la previsión de la noche aparte

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

Juanjo preguntó qué manda el canal. Un día normal, solo la previsión de las 7
h; en un temporal, los avisos de peligro que calcula la propia web, los
incendios cercanos y la riera, pero no los avisos oficiales de AEMET ni los
planes de Protección Civil (ADR 0018: entonces «solo quiere el aviso cuando la
previsión propia ve el peligro»). Pidió añadir los avisos oficiales nuevos al
canal y la previsión de mañana a las 21 h, y que en el bot se pueda elegir una
hora por la mañana y, si se quiere, también la de la noche.

## Decisión

- **Avisos oficiales nuevos** (`avisos_bot.py`), con los de peligro: llegan al
  canal, a quien tiene «Situacions de perill» en el bot y a los avisos del
  navegador.
  - **AEMET** (Prelitoral de Barcelona, lluvia y tormentas, del feed de
    Meteoalarm): al aparecer o subir de nivel, con el nivel, la franja («Des
    d'avui a les 15 h fins a mitjanit») y su texto en castellano, como lo
    publica AEMET (ADR 0033).
  - **Protección Civil**: un plan al pasar a alerta o a emergencia (con lo que
    significa la fase y el comunicado) y cuando deja de estar en ellas. La
    prealerta no avisa (ADR 0051).
  - La primera pasada solo apunta lo que hay, y si una fuente falla no se da
    nada por acabado.
- **El canal, a las 7 y a las 21**: a las 21 h, la previsión de mañana
  (`CANAL_RESUMS`).
- **En el bot, la mañana y la noche por separado**: una hora por la mañana (6,
  7 u 8, o ninguna) y, aparte, un botón «A les 21 h, la previsió de demà» que
  se activa o no. Quien tenía las 21 h la conserva (`nit`) sin hacer nada.
  Quien está en el canal no recibe repetida ninguna de las dos.

## Consecuencias

- En otoño, con avisos amarillos de lluvia frecuentes, el canal tendrá más
  mensajes; cada aviso sale una sola vez, salvo que suba de nivel.
- El estado del canal pasa de `canal_resum` a `canal_resums` (una fecha por
  hora) y el de cada suscriptor, de una fecha a una por hora; el estado viejo
  se convierte solo.
- La página «Avisos» del navegador sigue con una sola hora a elegir (6, 7, 8 o
  21).

## Validación

`tests/test_bot.py`: avisos oficiales (primera vez solo se apunta, AEMET una
vez y al subir de nivel, Protección Civil en alerta y al salir, fuente caída
sin efectos), canal a las 7 y a las 21 con el estado viejo convertido, mañana y
noche en el mismo día, y la migración de quien tenía las 20 o las 21 h.
