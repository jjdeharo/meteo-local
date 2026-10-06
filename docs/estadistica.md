# Estadística de meteo-local

Cómo aprenden las páginas de lo que pasó de verdad. Lo hace un programa
normal en el NAS (`aprenentatge.py`), con numpy: **no interviene ninguna IA**
y no tiene coste. La decisión y su porqué están en el
[ADR 0012](adr/0012-aprendizaje-de-la-pagina-de-casa.md).

Estado a 06-10-2026: la página de casa calcula la probabilidad de lluvia con
lo aprendido del archivo y corrige la temperatura con lo aprendido de un año
de la estación de casa ([ADR 0017](adr/0017-estacion-de-casa-con-la-api-de-ecowitt.md)).
Cada hora guarda lo necesario para aprender de Montflorit y de casa. La
página del trayecto sigue con su regla; su aprendizaje es el paso siguiente
(apartado 7).

## 1. Qué se registra

En cada pasada, el NAS guarda en `/estat/registre/`:

- **Lo que midió Montflorit**, hora a hora (`montflorit.csv`): la lluvia de
  la hora y la temperatura y la humedad en la hora en punto. La estación
  solo ofrece las últimas 24 horas, así que lo que no se guarda se pierde.
- **Lo que midió la estación de casa**, hora a hora (`estacio-casa.csv`): la
  lluvia de la hora y la temperatura, la humedad, el punto de rocío, la
  presión y la radiación en la hora en punto. Ecowitt guarda su historial:
  cada día se rellenan las horas que falten. Su pluviómetro solo cuenta
  cuando marca lluvia (ADR 0017).
- **Lo que daban los modelos**, una vez por hora y para las 24 horas
  siguientes (`casa-AAAA-MM.jsonl`): la lluvia de los tres modelos finos
  (AROME HD, AROME e ICON-EU), la fracción de las 40 simulaciones de
  ICON-EU-EPS con lluvia, la temperatura, las nubes, el viento, la humedad,
  la radiación, la antelación, lo que medían las estaciones al prever y lo que
  mostró la página.

Al cruzar las dos cosas se obtiene, para cada hora prevista, qué se dijo y qué
pasó. Con eso se ajustan dos regresiones.

## 2. Lluvia: regresión logística

### Qué es

Una fórmula que convierte varias señales $x_1, \dots, x_k$ en una
probabilidad entre 0 y 1:

```math
p = \frac{1}{1 + e^{-(w_0 + w_1 x_1 + \dots + w_k x_k)}}
```

Cada señal $x_j$ tiene un peso $w_j$. **Los pesos se ajustan con los casos
reales**: son los que hacen más verosímil lo que pasó en las $n$ horas
registradas, con una penalización pequeña que evita pesos exagerados cuando
hay pocos datos. Si $y_i = 1$ cuando llovió en la hora $i$ y $y_i = 0$ cuando
no, y $p_i$ es la probabilidad que da la fórmula, se minimiza

```math
-\sum_{i=1}^{n} \left[ y_i \ln p_i + (1 - y_i) \ln (1 - p_i) \right]
+ \frac{\lambda}{2} \sum_{j=1}^{k} w_j^2, \qquad \lambda = 1,
```

con el método de Newton-Raphson. La constante $w_0$ no se penaliza.

«Llueve» quiere decir 0,2 mm o más en la hora, el umbral a partir del cual ya
moja en moto (`UMBRAL_MM` de `config.py`).

### Señales

| Señal | Cómo entra | Por qué |
|---|---|---|
| Lluvia de AROME HD, AROME e ICON-EU | $\ln(1 + \text{mm})$, una por modelo | Cada modelo acierta de forma distinta; el logaritmo evita que un chubasco extremo pese demasiado |
| Antelación | $\min(t / 24, 1)$, con $t$ en horas | Una previsión a 24 horas es menos segura que una a 2 |
| Hora del día | $\sin(2\pi h / 24)$ y $\cos(2\pi h / 24)$ | Las tormentas de tarde no se reparten igual que la lluvia de frente |
| Día del año | $\sin(2\pi d / 365{,}25)$ y $\cos(2\pi d / 365{,}25)$ | La lluvia de otoño no es la de verano |
| Fracción del ensemble* | de 0 a 1 | Cuántas de las 40 simulaciones ven lluvia |
| Lluvia medida al prever* | $\ln(1 + \text{mm de la última hora})$ si $t \le 4$; si no, 0. La mayor de Montflorit y casa | Si ya llueve, es probable que siga |
| Sequedad del aire al prever* | $\min(T - T_d, 15) / 10$ en casa si $t \le 4$; si no, 0 | Con el aire seco, la lluvia cercana es menos probable |

\* Solo con datos propios: el archivo no las tiene (apartado 2.2). $T_d$ es
el punto de rocío.

### 2.1 Primer modelo: el archivo de 2024-2026

