# 13. Ropa según el tiempo

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

Juanjo pidió que la página del trayecto diga también qué ropa ponerse según
el frío, el calor o la lluvia. El vehículo es un ciclomotor: no pasa de
45 km/h.

## Decisión

- Una línea «Roba» en la recomendación de la mañana (`roba` en
  `prevision.py`), para todo el día, porque la ropa se elige al salir.
- Depende de la temperatura más baja de los dos trayectos. Con 10 °C o
  menos, de la sensación térmica a 45 km/h (`VELOCIDAD_CICLOMOTOR_KMH`) con el
  índice de Environment Canada, que solo vale en ese rango; por encima, de la
  temperatura del aire.
- En moto: menos de 0 °C de sensación, ropa de invierno completa; hasta 10 °C
  de aire, chaqueta de invierno, forro y cuello; hasta 17 °C, chaqueta con
  forro; hasta 24 °C, de media temporada; por encima, de verano. Con
  «compte», el impermeable delante. En coche, abrigo, chaqueta, chaqueta
  ligera o ropa de verano, y paraguas.
- Si entre la ida y la vuelta hay 8 °C o más (`ROPA_DIFERENCIA_CAPAS`),
  recomienda capas.
- Destacada en un recuadro con iconos de MingCute (Apache 2.0): chaqueta (en
  moto siempre, porque va con protecciones; en coche hasta 24 °C) o camiseta
  (coche con ropa de verano), y paraguas (coche) o nube con lluvia
  (impermeable en moto). Solo por la mañana, cuando se elige.

## Alternativas descartadas

- **Cifras de sensación térmica de webs de motos**: no cuadran con el índice
  oficial (por ejemplo, −2 °C con 10 °C a 50 km/h, cuando el índice da unos
  5 °C).
- **Usar el índice por encima de 10 °C**: está fuera de su validez.
- **Iconos de Lucide o Tabler**: Lucide solo tiene camiseta; la «chaqueta» de
  Tabler es un chaleco sin mangas.

## Evidencia

- Índice de Environment Canada (2001), adoptado también por Estados Unidos:
  13,12 + 0,6215·T − 11,37·V^0,16 + 0,3965·T·V^0,16, para T ≤ 10 °C y
  V ≥ 4,8 km/h.
- Recomendaciones de la DGT para ir en moto con frío (recogidas por
  Motopóliza y Torcal): chaqueta y pantalón térmicos con protecciones,
  guantes de invierno, cuello polar y tres capas.

## Riesgos y limitaciones

- Los umbrales de 17 y 24 °C son de criterio, sin fuente; se ajustan en
  `prevision.py` si no encajan con la experiencia.
- La sensación no tiene en cuenta el viento de cara, solo la marcha.

## Validación

`tests/test_decidir.py` (clase `Roba`): sensación a 45 km/h, frío, lluvia,
capas y coche.
