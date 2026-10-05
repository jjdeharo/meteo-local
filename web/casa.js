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

// «avui», «demà» o el dia de la setmana.
function nomDiaCurt(data, ara) {
  const dies = Math.round((new Date(data).setHours(0, 0, 0, 0) - new Date(ara).setHours(0, 0, 0, 0)) / 864e5);
  if (dies === 0) return 'avui';
  if (dies === 1) return 'demà';
  return new Date(data).toLocaleDateString('ca', { weekday: 'long' });
}

// «a les 18:00», «a la 01:00» o «a mitjanit».
function aLaHora(data) {
  const h = horaCurta(data);
  if (h === '00:00') return 'a mitjanit';
  return h.startsWith('01:') ? `a la ${h}` : `a les ${h}`;
}

// Franja d'un avís, amb el dia: «avui fins a les 20:00», «demà de 09:00 a
// 18:00», «demà de 22:00 a mitjanit». Si ja ha començat, només el final.
function textFranja(inici, fi, ara) {
  // Mitjanit és el final del dia de l'avís, no el començament del següent.
  const diaFi = nomDiaCurt(new Date(fi - 1), ara);
  if (inici <= ara) return diaFi === 'avui' ? `avui fins ${aLaHora(fi)}` : `fins ${diaFi} ${aLaHora(fi)}`;
  const h = horaCurta(inici);
  const de = /^(01|11):/.test(h) ? `d\u2019${h}` : `de ${h}`;
  const dia = nomDiaCurt(inici, ara);
  if (diaFi !== dia) return `${dia} ${de} fins ${diaFi} ${aLaHora(fi)}`;
  return `${dia} ${de} ${aLaHora(fi).replace(/^a (les |la )?/, 'a ')}`;
}

// Una frase per nivell i tipus d'avís, amb totes les franges i el dia de
// cadascuna: «Avís groc de l'AEMET per pluja i tempestes al Vallès: avui fins
// a les 20:00; demà de 09:00 a 18:00 i de 22:00 a mitjanit.»
function textAvisos(avisos, ara = new Date()) {
  // 1. Franges de cada nivell i tipus, ajuntant les que es toquen. Els avisos
  // acaben a «hh:59:59»: un segon més dona l'hora en punt.
  const perTipus = {};
  for (const a of avisos) {
    const fi = new Date(a.fin).getTime() + 1000;
    if (fi <= ara.getTime()) continue;
    const inici = Math.max(new Date(a.inicio).getTime(), ara.getTime());
    (perTipus[`${a.nivel}|${a.tipo}`] = perTipus[`${a.nivel}|${a.tipo}`] || []).push([inici, fi]);
  }
  // 2. Tipus que comparteixen franja: «pluja i tempestes».
  const perFranja = {};
  for (const [clau, franges] of Object.entries(perTipus)) {
    const [nivell, tipus] = clau.split('|');
    franges.sort((x, y) => x[0] - y[0]);
    const juntes = [];
    for (const f of franges) {
      const darrera = juntes[juntes.length - 1];
      if (darrera && f[0] <= darrera[1]) darrera[1] = Math.max(darrera[1], f[1]);
      else juntes.push([...f]);
    }
    for (const [inici, fi] of juntes) {
      const k = `${nivell}|${inici}|${fi}`;
      (perFranja[k] = perFranja[k] || new Set()).add(tipus);
    }
  }
  // 3. Una frase per nivell i tipus, amb les franges en ordre i agrupades
  // per dia.
  const frases = {};
  for (const [k, tipus] of Object.entries(perFranja)) {
    const [nivell, inici, fi] = k.split('|');
    const clau = `${nivell}|${[...tipus].sort().join(' i ')}`;
    (frases[clau] = frases[clau] || []).push([Number(inici), Number(fi)]);
  }
  const ordre = { vermell: 0, taronja: 1, groc: 2 };
  return Object.entries(frases)
    .sort(([a, fa], [b, fb]) => (ordre[a.split('|')[0]] ?? 3) - (ordre[b.split('|')[0]] ?? 3)
      || Math.min(...fa.map((f) => f[0])) - Math.min(...fb.map((f) => f[0])))
    .map(([clau, franges]) => {
      const [nivell, tipus] = clau.split('|');
      franges.sort((x, y) => x[0] - y[0]);
      // Les franges del mateix dia, juntes: «demà de 09:00 a 18:00 i de 22:00 a mitjanit».
      const dies = [];
      for (const [inici, fi] of franges) {
        const text = textFranja(new Date(inici), new Date(fi), ara);
        const dia = text.split(' ')[0];
        const darrer = dies[dies.length - 1];
        if (darrer && darrer.dia === dia && text.startsWith(`${dia} d`)) {
          darrer.parts.push(text.slice(dia.length + 1));
        } else {
          dies.push({ dia, parts: [text] });
        }
      }
      const quan = dies.map((d) => d.parts.join(' i ')).join('; ');
      return `Avís ${NIVELL_AVIS[nivell] || nivell} de l’AEMET per ${tipus} al Vallès: ${quan}.`;
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
  return sec;
}

function pinta(dades) {
  const cont = $('casa');
  cont.replaceChildren();
  const plans = blocPlans(dades.plans);
  if (plans) cont.append(plans);
  if (dades.ara) cont.append(blocAra(dades.ara));
  if (dades.avisos && dades.avisos.length) cont.append(element('p', 'avis', textAvisos(dades.avisos)));
  if (dades.models && dades.models.no_encerten) {
    const m = dades.models;
    cont.append(element('p', 'avis', `Avui els models no veuen aquesta pluja: en les darreres ${m.hores} hores `
      + `han caigut ${coma(m.mesurada_mm)}\u00a0mm a Montflorit i en preveien ${coma(m.prevista_mm)}. `
      + 'Les primeres hores de la taula parteixen del que mesura l\u2019estació; per a la resta, fes més cas dels avisos.'));
  }
  if (dades.hores) cont.append(taula(dades.hores));
  pintaHorari(dades);
  posaVersio(dades.versio);
}

carrega('casa.json', pinta, () => {
  $('casa').replaceChildren(element('p', 'avis', 'No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.'));
});