Montflorit no tiene historial, así que el primer modelo se ajusta con lo que
sí lo tiene (`calibracio/pluja_casa.py`):

- previsiones archivadas de Open-Meteo para casa, del 01-01-2024 al
  04-10-2026, a corto plazo y hechas un día antes;
- lluvia medida cada media hora en Sabadell y Sant Cugat (portal de datos
  abiertos de la Generalitat), cada estación como una muestra.

Son 94.380 muestras (una por hora y estación), con lluvia en 3.622, el 4 %.

**Comprobación antes de usarlo.** Se ajustó sin los últimos 90 días
(06-07 a 04-10-2026) y se comparó en esos días con lo que mostraba la página
hasta ahora, la fracción del ensemble. Se mide con el error de Brier, la media
del cuadrado de la diferencia entre la probabilidad dada y lo que pasó:

```math
B = \frac{1}{n} \sum_{i=1}^{n} (p_i - y_i)^2
```

Menos es mejor.

| Método | Error de Brier |
|---|---|
| Frecuencia habitual de lluvia (siempre la misma probabilidad) | 0,0216 |
| Fracción del ensemble (lo que mostraba la página) | 0,0187 |
| **Regresión logística** | **0,0122** |

La regresión tiene un 35 % menos de error que el ensemble. Además, sus
probabilidades significan lo que dicen:

| Probabilidad dada | Horas | Media dada | Llovió |
|---|---|---|---|
| 0-5 % | 4.202 | 1 % | 1 % |
| 5-10 % | 32 | 7 % | 9 % |
| 10-20 % | 24 | 15 % | 21 % |
| 20-30 % | 16 | 24 % | 25 % |
| 30-50 % | 22 | 40 % | 32 % |
| 50-100 % | 72 | 88 % | 71 % |

Con el ensemble, en cambio, cuando daba entre el 30 y el 50 % llovió el 9 %
de las veces.

Después de comprobarlo, el modelo se ajustó con todos los datos. Sus pesos
están en `calibracio/pluja_casa.json`. El de más peso es ICON-EU (3,6, frente
a 1,1 y 1,2 de los AROME): cuando ICON-EU da lluvia en este punto, llueve con
más frecuencia que cuando la dan los otros.

### 2.2 Segundo modelo: los datos de Montflorit y de casa

Una hora cuenta como lluviosa si Montflorit recoge 0,2 mm o más o si los
recoge casa: el pluviómetro de casa a veces no marca la lluvia débil, pero lo
que marca es lluvia (ADR 0017). Sin dato de Montflorit, una hora seca en casa
no se usa.

Cuando el registro reúna **30 horas con lluvia**, se ajusta un modelo propio
con todas las señales de la tabla, incluidas las tres que el archivo no tiene. Sustituye al del archivo solo si acierta mejor en semanas
que no ha visto (apartado 4). En otoño llueve unas 25 horas al mes (entre 9 y 48 en
Sabadell y Sant Cugat desde 2024): puede tardar de uno a varios meses. Si al
prever falta la estación de casa, se usa el modelo del archivo.

### 2.3 Lo que aporta casa con su historial

Con la lluvia de casa de octubre de 2025 a agosto de 2026, cuando el
pluviómetro iba bien (297 horas con lluvia), se comprobó si las señales de
casa mejoran el modelo del archivo (`calibracio/estacio_casa.py`). El error
de Brier pasa de 0,02629 a 0,02657: solo mejora la primera hora
(de 0,0256 a 0,0247) y empeora a partir de la segunda. La presión y su
tendencia no mejoran en ninguna antelación. Por eso el modelo del archivo no
cambia: las señales de casa solo entran en el modelo propio, que se adopta si
demuestra que acierta más.

## 3. Temperatura: regresión lineal

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
ese momento, entre las dos horas en punto, menos la que mide casa. Se apaga con
la antelación $t$: una parte en unas tres horas y otra en un día. Los pesos
deciden cuánto cuenta cada una.

Los pesos $\mathbf{v}$ minimizan

```math
\sum_{i=1}^{n} \left( e_i - \mathbf{v}^\top \mathbf{z}_i \right)^2
+ \lambda \sum_{j \ge 1} v_j^2, \qquad \lambda = 1,
```

una regresión «ridge», con la misma penalización pequeña que en la lluvia. La
temperatura que se muestra es la del modelo menos el error esperado:

```math
T_{\text{mostrada}} = T_{\text{modelo}} - \mathbf{v}^\top \mathbf{z}
```

Se mide con el error medio absoluto, $\frac{1}{n} \sum_i |T_i - T_{\text{medida},i}|$.

### 3.1 Primer modelo: un año de la estación de casa

