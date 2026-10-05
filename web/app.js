// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix dades.json (el genera prevision.py) i pinta la pàgina del trajecte.
// Les peces comunes amb la pàgina de casa són a comu.js.
// Només informa dins de les franges de l'horari (anada i tornada). Fins a les
// 7:30 recomana un sol mitjà per a tot el dia (qui va en moto torna en moto); a
// la tarda ja no en recomana cap: només diu el temps de la tornada. Fora de
// les franges diu quan és la propera actualització.

const TEXT_MITJA = {
  moto: { titol: 'Moto', frase: 'Pots anar i tornar en moto.' },
  compte: { titol: 'Moto, amb impermeable', frase: 'Pots anar en moto, però porta l\u2019impermeable: pot caure algun ruixat.' },
  cotxe: { titol: 'Cotxe', frase: 'Agafa el cotxe per anar i per tornar.' },
};
const TEXT_RISC = { moto: 'baix', compte: 'moderat', cotxe: 'alt' };
// Marge abans de dir que una actualització prevista no s'ha fet.
function nomDia(iso) {
  const data = new Date(iso + 'T12:00:00');
  return 'Avui, ' + data.toLocaleDateString('ca', { weekday: 'long', day: 'numeric', month: 'long' });
}

// Quan es va decidir i si encara pot canviar.
function notaDecisio(decisio, limit) {
  const hora = horaCurta(decisio.decidit);
  if (decisio.mantinguda || !decisio.abans_de_sortir) {
    return decisio.abans_de_sortir
      ? `Decidit a les ${hora}. Ja no canvia.`
      : `Decidit a les ${hora}: no hi havia dades d\u2019abans de les ${limit}.`;
  }
  return `Recomanació de les ${hora}. Es pot actualitzar fins a les ${limit}; després ja no canvia.`;
}

function liniaTemps(temps) {
  if (!temps) return null;
  const t = temps.temp_min === temps.temp_max
    ? `${temps.temp_min}\u00a0°C` : `De ${temps.temp_min} a ${temps.temp_max}\u00a0°C`;
  return temps.ratxa_max == null ? t + '.' : `${t}, ratxes de vent de fins a ${temps.ratxa_max}\u00a0km/h.`;
}

const MAX_MOTIUS_VISIBLES = 3;

function liMotiu(motiu, ambDetall) {
  const li = element('li', 'motiu ' + motiu.nivell);
  li.append(element('span', 'visualment-amagat', `Risc ${TEXT_RISC[motiu.nivell]}: `));
  li.append(document.createTextNode(motiu.text));
  if (ambDetall && motiu.detall) li.append(' ', element('span', 'detall', motiu.detall));
  return li;
}

// A la vista, només el que decideix el nivell (com a molt tres línies). La
// resta, i el detall de cada motiu, plegats a «Més detalls». El pla de
// Protecció Civil no es repeteix: ja surt a dalt de tot.
function llistaMotius(trajecte, plans) {
  const motius = trajecte.motius.filter((m) => !(m.font === 'pc' && plans && plans.length));
  let visibles = motius.filter((m) => m.nivell === trajecte.nivell).slice(0, MAX_MOTIUS_VISIBLES);
  if (!visibles.length) visibles = motius.slice(0, 2);
  const fragment = document.createDocumentFragment();
  const llista = element('ul', 'motius');
  for (const m of visibles) llista.append(liMotiu(m, false));
  fragment.append(llista);
  const resta = motius.filter((m) => !visibles.includes(m));
  if (resta.length || visibles.some((m) => m.detall)) {
    const plec = element('details', 'mes-detalls');
    plec.append(element('summary', null, 'Més detalls'));
    const tot = element('ul', 'motius');
    for (const m of [...visibles, ...resta]) tot.append(liMotiu(m, true));
    plec.append(tot);
    fragment.append(plec);
  }
  return fragment;
}

// Comentari de l'agent diari, només si encara val (el programa dona els
// mateixos nivells que quan es va escriure) i és del moment del dia que toca.
function comentari(dades, mode) {
  const c = dades.comentari;
  if (!c || !c.vigent || c.mode !== mode) return null;
  const p = element('p', 'comentari');
  p.append(element('strong', null, `Valoració feta amb IA (${horaCurta(c.generat)}): `));
  p.append(document.createTextNode(c.text));
  return p;
}

// Matí: el mitjà del dia.
function blocDecisio(dades) {
  const v = TEXT_MITJA[dades.decisio.mitja];
  const sec = element('section', 'decisio targeta ' + dades.decisio.mitja);
  sec.setAttribute('aria-label', `Recomanació d\u2019avui: ${v.titol}`);
  sec.append(element('h2', 'data', nomDia(dades.dia)));
  sec.append(element('p', 'veredicte', v.titol));
  sec.append(element('p', 'frase', v.frase));
  sec.append(element('p', 'nota', notaDecisio(dades.decisio, dades.anada.fi)
    + (dades.decisio.per_la_ia ? ' La valoració de la IA l\u2019ha fet més prudent que el càlcul.' : '')));
  const c = comentari(dades, 'mati');
  if (c) sec.append(c);
  return sec;
}

