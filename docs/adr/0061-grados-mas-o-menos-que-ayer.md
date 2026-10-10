# 61. Grados más o menos que ayer

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

Juanjo pidió que la previsión de un día o de un tramo dijera cuántos grados
más o menos hará que ayer: «la mayoría de predicciones de otros servicios lo
llevan y es muy útil» (10-10-2026). La estación de casa guarda la
temperatura de cada hora (`estacio-casa.csv`, ADR 0017) y la previsión ya
está corregida con esa misma estación (ADR 0036): las dos cifras se pueden
comparar.

## Decisión

- **Lo previsto contra lo medido.** Cada tramo se compara con las mismas
  horas del día antes: los de hoy, con lo que midió la estación ayer; los
  de mañana, con hoy (lo medido hasta ahora y lo previsto para el resto).
  Cada hora del día antes vale lo mismo que en la previsión: la media de sus
  dos extremos (ADR 0036).
- **La máxima de día y la mínima de noche**: en el día, la mañana y la tarde
  se compara la máxima; en la noche, la mínima.
- **La cifra, desde 2 grados** (`COMPARA_MIN`): la previsión de la máxima
  se equivoca en torno a un grado (ADR 0036), así que «1 grau més» sería
  ruido. Por debajo, «semblant a ahir».
- **Dónde sale**: en la cabecera de cada tramo de «El temps», junto a la
  temperatura («16–23 °C · 2° més que ahir»), y en la línea de la
  temperatura de la previsión del bot, que también usan «Consultes», el
  canal y los avisos del navegador («Temperatura: entre 11 °C i 23 °C, 2
  graus més que ahir»). Mañana se compara con hoy: «2 graus menys que avui».
- **Los datos**: `casa.py` añade a los datos `temperatura_mesurada`, la de
  cada hora en punto de las últimas 72 horas, del registro del NAS y de la
  lectura de la pasada (`registre.temperatures_casa`). La web
  (`web/casa.js`, `comparaTemp`) y el bot (`bot.compara_temp`) hacen la
  misma cuenta, y las pruebas lo comprueban.
- **Sin dato, nada**: si falta alguna hora del día antes, si falla la
  estación o si publica la reserva de IONOS (que no tiene el registro), no
  se compara. Nunca con una previsión del día antes.

## Alternativas descartadas

- **Comparar con la previsión de ayer**: una previsión no es lo que pasó, y
  la estación ya da lo medido.
- **Mañana contra ayer**: «mañana, 3 grados más que ayer» confunde; se
  compara con el día anterior a cada tramo.
- **Decir siempre la cifra**: con diferencias de un grado, más que
  informar, se repetiría el error de la previsión.

## Consecuencias

En el móvil, entre una y tres de las cinco cabeceras de tramo pasan a
ocupar dos líneas, según la anchura (medido el 10-10-2026 de 320 a 412 px:
el bloque de la previsión crece entre 0 y 78 px). Sin desbordamiento.
Juanjo lo vio en un servidor local antes de publicarlo.

## Evidencia

Con los datos reales del 10-10-2026 a las 07 h: la máxima prevista para el
resto del día, 22,7 °C, contra 20,7 °C medidos a las mismas horas del
09-10 (el bot dice «2 graus més que ahir»); mañana, 23 °C contra los 22,7
de hoy («semblant a la d'avui»).

## Riesgos y limitaciones

- El tramo en curso solo compara las horas que quedan («Matí, fins a les
  14 h»), contra las mismas horas de ayer.
- En los días de cambio de hora, las horas se emparejan por la hora del
  reloj, no por el instante.

## Validación

`tests/test_bot.py`: la cuenta (máxima de día, mínima de noche, mañana con
lo previsto de hoy, sin dato no se dice nada) y el texto en los dos
idiomas. `tests/test_web.py`: la web da lo mismo que el bot en los mismos
casos y la cabecera del tramo lleva la diferencia. Probado en Chromium,
Firefox y WebKit de 320 a 1280 px, en catalán y castellano.
