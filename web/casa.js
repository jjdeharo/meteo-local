// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix casa.json (el genera casa.py) i pinta el temps a casa: el que mesuren
// ara l'estació de casa i la de Montflorit i la previsió hora a hora per a 24 hores.

function coma(x, decimals = 1) {
  return Number(x).toFixed(decimals).replace('.', ',');
}

// Altura del sol (graus) a casa en un moment donat, amb la fórmula
// aproximada de la NOAA: n'hi ha prou per saber si és de dia o de nit.
const CASA_COORD = [41.482, 2.135];
function alturaSol(data) {
  const rad = Math.PI / 180;
  const dies = data.getTime() / 864e5 + 2440587.5 - 2451545;
  const l = (280.46 + 0.9856474 * dies) % 360;
  const g = ((357.528 + 0.9856003 * dies) % 360) * rad;
  const lambda = (l + 1.915 * Math.sin(g) + 0.02 * Math.sin(2 * g)) * rad;
  const eps = (23.439 - 0.0000004 * dies) * rad;
  const dec = Math.asin(Math.sin(eps) * Math.sin(lambda));
  const ar = Math.atan2(Math.cos(eps) * Math.sin(lambda), Math.cos(lambda));
  const gmst = (18.697374558 + 24.06570982441908 * dies) % 24;
  const angle = (gmst * 15 + CASA_COORD[1]) * rad - ar;
  const lat = CASA_COORD[0] * rad;
  return Math.asin(Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(angle)) / rad;
}

// Descripció del cel feta amb les mateixes dades que la taula, perquè no
// digui «serè» en una hora amb pluja, i la icona que hi correspon. De nit, la
// lluna en lloc del sol (a mitja hora del tram).
function cel(f) {
  const nit = alturaSol(new Date(new Date(f.hora).getTime() + 18e5)) < 0;
  if (f.codi >= 95) return ['Tempesta', 'i-cloud-lightning'];
  if (f.pluja_mm >= 4) return ['Pluja forta', 'i-cloud-rain-wind'];
  if (f.pluja_mm >= 1) return ['Pluja', 'i-cloud-rain'];
  if (f.pluja_mm >= 0.2) return ['Pluja feble', 'i-cloud-drizzle'];
  // Sense pluja prevista però amb probabilitat clara: no pot dir «serè».
  if (f.probabilitat >= 0.3) return ['Possible pluja', nit ? 'i-cloud-moon-rain' : 'i-cloud-sun-rain'];
  if (f.codi === 45 || f.codi === 48) return ['Boira', 'i-cloud-fog'];
  if (f.nuvols == null) return ['', null];
  if (f.nuvols < 20) return ['Serè', nit ? 'i-moon-cel' : 'i-sun'];
  if (f.nuvols < 50) return ['Poc núvol', nit ? 'i-cloud-moon' : 'i-cloud-sun'];
  if (f.nuvols < 85) return ['Núvols', 'i-cloud'];
  return ['Cobert', 'i-cloudy'];
}

// Com canvia la pressió en tres hores, amb els llindars habituals: menys d'1
// hPa és estable; 3,6 hPa o més, un canvi ràpid.
function textPressio(casa) {
  const p = `Pressió ${coma(casa.pressio, 0)} hPa`;
  const d = casa.pressio_3h;
  if (d == null) return p;
  if (Math.abs(d) < 1) return `${p}, estable`;
  const sentit = d > 0 ? 'pujant' : 'baixant';
  const rapid = Math.abs(d) >= 3.6 ? ' ràpid' : '';
  return `${p}, ${sentit}${rapid} (${d > 0 ? '+' : '\u2212'}${coma(Math.abs(d))} en 3 h)`;
}

// Temperatura, humitat i pressió, de l'estació de casa; pluja i vent, de
// Montflorit. Plou si qualsevol de les dues en marca (la de casa, només quan
// en marca: el seu zero no és fiable). Si en falla una, l'altra. Cada dada,
// amb la seva icona, perquè es llegeixi d'una ullada.
function dada(id, text) {
  const li = element('li');
  li.append(icona(id), document.createTextNode(text));
  return li;
}

