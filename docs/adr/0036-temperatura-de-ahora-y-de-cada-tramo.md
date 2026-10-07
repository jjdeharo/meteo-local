# 36. Temperatura de ahora y de cada tramo

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

El 07-10-2026, a las 17:53, la previsión del bot decía «Ara mateix: 26 °C» y
«Temperatura d'avui: entre 16 °C i 23 °C». Juanjo lo vio incongruente. Había
tres causas:

1. El «ahora» del bot tomaba la temperatura de la estación de Montflorit,
   mientras que la web y los avisos de peligro ya usaban la particular (ADR
   0017). Esa tarde, las dos diferían entre 1,5 y 3,3 °C.
2. El intervalo «d'avui» solo contaba las horas que quedaban hasta medianoche:
   por la tarde ya no incluía la máxima del día.
3. Cada tramo de la tabla («de 18 a 19») llevaba la temperatura del final (las
   19). La lluvia sí se acumula hasta el final del tramo, pero la temperatura
   es la de un instante: al anochecer, la fila se adelantaba una hora y casi un
   grado.

## Decisión

- **Ahora, la temperatura de la estación particular** también en el bot
  («Ara mateix» de la previsión y de /ara), como en la web y en los avisos; si
  no tiene dato, la de Montflorit. La lluvia de ahora, si cualquiera de las dos
  la marca, como en la web.
- **«Temperatura d'aquí a mitjanit»** («de aquí a medianoche») en lugar de
  «d'avui»: dice lo que cuenta a cualquier hora.
- **Cada tramo, la media de sus dos extremos**, los dos corregidos con lo
  aprendido (`casa.py`, `docs/estadistica.md`). La corrección se sigue
  calculando y comprobando en cada hora en punto, así que no hay que volver a
  ajustarla. Lo usan la tabla, «Si surts» y el bot. El texto de la tabla lo
  explica.

## Alternativas descartadas

- **La temperatura del principio del tramo**: tiene el mismo problema al
  revés.
- **«Temperatura d'avui» con lo medido hasta ahora más lo previsto**: más
  largo de explicar en una línea, y la máxima ya pasada no ayuda a decidir.

## Consecuencias

- La temperatura mostrada en el registro (`mostrat`) pasa a ser la media del
  tramo; nada la usa para aprender.
- Si la estación particular deja de dar datos, el bot vuelve a la de
  Montflorit.

## Evidencia

Registro del NAS (`montflorit.csv` y `estacio-casa.csv`) y meteo.cat, 07-10-2026:

| Hora | Montflorit | Particular | Sabadell (XF) | Sant Cugat (XV) |
|---|---|---|---|---|
| 15 h | 26,8 | 25,1 | 24,4 | 25,7 |
| 17 h | 24,7 | 23,2 | 22,3 | 23,3 |
| 18 h | 26,4 | 23,7 | – | – |

De noche, Montflorit y la particular coinciden con medio grado de diferencia.

## Riesgos y limitaciones

- Tres días de registro de las dos estaciones: la diferencia por la tarde es
  una observación, no una medida de su sesgo.

## Validación

`tests/test_previsio_anterior.py` (tramo de 18 a 19 con 18 y 19 °C: 18,5 °C) y
`tests/test_bot.py` (ahora con la estación particular, lluvia de cualquiera de
las dos, «d'aquí a mitjanit» en los dos idiomas). Previsión compuesta con los
datos reales del 07-10-2026.
