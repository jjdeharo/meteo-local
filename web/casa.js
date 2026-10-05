// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix casa.json (el genera casa.py) i pinta el temps a casa: el que mesura
// ara l'estació de Montflorit i la previsió hora a hora per a 24 hores.

function coma(x, decimals = 1) {
  return Number(x).toFixed(decimals).replace('.', ',');
}

// Descripció del cel feta amb les mateixes dades que la taula, perquè no
// digui «serè» en una hora amb pluja.
function cel(f) {
  if (f.codi >= 95) return 'Tempesta';
  if (f.pluja_mm >= 4) return 'Pluja forta';
  if (f.pluja_mm >= 1) return 'Pluja';
  if (f.pluja_mm >= 0.2) return 'Pluja feble';
  // Sense pluja prevista però amb probabilitat clara: no pot dir «serè».
  if (f.probabilitat >= 0.3) return 'Possible pluja';
  if (f.codi === 45 || f.codi === 48) return 'Boira';
  if (f.nuvols == null) return '';
  if (f.nuvols < 20) return 'Serè';
  if (f.nuvols < 50) return 'Poc núvol';
  if (f.nuvols < 85) return 'Núvols';
  return 'Cobert';
}

function blocAra(ara) {
  const sec = element('section', 'decisio targeta ara');
  sec.setAttribute('aria-label', 'El temps ara a Montflorit');
  sec.append(element('h2', 'data', `Ara a Montflorit (${horaCurta(ara.hora)})`));
  sec.append(element('p', 'veredicte', `${coma(ara.temperatura)} °C`));
  const plou = (ara.intensitat || 0) > 0 || (ara.pluja_30min || 0) > 0;
  const parts = [
    plou ? `Plou: ${coma(ara.intensitat || 0)} mm/h` : 'No plou',
    `${coma(ara.pluja_avui || 0)} mm avui`,
    `humitat ${ara.humitat} %`,
  ];
  if (ara.vent != null) parts.push(`vent ${coma(ara.vent, 0)} km/h`);
  sec.append(element('p', 'frase', parts.join(' · ') + '.'));
  return sec;
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
    const celCel = element('td', 'cel', f.plou_ara ? 'Plou ara' : cel(f));
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
      prob.textContent = `${pct} %${f.segons_estacio ? '*' : ''}`;
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
  let t = a.pluja.origen === 'montflorit'
    ? `Probabilitat de pluja apresa del que ha plogut de veritat a Montflorit des del ${data(a.pluja.des_de)}, quan els models deien el mateix.`
    : `Probabilitat de pluja apresa del que va ploure de veritat a Sabadell i Sant Cugat des del ${new Date(a.pluja.des_de).getFullYear()}, quan els models deien el mateix.`;
  if (a.temperatura) t += ` Temperatura corregida amb el que mesura Montflorit des del ${data(a.temperatura.des_de)}.`;
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
  if (dades.avisos && dades.avisos.length) avisos.append(element('p', 'avis', textAvisos(dades.avisos)));
  if (dades.models && dades.models.no_encerten) {
    const m = dades.models;
    avisos.append(element('p', 'avis', `Avui els models no veuen aquesta pluja: en les darreres ${m.hores} hores `
      + `han caigut ${coma(m.mesurada_mm)}\u00a0mm a Montflorit i en preveien ${coma(m.prevista_mm)}. `
      + 'Les primeres hores de la taula parteixen del que mesura l\u2019estació; per a la resta, fes més cas dels avisos.'));
  }
  if (dades.ara) cont.append(blocAra(dades.ara));
  if (dades.hores) cont.append(taula(dades.hores, dades.aprenentatge));
  pintaHorari(dades);
  posaVersio(dades.versio);
}

carrega('casa.json', pinta, () => {
  $('casa').replaceChildren(element('p', 'avis', 'No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.'));
});
