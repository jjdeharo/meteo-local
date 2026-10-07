# 35. El repositorio, en la organización meteo-montflorit

Fecha: 2026-10-07 · Estado: aceptado

## Contexto

El código y los ADR estaban en la cuenta personal de Juanjo
(`jjdeharo/meteo-local`) y la web pública en la organización de la aplicación
(`meteo-montflorit`, ADR 0028). Juanjo pidió trasladar el repositorio a la
organización sin que se rompiera nada (web, bot, canal…). Puso dos
condiciones: los enlaces a los ADR que ya había dado tenían que seguir
funcionando, y la dirección antigua de la web, que tiene mucha gente, tenía
que seguir llevando a la nueva, aunque las páginas de antes no le interesan.

## Decisión

- **Traslado** de `jjdeharo/meteo-local` a `meteo-montflorit/meteo-local`,
  con el mismo nombre: se conservan historial, versiones, ADR y la clave de
  despliegue del NAS. GitHub redirige solo las direcciones antiguas del
  repositorio (código, ADR, commits, versiones), también para `git`, mientras
  no se cree otro repositorio que se llame `jjdeharo/meteo-local`: **ese
  nombre no se vuelve a usar**.
- **La web del repositorio no se traslada**: GitHub no redirige las webs de
  GitHub Pages. Las redirecciones de la dirección antigua
  (`jjdeharo.github.io/meteo-local/…`, antes en `redireccions/` y en la rama
  `gh-pages` de este repositorio, ADR 0030) pasan al repositorio
  `jjdeharo/jjdeharo.github.io`, creado para eso: una carpeta `meteo-local/`
  con las mismas páginas y un `404.html` que lleva a Temps a Montflorit
  cualquier otra dirección de esa carpeta. El resto de direcciones de
  `jjdeharo.github.io` siguen sin encontrarse, como antes. El repositorio
  trasladado no publica ninguna web, y el NAS ya no publica esas
  redirecciones (`publica.sh`).
- **Al día**: el clon del NAS, el de IONOS (bot y reserva) y el local apuntan
  a la dirección nueva; `nas/reloj.sh`, `reserva/instalar.sh`, los enlaces de
  la web (créditos, pie) y el README, también.

## Alternativas descartadas

- **Dejar el repositorio en la cuenta personal**: funciona, pero la aplicación
  queda repartida entre dos sitios.
- **Volver a crear `jjdeharo/meteo-local` solo con las redirecciones**:
  rompería las redirecciones de GitHub hacia el repositorio trasladado y, con
  ellas, los enlaces a los ADR ya dados.

## Riesgos

- Si algún día se crea un repositorio `jjdeharo/meteo-local`, los enlaces
  antiguos al código y a los ADR dejan de llevar aquí.
- Las redirecciones de GitHub no tienen fecha de caducidad documentada, pero
  dependen de GitHub.

## Validación

Tras el traslado se comprobó en vivo: la web pública se sigue publicando
desde el NAS, el bot responde y se pone al día desde la dirección nueva, la
reserva pasa su prueba, las direcciones antiguas de la web llevan a la nueva y
los enlaces antiguos a los ADR abren el ADR en la organización.
