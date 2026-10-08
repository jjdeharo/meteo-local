# 39. Correcciones de la auditoría del 8 de octubre de 2026

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Con la 3.12.0 recién publicada (ADR 0038), Codex hizo una segunda revisión de
solo lectura del conjunto y encontró tres fallos graves y seis importantes,
todos reproducidos con datos ficticios o con el registro del NAS, sin tocar
producción. El informe es de trabajo y no se publica. Claude los reprodujo
uno a uno con el programa del informe sobre la 3.12.1, propuso qué aplicar
y qué no, y Juanjo lo aprobó en bloque («sí a todo»). Cada corrección lleva
en el código la referencia «auditoría del 08-10-2026».

## Decisión

1. **El coche no sale «bé» con lluvia** (`web/sortir.js`, `avalua`). Solo
   miraba el viento: con 90 mm/h previstos decía «Sense pluja ni vent
   fort». Ahora, lluvia muy fuerte en una hora (40 mm, el umbral naranja de
   AEMET en `config.RISC_LLINDARS`), «no»; fuerte (20 mm, el amarillo),
   probable (los umbrales de lluvia de siempre) o hielo (1 °C o menos),
   «compte»; lluvia posible, se dice sin cambiar el nivel. «Sense pluja ni
   vent fort» solo cuando ninguna hora del viaje la ve. Si el aviso de AEMET
   es lo único que ve lluvia, se dice, como en los demás medios. La ayuda de
   la página y el ADR 0029 lo recogen.
2. **Sin horas no hay previsión** (`bot/bot.py`, `resum`). Con un JSON
   reciente pero sin horas (un cálculo caído), el resumen decía «Sense pluja
   prevista». Ahora dice «Ara no hi ha previsió disponible: les dades de les
   HH:MM no en porten», también en la de mañana si no trae horas de ese día.
   Y en «Ara mateix», sin la estación de Montflorit, el cero del pluviómetro
   de casa no sirve para decir «no plou» (ADR 0017): solo se da la
   temperatura.
3. **La hora siguiente de la riera se cuenta desde ahora** (`riera.py`,
   `horitzo`, `maxim_amb_radar`). Las ventanas se evaluaban a 0, 30 y 60
   minutos del final de la última media hora de la estación, que llega con
   retraso (unos 30 minutos según la tabla de meteo.cat; hoy, 9; se admiten
   hasta 2 horas): se perdían de 10 a 35 minutos de anticipación, y un
   chaparrón de 37,5 mm entre 35 y 60 minutos después de ahora no daba
   atención. Ahora se evalúan ventanas cada media hora hasta ahora + 60
   minutos, con el radar cubriendo el hueco de la estación; `radar_1h` pasa
   a ser lo que el radar da desde el final de lo medido hasta dentro de una
   hora, y los mensajes dicen «des de llavors fins d'aquí a una hora».
   `index_d_aqui_a_min` se cuenta desde ahora.
4. **Transporte público con líneas sin datos** (`web/sortir.js`,
   `estatPublic`). Con R4, R7 y R8 sin datos y la S2 circulando salía «Bé,
   cap incidència». Ahora, si falta alguna línea, el veredicto es neutro
   («Dades parcials») y dice «S2 sense incidències; de R4, R7, R8 ara no hi
   ha dades»; con incidencias, se añade qué líneas no tienen datos.
5. **«Ara» es la franja vigente** (`web/sortir.js`, `horesVigents`). Los
   selectores tomaban todas las horas del JSON y llamaban «Ara» a la
   primera, aunque hubiera terminado (hasta 2 horas con datos atrasados;
   unos minutos en cada cambio de hora). Se descartan las franjas con `fins`
   pasado antes de pintar.
6. **Las 30 horas con lluvia son horas observadas distintas**
   (`aprenentatge.py`, `valida_pluja`). Se contaba cada previsión repetida
   de la misma hora: en el NAS, 124 muestras de lluvia eran 6 horas reales, y
   dos horas previstas 24 veces daban 48. Ahora se cuentan `fins` distintos
   con lluvia, que es lo que promete `docs/estadistica.md`.
7. **La validación agrupa por la hora observada** (`aprenentatge.py`,
   `grupo_semana`). Iba por la fecha de emisión, y una misma hora observada
   caía en dos grupos al cruzar el domingo (la previsión del domingo a las
   23:00 y la del lunes a las 00:00 para el lunes a la 01:00). Ahora el grupo
   lo fija la semana de `fins`, en lluvia y en temperatura.
