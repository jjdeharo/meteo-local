# 14. Salida fuera de las franjas

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

Fuera de sus franjas, la página del trayecto solo decía cuándo volvía a
informar (ADR 0011). Juanjo pidió que a cualquier hora diga lo mismo para una
salida sin trayecto fijo: coche o moto, la ropa y si el tiempo cambiará,
eligiendo la hora de vuelta.

## Decisión

- **Salida «ahora», vuelta a elegir** en las próximas 24 horas (campo de hora;
  por defecto, dentro de 4 horas, `SALIDA_VUELTA_POR_DEFECTO_H`).
- **El medio sale de las dos horas en que se circula**, la de salir y la de
  volver: mientras el vehículo está aparcado la lluvia no importa. Umbrales
  del trayecto: plan de Protección Civil en alerta o emergencia, aviso de
  AEMET, «plou ara», 50 % o 1 mm, coche; 20 % o 0,2 mm, moto con impermeable
  (`nivel_hora` en `casa.py`). Cada viaje dice su motivo.
- **Ropa** con la misma función que el trayecto (`prevision.roba`, ADR 0013),
  con la temperatura de las dos horas.
- **«Com canviarà»**: si empieza o para de llover entre la salida y la vuelta,
  o si la temperatura cambia 6 °C o más (`SALIDA_CAMBIO_TEMPERATURA`).
- **Todo se calcula en el NAS** (`sortides` en `casa.py`, en `casa.json`):
  cada hora de vuelta posible, con la salida en la hora en curso y en la
  siguiente, para que la página tenga resultado aunque los datos sean de la
  hora anterior. La página solo elige; la regla y la ropa no se duplican en
  JavaScript.
- Los avisos de Protección Civil y de AEMET se muestran arriba, como en el
  resto de páginas (salen de `casa.json`, que se actualiza todo el día).

## Alternativas descartadas

- **Calcular en el navegador:** duplicaría en JavaScript la regla y la ropa,
  que están en Python con pruebas.
- **Elegir también la hora de salida:** se deja para más adelante si hace
  falta.
- **Probabilidad de que llueva en algún momento del intervalo:** no cuenta si
  se circula o no; lo que decide el medio son las horas de los viajes.

## Consecuencias

`casa.json` crece unos 27 KB (dos salidas de 23 vueltas). La página del
trayecto lee también `casa.json`.

## Riesgos y limitaciones

- El tiempo es el de Cerdanyola: no sabe adónde se va.
- El radar y las estaciones solo cuentan en las primeras horas, a través de
  «Plou ara» y de la persistencia de la tabla de casa.

## Validación

`tests/test_sortida.py` (medio por las horas de circular, avisos, Protección
Civil, cambio de temperatura y ropa) y `tests/test_web.py` (salida de la hora
en curso y hora de vuelta elegida, también al día siguiente); `probar-web` y
axe-core.
