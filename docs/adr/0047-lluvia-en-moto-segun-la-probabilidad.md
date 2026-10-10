# 47. Lluvia en moto y en bici según la probabilidad

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

El 08-10-2026 «Si surts» desaconsejó la moto para una salida a las 10 h con
vuelta a las 17 h, y no llovió (0,0 mm todo el día en Montflorit y en la
estación de casa). Juanjo tuvo que cambiar de medio sin necesidad y preguntó
si el programa aprende de estos fallos.

Mirado en el registro del NAS:

- **10 h**: probabilidad del 0 %, los tres modelos a 0 mm. El «no» salía solo
  del aviso amarillo de AEMET por lluvia (20 mm en una hora) en el Prelitoral
  de Barcelona, de 10:00 a 24:00, que contaba como lluvia probable (ADR 0029).
- **17 h**: a las 6 y a las 7, ICON-EU daba 1,7 mm y los dos AROME, 0; la
  probabilidad aprendida era del 25 %. Con un solo modelo por encima de 1 mm
  la regla decía «Pluja probable».

La probabilidad, que es lo que aprende (ADR 0012), acertó; lo que falló son
dos reglas fijas que mandaban por encima de ella. Además, desde la retirada
de la página del trayecto (ADR 0030) nadie apuntaba si el veredicto acertaba.
Juanjo aprobó las tres cosas: decidir por la probabilidad, que el aviso solo
lleve a «compte» y que el programa aprenda también de los avisos.

## Decisión

- **En moto y en bici decide solo la probabilidad de cada hora**, que ya reúne
  los modelos, cuántos coinciden, el ensemble, el radar, las estaciones y lo
  aprendido: 40 % o más, o lluvia ahora, «millor no»; 10 % o más, «compte»
  (en moto, «porta l'impermeable»). Sin probabilidad, la lluvia del modelo más
  lluvioso (1 mm y 0,2 mm). Umbrales en `web/sortir.js` y en `config.py`
  (`MOTO_PROB_*`), que las pruebas comparan.
- **Un aviso de AEMET que no respalda ningún dato lleva a «compte», no a
  «millor no»**, en moto y en bici, y el motivo lo sigue diciendo («ni el
  radar, ni les estacions, ni els models hi veuen pluja. Per si de cas, porta
  l'impermeable»). Sustituye para estos dos medios lo decidido el 07-10-2026
  (ADR 0029: «seguir recomendando coche pero indicando bien claro que no hay
  motivo aparente para no ir en moto»).
- **A pie y en coche no cambia el nivel**: allí una falsa alarma solo añade un
  paraguas o un «condueix amb compte», y no se ha medido. **El texto del coche
  sí se iguala al de la moto** (3.23.1, Juanjo, 08-10-2026): «Pluja probable»
  solo desde el 40 %, «Pot ploure» desde el 10 %, y el texto del aviso cuando
  es lo único que ve lluvia. Antes, con el aviso, un 10 % y 0,3 mm, el coche
  decía «Pluja probable» y la moto «Pot ploure».
- **El modelo aprende el peso de lo oficial**: cada hora del registro lleva
  desde hoy `avis_pluja` (aviso de AEMET por lluvia o tormentas) y
  `pla_inuncat` (INUNCAT en alerta o emergencia), y `aprenentatge.py` ajusta
  una tercera variante con esas dos señales, que se adopta solo si acierta más
  en semanas no vistas, como la de Sant Cugat (ADR 0042).
- **Verificación diaria del veredicto** (`aprenentatge.py diari`): en
  `/estat/registre/moto.csv`, de cada hora pasada de 6 a 22 h con lluvia
  medida, el nivel de la regla nueva y el de la anterior, al salir (previsión
  de 1 a 3 horas antes) y con la vuelta decidida por la mañana (de 6 a 10
  horas antes). A los 28 días, un resumen por Telegram, una vez;
  `python3 aprenentatge.py moto`, cuando se quiera.
  Desde el 10-10-2026, sustituido por la comprobación de todos los medios
  (`sortir.csv`, ADR 0068).

## Alternativas descartadas

- **Solo la probabilidad con los umbrales de antes (50 % y 20 %)**: lo que se
  propuso primero. Con el archivo, las falsas alarmas bajan de 25 a 8 días,
  pero los días de lluvia con «bé» suben de 14 a 23. No se aplicó.
- **Mantener los milímetros solo para «compte»**: no reduce los días secos con
  «compte» (de 53 a 70) y deja igual los de lluvia con «bé».
- **Exigir dos modelos para el milímetro**: menos falsas alarmas (15 días),
  pero menos que la elegida (11) y sin bajar los días de lluvia con «bé».
- **Medir cuánto aciertan los avisos de AEMET en Montflorit**: sin la clave de
  OpenData no hay historial; el registro propio lo hará desde hoy.

## Consecuencias

- Menos «millor no» sin lluvia y algún «compte» más: el impermeable se
  recomienda unos 19 días secos más de cada 900.
- Cuando el modelo propio sustituya al del archivo, el veredicto mejorará con
  él; antes, las reglas fijas no aprendían.
- El registro crece unos pocos bytes por hora; `moto.csv`, unas 30 filas al
  día. Los dos van en la copia diaria (ADR 0044).

## Evidencia

- Registro del NAS del 08-10-2026 (`casa-2026-10.jsonl`, `montflorit.csv`,
  `estacio-casa.csv`) y aviso publicado en `montflorit.json`: «Precipitación
  acumulada en una hora: 20 mm», Prelitoral de Barcelona, de 10:00 a 23:59.
- `python3 calibracio/regla_moto.py` (archivo del 1-1-2024 al 5-10-2026,
  probabilidad en validación cruzada por semanas, verdad: Sabadell y Sant
  Cugat). Viaje de 10 a 17 h, a corto plazo (992 días, 80 con lluvia):

  | Regla | Secos con «no» | Secos con «compte» | Lluvia con «bé» | con «compte» | con «no» |
  |---|---|---|---|---|---|
  | Antes | 25 | 53 | 14 | 22 | 44 |
  | Probabilidad, 50 y 20 % | 8 | 34 | 23 | 27 | 30 |
  | **Probabilidad, 40 y 10 %** | **11** | 72 | **13** | 26 | 41 |

  Un día antes (971 días, 78 con lluvia): antes, 21 y 22; la elegida, 14 y 17
  (secos con «no» y lluvia con «bé»).

## Riesgos y limitaciones

- El archivo solo tiene los modelos: el radar, el ensemble y los avisos no se
  han comprobado con datos. El registro propio lo hará.
- Cada umbral se eligió entre seis variantes con el mismo archivo: puede
  estar algo ajustado a él. La verificación diaria lo dirá.
- La verdad del archivo son estaciones a 5-6 km.
- La variante con los avisos tardará en tener 30 horas de lluvia con dato.

## Validación

`tests/test_web.py` (el caso del 08-10-2026, aviso solo en bici y en moto,
probabilidad y milímetros), `tests/test_aprenentatge.py` (rasgos de los
avisos, mismos umbrales que la página, verificación sin repetir horas,
resumen una sola vez) y `tests/test_registre_casa.py` (aviso y plan de cada
hora). Ejecución real de `casa.py` el 08-10-2026 a las 17 h: el registro lleva
`avis_pluja`, `pla_inuncat` y `plou_ara`.
