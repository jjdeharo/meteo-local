# 45. Reinstalar lo de IONOS en otro hosting

Fecha: 2026-10-08 · Estado: aceptado

## Contexto

Tras la copia del NAS (ADR 0044), Juanjo preguntó por IONOS: «¿qué pasa si
un día abandono ese servicio?». En IONOS viven la reserva (ADR 0032), el bot
de Telegram (ADR 0034), el receptor de los datos del NAS (ADR 0038) y la
carpeta pública `app/meteo-local`. El código y los instaladores
(`reserva/instalar.sh`, `bot/instalar.sh`) ya estaban en el repositorio,
pero faltaban el `.htaccess` de la carpeta de los datos (CORS para la web de
GitHub Pages), una copia de los tokens fuera del hosting y una guía.

## Decisión

- **Una sola guía**, `RESTAURAR.md` en la raíz, con dos partes: el NAS (la
  de antes, `nas/RESTAURAR.md`) e IONOS: qué pasa mientras falta, qué
  necesita el hosting nuevo, las claves, los instaladores, la dirección de
  los datos y los suscriptores.
- **El `.htaccess` de los datos, en el repositorio** (`reserva/htaccess-dades`),
  y lo instala `reserva/instalar.sh` junto con la carpeta `app/meteo-local`.
- **Los tokens, cifrados**, en `claus/claus-ionos.tar.gz.gpg` del
  repositorio privado de la copia, con la misma contraseña que las claves del
  NAS: el del bot «Temps a Montflorit» y el del bot de avisos que usa la
  reserva. Comprobado que los dos archivos se descifran con ella.
- **Los suscriptores del bot, sin copia**, por la norma del proyecto: son
  datos personales y no salen del hosting, y `/baixa` tiene que poder
  borrarlos de verdad. En un cambio voluntario se pasa el archivo de un
  servidor al otro; si el hosting desaparece de golpe, se anuncia en el canal
  que se vuelva a escribir `/start`. Una copia cifrada tampoco serviría:
  volver a cifrarla pide la contraseña de Juanjo a cada alta o baja.

## Evidencia

- Si IONOS no responde, la web lee la copia de GitHub (ADR 0038, punto 3),
  así que la página pública no depende de IONOS; sí el bot, el canal y la
  reserva.
- La dirección de los datos está en `DADES_URL` (`web/comu.js`) y en
  `ionos.env` del NAS: cambiar de dominio son dos líneas.