function blocAra(ara, casa, radarDades) {
  const base = casa || ara;
  const sec = element('section', 'decisio targeta ara');
  sec.setAttribute('aria-label', casa ? 'El temps ara a casa' : 'El temps ara a Montflorit');
  sec.append(element('h2', 'data', `Ara a ${casa ? 'casa' : 'Montflorit'} (${horaCurta(base.hora)})`));
  const temp = element('p', 'veredicte');
  const termometre = icona('i-thermometer');
  termometre.classList.add('vehicle');
  temp.append(termometre, `${coma(base.temperatura)} °C`);
  sec.append(temp);
  const plouMont = !!ara && ((ara.intensitat || 0) > 0 || (ara.pluja_30min || 0) > 0);
  const plou = plouMont || !!(casa && casa.plou);
  const intensitat = Math.max((ara && ara.intensitat) || 0, (casa && casa.plou && casa.intensitat) || 0);
  const llista = element('ul', 'dades-ara');
  llista.append(plou ? dada('i-umbrella', `Plou: ${coma(intensitat)} mm/h`) : dada('i-umbrella-off', 'No plou'));
  if (ara) llista.append(dada('i-cloud-rain', `${coma(ara.pluja_avui || 0)} mm avui`));
  llista.append(dada('i-droplets', `Humitat ${coma(base.humitat, 0)} %`));
  if (casa && casa.pressio != null) llista.append(dada('i-gauge', textPressio(casa)));
  if (ara && ara.vent != null) llista.append(dada('i-wind', `Vent ${coma(ara.vent, 0)} km/h`));
  const radar = textRadar(radarDades, plou);
  if (radar) llista.append(dada('i-radar', radar));
  sec.append(llista);
  return sec;
}

// La pluja del radar portada endavant (ADR 0019): quan arribaria a casa.
function textRadar(r, plou) {
  if (!r) return '';
  const mov = r.cap_a ? `, va cap ${r.cap_a} a ${r.velocitat_kmh} km/h` : '';
  const aviat = (t) => new Date(t) <= new Date(Date.now() + 5 * 60e3);
  if (r.arriba) {
    if (plou || aviat(r.arriba)) return `Radar: pluja a sobre${mov}`;
    return `Radar: arribaria pluja cap a les ${horaCurta(r.arriba)}${mov}`;
  }
  if (r.possible) {
    if (aviat(r.possible)) return `Radar: pluja a prop, pot arribar${mov}`;
    return `Radar: pot arribar pluja cap a les ${horaCurta(r.possible)}${mov}`;
  }
  return 'Radar: no s\u2019acosta pluja en 2 hores';
}

// Situacions de perill segons el que mesuren les estacions i el que preveu
// la pàgina (riscos.py, ADR 0018), amb el color del nivell de l'AEMET.
function blocRiscos(riscos) {
  if (!riscos || !riscos.length) return null;
  const pitjor = riscos[0].nivell;
  const caixa = element('section', `avis risc-previst ${pitjor}`);
  caixa.setAttribute('aria-label', 'Risc previst');
  const titol = element('p', 'titol-risc');
  titol.append(icona('i-triangle-alert'), `Risc ${pitjor}`);
  caixa.append(titol);
  const llista = element('ul');
  for (const r of riscos) {
    const li = element('li', null, r.text);
    li.append(' ', element('span', 'detall',
      `(llindar ${r.nivell} de l\u2019AEMET: ${coma(r.llindar, 0).replace('-', '\u2212')} ${r.unitat})`));
    llista.append(li);
  }
  caixa.append(llista);
  return caixa;
}

function nomDia(iso) {
  return new Date(iso).toLocaleDateString('ca', { weekday: 'long', day: 'numeric', month: 'long' });
}

