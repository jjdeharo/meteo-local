# 19. Radar llevado hacia delante

Fecha: 2026-10-06 · Estado: aceptado

## Contexto

Juanjo preguntó si la evolución de la lluvia en el radar entra en la
predicción, porque «probablemente sea uno de los mejores indicadores». Hasta
ahora, el trayecto solo miraba a qué distancia estaba la lluvia y si crecía en
la última hora (ADR 0001), y la página de casa usaba el radar solo para pasar
al modo aviso. Ninguna de las dos sabía hacia dónde iba la lluvia. El
05-10-2026 los modelos daban 0,3 mm por hora mientras caían más de 20.

Preguntó también si RainViewer, la fuente de entonces, es mejor que el radar
de Meteocat, que es el que él mira.

## Decisión

- **Imagen**: la última de Meteocat, la composición corregida de su red de
  radares (XRAD: Vallirana, a unos 20 km de casa, Puig d'Arques, Tivissa-
  Llaberia y La Panadella), cada 6 minutos. Si se queda más de 15 minutos por
  detrás de la de RainViewer (composición de AEMET, cada 10 minutos), se usa
  la de RainViewer.
- **Movimiento**: el de la advección de Meteocat, su predicción a una hora,
  que calcula el campo de movimiento con las tres últimas imágenes. Se mide
  cuánto se desplaza su lluvia de la primera imagen prevista a la última en un
  cuadro de unos 300 km. Si la advección tiene más de una hora, el de
  RainViewer (pares a 30 minutos de la última hora), solo si los pares
  coinciden (menos de 20 km/h de diferencia). Si no, la lluvia se deja quieta.
- **Hacia delante** (`nowcast.py`): cada 5 minutos y hasta 2 horas, la lluvia
  de ahora en el punto de donde vendrá y en un círculo que crece con el tiempo
  (3 km más 0,08 km por minuto; 13 km a las 2 horas). Cada píxel es un caso
  posible: la lluvia esperada es la media y la probabilidad, la fracción con
  0,5 mm/h o más. Colores a dBZ con la leyenda de cada fuente; dBZ a mm/h con
  Marshall-Palmer (Z = 200 R^1,6).
- **Trayecto** (`prevision.py`): si la ventana del viaje cae dentro de las 2
  horas, el radar llevado hacia delante sustituye a la regla de la distancia,
  con los umbrales de los modelos: lluvia probable (50 %) y de 1 mm/h o más,
  riesgo alto; posible (20 %), moderado. Entre 2 y 3 horas, la distancia de
  siempre. Lluvia probable en casa en la hora siguiente activa el modo aviso.
- **Página de casa**: en las dos primeras horas de la tabla, si el radar da
  más lluvia o más probabilidad que los modelos, se usa la del radar, marcada
  con †; nunca rebaja la previsión, porque la lluvia que aún no se ha formado
  no está en el radar. Una hora debe quedar cubierta al menos 30 minutos. En
  «Ara a casa», una línea dice cuándo llegaría la lluvia, hacia dónde va y a
  qué velocidad. El riesgo propio (ADR 0018) lo recoge a través de la tabla.
- **Registro**: cada hora de la tabla guarda lo que daba el radar
  (`radar_mm`, `radar_prob`), y el trayecto, en sus señales
  (`radar_nowcast`), para comprobar con Montflorit si acierta y ajustarlo.

## Alternativas descartadas

- **Calcular el movimiento solo con RainViewer** (correlación de fase de
  toda la zona): con chubascos dispersos salta de 15 a 185 km/h entre pares
  seguidos (Evidencia). La advección de Meteocat da 21-29 km/h y la misma
  dirección.
- **Usar directamente la advección de Meteocat**: llega solo a una hora
  desde su imagen base, que se publica con unos 12 minutos de retraso. Queda
  menos de una hora por delante, y el trayecto se decide con hasta 2 horas.
- **Solo RainViewer o solo Meteocat**: Meteocat se para a veces (Evidencia);
  RainViewer marca más lluvia de la que hay.

## Consecuencias

- Las dos páginas descargan unas 90 teselas en cada pasada; el cálculo tarda
  unos 15 segundos.
- Si las dos fuentes fallan, todo sigue como antes, sin radar.
- La regla del trayecto cambia dentro de las 2 horas: `index.html` («Com es
  decideix») y el README lo explican.

## Evidencia

- Página del radar de Meteocat (consultada el 06-10-2026): fuentes, método de
  la advección («càlcul del camp de moviment de les tres darreres imatges»,
  horizonte de una hora, varias predicciones combinadas) y aviso de que La
  Panadella está fuera de servicio desde el 14-09-2026 durante unos 5 meses.
  Las teselas y la leyenda (franjas de 3 dBZ, de 9 a 66) salen de su script.
- Retraso: la imagen de las 09:42 UTC se publicó a las 09:54:24 (cabecera
  `last-modified`). Entre las 09:54 y las 10:14 UTC el servicio se paró (la
  página decía «Servei d'actualització d'imatges no disponible»); RainViewer
  tenía entonces la de las 10:10.
- Movimiento el 06-10-2026: RainViewer, pares de las 10:40 a las 12:10:
  25, 37, 34, 118, 51, 50, 58, 185, 169 y 15 km/h. Advección de Meteocat de las
  09:36 UTC: 21, 29 y 26 km/h hacia el nord-est y el est.
- Misma imagen (12:00), cuadro de 300 km: con 0,5 mm/h o más, 4.485 km² en
  Meteocat y 7.040 en RainViewer; con 20 mm/h, 108 y 188 km²; máximo, 107 y 205
  mm/h. El 66 % de la lluvia de Meteocat coincide con la de RainViewer.
- Tabla de colores de RainViewer: <https://www.rainviewer.com/api/color-schemes.html>
  (`calibracio/rainviewer_colors.csv`); todos los píxeles de las teselas
  descargadas están en ella.
- Hipótesis sin comprobar: los umbrales de probabilidad y del círculo. No hay
  archivo del radar (RainViewer guarda 2 horas); se comprobarán con el
  registro.

## Riesgos y limitaciones

- Un solo vector para toda la zona: si hay corrientes distintas en sitios
  distintos, se equivoca en las lejanas.
- No ve la lluvia que nace ni la que crece o se deshace.
- Las teselas de Meteocat no son una API documentada: si cambian, se usa
  RainViewer.

## Validación

`tests/test_nowcast.py` (conversiones, leyendas, desplazamiento de un
chubasco, coincidencia de los pares, advección vieja, llegada, alejamiento,
niveles del trayecto y modo aviso), cálculo real de las dos páginas con
Meteocat parado y en marcha, `probar-web` y axe-core.