Ecowitt guarda un año de lecturas cada 30 minutos. Con ellas y las previsiones
archivadas de Open-Meteo para casa, a corto plazo y hechas un día antes, se
ajusta el primer modelo (`calibracio/estacio_casa.py`, pesos en
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
y se compara con el primero (apartado 4).

## 4. Cuándo se usa un modelo nuevo

Cada día a las 16:00, después de la verificación del trayecto, el NAS ejecuta
`aprenentatge.py diari`:

1. Vuelve a ajustar los dos modelos con todo lo registrado.
2. **Los comprueba en semanas que no ha visto** (validación cruzada: los días
   se reparten en cuatro grupos por semanas; cada grupo se predice con un
   modelo ajustado con los otros tres). Las semanas enteras evitan que dos
   días seguidos, muy parecidos, caigan uno en el ajuste y otro en la
   comprobación.
3. Lo compara con lo que se usa ahora con las mismas horas: el modelo del
   archivo para la lluvia; la corrección del año de casa para la temperatura.
4. **Solo cambia si el error baja al menos un 5 %**:
   $E_{\text{nuevo}} < 0{,}95 \, E_{\text{actual}}$. Un método nuevo se
   propone, se avisa por Telegram con las cifras y se aplica al día
   siguiente. Para pararlo, basta pedírselo a Claude, que crea el archivo
   `/estat/aprenentatge/atura`.
5. Si el método no cambia, los pesos se ponen al día con los datos nuevos sin
   avisar.
6. Si un modelo propio deja de mejorar, se propone volver al anterior, con el
   mismo aviso.

Cada día queda apuntado en `/estat/aprenentatge/historial.csv`: muestras,
horas de lluvia y errores de cada método. `python3 aprenentatge.py estat`
dice qué se usa y las últimas cifras.

## 5. Lo que la estadística no cambia

- **Lo medido manda sobre lo calculado.** Si ahora llueve en Montflorit o en
  casa, la primera hora es «Plou ara» con el 100 %. En las cuatro primeras horas, la
  persistencia de la lluvia medida (cuántas veces siguió lloviendo en Sabadell
  y Sant Cugat después de una hora parecida) sustituye a la probabilidad
  calculada si da más.
- **Los avisos de AEMET y los planes de Protección Civil** se muestran tal
  cual, encima de la tabla y en cada hora.
- **La cantidad de lluvia** sigue siendo la mayor de los tres modelos: la
  regresión da la probabilidad, no los milímetros.

## 6. Límites

- **La lluvia es rara**: un 4 % de las horas. Las cifras del archivo se
  apoyan en unas 3.600 horas con lluvia, pero la comprobación de los últimos
  90 días, en 95; tienen bastante margen de error.
- **El archivo no es Montflorit**: Sabadell y Sant Cugat están a 5-6 km. Un
  chubasco puede caer en un sitio y no en otro. Por eso el modelo propio lo
  sustituirá cuando acierte más.
- **El corto plazo del archivo es optimista**: une las primeras horas de
  cada pasada del modelo. La comprobación con previsiones hechas un día antes
  da un error de 0,0198, frente a 0,0216 de la frecuencia habitual: la
  mejora a 24 horas es pequeña. Los datos propios, con la antelación real de
  cada hora, lo medirán mejor.
- **La verdad de la temperatura es una estación de aficionado.** Coincide
  con Montflorit (casa da 0,4 °C menos de media en las primeras 36 horas
  comparadas),
  pero no se ha comprobado con días de sol fuerte en las dos.
- **El corto plazo del archivo de temperatura** también une las primeras
  horas de cada pasada: el error al prever puede parecer algo más útil de lo
  que es con la antelación real. El registro propio lo medirá.

## 7. Trayecto (pendiente)

La página del trayecto usará el mismo método de lluvia, la regresión
logística, con las señales que guarda su registro desde el 05-10-2026
(avisos, radar, estaciones, modelos y ensemble). Se ajustará cuando haya
bastantes días de lluvia en el trayecto, unos 14 al año en cada trayecto, con
la misma comprobación en semanas no vistas y el mismo aviso antes de cambiar.
La calibración de 2026 ya la probó solo con los modelos: mejoraba el error un
38 % en la ida, frente al 30 % de la regla ([ADR 0003](adr/0003-calibracion-con-datos-reales-se-mantiene-la-regla.md)).

## Dónde está cada cosa

| Archivo | Qué hace |
|---|---|
| `aprenentatge.py` | Rasgos, regresiones, validación y decisión diaria |
| `calibracio/pluja_casa.py` | Ajusta y comprueba el modelo de lluvia del archivo |
| `calibracio/pluja_casa.json` | Sus pesos y la comprobación |
| `calibracio/estacio_casa.py` | Ajusta la corrección de temperatura con el año de casa y comprueba las señales de casa para la lluvia |
| `calibracio/temperatura_casa.json` | Sus pesos y la comprobación |
| `ecowitt.py` | Lee la estación de casa |
| `casa.py` | Usa el modelo en la tabla y guarda las previsiones |
| `registre.py` | Guarda lo que miden Montflorit y casa |
| `tests/test_aprenentatge.py`, `tests/test_estacio_casa.py` | Pruebas, con un registro inventado |