8. **Solo los avisos vigentes deciden el servicio** (`trens.py`, `vigent`).
   Se guardaba el inicio del aviso para ordenarlo, pero un aviso de carretera
   para mañana ganaba por ser el más nuevo y ponía «bus» hoy. Ahora se guarda
   también el final (`fi`, del `activePeriod` de Renfe y del `TimeRange` de
   FGC), y un aviso que no ha empezado o ya ha acabado se muestra pero no
   decide. Además `trens_renfe` comprueba la marca de tiempo del feed de
   posiciones: con más de 10 minutos (`POSICIONS_VELLES_MIN`) las líneas de
   Renfe quedan «sense dades», porque una respuesta correcta no demuestra
   que sea actual.
9. **Avisos de AEMET que vienen de ayer** (`bot/bot.py`,
   `text_avisos_aemet`). El resumen elegía los avisos cuya fecha de inicio
   era el día resumido, y omitía uno que empezó ayer y sigue hoy. Ahora se
   eligen por solapamiento con el día.
10. **Documentación al día**: el README dice que `desplegament.py` despliega
    igualmente si GitHub no responde o las pruebas llevan más de 20 minutos
    (las excepciones del ADR 0038, que antes solo estaban en el ADR);
    `docs/estadistica.md` explica las horas únicas y la agrupación por hora
    observada, y su apartado 7 ya no promete aprendizaje para el trayecto
    retirado (ADR 0030).

## Alternativas descartadas

- **Un margen temporal alrededor del grupo de validación** (propuesta del
  informe junto al punto 7): complica el método sin una medida de que
  mejore nada; con la agrupación por hora observada se cumple lo que dice la
  documentación. Queda como hipótesis por si las métricas resultan optimistas.
- **Recalcular en una prueba las métricas del modelo del archivo**: el
  archivo de 2024-2026 no está en el repositorio; la prueba sigue comprobando
  lo guardado y el ADR 0021 dice cómo se calculó.
- **Cambiar lo que dicen las promesas no demostradas** (aviso 15 minutos
  antes de llover, eficacia del radar en la riera, calibración de la
  probabilidad publicada): no hay código que cambiar; son evidencia que solo
  dan los episodios. La riera sigue «en proves» en el bot; el aviso de
  lluvia lleva 1 acierto en 3 episodios. Se revisará con un mes de datos.
- **Separar en el resumen los intervalos discontinuos de AEMET**: con un
  nivel y un tipo por línea, el caso no se ha dado; se junta por nivel como
  hasta ahora.

## Evidencia

- Los nueve casos del informe, reproducidos sobre la 3.12.1 con su programa
  (`avalua('cotxe', 90 mm, prob 1)` → «be, Sense pluja ni vent fort»; `resum`
  con `hores: null` → «Sin lluvia prevista»; riera con la estación media hora
  atrás y 37,5 mm de radar en la hora real → índice 0; `estatPublic` con tres
  líneas sin datos → «be»; `grupo_semana` → 3 y 0 para la misma hora;
  48 «horas de lluvia» con 2 reales; aviso de Renfe para mañana → `bus`;
  aviso de AEMET de ayer vigente hoy → lista vacía).
- Retraso de la estación de la riera: 30 minutos en la simulación del ADR
  0027 (tabla de meteo.cat); 9 minutos a las 08:09 del 08-10-2026.
- El feed de posiciones de Renfe lleva `header.timestamp` (comprobado el
  08-10-2026: 17 segundos de antigüedad).

## Validación

- Una prueba por corrección, con el caso del informe (`tests/test_web.py`,
  `test_bot.py`, `test_riera.py`, `test_trens.py`, `test_aprenentatge.py`);
  dos pruebas existentes se ajustaron porque describían el comportamiento
  antiguo (el protobuf sin `fi`; el caso real del 07-10 a las 20:21, que se
  evaluaba a las 07:50 y ahora el aviso nuevo no era «vigente»). 213 pruebas
  en verde el 08-10-2026, y el programa del informe ya no reproduce ninguno de
  los nueve casos.
- «Si surts» en Chromium, Firefox y WebKit, escritorio, móvil y tableta,
  claro y oscuro, en catalán y castellano, con `probar-web` y axe-core.

## Riesgos

- El coche con lluvia probable en «compte» puede parecer prudente de más en
  lluvia débil; el texto dice el motivo («condueix amb compte») y los
  umbrales están en un solo sitio (`PLUJA_COTXE`) por si hay que ajustarlos.
- Con el horizonte desde ahora, un radar que vea lluvia fuerte que luego no
  cae puede adelantar una atención que antes habría llegado media hora más
  tarde o no habría llegado; es el precio de la anticipación y el aviso ya
  dice que es orientativo.
