# Calibración de la regla con datos reales

Generado el 2026-10-05 con `calibracio/analitza.py`.

Lluvia en el trayecto: 0,2 mm o más en alguna media hora de la ventana en Sabadell (XF) o Sant Cugat (XV), del portal de datos abiertos de la Generalitat. Previsiones archivadas de Open-Meteo: «corto plazo» une las primeras horas de cada pasada del modelo; «24 h antes» es la previsión hecha un día antes.

## Anada 06:30-07:30, previsión a corto plazo

1003 días, del 2024-01-01 al 2026-10-04. Llovió en 38 (4 %).

| | Días que avisa | Lluvias detectadas | Lluvias no avisadas | Avisos sin lluvia |
|---|---|---|---|---|
| Regla: cotxe (≥ 1 mm) | 48 | 25 de 38 (66 %) | 13 | 23 (48 % de los avisos) |
| Regla: cotxe o compte (≥ 0,2 mm) | 106 | 31 de 38 (82 %) | 7 | 75 (71 % de los avisos) |
| Calibrado: probabilidad ≥ 20 % | 41 | 24 de 38 (63 %) | 14 | 17 (41 % de los avisos) |
| Calibrado: probabilidad ≥ 30 % | 33 | 19 de 38 (50 %) | 19 | 14 (42 % de los avisos) |

Error cuadrático de la probabilidad (Brier; menos es mejor), comprobado en meses que no se usaron para ajustar:

- Solo la frecuencia habitual de lluvia: 0.0365
- Regla actual: 0.0256 (mejora del 30 %)
- Calibrado: 0.0224 (mejora del 38 %)

Fiabilidad del calibrado (si dice 30 %, ¿llueve el 30 % de las veces?):

| Probabilidad dada | Días | Media dada | Llovió |
|---|---|---|---|
| 0 %–5 % | 935 | 1 % | 1 % |
| 5 %–10 % | 13 | 7 % | 15 % |
| 10 %–20 % | 14 | 13 % | 14 % |
| 20 %–30 % | 8 | 26 % | 62 % |
| 30 %–50 % | 12 | 40 % | 33 % |
| 50 %–100 % | 21 | 77 % | 71 % |

Frecuencia real de lluvia según el nivel de la regla:

| Nivel | Días | Llovió |
|---|---|---|
| moto | 897 | 7 (1 %) |
| compte | 58 | 6 (10 %) |
| cotxe | 48 | 25 (52 %) |

## Anada 06:30-07:30, previsión a 24 h antes

980 días, del 2024-01-20 al 2026-10-04. Llovió en 37 (4 %).

| | Días que avisa | Lluvias detectadas | Lluvias no avisadas | Avisos sin lluvia |
|---|---|---|---|---|
| Regla: cotxe (≥ 1 mm) | 47 | 16 de 37 (43 %) | 21 | 31 (66 % de los avisos) |
| Regla: cotxe o compte (≥ 0,2 mm) | 99 | 23 de 37 (62 %) | 14 | 76 (77 % de los avisos) |
| Calibrado: probabilidad ≥ 20 % | 23 | 11 de 37 (30 %) | 26 | 12 (52 % de los avisos) |
| Calibrado: probabilidad ≥ 30 % | 18 | 9 de 37 (24 %) | 28 | 9 (50 % de los avisos) |

Error cuadrático de la probabilidad (Brier; menos es mejor), comprobado en meses que no se usaron para ajustar:

- Solo la frecuencia habitual de lluvia: 0.0364
- Regla actual: 0.0321 (mejora del 12 %)
- Calibrado: 0.0314 (mejora del 14 %)

Fiabilidad del calibrado (si dice 30 %, ¿llueve el 30 % de las veces?):

| Probabilidad dada | Días | Media dada | Llovió |
|---|---|---|---|
| 0 %–5 % | 850 | 2 % | 2 % |
| 5 %–10 % | 90 | 6 % | 8 % |
| 10 %–20 % | 17 | 15 % | 12 % |
| 20 %–30 % | 5 | 26 % | 40 % |
| 30 %–50 % | 11 | 40 % | 55 % |
| 50 %–100 % | 7 | 74 % | 43 % |

Frecuencia real de lluvia según el nivel de la regla:

| Nivel | Días | Llovió |
|---|---|---|
| moto | 881 | 14 (2 %) |
| compte | 52 | 7 (13 %) |
| cotxe | 47 | 16 (34 %) |

## Tornada 15:00-15:30, previsión a corto plazo

1006 días, del 2024-01-01 al 2026-10-04. Llovió en 40 (4 %).

