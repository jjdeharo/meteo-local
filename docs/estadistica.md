# Método y estadística de «Temps a Montflorit»

«Temps a Montflorit» (<https://meteo-montflorit.github.io/>) es una web del
tiempo para el barrio de Montflorit, en Cerdanyola del Vallès. Junta
previsiones de varios modelos, el radar, estaciones cercanas y los avisos
oficiales, y aprende de lo que pasa de verdad para que sus porcentajes
signifiquen lo que dicen.

Este documento explica con detalle cómo se calcula lo que muestra. Trata la
probabilidad y los milímetros de lluvia de cada hora, la temperatura, el uso
del radar en las dos primeras horas, los avisos, las recomendaciones de «Si
surts» y la calidad del aire. Está pensado para un lector con nociones de
estadística; la ayuda de la web lo cuenta sin fórmulas. Todo lo hace un
programa normal en un servidor doméstico, con numpy y sin coste. El
aprendizaje automático son regresiones estadísticas clásicas, ajustadas con
lo que ha pasado de verdad: **no interviene ninguna inteligencia artificial
generativa** ni ningún modelo de lenguaje. El último apartado, «Operación»,
recoge los detalles internos que solo necesita la persona que mantiene el
código.

El documento está en castellano. Las decisiones y su porqué están en los
registros de decisiones de arquitectura (ADR, siglas en inglés de
*Architecture Decision Record*) de la carpeta [`adr/`](adr/).

## Índice

1. [Qué se registra](#1-qué-se-registra)
2. [La probabilidad de lluvia: regresión logística](#2-la-probabilidad-de-lluvia-regresión-logística)
3. [La temperatura: regresión lineal](#3-la-temperatura-regresión-lineal)
4. [Las dos primeras horas: el radar llevado hacia delante](#4-las-dos-primeras-horas-el-radar-llevado-hacia-delante)
5. [La persistencia de la lluvia medida](#5-la-persistencia-de-la-lluvia-medida)
6. [Cómo se calcula cada hora de la tabla](#6-cómo-se-calcula-cada-hora-de-la-tabla)
7. [Cómo se dice en la página](#7-cómo-se-dice-en-la-página)
8. [Cuándo se usa un modelo nuevo](#8-cuándo-se-usa-un-modelo-nuevo)
9. [Cuándo para la lluvia](#9-cuándo-para-la-lluvia)
10. [Aviso antes de llover](#10-aviso-antes-de-llover)
11. [Situaciones de peligro](#11-situaciones-de-peligro)
12. [La riera de Sant Cugat](#12-la-riera-de-sant-cugat)
13. [Cuando los modelos no ven la lluvia](#13-cuando-los-modelos-no-ven-la-lluvia)
14. [Si surts](#14-si-surts)
15. [La calidad del aire](#15-la-calidad-del-aire)
16. [Límites](#16-límites)
17. [Operación](#17-operación)
18. [Dónde está cada cosa](#18-dónde-está-cada-cosa)

## 1. Qué se registra

Para aprender hace falta saber qué se dijo y qué pasó. Los modelos que se
usan llegan a través de Open-Meteo: AROME (*Applications of Research to
Operations at Mesoscale*) es el de Météo-France, a 1,5 km en su versión HD y
a 2,5 km en la normal, e ICON-EU (*ICOsahedral Nonhydrostatic*) es el del
servicio meteorológico alemán, a 7 km. En cada pasada, el servidor guarda:

- **Lo que midió la estación de Montflorit**, hora a hora: la lluvia de la
  hora y la temperatura y la humedad en la hora en punto. La estación solo
  ofrece las últimas 24 horas, así que lo que no se guarda se pierde.
- **Lo que midió una estación particular del barrio** («la estación de
  casa»), hora a hora: la lluvia de la hora y la temperatura, la humedad, el
  punto de rocío, la presión y la radiación en la hora en punto. Ecowitt, el
  fabricante, guarda su historial, y cada día se rellenan las horas que
  falten. Su pluviómetro solo cuenta cuando marca lluvia (ADR 0017).
- **Lo que daban los modelos**, una vez por hora y para las 24 horas
  siguientes: la lluvia de los tres modelos finos (AROME HD, AROME e ICON-EU),
  la fracción de las 40 simulaciones del conjunto ICON-EU-EPS con lluvia, la
  temperatura, las nubes, el viento, la humedad, la radiación, la antelación,
  lo que medían las estaciones al prever y lo que mostró la página. Desde el
  08-10-2026, también lo oficial de cada hora: si había aviso de la Agencia
  Estatal de Meteorología (AEMET) por lluvia o tormentas y si el plan de
  inundaciones de Protección Civil de Cataluña (INUNCAT) estaba en alerta o
  emergencia (ADR 0047).
- **El veredicto de lluvia de la moto en «Si surts»** (apartado 14).

Al cruzar lo previsto con lo medido se obtiene, para cada hora prevista, qué
se dijo y qué pasó. Con eso se ajustan dos regresiones, una para la lluvia y
otra para la temperatura.

## 2. La probabilidad de lluvia: regresión logística

### Qué es

Una fórmula que convierte varias señales $x_1, \dots, x_k$ en una
probabilidad entre 0 y 1:

```math
p = \frac{1}{1 + e^{-(w_0 + w_1 x_1 + \dots + w_k x_k)}}
```

Cada señal $x_j$ tiene un peso $w_j$. **Los pesos se ajustan con los casos
reales**: son los que hacen más verosímil lo que pasó en las $n$ horas
registradas, con una penalización pequeña que evita pesos exagerados cuando
hay pocos datos. Si $y_i = 1$ cuando llovió en la hora $i$ e $y_i = 0$ cuando
no, y $p_i$ es la probabilidad que da la fórmula, se minimiza

```math
-\sum_{i=1}^{n} \left[ y_i \ln p_i + (1 - y_i) \ln (1 - p_i) \right]
+ \frac{\lambda}{2} \sum_{j=1}^{k} w_j^2, \qquad \lambda = 1,
```

con el método de Newton-Raphson. La constante $w_0$ no se penaliza
(`aprenentatge.py`, `ajustar`).

«Llueve» quiere decir 0,2 mm o más en la hora, el umbral a partir del cual ya
moja en moto (`UMBRAL_MM` de `config.py`).

### Señales

| Señal | Cómo entra | Por qué |
|---|---|---|
| Lluvia de AROME HD, AROME e ICON-EU | $\ln(1 + \text{mm})$, una por modelo | Cada modelo acierta de forma distinta; el logaritmo evita que un chubasco extremo pese demasiado |
| Si cada modelo da lluvia | 1 si da 0,1 mm o más; si no, 0. Una por modelo | Que un modelo ponga algo de lluvia ya dice mucho, aunque sea poca: con solo ICON-EU dando 0,2 mm llovió una de cada diez horas |
| Cuántos modelos coinciden | 1 si dan lluvia dos o más; otra, 1 si la dan los tres | La coincidencia no suma sin más: con un modelo solo llovió el 21-23 % de las horas; con los tres, el 66 % |
| Lo anterior según la antelación | La cantidad de cada modelo, «alguno da lluvia» y «la dan los tres», multiplicados por la antelación | La lluvia prevista para dentro de un día se cumple menos que la de las próximas horas |
| Antelación | $\min(t / 24, 1)$, con $t$ en horas | Una previsión a 24 horas es menos segura que una a 2 |
| Hora del día | $\sin(2\pi h / 24)$ y $\cos(2\pi h / 24)$, con $h$ la hora en que acaba el tramo | Las tormentas de tarde no se reparten igual que la lluvia de frente |
| Día del año | $\sin(2\pi d / 365{,}25)$ y $\cos(2\pi d / 365{,}25)$ | La lluvia de otoño no es la de verano |
| Fracción del conjunto* | de 0 a 1 | Cuántas de las 40 simulaciones de ICON-EU-EPS ven lluvia |
| Lluvia medida al prever* | $\ln(1 + \text{mm de la última hora})$ si $t \le 4$; si no, 0. La mayor de Montflorit y casa | Si ya llueve, es probable que siga |
| Sequedad del aire al prever* | $\min(\max(T - T_d, 0), 15) / 10$ en casa si $t \le 4$; si no, 0 | Con el aire seco, la lluvia cercana es menos probable |
| Lluvia en Sant Cugat al prever*† | $\ln(1 + \text{mm de la última hora})$ en la estación de Meteocat de Sant Cugat (4,6 km al oeste, en la cuenca de la riera) si $t \le 4$; si no, 0 | Lo que llueve cerca puede llegar o anticipar. Es una hipótesis: se ajusta en una variante aparte y solo se adopta si acierta más (ADR 0042) |

\* Solo con datos propios: el archivo no las tiene (apartado 2.2). $T_d$ es
el punto de rocío. † Registrada desde el 08-10-2026. Meteocat es el Servei
Meteorològic de Catalunya.

### 2.1 Primer modelo: el archivo de 2024-2026

Montflorit no tiene historial, así que el primer modelo se ajusta con lo que
sí lo tiene (`calibracio/pluja_casa.py`):

- previsiones archivadas de Open-Meteo para el barrio, del 01-01-2024 al
  04-10-2026, a corto plazo y hechas un día antes;
- lluvia medida cada media hora en Sabadell y Sant Cugat (portal de datos
  abiertos de la Generalitat), cada estación como una muestra.

Son 94.380 muestras (una por hora y estación), con lluvia en 3.622, el 4 %.

**Comprobación antes de usarlo.** Se hace con todo el archivo, en semanas que
el modelo no ha visto: los días se reparten en cuatro grupos por semanas y
cada grupo se predice con un modelo ajustado con los otros tres
(apartado 8). Se mira por separado el corto plazo y la previsión hecha un día
antes. Se mide con el error de Brier, la media del cuadrado de la diferencia
entre la probabilidad dada y lo que pasó:

```math
B = \frac{1}{n} \sum_{i=1}^{n} (p_i - y_i)^2
```

Menos es mejor.

| Método | Corto plazo | Un día antes |
|---|---|---|
| Frecuencia habitual de lluvia (siempre la misma probabilidad) | 0,0368 | 0,0370 |
| Regresión solo con la cantidad de lluvia de cada modelo (hasta la versión 2.11) | 0,0251 | 0,0296 |
| **Regresión con las señales de la tabla** | **0,0225** | **0,0271** |

Más que el error importa la **fiabilidad**: que cuando la página dice un
15 % llueva el 15 % de las veces. A corto plazo (1.825 horas de lluvia):

| Probabilidad dada | Horas | Media dada | Llovió | Parte de toda la lluvia |
|---|---|---|---|---|
| 0-5 % | 42.327 | 0,6 % | 0,6 % | 13 % |
| 5-10 % | 1.049 | 8 % | 8 % | 5 % |
| 10-20 % | 1.736 | 14 % | 15 % | 15 % |
| 20-30 % | 713 | 24 % | 27 % | 10 % |
| 30-50 % | 817 | 40 % | 38 % | 17 % |
| 50-70 % | 538 | 59 % | 62 % | 18 % |
| 70-100 % | 496 | 82 % | 79 % | 22 % |

Con la previsión de un día antes (1.797 horas de lluvia):

| Probabilidad dada | Horas | Media dada | Llovió | Parte de toda la lluvia |
|---|---|---|---|---|
| 0-5 % | 41.538 | 1 % | 1 % | 24 % |
| 5-10 % | 642 | 8 % | 9 % | 3 % |
| 10-20 % | 1.983 | 15 % | 14 % | 16 % |
| 20-30 % | 1.012 | 24 % | 27 % | 15 % |
| 30-50 % | 879 | 39 % | 37 % | 18 % |
| 50-70 % | 456 | 59 % | 58 % | 15 % |
| 70-100 % | 194 | 79 % | 81 % | 9 % |

La última columna dice dónde cae la lluvia de verdad: **el 13 % de las horas
de lluvia a corto plazo, y el 24 % un día antes, llegan cuando la página daba
menos de un 5 %**. Es lluvia que ninguno de los tres modelos veía, y ninguna
fórmula hecha con ellos la recupera.

**Por qué se cambió la fórmula (06-10-2026).** La primera solo usaba la
cantidad de lluvia de cada modelo y se comprobó con los últimos 90 días, que
tenían 95 horas de lluvia: parecía fiable. Con todo el archivo no lo era:
cuando daba un 7 % llovió el 25 % de las horas; con un 14 %, el 33 %; con un
24 %, el 44 %, y cuando daba un 89 %, el 77 %. El logaritmo de los
milímetros casi no distingue 0 de 0,2 mm, y esa diferencia es la que más
cuenta. La comparación de entonces con la fracción del conjunto tampoco
valía: Open-Meteo solo conservaba simulaciones de 96 de las 4.368 muestras, y
las demás se contaron como «0 %» (ADR 0021).

Una prueba (`tests/test_aprenentatge.py`) falla si, al volver a ajustar, lo
dado y lo que llovió se separan más de 5 puntos en algún tramo con 150 horas
o más.

Después de comprobarlo, el modelo se ajusta con todos los datos. Sus pesos y
las dos tablas están en `calibracio/pluja_casa.json`.

### 2.2 Segundo modelo: los datos de Montflorit y de casa

Una hora cuenta como lluviosa si Montflorit recoge 0,2 mm o más o si los
recoge casa: el pluviómetro de casa a veces no marca la lluvia débil, pero lo
que marca es lluvia (ADR 0017). Sin dato de Montflorit, una hora seca en casa
no se usa.

Cuando el registro reúna **30 horas con lluvia** (horas observadas distintas:
cada hora se prevé muchas veces, con distintas antelaciones, y no cuenta más
por eso), se ajusta un modelo propio con todas las señales de la tabla,
incluidas las que el archivo no tiene. Sustituye al del archivo solo si
acierta mejor en semanas que no ha visto (apartado 8). En otoño llueve unas
25 horas al mes (entre 9 y 48 en Sabadell y Sant Cugat desde 2024): puede
tardar de uno a varios meses.

Si al prever falta alguna señal del modelo propio (por ejemplo, la estación
de casa), se usa el del archivo. Si tampoco se puede, porque falta la lluvia
de alguno de los tres modelos, la probabilidad es la fracción del conjunto
ICON-EU-EPS (apartado 6).

Se ajustan dos variantes, sin y con la lluvia de Sant Cugat. La variante
se valida solo con las muestras que llevan ese dato y, con esas mismas
muestras, se ajusta y valida otra vez el modelo sin él: un error medido en
horas distintas no se puede comparar (hasta el 09-10-2026 se comparaba con
el error del modelo base en todas las horas; ADR 0057). La variante se
adopta si mejora al modelo base en sus mismas horas en un 5 % como mínimo,
además de mejorar al archivo. Al prever, la lluvia de Sant Cugat es la de
la última media hora medida que usa la riera (apartado 12), si tiene menos
de 2 horas; sin ella, en las cuatro primeras horas se usa el modelo del
archivo. Cuando la variante llegue a las 30 horas de lluvia, se comunica
una sola vez el error de las dos a las mismas horas. Si la estación cercana
ayuda, se valorará añadir la del aeropuerto de Sabadell (5 km al norte),
que publica la AEMET (ADR 0042).

Una tercera variante añade lo oficial de cada hora (ADR 0047): $a$, 1 si hay
aviso de la AEMET por lluvia o tormentas en el Prelitoral de Barcelona, y
$c$, 1 si el INUNCAT está en alerta o emergencia. Así el peso de un aviso
sale de lo que pasa en Montflorit en lugar de fijarse a mano. Como se
registran desde el 08-10-2026, se valida solo con esas horas y se adopta con
las mismas condiciones que las otras.

### 2.3 Lo que aporta casa con su historial

Con la lluvia de casa de octubre de 2025 a agosto de 2026, cuando el
pluviómetro iba bien (297 horas con lluvia), se comprobó si las señales de
casa mejoran el modelo del archivo (`calibracio/estacio_casa.py`). El error
de Brier pasa de 0,0236 a 0,0241: solo mejora la primera hora (de 0,0227 a
0,0223) y empeora a partir de la segunda. La presión y su tendencia no
mejoran en ninguna antelación. Por eso el modelo del archivo no cambia: las
señales de casa solo entran en el modelo propio, que se adopta si demuestra
que acierta más.

Esta comprobación sirve además de contraste de la fórmula con una estación
que no se usó para ajustarla: con la lluvia de casa como verdad, el error del
modelo del archivo bajó de 0,0263 a 0,0236 al pasar a la fórmula del
apartado 2.1.

## 3. La temperatura: regresión lineal

La temperatura que da el modelo (AROME a 1,5 km) es la de una celda, no la de
casa. La diferencia suele repetirse: en casa, el modelo da de media 0,8 °C
más, y sobre todo de noche.

Se ajusta una regresión lineal del **error del modelo**,
$e = T_{\text{modelo}} - T_{\text{medida}}$, con la temperatura medida en la
estación de casa, a partir de unas señales $\mathbf{z}$:

| Señal | Cómo entra | Por qué |
|---|---|---|
| Temperatura prevista | en °C | El error no es el mismo con frío que con calor |
| Nubes y humedad previstas | de 0 a 1 | Las noches despejadas y secas enfrían más en casa que en la celda |
| Radiación prevista | en kW/m² | Con sol fuerte, el error de día cambia |
| Hora del día y día del año | seno y coseno | El error tiene ciclo diario y estacional |
| Antelación | $\min(t / 24, 1)$ | Cuanto más lejos, más incierto |
| Error al prever* | $e_0 \, e^{-t/3}$ y $e_0 \, e^{-t/24}$ | Si el modelo se equivoca ahora, en las horas siguientes suele equivocarse igual |

\* $e_0$ es el error del modelo en el momento de prever: su temperatura en
ese momento, interpolada entre las dos horas en punto, menos la que mide
casa. Se apaga con la antelación $t$: una parte en unas tres horas y otra en
un día. Los pesos deciden cuánto cuenta cada una.

Los pesos $\mathbf{v}$ minimizan

```math
\sum_{i=1}^{n} \left( e_i - \mathbf{v}^\top \mathbf{z}_i \right)^2
+ \lambda \sum_{j \ge 1} v_j^2, \qquad \lambda = 1,
```

una regresión *ridge*, con la misma penalización pequeña que en la lluvia
(`aprenentatge.py`, `ajustar_ridge`). La temperatura que se muestra es la del
modelo menos el error esperado:

```math
T_{\text{mostrada}} = T_{\text{modelo}} - \mathbf{v}^\top \mathbf{z}
```

La corrección se calcula para cada hora en punto, que es lo que se compara
con lo medido. Como la temperatura es la de un instante, cada tramo de la
tabla («de 18 a 19») muestra la media de sus dos extremos, los dos
corregidos:

```math
T_{18\text{–}19} = \tfrac{1}{2}\left(T_{\text{mostrada}}(18) + T_{\text{mostrada}}(19)\right)
```

Se mide con el error medio absoluto,
$\frac{1}{n} \sum_i \lvert T_i - T_{\text{medida},i} \rvert$.

### 3.1 Primer modelo: un año de la estación de casa

Ecowitt guarda un año de lecturas cada 30 minutos. Con ellas y las
previsiones archivadas de Open-Meteo, a corto plazo y hechas un día antes,
se ajusta el primer modelo (`calibracio/estacio_casa.py`, pesos en
`calibracio/temperatura_casa.json`): 43.099 horas de 364 días, del
08-10-2025 al 06-10-2026. Comprobado en semanas que no ha visto:

| Antelación | Modelo sin corregir | Corregida | Corregida sin el error al prever |
|---|---|---|---|
| 1 h | 1,44 °C | **0,77 °C** | 1,13 °C |
| 3 h | 1,45 °C | **1,04 °C** | 1,13 °C |
| 6 h | 1,45 °C | 1,14 °C | 1,13 °C |
| 24 h | 1,54 °C | **1,26 °C** | 1,29 °C |
| Todas | 1,46 °C | **1,03 °C** | 1,16 °C |

La corrección quita un 30 % del error, y en la hora siguiente casi la mitad.
Si la estación de casa falla al prever, se usan los pesos ajustados sin el
error al prever (última columna).

### 3.2 Segundo modelo: el registro propio

Con **14 días** registrados, cada día se ajusta el mismo modelo con lo que
se previó de verdad y lo que midió casa, con la antelación real de cada hora,
y se compara con el primero (apartado 8).

## 4. Las dos primeras horas: el radar llevado hacia delante

En las primeras horas, la lluvia que ya existe y cómo se mueve dicen más que
los modelos: el 05-10-2026 los modelos daban 0,3 mm por hora mientras caían
más de 20 (ADR 0019). Por eso, hasta dos horas, se usa también el radar
(`nowcast.py`). Es un cálculo fijo, no aprendido; lo único que se aprende es
qué radar usar (apartado 8).

### De color a lluvia

La imagen es la última del radar de Meteocat (cada 6 minutos; el radar de
Vallirana está a unos 20 km) o la de RainViewer, una composición de la
AEMET cada 10 minutos, si es bastante más nueva. Cada píxel se pasa a
reflectividad en dBZ (decibelios de reflectividad) con la leyenda de cada
radar, y de ahí a intensidad $R$ en mm/h con la relación de Marshall-Palmer:

```math
Z = 200\,R^{1{,}6}, \qquad Z = 10^{\text{dBZ}/10}
\quad\Longrightarrow\quad
R = \left(\frac{Z}{200}\right)^{1/1{,}6}
```

Se considera que llueve en un píxel desde $R \ge 0{,}5$ mm/h, unos 18 dBZ.

### El movimiento

Se usa el de la advección de Meteocat, su previsión a una hora calculada con
las tres últimas imágenes, si tiene menos de 60 minutos. Se mide el
desplazamiento entre su primera y su última imagen prevista, **en la lluvia
que hay a 60 km o menos de casa** (ADR 0023): la que puede llegar es esa, y
la de más lejos puede moverse de otra manera. Se busca la traslación
$\Delta$ que más hace coincidir las dos manchas de lluvia, con el índice de
Jaccard

```math
J(\Delta) = \frac{\left|A_{\Delta} \cap B\right|}{\left|A_{\Delta} \cup B\right|},
```

donde $A_{\Delta}$ son los píxeles con lluvia de la primera imagen
desplazados y $B$ los de la segunda. Solo se acepta si $J \ge 0{,}3$, si cada
imagen tiene al menos 50 píxeles con lluvia cerca y si el mejor salto no
queda en el borde de la búsqueda, que llega a 120 km/h como mucho.

Si no se cumple, el movimiento se mide en un cuadro de unos 300 km con la
correlación de fase de las dos imágenes $a$ y $b$, tomadas como
$\ln(1 + R)$ y con una ventana de Hann:

```math
c = \mathcal{F}^{-1}\!\left[\frac{\mathcal{F}(b)\,\overline{\mathcal{F}(a)}}{\left|\mathcal{F}(b)\,\overline{\mathcal{F}(a)}\right|}\right]
```

El desplazamiento es la posición del máximo de $c$, afinada con una parábola
en cada eje. Sin advección, se usan pares de imágenes de RainViewer separados
30 minutos, solo si los pares difieren menos de 20 km/h.

Con las imágenes de la tarde del 06-10-2026 (ADR 0023,
`calibracio/moviment_radar.py`), el error de la flecha a 60 minutos bajó de
16,3 km, midiendo en el cuadro de 300 km, a 8,0 km, midiendo en la lluvia de
cerca. En 97 puntos a menos de 55 km de casa, el error de Brier a 60 minutos
pasó de 0,184 a 0,126 (0,179 con la lluvia quieta).

### Hacia delante

Para cada lugar (casa y el centro de la cuenca de la riera) y cada 5 minutos
$t$, hasta 120, se mira la lluvia de ahora en el punto de donde vendrá,
$\mathbf{x} - \mathbf{v}\,t$, y en un círculo $\mathcal{C}_t$ alrededor, de
radio

```math
r(t) = 3 + 0{,}08\,t \ \text{km} \qquad (t \ \text{en minutos}),
```

que crece porque el movimiento es incierto. Cada píxel del círculo es un caso
posible:

```math
\hat R(t) = \frac{1}{\left|\mathcal{C}_t\right|}\sum_{j \in \mathcal{C}_t} R_j,
\qquad
p(t) = \frac{\left|\{\, j \in \mathcal{C}_t : R_j \ge 0{,}5 \,\}\right|}{\left|\mathcal{C}_t\right|}
```

La lluvia que nace o muere en ese tiempo no se ve: por eso solo dos horas, y
por eso el radar **nunca baja** lo que dan los modelos.

### En la tabla y en la tarjeta de ahora

Para una hora de la tabla, el radar da

```math
p_{\text{radar}} = \max_{t \in \text{hora}} p(t), \qquad
\text{mm}_{\text{radar}} = \sum_{t \in \text{hora}} \hat R(t) \cdot \frac{5}{60}
```

sobre los pasos de 5 minutos que caen en ella. Cómo se combina con lo demás
está en el apartado 6.

En la tarjeta de ahora, «Arribaria pluja cap a les…» es el primer paso con
$p(t) \ge 0{,}5$, la mitad del círculo con lluvia, y «Pot arribar pluja cap a
les…», el primero con $p(t) \ge 0{,}2$. La hora en que pararía está en el
apartado 9.

## 5. La persistencia de la lluvia medida

Si ya llueve, lo más probable es que siga lloviendo un rato, aunque los
modelos no lo vean. Con la lluvia cada media hora de Sabadell y Sant Cugat
entre 2024 y 2026 (`calibracio/analitza.py`, guardada en
`calibracio/calibracio.json`), se cuenta qué pasó después de cada hora con
lluvia. Para una clase $c$ de lluvia en una hora y $k$ horas después:

```math
P_k(c) = \frac{\#\{\, h : \text{mm}(h) \ge c,\ \text{mm}(h+k) \ge 0{,}2 \,\}}{\#\{\, h : \text{mm}(h) \ge c \,\}}
```

y la lluvia esperada es la mediana de $\text{mm}(h+k)$ en esas horas:

| Lluvia en la última hora | 1 h después | 2 h | 3 h | 4 h | Casos |
|---|---|---|---|---|---|
| 0,2 mm o más | 63 % (0,4 mm) | 48 % (0,1 mm) | 40 % (0 mm) | 34 % (0 mm) | 1.842 |
| 1 mm o más | 78 % (1,1 mm) | 56 % (0,3 mm) | 44 % (0,1 mm) | 38 % (0 mm) | 859 |
| 4 mm o más | 86 % (2,0 mm) | 57 % (0,4 mm) | 43 % (0 mm) | 38 % (0 mm) | 245 |

Se aplica con la lluvia de la última hora, la mayor de Montflorit y casa, a
las cuatro primeras filas de la tabla: la primera, la hora en curso, usa
$k = 1$.

## 6. Cómo se calcula cada hora de la tabla

Para cada hora, en este orden (`casa.py`, `previsio`):

1. **Probabilidad aprendida** con el modelo en uso (apartado 2). Si al
   modelo propio le falta una señal, se usa el del archivo; si tampoco se
   puede, porque falta la lluvia de algún modelo, la fracción de las 40
   simulaciones de ICON-EU-EPS con 0,2 mm o más.
2. **Milímetros**: el máximo de los tres modelos finos,
   $\text{mm} = \max(\text{AROME HD}, \text{AROME}, \text{ICON-EU})$; sin
   ninguno, el de Météo-France que Open-Meteo da por defecto. Un solo modelo
   puede fallar: la mañana del 05-10-2026 AROME daba 0,0 mm mientras en
   Montflorit caían más de 20 mm/h. **La regresión da la probabilidad, no los
   milímetros.**
3. **Temperatura** corregida (apartado 3), media de los dos extremos de la
   hora.
4. **Persistencia**, en las cuatro primeras horas: si en la última hora han
   caído 0,2 mm o más, la probabilidad y los milímetros suben a los del
   apartado 5, cada uno si es mayor. Estas cifras llevan «*».
5. **Radar**, en las dos primeras horas: la probabilidad sube a
   $p_{\text{radar}}$ si es mayor y llega al 20 %; los milímetros suben a
   $\text{mm}_{\text{radar}}$ si es mayor, llega a 0,2 mm y el radar cubre al
   menos 30 minutos de la hora. Nunca baja nada. Estas cifras llevan «†».
6. **Lo medido manda**: si ahora llueve en Montflorit (ha recogido lluvia en
   los últimos 15 minutos) o casa marca lluvia, la primera hora es «Plou ara»
   con el 100 %.

**Cuántas horas.** Desde la versión 3.40.0 (ADR 0041), la tabla llega a 24
horas como mínimo y hasta las 21 h de mañana. Acaba siempre al final de un
tramo del día, a las 7, las 14 o las 21 h, así que tiene entre 24 y 38 filas:
38 cuando se calcula a las 7 h. Más allá de 24 horas, la antelación del modelo de lluvia y
de la corrección de temperatura vale como un día, porque
$\min(t/24, 1) = 1$ (apartado 16). El registro con que se aprende y el riesgo
propio (apartado 11) usan solo las 24 primeras horas.

**Lo que no cambia la estadística.** Los avisos de la AEMET y los planes de
Protección Civil se muestran tal cual, encima de la tabla y en cada hora.

## 7. Cómo se dice en la página

**El cielo de cada hora** sale de la probabilidad (`web/casa.js`, `cel`):
«pluja» desde el 50 %, «possible pluja» desde el 20 %, y por debajo, solo las
nubes. Antes salía de los milímetros del modelo más lluvioso, y la tabla podía
decir «Pluja feble» con un 2 %. Con los nombres del manual de estilo de
Meteocat (ADR 0043):

- **Nubes**, por la fracción del cielo tapado: serè por debajo del 20 %, poc
  ennuvolat hasta el 45 %, mig ennuvolat hasta el 70 %, molt ennuvolat hasta
  el 85 % y cobert por encima. Si la lluvia de la hora llega a 0,2 mm, las
  nubes cuentan al menos como un 50 %, para que una hora con lluvia prevista
  no salga serena. De noche, la luna en lugar del sol.
- **Intensidad de la lluvia**, por los milímetros de la hora: feble,
  moderada desde 6 mm, forta desde 40 y torrencial desde 80. El manual da
  esos valores por media hora; aquí se usan por hora, el doble.
- **Nieve**: moderada desde 2 cm y forta desde 10.

**El resumen de cada tramo** (mañana de 7 a 14, tarde de 14 a 21 y noche de 21
a 7) va en la cabecera de cada desplegable. El cielo es la media de las nubes
de sus horas, o niebla si la hay en más de la mitad. Le siguen la temperatura
mínima y máxima y, solo si alguna hora llega al 20 %, el paraguas con la
probabilidad máxima y los milímetros sumados si llegan a 1. Solo cuando se
dan, y en color ámbar, se añaden tormenta, lluvia forta (40 mm en una hora) o torrencial (80),
rachas de 70 km/h, calor de 36 °C, helada (0 °C o menos) y nieve (0,1 cm o más
en el tramo). Las rachas y el calor son los umbrales amarillos del apartado
11 (ADR 0041).

## 8. Cuándo se usa un modelo nuevo

Cada día, a las 16:00, el servidor completa las horas que falten de la
estación de casa y ejecuta `aprenentatge.py diari`:

1. Vuelve a ajustar los dos modelos con todo lo registrado.
2. **Los comprueba en semanas que no ha visto** (validación cruzada: los días
   se reparten en cuatro grupos por semanas; cada grupo se predice con un
   modelo ajustado con los otros tres). Las semanas enteras evitan que dos
   días seguidos, muy parecidos, caigan uno en el ajuste y otro en la
   comprobación. El grupo lo fija la hora observada, no el momento en que se
   hizo la previsión: así todas las previsiones de una misma hora caen en el
   mismo grupo y ninguna observación se usa a la vez para ajustar y
   comprobar.
3. Lo compara con lo que se usa ahora con las mismas horas: el modelo del
   archivo para la lluvia; la corrección del año de casa para la
   temperatura. Las variantes de la lluvia (Sant Cugat, los avisos) se
   comparan además con el modelo sin su señal ajustado a sus mismas horas,
   y solo ganan si lo mejoran en la misma proporción (apartado 2).
4. **Solo cambia si el error baja al menos un 5 %**:
   $E_{\text{nuevo}} < 0{,}95 \, E_{\text{actual}}$. Un método nuevo se
   propone, se comunica con las cifras y se aplica al día siguiente, salvo
   que se pare antes (apartado 17).
5. Si el método no cambia, los pesos se ponen al día con los datos nuevos.
6. Si un modelo propio deja de mejorar, se propone volver al anterior, de la
   misma manera.

### Qué radar se usa

El mismo día se comparan también los dos radares (`radar_fonts.py`, ADR
0026). En cada pasada se apunta la probabilidad que daba cada uno para casa,
$p_M$ (Meteocat) y $p_R$ (RainViewer), con su última imagen y el mismo
movimiento, y si llovía en ese momento en Montflorit o en casa ($o = 1$ u
$o = 0$). Para cada hora prevista entre 10 y 60 minutos después de la
pasada, con una observación a menos de 4 minutos, se calcula la puntuación de
Brier de los últimos 30 días:

```math
B_M = \frac{1}{n}\sum_{i=1}^{n} (p_{M,i} - o_i)^2, \qquad
B_R = \frac{1}{n}\sum_{i=1}^{n} (p_{R,i} - o_i)^2
```

Cuanto más baja, mejor. Con al menos 30 casos con lluvia en 3 días
distintos, se cambia de radar si el otro cumple la misma regla del 5 %:
$B_{\text{otro}} < 0{,}95 \, B_{\text{actual}}$. Con RainViewer como
preferido, su imagen se usa en cuanto es 10 minutos más nueva que la de
Meteocat; con Meteocat, solo si lo es más de 15.

## 9. Cuándo para la lluvia

Cuando ya llueve, la tarjeta de ahora dice a qué hora pararía según el radar,
con la marca «en entrenament» (`fi_pluja.py`, ADR 0049). Con la serie $p(t)$
del apartado 4, el final previsto es el primer paso $t_k$, desde ahora o desde
que llegue la lluvia, en que la probabilidad queda por debajo de un umbral
$u$ durante $s$ pasos seguidos de 5 minutos:

```math
t_{\text{fi}} = \min\left\{\, t_k \ge t_0 :\ p(t_{k+m}) < u \ \text{para}\ m = 0, \dots, s-1 \,\right\}
```

Si no pasa en las dos horas del radar, «no s'acaba en 2 hores». La regla de
partida es $u = 0{,}2$ y $s = 3$, es decir, menos del 20 % durante 15
minutos.

**Qué es la verdad.** La lluvia de Montflorit cada 5 minutos: un episodio son
los tramos con lluvia separados por menos de 30 minutos secos, y su final, el
último tramo con lluvia. Se juzgan las pasadas registradas mientras llovía,
con el radar que usaba la página. El error de una pasada es
$\lvert t_{\text{fi}} - t_{\text{real}} \rvert$ en minutos. Si la regla no da
final, el error es cero cuando el final real cae más allá del horizonte del
radar y, si no, lo que faltaba hasta el horizonte. Un acierto es un error de
15 minutos o menos.

**Cómo aprende.** Cada día se prueban las nueve combinaciones de
$u \in \{0{,}1;\ 0{,}2;\ 0{,}3\}$ y $s \in \{2, 3, 4\}$ con todos los
episodios registrados. Con tres episodios o más, si la mejor tiene un error
medio al menos un 5 % menor que la que se usa, pasa a usarse. Con cinco
episodios, el resultado se comunica una vez, para decidir si se sigue
mostrando «en entrenament».

**Limitaciones conocidas.** La regla se elige y se mide con los mismos
episodios. Con pocos episodios y nueve combinaciones, la elegida puede ganar
por azar, y su error es optimista. Además, a diferencia del aprendizaje de la
lluvia y la temperatura (apartado 8), el cambio se aplica el mismo día, sin
propuesta previa. Mientras haya pocos episodios, la cifra de error conviene
leerla con esa reserva; una validación que deje fuera cada episodio al
juzgarlo la haría comparable con el resto.

## 10. Aviso antes de llover

Tras cada pasada se mira cuántos minutos faltan para la llegada que da el
radar, el primer paso con $p(t) \ge 0{,}5$ (`pluja_arriba.py`, ADR 0022). Si
faltan 21 o menos (15 minutos más el intervalo de 6 del modo aviso) y aún no
llueve en Montflorit ni en casa, se avisa a los suscriptores (ADR 0048). La
intensidad que se anuncia es el máximo de $\hat R$ en los 30 minutos
siguientes a la llegada: feble por debajo de 1 mm/h, moderada desde 1 y forta
desde 4.

Los avisos van por episodios: uno empieza cuando el radar anuncia la lluvia o
cuando empieza a llover, y acaba tras 60 minutos sin lluvia medida ni
anunciada. En cada episodio hay un aviso como mucho. Al acabar se apunta qué
pasó: acierto si llovió en los 45 minutos siguientes al aviso, «avís sense
pluja» si no, y «pluja sense avís» si llovió sin aviso.

## 11. Situaciones de peligro

Lo medido en las estaciones y la previsión de las 24 primeras horas se
comparan con los umbrales del Plan Meteoalerta de la AEMET (anexo 1, versión
del 31-05-2022) para el Prelitoral de Barcelona (`riscos.py`,
`RISC_LLINDARS` de `config.py`, ADR 0018):

| Fenómeno | Amarillo | Naranja | Rojo |
|---|---|---|---|
| Lluvia en 1 hora | 20 mm | 40 mm | 90 mm |
| Lluvia en 12 horas | 60 mm | 100 mm | 180 mm |
| Racha | 70 km/h | 90 km/h | 130 km/h |
| Calor | 36 °C | 39 °C | 42 °C |
| Frío | −4 °C | −8 °C | −12 °C |
| Nieve en 24 horas | 2 cm | 5 cm | 20 cm |

La lluvia de 12 horas es la ventana de 12 horas seguidas que más acumula.
Para cada fenómeno se da el peor valor y el tramo de horas seguidas en que
ocurre. Un riesgo se da por acabado tras 3 horas sin verlo, para que el
vaivén de los modelos entre pasadas no repita el aviso. No sustituye a los
avisos de la AEMET, que se muestran aparte.

## 12. La riera de Sant Cugat

La riera nace en Collserola, en la zona de Les Planes, cruza Sant Cugat y
pasa por Montflorit, donde se desbordó el 29-09-2026 y el 04-10-2026 con el
agua dentro de las casas. Su cuenca es pequeña (unos 50 km²) y responde
enseguida: las tres veces conocidas se desbordó al acabar las tres horas más
lluviosas (`riera.py`, ADR 0027). Es la parte más delicada de la web, y por
eso se explica entera: qué se mide, cómo se calcula el índice, de dónde
salen los umbrales, qué habría avisado en el pasado y cómo llega el aviso.

### 12.1 Qué se mide

La Agència Catalana de l'Aigua no mide el nivel de la riera: su aforo más
cercano está en el Ripoll, en Montcada, aguas abajo. Solo queda la lluvia.
Decide la de la estación de Meteocat de Sant Cugat (CAR, código XV), en
medio de la cuenca, por medias horas y unos 30 minutos por detrás, leída en
la web de meteo.cat o, si falla, en el portal de datos abiertos de la
Generalitat. Se guardan y se dicen en el aviso, pero no deciden, la del
Observatori Fabra (D5), en la cresta de Collserola junto a donde nace la
riera, y la de Montflorit, en la parte baja: aún no hay historial para saber
qué umbral les corresponde. A lo medido se suma lo que el radar lleva hacia
delante sobre el centro de la cuenca (apartado 4), que cubre también la
media hora que la estación va por detrás.

### 12.2 El índice

El índice es la lluvia de tres horas más alta que se alcanzará en la hora
siguiente, y la de seis horas del mismo momento:

```math
I_3(k) = M_{3-k} + P_k, \qquad I_6(k) = M_{6-k} + P_k, \qquad k \in \{0;\ 0{,}5;\ 1\}
```

donde $M_h$ es la lluvia medida en las últimas $h$ horas y $P_k$ la prevista
por el radar para las $k$ horas siguientes, contando también el hueco entre
la última media hora medida y la imagen del radar. Para cada momento $k$ se
aplica la tabla a la pareja $(I_3(k), I_6(k))$ y el nivel de la pasada es
el más alto que alcanza algún momento; el índice que se publica es el de
ese momento (entre varios, el de más lluvia de 3 horas). Hasta el
09-10-2026 se tomaban el máximo de $I_3$ y el máximo de $I_6$ por separado,
de momentos distintos, y 50 mm sobre suelo seco ahora con 60 en 6 horas
una hora después daban peligro sin que ningún momento cumpliera las dos
condiciones (ADR 0057).

| Nivel | Condición, en un mismo momento $k$ |
|---|---|
| Se registra el episodio | $I_3 \ge 20$ mm |
| Atención: aviso | $I_3 \ge 35$ mm |
| Peligro: segundo aviso | $I_3 \ge 50$ mm y $I_6 \ge 60$ mm |

Cada nivel se avisa una sola vez por episodio, y un episodio acaba tras 3
horas por debajo de 20 mm; al acabar se apunta en el registro con sus
máximos. Si a la ventana de 3 horas le falta más de una media hora medida,
o a la de 6 más de dos, el índice se da por incompleto: un hueco cuenta
como cero y no se puede decir que el riesgo haya bajado.

### 12.3 De dónde salen los umbrales

De cuatro casos, con la lluvia de Sant Cugat (XV) y del Fabra (D5) del
portal de datos abiertos de la Generalitat (conjunto `nzvn-apee`), por
medias horas:

| Día | Qué pasó | XV, 3 h | XV, 6 h | D5, 3 h | Fin de las 3 h más lluviosas |
|---|---|---:|---:|---:|---|
| 29-04-2024 | El agua llegó a la puerta de las casas | 53 | 75 | 22 | 20:30 |
| 29-09-2026 | Entró en las casas | 67 | 67 | 76 | 12:30 |
| 04-10-2026 | Entró en las casas, entre la 1 y las 2 | 67 | 104 | 43 | 02:00 |
| 13-09-2025 | **No se desbordó** | 52 | 52 | 17 | 17:30 |

Lo que separa el 13-09-2025 de los desbordamientos es la lluvia de antes:
fue un chaparrón de 3 horas sobre suelo seco, con poca lluvia en Collserola
(18 mm en 24 horas en el Fabra, frente a 64 o más), y los tres
desbordamientos tenían 67 mm o más en 6 horas. De ahí la segunda condición
del peligro. Del 11-05-2025 (48 mm en 3 horas) y del 06-11-2025 (38) no
hay fotos; con la regla, ninguno de los dos daría peligro. En los tres
desbordamientos el agua llegó al acabar las 3 horas más lluviosas.

### 12.4 Qué habría avisado desde 2013

Con la lluvia medida cada media hora desde 2013, con los 30 minutos de
retraso de la tabla de meteo.cat y sin radar, porque no hay archivo de
imágenes, la regla da 51 episodios de 20 mm o más, 13 avisos de atención y
5 de peligro en 13 años: el 28-09-2014, el 15-11-2018, el 29-04-2024, el
29-09-2026 y el 04-10-2026. De los dos primeros no se sabe si hubo
desbordamiento. Con solo la condición de 3 horas habrían sido 7.

El margen, en los tres casos conocidos: la atención habría llegado a las
20:00 el 29-04-2024 (30 minutos antes de que el agua llegara a las
puertas), a las 12:00 el 29-09-2026 (con el desbordamiento ya en marcha) y a
las 0:30 el 04-10-2026 (de 30 a 90 minutos antes); el peligro, siempre
después. Con la hora siguiente conocida, que es lo que aporta el radar
cuando acierta, la atención habría llegado a las 18:30, a las 10:30 y a las
23:00: de 1 a 3 horas antes. El radar real queda entre los dos extremos.

### 12.5 Cómo llega el aviso

El aviso de atención y el de peligro van a todo el mundo igual: al canal de
Telegram, a cada persona que lo ha elegido en el bot y a las notificaciones
del navegador (ADR 0034 y 0048), con la lluvia de Sant Cugat, del Fabra y
de Montflorit y lo que el radar prevé para la hora siguiente. Al cerrarse el
episodio llega un solo mensaje de final (ADR 0027). La web pública no
muestra el índice: solo los avisos. Los textos dicen que el aviso está en
pruebas y no es oficial, y que mandan siempre las indicaciones de Protección
Civil.

**Limitación conocida.** Los umbrales son una hipótesis basada en cuatro
casos. Cada episodio se guarda con sus máximos para ajustarlos con lo que
pase; ese ajuste no es automático. Hasta el 09-10-2026 no se ha visto
ningún aviso real.

## 13. Cuando los modelos no ven la lluvia

En cada pasada se suman la lluvia medida en Montflorit en las tres últimas
horas completas, $M$, y la que daban los modelos en esas horas, $P$ (el
máximo de los tres, hora a hora). Si

```math
M \ge 3 \ \text{mm} \quad \text{y} \quad M > 3P + 1,
```

la página avisa de que los modelos no ven esta lluvia: las primeras horas de
la tabla parten de lo que mide la estación (apartados 5 y 6), y para el resto
conviene hacer más caso de los avisos (`casa.py`, `comprobacion_modelos`).

## 14. Si surts

«Si surts» dice, para una hora de salida y otra de vuelta, cómo irá cada
medio de transporte, qué ropa conviene y algunos consejos (ADR 0029). Los
umbrales están en `web/sortir.js`.

### La lluvia en moto y en bici

Desde el 08-10-2026 (ADR 0047), en moto y en bici decide **solo la
probabilidad** $p$ de cada hora, la de la tabla, que ya reúne los modelos, el
conjunto de simulaciones, el radar, las estaciones y lo aprendido. Para la
hora de ida y la de vuelta:

```math
\text{nivel} =
\begin{cases}
\text{millor no} & \text{si } p \ge 0{,}40 \text{ o llueve ahora} \\
\text{compte} & \text{si } p \ge 0{,}10 \text{ o hay aviso de la AEMET} \\
\text{bé} & \text{en otro caso}
\end{cases}
```

El nivel del viaje es el peor de las dos horas. Sin probabilidad, se usa la
lluvia del modelo más lluvioso: 1 mm, «millor no»; 0,2 mm, «compte».

Antes mandaba también la lluvia del modelo más lluvioso (1 mm, «millor no»;
0,2 mm, «compte») junto a una probabilidad del 50 % y del 20 %, y un aviso de
la AEMET solo daba «millor no». El 08-10-2026 eso desaconsejó la moto a las
10 y a las 17 h por el aviso amarillo y por 1,7 mm de ICON-EU (los dos AROME
daban 0 y la probabilidad, un 25 %), y no llovió.

**Comprobación con el archivo.** `calibracio/regla_moto.py` aplica las dos
reglas a cada hora del archivo (01-01-2024 a 05-10-2026), con la probabilidad
del modelo del archivo ajustado sin la semana que se juzga, y a un viaje de
cada día a las 10 y a las 17 h. La verdad es 0,2 mm o más en Sabadell o Sant
Cugat. Viaje con la previsión a corto plazo (992 días, 80 con lluvia):

| Regla | Días secos con «no» | Días secos con «compte» | Días de lluvia con «bé» | con «compte» | con «no» |
|---|---|---|---|---|---|
| Antes (50 % o 1 mm; 20 % o 0,2 mm) | 25 | 53 | 14 | 22 | 44 |
| Solo la probabilidad, 50 % y 20 % | 8 | 34 | 23 | 27 | 30 |
| **Solo la probabilidad, 40 % y 10 %** | **11** | 72 | **13** | 26 | 41 |

Con la previsión de un día antes (971 días, 78 con lluvia), la elegida da 14
días secos con «no» (antes, 21) y 17 de lluvia con «bé» (antes, 22). Quitar
los milímetros con los umbrales de siempre reducía las falsas alarmas, pero
dejaba sin aviso nueve días más de lluvia: por eso se bajaron los umbrales.
El precio es recomendar el impermeable unos 19 días secos más de cada 900. El
archivo no tiene avisos de la AEMET, radar ni conjunto de simulaciones: esas
partes no están comprobadas.

**Comprobación con lo que pasa.** Cada día se apunta, de cada hora pasada de 6
a 22 h con lluvia medida, qué nivel daba la regla nueva y cuál la de antes,
con dos antelaciones: al salir (la previsión más reciente de 1 a 3 horas
antes) y la vuelta decidida por la mañana (de 6 a 10 horas antes). A los 28
días se comunica una vez el número de horas secas con «no» y con «compte» y
el de horas de lluvia con «bé» de las dos reglas.

### Los demás medios

Estos umbrales son de criterio, no ajustados con datos:

- **Coche**: «millor no» con 40 mm o más en una hora y «compte» con 20 (los
  umbrales naranja y amarillo de la AEMET); con lluvia probable (50 % o más,
  1 mm, lluvia ahora o aviso de la AEMET), también «compte».
- **A pie**: «compte» si alguna hora fuera de casa tiene un 20 % o más, 0,2
  mm, lluvia ahora o aviso de la AEMET por lluvia o tormentas.
- **Viento y frío**, como pares [«compte», «millor no»]: rachas en bici de
  40 y 50 km/h, en moto de 50 y 70, en coche «compte» desde 90 y a pie
  «millor no» desde 70; frío en bici y en moto de 3 y 1 °C, y en coche
  «compte» desde 1 °C.
- **Transporte público**: el estado de los trenes de Cerdanyola en tiempo
  real, sin umbrales meteorológicos.

### La ropa

La ropa sale del frío que se nota. Con 10 °C o menos y una velocidad
$v \ge 5$ km/h, se usa el índice de enfriamiento por viento de Environment
Canada:

```math
T_s = 13{,}12 + 0{,}6215\,T - 11{,}37\,v^{0{,}16} + 0{,}3965\,T\,v^{0{,}16}
```

con $T$ en °C y $v$ en km/h. La velocidad es la del medio (bici 18 km/h,
moto 45) y, a pie o hasta el coche o la estación, el viento previsto. La
prenda sale de $T_s$ por tramos. Además se avisa de un cambio de temperatura
de 6 °C o más entre la ida y la vuelta, del calor desde 32 °C y de la
protección solar con un índice ultravioleta (UV) de 3 o más.

## 15. La calidad del aire

El índice sale del modelo europeo del servicio de vigilancia atmosférica de
Copernicus (CAMS, *Copernicus Atmosphere Monitoring Service*), que sirve
Open-Meteo en celdas de 0,1°, unos 11 × 8 km aquí (`aire.py`, ADR 0054). La
celda de Montflorit tiene el centro en Bellaterra: **es una estimación de
zona, no una medida del barrio**.

Cada día se corrige con las estaciones de la red de vigilancia de la
contaminación atmosférica de la Generalitat (XVPCA) de Barberà, Sant Cugat y
Montcada. Para cada contaminante $c$, con las horas de los últimos 30 días
que tienen a la vez modelo y medida:

```math
f_c = \frac{\sum_t \bar m_{c,t}}{\sum_t \hat m_{c,t}}
```

donde $\bar m_{c,t}$ es la media de las estaciones que lo miden en la hora
$t$ y $\hat m_{c,t}$ lo que daba el modelo. Solo se corrige con 72 horas
emparejadas o más y si lo miden al menos dos estaciones. Las partículas de
menos de 10 micras (PM10) solo las mide Montcada, junto a la cementera, y
su factor diría más de Montcada que de Montflorit. El 09-10-2026 se corregían el dióxido de
nitrógeno (NO₂), ×0,70, y el ozono, ×0,71, con 725 horas.

Las concentraciones del modelo se multiplican por $f_c$ y el índice europeo
de calidad del aire (EAQI, *European Air Quality Index*) se recalcula
interpolando dentro del tramo de cada contaminante, con la tabla que publica
Open-Meteo; el total es el del peor contaminante.

**Limitaciones conocidas.** Es un factor único para todas las horas del día, y
no se ha comprobado, en días que no se usaron para calcularlo, que el índice
corregido acierte más que el modelo sin corregir. Las medidas de la red se
publican con 7 u 8 horas de retraso, por eso no se muestran en la página.

## 16. Límites

- **La lluvia es rara**: un 4 % de las horas. Las cifras del archivo se
  apoyan en unas 3.600 horas con lluvia; los tramos de la tabla de fiabilidad
  con pocos cientos de horas tienen un margen de unos 3 puntos.
- **Una de cada ocho horas de lluvia a corto plazo, y una de cada cuatro un
  día antes, llega con menos de un 5 %** (apartado 2.1): un porcentaje bajo
  no es un cero.
- **El archivo no es Montflorit**: Sabadell y Sant Cugat están a 5-6 km. Un
  chubasco puede caer en un sitio y no en otro. Por eso el modelo propio lo
  sustituirá cuando acierte más.
- **El corto plazo del archivo es optimista**: une las primeras horas de cada
  pasada del modelo. Con previsiones hechas un día antes el error sube de
  0,0225 a 0,0271, y las probabilidades altas casi desaparecen (194 horas por
  encima del 70 %, frente a 496). El archivo solo tiene esas dos antelaciones:
  entre una y otra, la fórmula interpola. Los datos propios, con la antelación
  real de cada hora, lo medirán mejor.
- **Más allá de 24 horas**, desde la versión 3.40.0, la antelación vale como
  un día ($\min(t/24, 1) = 1$): de 24 a 38 horas, la lluvia y la temperatura
  se calculan con una fórmula que no se ha comprobado a esa distancia. AROME,
  además, puede no llegar a las últimas horas: la lluvia sale entonces de los
  otros modelos y, sin la de alguno, la probabilidad es la fracción del
  conjunto. La nota de la tabla lo advierte.
- **La verdad de la temperatura es una estación de aficionado.** Coincide con
  Montflorit (casa da 0,4 °C menos de media en las primeras 36 horas
  comparadas), pero no se ha comprobado con días de sol fuerte en las dos.
- **El corto plazo del archivo de temperatura** también une las primeras horas
  de cada pasada: el error al prever puede parecer algo más útil de lo que es
  con la antelación real. El registro propio lo medirá.
- **El radar no ve la lluvia que nace** en las dos horas siguientes, y su
  círculo y su umbral del 50 % no se han ajustado con datos propios; el
  registro de avisos de lluvia (apartado 10) lo dirá.
- **Limitaciones de método** ya descritas: el final de la lluvia se elige y
  se mide con los mismos episodios (apartado 9), los umbrales de la riera
  salen de cuatro casos (apartado 12) y la corrección del aire no se ha
  comprobado fuera de los datos con que se calcula (apartado 15).

## 17. Operación

Detalles internos para la persona que mantiene el código.

**Dónde se guarda.** En el servidor doméstico (un NAS, *Network Attached
Storage*), en `/estat/registre/`: `montflorit.csv` y `estacio-casa.csv` (lo
medido hora a hora), `montflorit-5min.csv` (la lluvia de Montflorit cada 5
minutos), `casa-AAAA-MM.jsonl` (lo previsto), `radar-fonts-*.jsonl` (lo que
daba cada radar), `moto.csv` (la regla de la moto), `avisos-pluja.csv`
(episodios del aviso de lluvia) y `riera.csv` (episodios de la riera). Los
modelos aprendidos, en `/estat/aprenentatge/`: `model.json`, `proposat.json`,
`fi-pluja.json` y `historial.csv`, con las muestras, las horas de lluvia y
los errores de cada método día a día.

**Cuándo se ejecuta.** A las 16:00 (`HORA_VERIFICACION` de `config.py`) el
reloj del NAS (`nas/reloj.sh`) completa la estación de casa con
`registre.py estacio` y ejecuta `aprenentatge.py diari`, que además compara
los radares, juzga el final de la lluvia y apunta la regla de la moto.

**Avisos al responsable.** Llegan a Juanjo por Telegram:

- cada cambio de método propuesto, con las cifras;
- el resultado de la variante con Sant Cugat, a las 30 horas de lluvia;
- el del final de la lluvia, a los 5 episodios, y el de la moto, a los 28 días;
- cada cambio de radar o de regla del final de la lluvia.

**Parar un cambio.** El archivo `/estat/aprenentatge/atura` detiene la
aplicación de una propuesta, los cambios de radar y los de regla del final de
la lluvia.

**Consultas.** `python3 aprenentatge.py estat` (qué se usa y las últimas
cifras), `python3 aprenentatge.py moto`, `python3 fi_pluja.py resum`,
`python3 pluja_arriba.py resum` y `python3 riera.py resum`.

**El pluviómetro de casa** (`pluviometre.py`, ADR 0017). Su cero no es
fiable: solo cuenta cuando marca lluvia. Tras limpiarlo, una vigilancia de una
sola vez compara cada episodio débil de Montflorit (de 0,6 a 4 mm, con dos
horas secas como mucho entre medias) con casa: cuenta como detectado si casa
marca algo en él o en la hora de antes o de después. Con tres episodios
débiles, o a los 45 días, se comunica el resultado para decidir si la página
vuelve a fiarse de su cero.

## 18. Dónde está cada cosa

| Archivo | Qué hace |
|---|---|
| `aprenentatge.py` | Señales, regresiones, validación y decisión diaria; veredicto de la moto y lo que pasó |
| `casa.py` | Calcula cada hora de la tabla (apartado 6) y guarda las previsiones |
| `nowcast.py` | El radar llevado hacia delante |
| `radar_fonts.py` | Compara los dos radares |
| `fi_pluja.py` | La hora en que para la lluvia y su aprendizaje |
| `pluja_arriba.py` | El registro del aviso antes de llover |
| `riscos.py` | Las situaciones de peligro con los umbrales de la AEMET |
| `riera.py` | El índice de la riera |
| `aire.py` | La calidad del aire y su corrección |
| `web/casa.js`, `web/sortir.js` | Cómo se dice en la página y las reglas de «Si surts» |
| `calibracio/pluja_casa.py`, `calibracio/pluja_casa.json` | Ajusta y comprueba el modelo de lluvia del archivo; sus pesos y la comprobación |
| `calibracio/estacio_casa.py`, `calibracio/temperatura_casa.json` | Ajusta la corrección de temperatura con el año de casa y comprueba las señales de casa para la lluvia; sus pesos |
| `calibracio/analitza.py`, `calibracio/calibracio.json` | La persistencia de la lluvia |
| `calibracio/regla_moto.py` | Compara con el archivo las reglas de lluvia de la moto |
| `calibracio/moviment_radar.py` | Comprueba de dónde medir el movimiento del radar |
| `ecowitt.py`, `registre.py`, `pluviometre.py` | Leen y guardan lo que miden Montflorit y casa; vigilan el pluviómetro |
| `tests/test_aprenentatge.py`, `tests/test_estacio_casa.py` | Pruebas, con un registro inventado |
