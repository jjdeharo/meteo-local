# 8. Planes de Protección Civil

Fecha: 2026-10-05 · Estado: aceptado

## Contexto

El 05-10-2026 a las 9:55 llegó a los móviles una alerta ES-Alert de Protecció
Civil: «Pluges torrencials fins a les 14h d'avui. Eviteu desplaçaments
innecessaris». La web no la recogía. El mensaje ES-Alert no se publica en
ningún canal abierto que se haya encontrado, pero sí el estado de los planes
de protección civil que lo motivan.

## Decisión

- Se leen los planes activados del conjunto de datos abiertos de la
  Generalitat «Plans de protecció civil en fase de prealerta, alerta o
  emergència» (`analisi.transparenciacatalunya.cat`, `wj9c-j6vf`), que se
  actualiza en tiempo real.
- Solo los meteorológicos: INUNCAT (inundaciones), VENTCAT (viento) y NEUCAT
  (nieve) (`PLANES_PC` en `config.py`).
- Un plan cuenta salvo que su descripción nombre solo otras zonas
  (`ZONAS_AJENAS_PC`); si nombra el Vallès, Barcelona o Cataluña, cuenta.
  Ejemplo descartado: «CHE. Vigilància … conca de l'Ebre».
- **En alerta o emergencia es riesgo alto** en los dos trayectos: el día sale
  «coche», con el plan como motivo. En prealerta solo se avisa.
- Las dos páginas muestran el plan en un aviso destacado arriba, con el enlace
  al comunicado del CECAT; en fase de emergencia añaden «Eviteu els
  desplaçaments que no siguin necessaris».

## Alternativas descartadas

- **Leer el mensaje ES-Alert:** no se ha encontrado una fuente pública.

## Consecuencias

La recomendación sigue a Protección Civil mientras el plan esté activado, sin
hora de fin: el plan no la tiene. La descripción del plan no siempre dice la
zona; en caso de duda se da por afectado el Vallès.

**Cuando el plan es el único motivo** (versión 2.19.1, 07-10-2026): el INUNCAT
siguió en emergencia días después de las lluvias del 3 al 6 de octubre, y una
mañana seca la ida salía con «riesgo de lluvia alto» y todos los motivos
visibles en verde, porque la ficha omitía el plan (ya sale arriba de todo).
Juanjo pidió explicarlo tal cual: se sigue recomendando el coche, pero si el
plan es el único motivo y ninguna otra fuente ve lluvia (todas en «moto»), la
ficha muestra el plan y una nota con franja verde: «Només ho decideix el pla
de Protecció Civil: ni els avisos de l'AEMET, ni el radar, ni les estacions,
ni els models hi veuen pluja. No hi ha cap motiu aparent per no anar en moto.»
Lo decide `nomesPla` en `web/app.js` (prueba en `tests/test_web.py`).

## Evidencia

05-10-2026, 10:06: dos planes INUNCAT activados en fase de emergencia, uno
«Emergència INUNCAT 3-5 Octubre» (cuenta) y otro de la cuenca del Ebro (se
descarta).

## Riesgos y limitaciones

- Si el plan sigue activado tras el episodio, la web seguirá recomendando el
  coche hasta que Protección Civil lo desactive.

## Validación

Pruebas automáticas: emergencia da coche, prealerta no cambia el riesgo y un
plan de otra zona no cuenta (`tests/test_decidir.py`).
