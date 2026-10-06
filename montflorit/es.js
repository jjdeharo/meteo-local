// SPDX-License-Identifier: AGPL-3.0-or-later
// La pàgina en castellà (ADR 0025): les traduccions dels textos que comu.js i
// casa.js passen per T (la clau és el text català, amb {0}, {1}… on van els
// valors) i de les paraules que venen a les dades (TD). Es carrega abans que
// comu.js. Si a la pàgina s'hi afegeix o s'hi canvia un text, les proves
// avisen que aquí falta.

// «hasta el viernes», però «hasta mañana».
function ambArticle(dia) {
  return dia === 'hoy' || dia === 'mañana' ? dia : `el ${dia}`;
}

var IDIOMA = {
  codi: 'es',
  textos: {
    "Mode avís: dades cada {0} min{1}.": "Modo aviso: datos cada {0} min{1}.",
    "Dades en directe cada {0} min.": "Datos en directo cada {0} min.",
    "Dades en directe cada {0} min ({1}).": "Datos en directo cada {0} min ({1}).",
    " del {0}": " del {0}",
    "demà a les {0}": "mañana a las {0}",
    "L’actualització de les {0} no s’ha fet: les dades són de les {1}.": "La actualización de las {0} no se ha hecho: los datos son de las {1}.",
    "a la {0}": "a la {0}",
    "a les {0}": "a las {0}",
    "avui fins {0}":
      (hora) => `hoy hasta ${hora.replace(/^a /, '')}`,
    "fins {0} {1}":
      (dia, hora) => `hasta ${ambArticle(dia)} ${hora}`,
    "d’{0}": "de {0}",
    "de {0}": "de {0}",
    "{0} {1} fins {2} {3}":
      (dia, de, diaFi, hora) => `${dia} ${de} hasta ${ambArticle(diaFi)} ${hora}`,
    "a {0}": "a {0}",
    "Avís {0} de l’AEMET per {1} al Vallès: {2}.": "Aviso {0} de la AEMET por {1} en el Vallès: {2}.",
    "Open-Meteo, d’on surten els models, ara no respon: la previsió és la de les {0}{1}.": "Open-Meteo, de donde salen los modelos, ahora no responde: la previsión es la de las {0}{1}.",
    "Protecció Civil: pla {0} ({1}) en fase d’{2}.": "Protección Civil: plan {0} ({1}) en fase de {2}.",
    "versió {0}": "versión {0}",
    " i ": " y ",
    "Actualitzat a les ": "Actualizado a las ",
    " · propera: ": " · próxima: ",
    "No s’han pogut llegir totes les fonts: la informació és menys segura.": "No se han podido leer todas las fuentes: la información es menos segura.",
    "avui": "hoy",
    "demà": "mañana",
    "a mitjanit": "a medianoche",
    "Avís de Protecció Civil": "Aviso de Protección Civil",
    " Eviteu els desplaçaments que no siguin necessaris.": " Evitad los desplazamientos que no sean necesarios.",
    "Comunicat (PDF)": "Comunicado (PDF)",
    "Pressió {0}\u00a0hPa": "Presión {0}\u00a0hPa",
    "{0}, estable": "{0}, estable",
    "{0}, {1}{2} ({3}{4} en 3\u00a0h)": "{0}, {1}{2} ({3}{4} en 3\u00a0h)",
    "El temps ara a {0}": "El tiempo ahora en {0}",
    "Ara a {0} ({1})": "Ahora en {0} ({1})",
    "Plou: {0} mm/h": "Llueve: {0} mm/h",
    "{0} mm avui": "{0} mm hoy",
    "Humitat {0} %": "Humedad {0} %",
    "Vent {0} km/h": "Viento {0} km/h",
    "Arribaria pluja cap a les\u00a0{0}": "Llegaría lluvia hacia las\u00a0{0}",
    "Pot arribar pluja cap a les\u00a0{0}": "Puede llegar lluvia hacia las\u00a0{0}",
    " · va cap {0} a {1}\u00a0km/h": " · va hacia {0} a {1}\u00a0km/h",
    "Radar de {0} de les {1}{2}": "Radar de {0} de las {1}{2}",
    "Risc {0}": "Riesgo {0}",
    "(llindar {0} de l’AEMET: {1} {2})": "(umbral {0} de la AEMET: {1} {2})",
    "Avís {0} de l’AEMET per {1}": "Aviso {0} de la AEMET por {1}",
    "Avís {0} · {1}": "Aviso {0} · {1}",
    "Avís {0}": "Aviso {0}",
    "Probabilitat de pluja apresa del que ha plogut de veritat a {0} des del {1}, quan els models deien el mateix.": "Probabilidad de lluvia aprendida de lo que ha llovido de verdad en {0} desde el {1}, cuando los modelos decían lo mismo.",
    "Probabilitat de pluja apresa del que va ploure de veritat a Sabadell i Sant Cugat des del {0}, quan els models deien el mateix.": "Probabilidad de lluvia aprendida de lo que llovió de verdad en Sabadell y Sant Cugat desde {0}, cuando los modelos decían lo mismo.",
    " Temperatura corregida amb el que ha mesurat {0} des del {1}.": " Temperatura corregida con lo que ha medido {0} desde el {1}.",
    " Temperatura corregida amb el registre propi de {0} des del {1}.": " Temperatura corregida con el registro propio de {0} desde el {1}.",
    "Avui els models no veuen aquesta pluja: en les darreres {0} hores han caigut {1}\u00a0mm a Montflorit i en preveien {2}. Les primeres hores de la taula parteixen del que mesura l’estació; per a la resta, fes més cas dels avisos.": "Hoy los modelos no ven esta lluvia: en las últimas {0} horas han caído {1}\u00a0mm en Montflorit y preveían {2}. Las primeras horas de la tabla parten de lo que mide la estación; para el resto, haz más caso de los avisos.",
    "Tempesta": "Tormenta",
    "Pluja forta": "Lluvia fuerte",
    "Pluja": "Lluvia",
    "Pluja feble": "Lluvia débil",
    "Possible tempesta": "Posible tormenta",
    "Possible pluja": "Posible lluvia",
    "Boira": "Niebla",
    "Serè": "Despejado",
    "Poc núvol": "Poco nuboso",
    "Núvols": "Nubes",
    "Cobert": "Cubierto",
    "pujant": "subiendo",
    "baixant": "bajando",
    " ràpid": " rápido",
    "No plou": "No llueve",
    "Pluja a sobre": "Lluvia encima",
    "Pluja a prop: pot arribar": "Lluvia cerca: puede llegar",
    "No s’acosta pluja en 2 hores": "No se acerca lluvia en 2 horas",
    "Risc previst": "Riesgo previsto",
    "Avís": "Aviso",
    "Pròximes 24 hores": "Próximas 24 horas",
    "Hora": "Hora",
    "Avisos": "Avisos",
    "Cel": "Cielo",
    "Pluja (mm)": "Lluvia (mm)",
    "Prob.": "Prob.",
    "Vent": "Viento",
    "Plou ara": "Llueve ahora",
    "* Segons la pluja que mesura ara l’estació i el que va passar en casos semblants a Sabadell i Sant Cugat entre el 2024 i el 2026.": "* Según la lluvia que mide ahora la estación y lo que pasó en casos parecidos en Sabadell y Sant Cugat entre 2024 y 2026.",
    "† Segons el radar: la pluja que hi ha ara, portada endavant a la velocitat i en la direcció que porta.": "† Según el radar: la lluvia que hay ahora, llevada hacia delante a la velocidad y en la dirección que lleva.",
    "La barra de color al costat de l’hora marca les hores amb avís de l’AEMET, del color del nivell.": "La barra de color junto a la hora marca las horas con aviso de la AEMET, del color del nivel.",
    "Vent en km/h: mitjana i, entre parèntesis, les ratxes.": "Viento en km/h: media y, entre paréntesis, las rachas.",
    "No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.": "No se ha podido cargar la previsión. Vuelve a probarlo dentro de un rato.",
  },
  // Paraules que venen a les dades: nivells, tipus d'avís, plans i rumbs.
  dades: {
    groc: 'amarillo', taronja: 'naranja', vermell: 'rojo',
    pluja: 'lluvia', tempestes: 'tormentas',
    "d'inundacions": 'de inundaciones', 'de vent': 'de viento', 'de neu': 'de nieve',
    prealerta: 'prealerta', alerta: 'alerta', 'emergència': 'emergencia',
    'al nord': 'el norte', 'al nord-est': 'el nordeste', "a l'est": 'el este', 'al sud-est': 'el sudeste',
    'al sud': 'el sur', 'al sud-oest': 'el sudoeste', "a l'oest": 'el oeste', 'al nord-oest': 'el noroeste',
  },
  // El text d'un risc (riscos.py el fa en català): la previsió i el que es mesura.
  riscos: {
    pluja_1h: ['Lluvia muy fuerte prevista: hasta {v} mm en una hora, {q}.', 'Ahora llueve muy fuerte: {v} mm en la última hora.'],
    pluja_12h: ['Mucha lluvia prevista: {v} mm en 12 horas, {q}.', 'Ha llovido mucho: {v} mm en las últimas 12 horas.'],
    ratxa: ['Viento muy fuerte previsto: rachas de hasta {v} km/h, {q}.', null],
    calor: ['Calor extremo previsto: hasta {v} °C, {q}.', 'Ahora hace calor extremo: {v} °C.'],
    fred: ['Frío intenso previsto: hasta {v} °C, {q}.', 'Ahora hace frío intenso: {v} °C.'],
    neu_24h: ['Nieve prevista: {v} cm en las próximas 24 horas.', null],
  },
  risc(r) {
    const plantilla = (this.riscos[r.tipus] || [])[r.origen === 'previsio' ? 0 : 1];
    if (!plantilla) return r.text;
    let quan = '';
    if (r.des_de && r.fins) {
      const ini = new Date(r.des_de);
      const dies = Math.round((new Date(ini).setHours(0, 0, 0, 0) - new Date().setHours(0, 0, 0, 0)) / 864e5);
      const dia = dies === 0 ? 'hoy' : dies === 1 ? 'mañana'
        : `${String(ini.getDate()).padStart(2, '0')}/${String(ini.getMonth() + 1).padStart(2, '0')}`;
      quan = `${dia} de ${ini.getHours()} a ${new Date(r.fins).getHours()} h`;
    }
    return plantilla.replace('{v}', Number(r.valor).toFixed(0).replace('-', '\u2212')).replace('{q}', quan);
  },
};
