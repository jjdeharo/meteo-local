# 46. Incendios cerca y Pla Alfa (y por qué no el acceso a Collserola)

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Codex propuso añadir los avisos de Collserola que afectan al barrio: riesgo de
incendio y, sobre todo, restricciones de acceso y su levantamiento. Juanjo
pidió buscar fuentes legibles (y aportó la página de actuaciones de Bombers) y
hacerlo con aviso de incendio cerca. Collserola está cerrado al público desde
el 12-03-2026 por la peste porcina africana, sin fecha de reapertura.

## Decisión

- **Fuentes** (`entorn.py`, en cada pasada del cálculo; cada parte, `None` y
  un error si su fuente falla):
  - **Incendios**: la capa pública de ArcGIS que usa el visor de actuaciones
    de Bombers (`ACTUACIONS_URGENTS_online_PRO_AMB_FASE_VIEW`). Solo guarda
    las actuaciones en curso; se piden las de vegetación (`IV`) a menos de
    `ENTORN_RADI_KM` (5 km) de Montflorit y se quedan las forestales sin
    final. Las de vegetación urbana (solares) son muchas y no limitan salir.
  - **Pla Alfa**: las capas de los Agents Rurals de hoy y mañana, por
    municipio (Cerdanyola, `082665`) y de cierres de espacios naturales.
    La escala es 0-4; el mapa oficial pinta el 5 en gris claro, aparte del
    blanco del 0: es «sin nivel» y se trata como tal. Fuera de campaña la
    capa municipal de hoy se queda con el último valor (el 08-10-2026, sin
    editar desde el 18-08): solo vale si se ha editado en las últimas 36 h.
  - **Dónde va** (Juanjo, 08-10-2026): lo que dura poco, en «Avisos actius» de
  las dos páginas y en `/avisos_actius` del bot: el incendio forestal cerca
  (franja roja) y el Pla Alfa de Cerdanyola desde el nivel 3, que restringe el
  acceso a los espacios forestales (naranja el 3, rojo el 4), con los cierres
  que tocan Collserola.
- **Avisos por Telegram, dentro de «Situacions de perill»** (el antiguo
  «Temps excepcional»), sin botón nuevo: Juanjo no quería que el menú
  `/avisos` creciera, y pidió un nombre corto que quepa en la pantalla
  («Situacions de perill» / «Situaciones de peligro», sin paréntesis). Se
  avisa de un incendio forestal a menos de 5 km al aparecer y cuando deja de
  constar. Van al canal (como todo «perill») y a quien lo tenga marcado. La
  primera vez solo se apunta lo que hay, y si Bombers no responde no se toca
  el estado (no se dice «ha acabado» por un fallo de la fuente).
- **`/avisos_actius` del bot, sin título**: un bloque por fuente con su
  nombre en negrita; «Avisos actius» encima era redundante, porque la orden
  ya dice qué es (Juanjo, 08-10-2026).
- **Sin aviso del Pla Alfa por Telegram**: es oficial, cambia a diario y en
  campaña saldría casi cada día; con el incendio cerca basta.

## Collserola, retirado el mismo día

La primera versión (3.21.0) leía también las restricciones de acceso a
Collserola de los avisos vigentes de la web del parque (API de WordPress,
categoría `avisos-ca`), las mostraba en una línea de «Si surts» y en
`/avisos_actius`, y avisaba al cerrarse o reabrirse. Juanjo vio en la web el
aviso del 12-03-2026 y preguntó cómo se retiraría: el parque pasa los avisos
a «caducats» a mano y a veces meses tarde (el de horarios de Navidad, el
16-03), y una reapertura anunciada con «s'aixequen les restriccions d'accés»
se habría tomado por otra restricción. Se buscó una fuente oficial: la tabla
de municipios de la página de la peste porcina del Departament d'Agricultura
(Cerdanyola, «Zona infectada d'alt risc», con la prohibición de entrar en
bosques, rieras, prados, campos y caminos fuera del núcleo urbano, y el
cierre del parque desde el 12-03-2026). Juanjo decidió quitar todo lo del
cierre de Collserola (3.21.2): ni los avisos del parque ni la tabla.

## Alternativas descartadas

- **Un botón nuevo en `/avisos`** («Incendis i Collserola»): Juanjo prefirió
  no alargar el menú.
- **Leer el HTML de la página de avisos del parque**: la API de WordPress da
  los mismos avisos con estructura y separa vigentes de caducados.
- **La API de la app de la AMB, la de Bombers con clave u otras privadas**:
  solo fuentes públicas sin clave.

## Riesgos

- Las capas de ArcGIS son las de los visores oficiales, no conjuntos de
  datos documentados: pueden cambiar sin aviso. Si fallan, la página no
  muestra esa parte y el error queda en los datos.

## Validación

- `tests/test_entorn.py`: incendios (solo forestales y en curso, distancia),
  Pla Alfa (el 5 no es nivel, capa vieja no vale) y los avisos (primera vez
  sin aviso, incendio al empezar y al acabar, fuente caída sin cambios);
  `tests/test_bot.py`: `/avisos_actius` sin título y el nombre corto.
- Datos reales el 08-10-2026: ningún incendio a menos de 5 km, Pla Alfa sin
  nivel (5 mañana, capa de hoy sin editar desde agosto).
- Web con datos de ejemplo (incendio a 3,2 km, Pla Alfa 4 y 3) en Chromium, Firefox y WebKit, escritorio, móvil y tableta, claro
  y oscuro, en catalán y castellano, y axe-core sin incidencias.