| | Días que avisa | Lluvias detectadas | Lluvias no avisadas | Avisos sin lluvia |
|---|---|---|---|---|
| Regla: cotxe (≥ 1 mm) | 63 | 23 de 40 (57 %) | 17 | 40 (63 % de los avisos) |
| Regla: cotxe o compte (≥ 0,2 mm) | 153 | 35 de 40 (88 %) | 5 | 118 (77 % de los avisos) |
| Calibrado: probabilidad ≥ 20 % | 39 | 17 de 40 (42 %) | 23 | 22 (56 % de los avisos) |
| Calibrado: probabilidad ≥ 30 % | 24 | 12 de 40 (30 %) | 28 | 12 (50 % de los avisos) |

Error cuadrático de la probabilidad (Brier; menos es mejor), comprobado en meses que no se usaron para ajustar:

- Solo la frecuencia habitual de lluvia: 0.0384
- Regla actual: 0.0302 (mejora del 21 %)
- Calibrado: 0.0301 (mejora del 22 %)

Fiabilidad del calibrado (si dice 30 %, ¿llueve el 30 % de las veces?):

| Probabilidad dada | Días | Media dada | Llovió |
|---|---|---|---|
| 0 %–5 % | 912 | 2 % | 1 % |
| 5 %–10 % | 38 | 7 % | 21 % |
| 10 %–20 % | 17 | 14 % | 29 % |
| 20 %–30 % | 15 | 23 % | 33 % |
| 30 %–50 % | 8 | 41 % | 38 % |
| 50 %–100 % | 16 | 75 % | 56 % |

Frecuencia real de lluvia según el nivel de la regla:

| Nivel | Días | Llovió |
|---|---|---|
| moto | 853 | 5 (1 %) |
| compte | 90 | 12 (13 %) |
| cotxe | 63 | 23 (37 %) |

## Tornada 15:00-15:30, previsión a 24 h antes

985 días, del 2024-01-19 al 2026-10-04. Llovió en 40 (4 %).

| | Días que avisa | Lluvias detectadas | Lluvias no avisadas | Avisos sin lluvia |
|---|---|---|---|---|
| Regla: cotxe (≥ 1 mm) | 51 | 18 de 40 (45 %) | 22 | 33 (65 % de los avisos) |
| Regla: cotxe o compte (≥ 0,2 mm) | 140 | 34 de 40 (85 %) | 6 | 106 (76 % de los avisos) |
| Calibrado: probabilidad ≥ 20 % | 36 | 14 de 40 (35 %) | 26 | 22 (61 % de los avisos) |
| Calibrado: probabilidad ≥ 30 % | 25 | 9 de 40 (22 %) | 31 | 16 (64 % de los avisos) |

Error cuadrático de la probabilidad (Brier; menos es mejor), comprobado en meses que no se usaron para ajustar:

- Solo la frecuencia habitual de lluvia: 0.0392
- Regla actual: 0.0321 (mejora del 18 %)
- Calibrado: 0.0336 (mejora del 14 %)

Fiabilidad del calibrado (si dice 30 %, ¿llueve el 30 % de las veces?):

| Probabilidad dada | Días | Media dada | Llovió |
|---|---|---|---|
| 0 %–5 % | 856 | 2 % | 1 % |
| 5 %–10 % | 68 | 6 % | 16 % |
| 10 %–20 % | 25 | 15 % | 20 % |
| 20 %–30 % | 11 | 24 % | 45 % |
| 30 %–50 % | 15 | 40 % | 20 % |
| 50 %–100 % | 10 | 72 % | 60 % |

Frecuencia real de lluvia según el nivel de la regla:

| Nivel | Días | Llovió |
|---|---|---|
| moto | 845 | 6 (1 %) |
| compte | 89 | 16 (18 %) |
| cotxe | 51 | 18 (35 %) |

## El día entero (un solo medio), previsión a corto plazo

1001 días. Llovió en algún trayecto en 69 (7 %).

| | Días de coche | Días de lluvia con coche | Días de lluvia en moto | Coche sin lluvia |
|---|---|---|---|---|
| Regla actual (cotxe) | 91 | 42 | 27 | 49 |
| Regla actual (cotxe o compte) | 203 | 60 | 9 | 143 |
| Calibrado ≥ 20 % en algún trayecto | 64 | 35 | 34 | 29 |
| Calibrado ≥ 30 % en algún trayecto | 46 | 27 | 42 | 19 |

## Persistencia de la lluvia

Si en una hora ha llovido al menos lo que dice la fila, cuántas veces siguió lloviendo (0,2 mm o más) en las horas siguientes, en Sabadell y Sant Cugat juntas:

| Última hora | +1 h | +2 h | +3 h | +4 h |
|---|---|---|---|---|
| ≥ 4,0 mm | 86 % (245) | 57 % (245) | 43 % (245) | 38 % (245) |
| ≥ 1,0 mm | 78 % (859) | 56 % (859) | 44 % (859) | 38 % (859) |
| ≥ 0,2 mm | 63 % (1842) | 48 % (1842) | 40 % (1838) | 34 % (1839) |
