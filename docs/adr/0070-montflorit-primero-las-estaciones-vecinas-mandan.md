# 70. Montflorit primero: las estaciones vecinas mandan sobre Sabadell y Sant Cugat

Fecha: 2026-10-10 · Estado: aceptado

## Contexto

Para aprender, una hora contaba como lluviosa solo si la estación de casa lo
marcaba; con casa a cero, contaba como seca solo si tampoco recogieron nada
Sabadell, Sant Cugat (Meteocat, a 2,5 y 4,6 km) e ICERDA6 (ADR 0058 y 0060).
La vigilancia del pluviómetro usaba la menor de esas tres. Juanjo, 10-10-2026:
«para la predicción de la lluvia en Montflorit para mí tiene mucho más valor
las estaciones de aquí mismo que las de Sant Cugat o Sabadell» y «si está
lloviendo en 2 estaciones de Montflorit eso no puede ser una hora seca, a lo
mejor sí lo es en Sant Cugat o Sabadell».

## Evidencia

Historial de cada 5 minutos de las cuatro vecinas (Weather Underground,
`history/all`, del 27-07 al 09-10-2026, en `calibracio/dades/veines`, sin
subir) contra la estación de casa y Meteocat, hora a hora, del 27-07 al
04-10-2026 (1.679 horas); scripts `calibracio/veines_*.py`:

- De las 36 horas en que llovió en casa, ICERDA6 y ICERDA28 no vieron lluvia
  en 2, ICERDA18 en 3, ICERDA48 en 7, Sabadell en 8 y Sant Cugat en 4.
- Con casa a cero, una vecina sola con las demás secas marca lluvia en 0 a
  2 horas de 1.643: casi nunca en falso. Cuando marca, suelen marcar varias.
- Con la regla nueva, 11 horas que no se sabían pasan a lluviosas (el
  03-10-2026 de 14 a 21 h las cuatro vecinas recogieron de 1 a 5 mm por hora
  y casa, cero), 10 pasan a secas (llovía en Sabadell o Sant Cugat, no aquí),
  1 seca pasa a no saberse y el resto no cambia.
- Como señal de la probabilidad a corto plazo (archivo, 1.674 horas, 47 con
  lluvia, validación por semanas): Brier 0,0149 solo con los modelos,
  0,0139 con la lluvia de casa de la hora anterior y 0,0128 con la de casa y
  la mediana de las vecinas.
- El modelo base del archivo, ajustado con la lluvia de Montflorit (un año)
  en lugar de con Sabadell y Sant Cugat (casi tres), no acierta más en
  Montflorit: Brier 0,0207 contra 0,0207 a corto plazo y 0,0273 contra 0,0267
  un día antes. Con solo los modelos como entrada, más años pesan más.

## Decisión

- **Qué pasó en Montflorit** (`aprenentatge.pluja_observada`, para aprender
  y para la comprobación de «Si surts»): llueve si casa lo marca o si lo
  marcan al menos dos vecinas de las que cuentan (`C.VEINES_PLUJA_MIN`;
  ICERDA6, ICERDA18 e ICERDA28); seca si casa marca cero, ninguna de esas ve
  lluvia y las que confirman (`sec`, ahora las tres) están a cero. Si una
  sola ve lluvia, no se sabe. Sin vecinas, como antes: Sabadell y Sant Cugat.
  ICERDA48 sigue sin contar: pierde demasiada lluvia.
- **Vigilancia del pluviómetro**: la referencia es la mediana de las vecinas
  fiables (con dos al menos); si no hay, la menor de Sabadell y Sant Cugat.
- **La lluvia de las vecinas, en el registro y en el modelo**: cada línea
  del registro guarda desde hoy la lluvia de la última hora de cada vecina
  (`veines`), y la variante `RASGOS_PROPIS_VEINES` (la mediana de las que
  cuentan, como la persistencia) se ajusta cada día y solo se adopta si
  acierta más que el base en sus mismas horas, como la de Sant Cugat
  (ADR 0042). Al prever, la misma mediana de esa pasada.
- **El modelo base del archivo no cambia** (lo dice la evidencia).

## Riesgos y limitaciones

- Las vecinas son estaciones personales: pueden moverse, cambiar o dejar de
  emitir. Si faltan, se vuelve solo a la regla con Meteocat.
- La variante tardará en tener las 30 horas de lluvia que pide el
  aprendizaje: el registro las guarda desde hoy.
- 75 días y 36 horas de lluvia en casa: el examen se repetirá con más datos
  en la revisión prevista a partir del 07-11-2026.
