# 33. Texto de los avisos de AEMET

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

Juanjo recibió en el móvil el aviso amarillo de tormentas de AEMET para el
Prelitoral de Barcelona con un detalle que la web no mostraba: «Pueden ir
acompañadas de granizo, en general inferior a 2 cm.». La web leía el resumen
de Meteoalarm, que solo trae zona, tipo, nivel y horas; el texto está en la
ficha de cada aviso, que el resumen enlaza. AEMET publica la descripción solo
en castellano (la versión inglesa de la ficha repite el mismo texto).

## Decisión

- `prevision.descripcion_aviso` lee la ficha de cada aviso vigente del
  Prelitoral de Barcelona y guarda su descripción (`descripcio`). La ficha
  cambia de dirección si cambia el aviso: se guarda hasta 6 horas.
- Las dos páginas la muestran tras la frase del aviso, agrupada por día:
  «L'AEMET hi afegeix — avui: «…» «…»; demà: «…»», **en castellano en las dos
  versiones**, citada (`<q>`, comillas latinas y cursiva) y marcada como
  `lang="es"` para los lectores de pantalla. Es el criterio de los avisos de
  Renfe y FGC (ADR 0029): los textos oficiales no se traducen (Juanjo,
  07-10-2026: «sí, hazlo así»).
- No se muestran las instrucciones («Esté atento. Manténgase informado…»): son
  las mismas en todos los avisos.

## Alternativas descartadas

- **Traducir el texto al catalán**: dejaría de ser lo que dice AEMET.
- **Los avisos de Meteocat, en catalán**: otro sistema, con otros umbrales y
  zonas, y con clave de acceso.

## Consecuencias

Una petición más por aviso vigente de la zona (suelen ser de 2 a 4), solo
cuando cambia el aviso.

## Evidencia

Ficha del aviso del 07-10-2026 (actualización de las 06:56 UTC): `es-ES`,
«Pueden ir acompañadas de granizo, en general inferior a 2 cm.»; `en-GB`, la
misma descripción y las instrucciones en inglés.

## Validación

`tests/test_avisos.py` (texto en castellano tal cual, ficha sin texto); las dos
páginas, en catalán y castellano, con los avisos reales del 07-10-2026.
