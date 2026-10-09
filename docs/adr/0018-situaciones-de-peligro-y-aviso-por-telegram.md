# 18. Situaciones de peligro y aviso por Telegram

Fecha: 2026-10-06 · Estado: aceptado; el envío a Juanjo, retirado el 08-10-2026

**08-10-2026:** el aviso ya no se manda aparte a Juanjo por Telegram (lo pidió
al ver que le llegaba repetido): lo reciben todos por las notificaciones, el
bot y el canal (`avisos_bot.py`, ADR 0034 y 0048), con la misma detección.
Este programa sigue llevando el estado y el registro. Desde entonces el aviso
público dice también cuándo ya no queda ningún peligro, como hacía el privado.


**09-10-2026 (ADR 0058).** Sin Montflorit, lo medido de ahora es solo casa: la lluvia de la última hora cuando marca y la temperatura. La lluvia de 12 horas medida ya no se evalúa; queda la prevista.

## Contexto

Juanjo pidió que la página de casa indique las situaciones de riesgo («viento
muy fuerte, lluvia, etc.») y que, cuando las haya, le llegue un mensaje por
Telegram. Al verlo en marcha concretó: con aviso amarillo de AEMET pero sin
ninguna previsión de lluvia torrencial, no quiere el mensaje; «solo lo quiero
si predices una situación meteorológica peligrosa, no avisos de otros».

En la misma petición quiso iconos en el bloque «Ara a casa», para leerlo más
deprisa.

## Decisión

- **Qué es peligro**: los umbrales de aviso de AEMET para el Prelitoral de
  Barcelona, la zona del Vallès (`RISC_LLINDARS` en `config.py`), aplicados a
  lo que mide y prevé la propia página, no a los avisos que emite AEMET:

  | | Amarillo | Naranja | Rojo |
  |---|---|---|---|
  | Lluvia en 1 h | 20 mm | 40 mm | 90 mm |
  | Lluvia en 12 h | 60 mm | 100 mm | 180 mm |
  | Racha máxima | 70 km/h | 90 km/h | 130 km/h |
  | Temperatura máxima | 36 °C | 39 °C | 42 °C |
  | Temperatura mínima | −4 °C | −8 °C | −12 °C |
  | Nieve en 24 h | 2 cm | 5 cm | 20 cm |

- **De dónde salen los valores** (`riscos.py`, que llama `casa.py` y guarda en
  `casa.json` como `riscos`):
  - Previsión, las 24 horas de la tabla: la lluvia de cada hora (la mayor de
    los tres modelos finos, la misma de la tabla), la ventana de 12 horas que
    más acumula, las rachas, la temperatura corregida y la nieve de AROME.
  - Ahora: la lluvia de la última hora y de las últimas 12 en Montflorit (y la
    de casa solo cuando marca lluvia, ADR 0017) y la temperatura de casa. El
    viento medido no cuenta: Montflorit da la media y el anemómetro de casa no
    va bien.
  - Lo medido y lo previsto son riesgos distintos: «ara plou molt fort» no es
    lo mismo que «es preveu».
- **En la página**: un recuadro «Risc» con el color del peor nivel, debajo de
  los planes de Protección Civil y encima de los avisos de AEMET, con cada
  situación, cuándo y el umbral que supera. «D'on surt» lo explica.
- **Por Telegram** (el reloj del NAS, tras cada publicación de la página de
  casa): un mensaje en catalán cuando aparece un riesgo o sube de nivel, con el
  enlace a la página, y otro cuando ya no queda ninguno. Un riesgo se da por
  acabado tras 3 horas sin verlo (`RISC_FI_H`), para que el vaivén de los
  modelos no repita el mensaje. Si falta la previsión o las estaciones, lo que
  dependía de ellas no se da por acabado. Estado en `/estat/riscos.json`.
- **Iconos de Lucide** en «Ara a casa»: termómetro, paraguas (o paraguas
  tachado si no llueve), nube con lluvia para la lluvia del día, gotas para la
  humedad, manómetro para la presión y viento.

## Alternativas descartadas

- **Avisar también de los avisos de AEMET y de los planes de Protección
  Civil**: era la primera idea. Juanjo la descartó: ya salen en la página y
  muchos avisos amarillos no llegan a nada en casa.
- **La tormenta prevista por el modelo (código 95-99) como riesgo**: el código
  solo dice que hay tormenta, no que sea fuerte, y en otoño sale a menudo. La
  tormenta fuerte la avisa AEMET y la tabla ya la muestra.
- **Umbrales propios**: los de AEMET son oficiales, están pensados para el
  Vallès y se pueden citar.

## Consecuencias

- Pocos mensajes, en días que lo merecen (Evidencia). Puede callar en un
  episodio que los modelos no ven; si la lluvia llega a los umbrales en
  Montflorit, lo medido sí avisa.
- `nas/reloj.sh` cambia: hay que reconstruir el contenedor.

## Evidencia

- Umbrales: AEMET, Plan Meteoalerta, anexo 1, «Umbrales y niveles de aviso»,
  versión del 31-05-2022, tabla de Cataluña, zona 690803
  (<https://www.aemet.es/documentos/es/eltiempo/prediccion/avisos/plan_meteoalerta/METEOALERTA_ANX1_Umbrales_y_niveles_de_aviso.pdf>).
- Frecuencia, con el archivo de `calibracio/` (enero de 2024 a 4 de octubre de
  2026): la previsión (la mayor de los tres modelos finos) llega a 20 mm en una
  hora en 5 días (12-07-2025, 20-08-2025, 13-09-2025, 3 y 4 de octubre de
  2026) y a 60 mm en 12 horas en 3 (13-09-2025, 3 y 4 de octubre de 2026). Las
  estaciones de Meteocat midieron 20 mm en una hora en 7 días en Sabadell y 9
  en Sant Cugat.
- El 05-10-2026, con el INUNCAT en emergencia, Montflorit midió como mucho
  16,4 mm en una hora y 52 mm en el día: no habría avisado por lo medido.
- El 06-10-2026, con aviso amarillo de AEMET por lluvia y tormentas, la
  previsión daba como mucho 3,2 mm en una hora y rachas de 19 km/h: sin
  riesgo, sin mensaje, como pidió Juanjo.
- Hipótesis sin comprobar: la frecuencia de las rachas de 70 km/h previstas
  por AROME (el archivo no guarda el viento).

## Riesgos y limitaciones

- Los umbrales de AEMET son para la zona entera; en un punto se superan menos.
- La lluvia prevista es la mayor de tres modelos: algún aviso de más es
  posible (2 de los 5 días del archivo no tuvieron esa lluvia en Sabadell ni
  en Sant Cugat).

## Validación

`tests/test_riscos.py` (detección, niveles, tramos, aviso una vez, subida de
nivel, final tras 3 horas y fuente caída), `probar-web` en Chromium, Firefox y
WebKit, escritorio, móvil y tableta, claro y oscuro, con un riesgo simulado, y
axe-core sin fallos en las dos páginas.