// Tarda: només el temps de la tornada, sense recomanar mitjà.
function blocTornada(dades) {
  const t = dades.tornada;
  const risc = TEXT_RISC[t.nivell];
  const sec = element('section', 'decisio targeta ' + t.nivell + (t.passat ? ' passat' : ''));
  sec.setAttribute('aria-label', `Tornada: risc de pluja ${risc}`);
  sec.append(element('h2', 'data', nomDia(dades.dia)));
  const cap = element('p', 'trajecte', `Tornada · ${t.inici}\u2013${t.fi}`);
  if (t.passat) cap.append(element('span', 'etiqueta-passat', 'Ja ha passat'));
  sec.append(cap);
  sec.append(element('p', 'veredicte', 'Risc de pluja: ' + risc));
  const temps = liniaTemps(t.temps);
  if (temps) sec.append(element('p', 'frase', temps));
  const c = comentari(dades, 'tarda');
  if (c) sec.append(c);
  sec.append(element('h3', 'perque', 'Per què'), llistaMotius(t, dades.plans));
  return sec;
}

function targeta(nom, trajecte, plans) {
  const risc = TEXT_RISC[trajecte.nivell];
  const art = element('article', 'targeta ' + trajecte.nivell + (trajecte.passat ? ' passat' : ''));
  art.setAttribute('aria-label', `${nom}: risc de pluja ${risc}`);
  const cap = element('h3', 'trajecte', `${nom} · ${trajecte.inici}\u2013${trajecte.fi}`);
  if (trajecte.passat) cap.append(element('span', 'etiqueta-passat', 'Ja ha passat'));
  art.append(cap);
  art.append(element('p', 'risc', 'Risc de pluja: ' + risc));
  const temps = liniaTemps(trajecte.temps);
  if (temps) art.append(element('p', 'temps', temps));
  art.append(llistaMotius(trajecte, plans));
  return art;
}

// Franja activa ara, segons l'horari: des de la primera actualització fins
// que s'ha publicat la darrera. Si no n'hi ha cap, null.
function franjaActiva(horari, ara = new Date()) {
  const marge = ((horari.desfase_min || 0) + ESPERA_PUBLICACIO_MIN) * 60000;
  for (const [inici, fi] of horari.trams) {
    const franja = { inici: avuiA(inici), fins: new Date(avuiA(fi).getTime() + marge) };
    if (ara >= franja.inici && ara < franja.fins) return franja;
  }
  return null;
}

// Quan torna a informar: la franja que acaba de començar (si les seves dades
// encara no han arribat), la propera d'avui o la primera de demà.
function properaFranja(horari, ara = new Date()) {
  const activa = franjaActiva(horari, ara);
  const avui = activa ? activa.inici : horari.trams.map(([inici]) => avuiA(inici)).find((t) => t > ara);
  if (avui) return { dia: 'avui', hora: horaCurta(avui) };
  return { dia: 'demà', hora: horari.trams[0][0] };
}

// Fora de les franges: quan torna a informar i l'enllaç al temps a casa.
function blocFora(horari) {
  const p = properaFranja(horari);
  const sec = element('section', 'decisio targeta fora');
  sec.setAttribute('aria-label', 'Fora d\u2019horari');
  sec.append(element('h2', 'data', 'Propera actualització'));
  sec.append(element('p', 'veredicte', `${p.dia === 'avui' ? 'Avui' : 'Demà'} a les ${p.hora}`));
  const franges = horari.trams.map(([a, b]) => `de ${a} a ${b}`).join(' i ');
  sec.append(element('p', 'frase', `Aquesta pàgina només informa del trajecte ${franges}.`));
  const mes = element('p', 'frase');
  const enllac = element('a', null, 'el temps a casa');
  enllac.href = 'casa.html';
  mes.append('Mentrestant, pots consultar ', enllac, '.');
  sec.append(mes);
  return sec;
}

let repinta = null;

function pinta(dades) {
  const cont = $('dies');
  clearTimeout(repinta);
  const franja = franjaActiva(dades.horari);
  // Fora de franja, o dades d'abans que comencés (la primera actualització
  // encara no ha arribat): no es mostra res del trajecte.
  if (!franja || new Date(dades.generat) < franja.inici) {
    cont.replaceChildren(blocFora(dades.horari));
    $('horari').hidden = true;
    // Dins de la franja, si l'actualització no arriba, es diu.
    if (franja) pintaHorari(dades);
    else $('avis-dades').hidden = true;
    posaVersio(dades.versio);
    return;
  }
  // En acabar la franja, la pàgina passa sola a dir quan torna.
  repinta = setTimeout(() => pinta(dades), franja.fins - new Date());
  $('horari').hidden = false;
  const tarda = new Date() >= avuiA(dades.anada.fi) && dades.dia === new Date().toLocaleDateString('sv');
  if (tarda) {
    cont.replaceChildren(blocTornada(dades));
  } else {
    cont.replaceChildren(blocDecisio(dades));
    cont.append(element('h2', 'perque', 'Per què'));
    const graella = element('div', 'graella');
    graella.append(targeta('Anada', dades.anada, dades.plans), targeta('Tornada', dades.tornada, dades.plans));
    cont.append(graella);
  }
  const plans = blocPlans(dades.plans);
  if (plans) cont.prepend(plans);
  pintaHorari(dades);
  posaVersio(dades.versio);
}

carrega('dades.json', pinta, () => {
  $('dies').replaceChildren(element('p', 'avis', 'No s\u2019ha pogut carregar la previsió. Torna-ho a provar d\u2019aquí a una estona.'));
});
