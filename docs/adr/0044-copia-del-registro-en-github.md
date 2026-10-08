# 44. Copia del registro en un repositorio privado de GitHub

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Juanjo preguntó si, con el NAS destruido, todo lo de meteo-montflorit
estaba respaldado para montarlo en otro. El servicio sí sigue (la reserva de
IONOS toma el relevo, ADR 0032) y el código y la instalación están en
GitHub, pero el NAS UGREEN no tiene ningún paquete de copias, y en
`/volume1/docker/meteo-local/estat` hay datos que no se pueden volver a
pedir: el registro de lo que preveía la página cada hora junto a lo que pasó
(la base del aprendizaje, ADR 0012), la lluvia de Sant Cugat desde el
08-10-2026 (ADR 0042), la comparación de radares (ADR 0026), los episodios
de la riera con la columna de desbordamiento que se rellena a mano (ADR
0027) y el estado del aprendizaje. Tampoco estaba escrito qué claves usa el
NAS ni dónde se autoriza cada una.

## Decisión

- **Copia diaria en un repositorio privado** `meteo-montflorit/meteo-local-registre`,
  aparte del programa, que es público. La propuesta inicial era IONOS con
  siete días de rotación; Juanjo preguntó si no era mejor GitHub, y lo es:
  guarda un commit por día (se puede volver a cualquier día), queda fuera de
  casa y de IONOS, y no hace falta montar otro receptor en el hosting.
- **Qué entra**: `estat/registre` y `estat/aprenentatge` enteros, sin las
  copias `.bak`. Son datos del tiempo, sin nada personal (los suscriptores
  del bot viven en IONOS y no se copian). Las claves no se copian nunca.
- **Cómo**: `nas/copia-registre.sh`, que llama el reloj una vez al día a
  partir de las 04:15 (`HORA_COPIA` en `nas/reloj.sh`). Usa una clave de
  despliegue propia del NAS (`~/.ssh/id_registre`) con escritura solo en ese
  repositorio. Apunta el resultado en `estat/copia.json`; si lleva más de dos
  días sin poder copiar (contando desde el primer intento si aún no hubo
  ninguno bueno), avisa a Juanjo una vez por Telegram, por `avis_privat.py`.
- **Guía de reinstalación**, `nas/RESTAURAR.md`: el programa, la tabla de
  claves con dónde se regenera cada una (sin ningún valor), cómo traer el
  registro de vuelta y cómo arrancar.
- **Las claves, cifradas, en el mismo repositorio privado**
  (`claus/claus-nas.tar.gz.gpg`): las claves SSH del NAS y los archivos de
  configuración con claves, en un tar cifrado con GnuPG (AES-256) y una
  contraseña que Juanjo escribió en una ventana del escritorio; Claude no la
  conoce. Juanjo no tenía gestor de contraseñas (solo el llavero del sistema,
  que se perdería con el portátil) y eligió esta opción entre tres (archivo
  cifrado, KeePassXC, Bitwarden). No se pone al día solo: si una clave
  cambia, hay que volver a cifrarlo. Se comprobó que se descifra y contiene
  los 15 archivos, y se vació la caché de la contraseña del agente gpg.

## Alternativas descartadas

- **Copia en IONOS con rotación de siete días**: un fallo que no se nota en
  una semana pierde lo bueno; además, otra clave con orden fija y otro
  receptor en el hosting.
- **Las claves sin cifrar en el repositorio privado**: un repositorio no es
  un gestor de contraseñas. Cifradas, sí: si el repositorio se filtra, sin la
  contraseña no sirven.
- **Copia de todo `estat/`**: las cachés del radar y de la web ocupan más que
  el registro y se regeneran solas.

## Evidencia y validación

- En el NAS, el 08-10-2026: `estat/registre` 2,1 MB, `estat/aprenentatge`
  8 KB; ningún paquete de copias en `/var/packages`; `compose.yml`,
  `Dockerfile` y `reloj.sh` idénticos a los de `nas/`.
- `copia-registre.sh` probado en local contra un repositorio vacío (primer
  commit, sin cambios, un cambio) y contra uno que no existe (sin aviso el
  primer día; con aviso a los cuatro). Una primera versión de la prueba de
  fallo contaba desde el año 2000 y mandó a Juanjo un aviso falso; corregido.
- Primera copia real desde el NAS el mismo día (ver el registro del reloj).
