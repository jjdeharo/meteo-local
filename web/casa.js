// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix casa.json (el genera casa.py) i pinta el temps a casa: el que mesura
// ara l'estació de Montflorit i la previsió hora a hora per a 24 hores.

const NIVELL_AVIS = { groc: 'groc', taronja: 'taronja', vermell: 'vermell' };

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

function textAvisos(avisos) {
  const grups = {};
  for (const a of avisos) {
    // Els avisos acaben a «hh:59:59»: un segon més dona l'hora en punt.
    const fins = horaCurta(new Date(new Date(a.fin).getTime() + 1000));
    const clau = `${a.nivel}|${fins}`;
    (grups[clau] = grups[clau] || new Set()).add(a.tipo);
  }
  return Object.entries(grups).map(([clau, tipus]) => {
    const [nivell, fins] = clau.split('|');
    const fi = fins === '00:00' ? 'fins a mitjanit' : `fins a les ${fins}`;
    return `Avís ${NIVELL_AVIS[nivell] || nivell} de l’AEMET per ${[...tipus].sort().join(' i ')} al Vallès, ${fi}.`;
  }).join(' ');
}

function nomDia(iso) {
  return new Date(iso).toLocaleDateString('ca', { weekday: 'long', day: 'numeric', month: 'long' });
}

function taula(hores) {
  const sec = element('section', 'previsio');
  sec.append(element('h2', 'perque', 'Pròximes 24 hores'));
  const contenidor = element('div', 'taula-contenidor');
  const t = element('table', 'taula-hores');
  const cap = element('thead');
  const fila = element('tr');
  // Les unitats van a la capçalera perquè la taula càpiga al mòbil.
  for (const [text, classe] of [['Hora', ''], ['Cel', ''], ['°C', 'num'], ['Pluja (mm)', 'num'],
    ['Prob.', 'num'], ['Vent (km/h)', 'num']]) {
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
    tr.append(element('td', '', cel(f)));
    tr.append(element('td', 'num', f.temperatura == null ? '' : `${Math.round(f.temperatura)}`));
    tr.append(element('td', 'num', f.pluja_mm >= 0.1 ? coma(f.pluja_mm) : '\u2013'));
    const prob = element('td', 'num prob');
    if (f.probabilitat != null) {
      const pct = Math.round(f.probabilitat * 100);
      prob.textContent = `${pct} %`;
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
  sec.append(element('p', 'nota', 'Vent: mitjana i, entre parèntesis, les ratxes.'));
  return sec;
}

function pinta(dades) {
  const cont = $('casa');
  cont.replaceChildren();
  if (dades.ara) cont.append(blocAra(dades.ara));
  if (dades.avisos && dades.avisos.length) cont.append(element('p', 'avis', textAvisos(dades.avisos)));
  if (dades.hores) cont.append(taula(dades.hores));
  pintaHorari(dades);
  posaVersio(dades.versio);
}

fetch('casa.json', { cache: 'no-store' })
  .then((r) => r.json())
  .then(pinta)
  .catch(() => {
    $('casa').replaceChildren(element('p', 'avis', 'No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.'));
  });