function taula(hores, aprenentatge) {
  const sec = element('section', 'previsio');
  sec.append(element('h2', 'perque', 'Pròximes 24 hores'));
  const contenidor = element('div', 'taula-contenidor');
  const t = element('table', 'taula-hores');
  const cap = element('thead');
  const fila = element('tr');
  // Les unitats van a la capçalera perquè la taula càpiga al mòbil.
  for (const [text, classe] of [['Hora', ''], ['Cel', ''], ['°C', 'num'], ['Pluja (mm)', 'num'],
    ['Prob.', 'num'], ['Vent', 'num']]) {
    const th = element('th', classe, text);
    th.scope = 'col';
    fila.append(th);
  }
  cap.append(fila);
  t.append(cap);
  const cos = element('tbody');
  let diaAnterior = new Date().toDateString();
  for (const f of hores) {
    const inici = new Date(f.hora);
    if (inici.toDateString() !== diaAnterior) {
      diaAnterior = inici.toDateString();
      const separador = element('tr', 'dia-nou');
      const td = element('th', '', nomDia(f.hora));
      td.colSpan = 6;
      td.scope = 'rowgroup';
      separador.append(td);
      cos.append(separador);
    }
    const tr = element('tr', f.pluja_mm >= 0.2 ? 'amb-pluja' : '');
    const h0 = inici.getHours();
    const hora = element('th', 'hora', `${h0}–${(h0 + 1) % 24}`);
    hora.scope = 'row';
    tr.append(hora);
    const [textCel, iconaCel] = f.plou_ara ? ['Plou ara', 'i-umbrella'] : cel(f);
    const celCel = element('td', 'cel');
    const linia = element('span', 'cel-text');
    if (iconaCel) linia.append(icona(iconaCel));
    linia.append(textCel);
    celCel.append(linia);
    for (const a of f.avisos || []) {
      const marca = element('span', `marca-avis ${a.nivell}`, `Avís ${a.nivell}`);
      marca.title = `Avís ${a.nivell} de l\u2019AEMET per ${a.tipus.join(' i ')}`;
      marca.append(element('span', 'visualment-amagat', ` per ${a.tipus.join(' i ')}`));
      celCel.append(marca);
    }
    tr.append(celCel);
    tr.append(element('td', 'num', f.temperatura == null ? '' : `${Math.round(f.temperatura)}`));
    tr.append(element('td', 'num', f.pluja_mm >= 0.1 ? coma(f.pluja_mm) : '\u2013'));
    const prob = element('td', 'num prob');
    if (f.probabilitat != null) {
      const pct = Math.round(f.probabilitat * 100);
      prob.textContent = `${pct} %${f.segons_estacio ? '*' : f.segons_radar ? '\u2020' : ''}`;
      prob.style.setProperty('--prob', `${pct}%`);
    }
    tr.append(prob);
    tr.append(element('td', 'num', f.vent == null ? ''
      : `${Math.round(f.vent)}${f.ratxa ? ` (${Math.round(f.ratxa)})` : ''}`));
    cos.append(tr);
  }
  t.append(cos);
  contenidor.append(t);
  sec.append(contenidor);
  if (hores.some((f) => f.segons_estacio)) {
    sec.append(element('p', 'nota', '* Segons la pluja que mesura ara l\u2019estació i el que va passar '
      + 'en casos semblants a Sabadell i Sant Cugat entre el 2024 i el 2026.'));
  }
  if (hores.some((f) => f.segons_radar)) {
    sec.append(element('p', 'nota', '\u2020 Segons el radar: la pluja que hi ha ara, portada endavant '
      + 'a la velocitat i en la direcció que porta.'));
  }
  sec.append(element('p', 'nota', 'Vent en km/h: mitjana i, entre parèntesis, les ratxes.'));
  const apres = textAprenentatge(aprenentatge);
  if (apres) sec.append(element('p', 'nota', apres));
  return sec;
}

// Com s'ha après la probabilitat de pluja i, si cal, la correcció de la
// temperatura (aprenentatge.py, ADR 0012).
function textAprenentatge(a) {
  if (!a || !a.pluja) return '';
  const data = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString('ca');
  let t = a.pluja.origen !== 'arxiu'
    ? `Probabilitat de pluja apresa del que ha plogut de veritat a Montflorit i a casa des del ${data(a.pluja.des_de)}, quan els models deien el mateix.`
    : `Probabilitat de pluja apresa del que va ploure de veritat a Sabadell i Sant Cugat des del ${new Date(a.pluja.des_de).getFullYear()}, quan els models deien el mateix.`;
  if (a.temperatura) {
    t += a.temperatura.origen === 'arxiu'
      ? ` Temperatura corregida amb el que ha mesurat l\u2019estació de casa des del ${data(a.temperatura.des_de)}.`
      : ` Temperatura corregida amb el registre propi de l\u2019estació de casa des del ${data(a.temperatura.des_de)}.`;
  }
  return t;
}

function pinta(dades) {
  const cont = $('casa');
  cont.replaceChildren();
  // Tots els avisos junts, a dalt; després, l'hora d'actualització.
  const avisos = $('avisos');
  avisos.replaceChildren();
  const plans = blocPlans(dades.plans);
  if (plans) avisos.append(plans);
  const riscos = blocRiscos(dades.riscos);
  if (riscos) avisos.append(riscos);
  if (dades.avisos && dades.avisos.length) avisos.append(element('p', 'avis', textAvisos(dades.avisos)));
  if (dades.previsio_de) avisos.append(element('p', 'avis', textPrevisioAnterior(dades)));
  if (dades.models && dades.models.no_encerten) {
    const m = dades.models;
    avisos.append(element('p', 'avis', `Avui els models no veuen aquesta pluja: en les darreres ${m.hores} hores `
      + `han caigut ${coma(m.mesurada_mm)}\u00a0mm a Montflorit i en preveien ${coma(m.prevista_mm)}. `
      + 'Les primeres hores de la taula parteixen del que mesura l\u2019estació; per a la resta, fes més cas dels avisos.'));
  }
  if (dades.ara || dades.ara_casa) cont.append(blocAra(dades.ara, dades.ara_casa, dades.radar));
  if (dades.hores) cont.append(taula(dades.hores, dades.aprenentatge));
  pintaHorari(dades);
  posaVersio(dades.versio);
}

carrega('casa.json', pinta, () => {
  $('casa').replaceChildren(element('p', 'avis', 'No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.'));
});
