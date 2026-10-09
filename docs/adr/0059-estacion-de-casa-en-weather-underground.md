# 59. La estación de casa en Weather Underground, para leer las de los vecinos

Fecha: 2026-10-09 · Estado: aceptado

## Contexto

Sin la estación de meteocerdanyola.com (ADR 0058), «¿llueve ahora?» depende
de un solo pluviómetro. Juanjo pidió buscar si las estaciones particulares
del barrio «emiten en abierto» por otra red. En Weather Underground hay dos
a 400 y 600 m (ICERDA28 e ICERDA48, Bresser 5 en 1, con pluviómetro, que
actualizan cada pocos segundos) y The Weather Company da una clave de API
gratuita a quien aporta una estación a su red: con ella se leen las
observaciones actuales y recientes de cualquier estación personal (unas
1.500 llamadas al día). Es su API, con su clave y con el consentimiento de
quien publica su estación ahí; nada que ver con el scraping que prohíben
Weathercloud y Meteoclimatic.

Juanjo dio de alta su estación (ICERDA50, «Montflorit Riera») el 09-10-2026
y, al no encontrar en la app de Ecowitt la pantalla de subida a Weather
Underground, pidió que la subiera el NAS («hazlo por el nas, tengo prisa»).

## Decisión

- **En cada pasada de la página** (cada 15 minutos; 6 en modo aviso),
  `casa.py` manda a Weather Underground la lectura de Ecowitt que ya tiene
  (`wunderground.py`): temperatura, humedad, punto de rocío, presión al
  nivel del mar, lluvia de la última hora y del día, radiación y UV. El
  viento no: el anemómetro no funciona bien (ADR 0017). Un programa normal,
  sin IA ni coste: una petición HTTP más por pasada.
- **Las claves** (`WU_STATION_ID`, `WU_STATION_KEY`) van en
  `~/.config/meteo-local/wunderground.env` del NAS, como las de Ecowitt, y
  en el paquete cifrado del repositorio privado (`RESTAURAR.md`). Sin ellas,
  no se sube nada; el resto de la pasada sigue igual.
- **Si la subida falla**, no es un error de la página: se apunta en el
  registro del NAS y no sale en la web (cada página solo avisa de lo que
  usa, ADR 0031).
- **Lo que viene después**, cuando Juanjo genere la clave de lectura: leer
  ICERDA28 (e ICERDA48 de reserva) como estación del barrio para «plou
  ara», el modo aviso y la verdad de la lluvia por horas, con atribución a
  Weather Underground en «Fonts». Se decidirá y registrará entonces.

## Alternativas descartadas

- **Que suba la propia consola de Ecowitt** (su app, «Weather Services»):
  es el mecanismo estándar y sube cada minuto; fue la primera propuesta.
  Juanjo no encontró esa pantalla en su app y prefirió el NAS. Si algún día
  la activa, se quita de aquí: dos subidas de la misma estación no tienen
  sentido.
- **Subir cada 5 minutos desde el reloj del NAS**: más fiel al ritmo de la
  red, pero exige tocar `nas/reloj.sh` y reconstruir el contenedor; con una
  subida por pasada la estación ya cuenta como activa. Se puede cambiar si
  hace falta.

## Consecuencias

Una dependencia saliente más (Weather Underground) y una clave más que
guardar y cifrar. La estación de Juanjo pasa a verse en público en esa red,
con la ubicación que él eligió en el mapa.

## Evidencia

- Protocolo de subida de estaciones personales de Weather Underground
  (`updateweatherstation.php`, `action=updateraw`, respuesta «success»),
  comprobado con la primera subida desde el NAS el 09-10-2026.
- Documentación de las API para contribuidores («APIs for Personal Weather
  Station Contributors», The Weather Company): observaciones actuales,
  historial rápido de un día, 7 días por horas y estaciones cercanas.

## Riesgos y limitaciones

- Con la estación recién dada de alta, el 09-10-2026 la misma petición se
  aceptó y se rechazó («unauthorized») a ratos durante la primera hora:
  las credenciales tardan en llegar a todos los servidores de la red. Desde
  la 3.45.1 cada subida se intenta hasta tres veces; además la pasada
  siguiente vuelve a probar.

- Las condiciones de la clave de lectura (uso personal, no comercial) se
  revisarán al generarla; la web es pública pero no comercial.
- Si cambia el protocolo de subida o la red cierra las claves gratuitas, se
  deja de subir sin que la página lo note.

## Validación

`tests/test_wunderground.py`: unidades (°F, inHg, pulgadas, hora en UTC),
campos vacíos que no se mandan, sin claves no se sube, con claves van el
identificador y la clave.
