// SPDX-License-Identifier: AGPL-3.0-or-later
// «Si surts» (ADR 0029): per a qui surt de Montflorit a una hora i torna a una
// altra, com anirà cada mitjà, quina roba cal, consells i si circulen els
// trens. Tot surt de la previsió hora a hora de casa.json (o, a la web
// pública, montflorit.json): no cal res més del servidor que l'índex UV i
// l'estat dels trens.

const FITXER_DADES = document.documentElement.dataset.dades || 'casa.json';
const TORNADA_PER_DEFECTE_H = 3;

// Llindars de pluja: els del trajecte (config.py), comprovats amb dades.
const PROB_RISC = 0.2;
const PROB_PLUJA = 0.5;
const MM_RISC = 0.2;
const MM_PLUJA = 1;
// Vent (ratxes, km/h) i fred (°C) per mitjà: [compte, millor no].
const LLINDARS = {
  peu: { ratxa: [null, 70], fred: [null, null] },
  bici: { ratxa: [40, 50], fred: [3, 1] },
  moto: { ratxa: [50, 70], fred: [3, 1] },
  cotxe: { ratxa: [90, null], fred: [null, null] },
  public: { ratxa: [null, null], fred: [null, null] },
};
const VELOCITAT = { peu: 0, bici: 18, moto: 45, cotxe: 0, public: 0 };
const CAPES_DIFERENCIA = 8;
const CANVI_TEMPERATURA = 6;
const CALOR = 32;
const UV_MINIM = 3;
const ORDRE = ['neutre', 'be', 'compte', 'no'];

function avisPluja(f) {
  return (f.avisos || []).some((a) => a.tipus.some((t) => t === 'pluja' || t === 'tempestes'));
}

// Risc de pluja en una hora: el mateix que «moja» de casa.py.
function mulla(f) {
  return (f.probabilitat || 0) >= PROB_RISC || (f.pluja_mm || 0) >= MM_RISC || f.plou_ara || avisPluja(f);
}

function plouClar(f) {
  return (f.probabilitat || 0) >= PROB_PLUJA || (f.pluja_mm || 0) >= MM_PLUJA || f.plou_ara || avisPluja(f);
}

function hora(f) {
  return new Date(f.hora).getHours();
}

// Temperatura que es nota a la velocitat del mitjà (índex d'Environment
// Canada, el de la roba del trajecte): només amb 10 °C o menys i en marxa.
function esNota(t, kmh) {
  if (t > 10 || kmh < 5) return t;
  const v = kmh ** 0.16;
  return 13.12 + 0.6215 * t - 11.37 * v + 0.3965 * t * v;
}

function graus(t) {
  return `${Math.round(t)} °C`;
}

// On passa: «a l'anada (17 h)», «a la tornada (21 h)» o «a l'anada i a la tornada».
function quan(anada, tornada, cond) {
  const a = cond(anada);
  const t = cond(tornada);
  if (a && t) return T('a l’anada i a la tornada');
  if (a) return T`a l’anada (${hora(anada)} h)`;
  return T`a la tornada (${hora(tornada)} h)`;
}

// Veredicte d'un mitjà: {nivell: be|compte|no, motius: [...]}.
function avalua(mitja, tram, trens) {
  const anada = tram[0];
  const tornada = tram[tram.length - 1];
  const viatge = [anada, tornada];
  const ll = LLINDARS[mitja];
  const res = { nivell: 'be', motius: [] };
  const puja = (nivell, motiu) => {
    if (ORDRE.indexOf(nivell) > ORDRE.indexOf(res.nivell)) res.nivell = nivell;
    res.motius.push(motiu);
  };
  const ratxa = Math.max(...viatge.map((f) => f.ratxa || 0));
  const temps = viatge.map((f) => f.temperatura).filter((t) => t != null);
  const tMin = temps.length ? Math.min(...temps) : null;

  if (mitja === 'bici' || mitja === 'moto') {
    if (viatge.some(plouClar)) puja('no', T`Pluja probable ${quan(anada, tornada, plouClar)}.`);
    else if (viatge.some(mulla)) {
      puja('compte', mitja === 'moto' ? T`Pot ploure ${quan(anada, tornada, mulla)}: porta l’impermeable.`
        : T`Pot ploure ${quan(anada, tornada, mulla)}.`);
    }
  }
  if (ll.ratxa[1] != null && ratxa >= ll.ratxa[1]) puja('no', T`Ratxes de vent de fins a ${Math.round(ratxa)} km/h.`);
  else if (ll.ratxa[0] != null && ratxa >= ll.ratxa[0]) puja('compte', T`Ratxes de vent de fins a ${Math.round(ratxa)} km/h.`);
  if (tMin != null && ll.fred[1] != null && tMin <= ll.fred[1]) puja('no', T`${graus(tMin)}: hi pot haver gel.`);
  else if (tMin != null && ll.fred[0] != null && tMin <= ll.fred[0]) puja('compte', T`${graus(tMin)}: compte amb el gel a primera hora.`);
  if (mitja === 'peu' && tram.some(mulla)) puja('compte', T('Pot ploure mentre ets fora: porta paraigua.'));
  if (mitja === 'public') return avaluaPublic(trens);
  if (!res.motius.length) res.motius.push(T('Sense pluja ni vent fort.'));
  return res;
}

// El transport públic, segons els trens de Cerdanyola: tots circulen, algun
// té incidències o no en circula cap. Dels busos no hi ha dades en temps real.
function avaluaPublic(trens) {
  const deDia = (trens || []).filter((l) => l.estat !== 'fora_horari' && l.estat !== 'sense_dades');
  if (!deDia.length) {
    const nit = (trens || []).some((l) => l.estat === 'fora_horari');
    return { nivell: 'neutre', etiqueta: nit ? 'Fora d’horari' : 'Sense dades',
      motius: [nit ? T('A aquesta hora no circulen trens.') : T('Ara no hi ha dades dels trens.')] };
  }
  const malament = deDia.filter((l) => l.estat !== 'circula');
  if (!malament.length) return { nivell: 'be', motius: [T('Cap incidència als trens de Cerdanyola.')], detall: true };
  const quines = malament.map((l) => `${l.linia} ${TD(TEXT_ESTAT[l.estat]).toLowerCase()}`).join(', ');
  const cap = deDia.every((l) => l.estat === 'sense_trens' || l.estat === 'bus');
  return { nivell: cap ? 'no' : 'compte', etiqueta: cap ? 'Sense trens' : 'Amb incidències',
    motius: [T`Trens: ${quines}.`], detall: true };
}

// Roba per a un mitjà, segons la temperatura més baixa de l'anada i la
// tornada i el fred a la seva velocitat (com la del trajecte).
function roba(mitja, tram, pluja) {
  const viatge = [tram[0], tram[tram.length - 1]];
  const temps = viatge.map((f) => f.temperatura).filter((t) => t != null);
  if (!temps.length) return '';
  const tMin = Math.min(...temps);
  const tMax = Math.max(...temps);
  const s = esNota(tMin, VELOCITAT[mitja]);
  const parts = [];
  if (mitja === 'moto') {
    if (s < 0) parts.push(T('Roba de moto d’hivern tèrmica, guants d’hivern i tub de coll.'));
    else if (tMin <= 10) parts.push(T('Jaqueta de moto d’hivern, guants d’hivern i tub de coll.'));
    else if (tMin <= 17) parts.push(T('Jaqueta de moto amb folre i guants d’entretemps.'));
    else if (tMin <= 24) parts.push(T('Jaqueta de moto de mitja temporada i guants d’entretemps.'));
    else parts.push(T('Jaqueta de moto d’estiu, ventilada, i guants d’estiu.'));
  } else if (mitja === 'bici') {
    if (s <= 0) parts.push(T('Jaqueta d’abric, guants i tub de coll.'));
    else if (s <= 10) parts.push(T('Jaqueta tallavent amb una capa a sota, i guants.'));
    else if (tMin <= 17) parts.push(T('Jaqueta tallavent lleugera.'));
    else if (tMin <= 24) parts.push(T('Màniga llarga o una jaqueta molt lleugera.'));
    else parts.push(T('Roba d’estiu.'));
  } else if (tMin <= 0) parts.push(T('Abric, guants i gorra.'));
  else if (tMin <= 10) parts.push(T('Abric.'));
  else if (tMin <= 17) parts.push(T('Jaqueta.'));
  else if (tMin <= 24) parts.push(T('Jaqueta lleugera o jersei.'));
  else parts.push(T('Roba d’estiu.'));
  if (VELOCITAT[mitja] && Math.round(s) < Math.round(tMin)) {
    parts.push(T`A ${VELOCITAT[mitja]} km/h, ${graus(tMin)} es noten com ${graus(s)}.`);
  }
  if (tMax - tMin >= CAPES_DIFERENCIA) parts.push(T`De ${graus(tMin)} a ${graus(tMax)}: millor capes.`);
  if (pluja && (mitja === 'moto' || mitja === 'bici')) parts.push(T('Impermeable.'));
  return parts.join(' ');
}

const NIVELL_UV = [[11, 'extrem'], [8, 'molt alt'], [6, 'alt'], [3, 'moderat']];

// Consells per a tota la sortida: pluja que comença o s'acaba, canvi de
// temperatura, sol, nit i calor.
function consells(tram, ara) {
  const res = [];
  const mullat = tram.map(mulla);
  if (!mullat[0] && mullat.some(Boolean)) {
    const f = tram[mullat.indexOf(true)];
    res.push(T`A partir de les ${hora(f)} h, risc de pluja.`);
  } else if (mullat[0] && !mullat.every(Boolean)) {
    res.push(T`Cap a les ${hora(tram[mullat.indexOf(false)])} h s’acaba el risc de pluja.`);
  }
  const amb = tram.filter((f) => f.temperatura != null);
  if (amb.length) {
    const fMin = amb.reduce((a, b) => (b.temperatura < a.temperatura ? b : a));
    const fMax = amb.reduce((a, b) => (b.temperatura > a.temperatura ? b : a));
    if (fMax.temperatura - fMin.temperatura >= CANVI_TEMPERATURA) {
      res.push(T`La temperatura va de ${graus(fMin.temperatura)} (${hora(fMin)} h) a ${graus(fMax.temperatura)} (${hora(fMax)} h).`);
    }
    if (fMax.temperatura >= CALOR) {
      res.push(T`Calor: fins a ${graus(fMax.temperatura)}. Porta aigua i evita el sol de les hores centrals.`);
    }
  }
  const uv = tram.filter((f) => f.uv != null).reduce((a, b) => (!a || b.uv > a.uv ? b : a), null);
  if (uv && uv.uv >= UV_MINIM) {
    const nivell = NIVELL_UV.find(([minim]) => uv.uv >= minim)[1];
    res.push(T`Protector solar: índex UV ${TD(nivell)} (${Math.round(uv.uv)}) cap a les ${hora(uv)} h.`);
  }
  // De nit: el sol per sota de l'horitzó en sortir o en tornar.
  const surt = new Date(Math.max(new Date(tram[0].hora).getTime(), ara.getTime()));
  const torna = new Date(tram[tram.length - 1].hora);
  const nitSurt = alturaSol(surt) < -0.8;
  const nitTorna = alturaSol(torna) < -0.8;
  if (nitSurt && nitTorna) res.push(T('Surts i tornes de nit: a peu, en bici o en patinet, roba visible i llum.'));
  else if (nitSurt) res.push(T('Surts de nit: a peu, en bici o en patinet, roba visible i llum.'));
  else if (nitTorna) res.push(T('Tornaràs de nit: a peu, en bici o en patinet, roba visible i llum.'));
  return res;
}

// --- Selectors d'hora ------------------------------------------------------------

function etiquetaHora(f, ara) {
  const d = new Date(f.hora);
  const text = horaCurta(d);
  return d.toDateString() === ara.toDateString() ? text : T`demà ${text}`;
}

function omple(select, opcions, triada) {
  select.replaceChildren(...opcions.map(([valor, text]) => {
    const o = element('option', null, text);
    o.value = valor;
    return o;
  }));
  if (opcions.some(([v]) => v === triada)) select.value = triada;
}

let DADES = null;

function pintaSelectors(hores, ara) {
  const surto = $('surto');
  const torno = $('torno');
  const abansSurto = surto.value;
  const abansTorno = torno.value;
  omple(surto, hores.slice(0, -1).map((f, i) => [f.hora, i === 0 ? T('Ara') : etiquetaHora(f, ara)]), abansSurto);
  const i = Math.max(0, hores.findIndex((f) => f.hora === surto.value));
  const per = Math.min(i + TORNADA_PER_DEFECTE_H, hores.length - 1);
  omple(torno, hores.slice(i + 1).map((f) => [f.hora, etiquetaHora(f, ara)]),
    abansTorno && abansTorno > surto.value ? abansTorno : hores[per].hora);
}

// --- Pintar ----------------------------------------------------------------------

// Noms que es tradueixen com les paraules de les dades (TD).
const MITJANS = [['peu', 'A peu', 'i-footprints'], ['bici', 'Bici o patinet', 'i-bike'],
  ['moto', 'Moto', 'i-motorbike'], ['cotxe', 'Cotxe', 'i-car'], ['public', 'Transport públic', 'i-train-front']];

// Els mitjans que cadascú vol veure, en aquest navegador. Es desa el que s'ha
// tret, perquè un mitjà nou surti marcat.
const CLAU_AMAGATS = 'meteo.mitjans-amagats';
function amagats() {
  try { return new Set(JSON.parse(localStorage.getItem(CLAU_AMAGATS)) || []); } catch (_) { return new Set(); }
}
function desaAmagats(conjunt) {
  try { localStorage.setItem(CLAU_AMAGATS, JSON.stringify([...conjunt])); } catch (_) {}
}

// L'explicació de les caselles surt fins que algú en desmarca una per primer
// cop: llavors ja se sap com funciona.
const CLAU_EXPLICAT = 'meteo.mitjans-explicat';
function explicat() {
  try { return localStorage.getItem(CLAU_EXPLICAT) === '1'; } catch (_) { return amagats().size > 0; }
}

function pintaTriats() {
  const caixa = $('triats');
  const fora = amagats();
  const explica = element('p', 'nota explica-triats',
    T('Toca un mitjà per deixar de veure’l; torna-hi a tocar per recuperar-lo. Es recorda en aquest dispositiu.'));
  explica.hidden = explicat() || fora.size > 0;
  for (const [clau, nom, icon] of MITJANS) {
    const etiqueta = element('label', 'xip');
    const casella = element('input');
    casella.type = 'checkbox';
    casella.value = clau;
    casella.checked = !fora.has(clau);
    casella.addEventListener('change', () => {
      const ara = amagats();
      if (casella.checked) ara.delete(clau); else ara.add(clau);
      desaAmagats(ara);
      if (!casella.checked) {
        try { localStorage.setItem(CLAU_EXPLICAT, '1'); } catch (_) {}
        explica.hidden = true;
      }
      if (DADES) {
        pintaTrens(DADES.trens);
        pintaSortida();
      }
    });
    etiqueta.append(casella, icona(icon), element('span', null, TD(nom)));
    caixa.append(etiqueta);
  }
  caixa.after(explica);
}
const TEXT_NIVELL = { be: 'Bé', compte: 'Compte', no: 'Millor no' };
const TEXT_ESTAT = {
  circula: 'Sense incidències', incidencies: 'Amb incidències', bus: 'Servei per carretera',
  sense_trens: 'Sense trens', fora_horari: 'Fora d’horari', sense_dades: 'Sense dades',
};
// On publica cada operador l'estat del servei: Rodalies, a la portada; FGC
// remet a la seva compte d'X; dels busos, la mobilitat de l'AMB.
const ESTAT_OPERADOR = {
  rodalies: { text: () => 'Rodalies', href: () => `https://rodalies.gencat.cat/${IDIOMA.codi === 'es' ? 'es' : 'ca'}/inici/` },
  fgc: { text: () => 'FGC', href: () => 'https://x.com/fgc' },
  amb: { text: () => T('Busos de l’AMB'), href: () => `https://www.amb.cat/${IDIOMA.codi === 'es' ? 'es/' : ''}web/mobilitat` },
};
const COLOR_ESTAT = {
  circula: 'be', incidencies: 'compte', bus: 'compte', sense_trens: 'no', fora_horari: 'neutre', sense_dades: 'neutre',
};

function pintaSortida() {
  const dades = DADES;
  const ara = new Date();
  const hores = dades.hores || [];
  const cont = $('sortida');
  if (hores.length < 2) {
    cont.replaceChildren(element('p', 'avis', T('Ara no hi ha previsió hora a hora.')));
    return;
  }
  const i = hores.findIndex((f) => f.hora === $('surto').value);
  const j = hores.findIndex((f) => f.hora === $('torno').value);
  const tram = hores.slice(i, j + 1);
  const trens = dades.trens && dades.trens.linies;
  const llista = element('ul', 'mitjans');
  const fora = amagats();
  for (const [clau, nom, icon] of MITJANS) {
    if (fora.has(clau)) continue;
    const v = avalua(clau, tram, trens);
    const li = element('li', 'mitja ' + v.nivell);
    const cap = element('p', 'mitja-cap');
    const titol = element('span', 'mitja-nom');
    titol.append(icona(icon), TD(nom));
    cap.append(titol, ' ', element('span', 'mitja-nivell', TD(v.etiqueta || TEXT_NIVELL[v.nivell])));
    li.append(cap, element('p', 'mitja-motiu', v.motius.join(' ')));
    // Els detalls de cada línia, al bloc «Trens ara» de sota: la fitxa no creix.
    if (v.detall && !$('trens').hidden) {
      const a = element('a', 'mitja-detall', T('Estat de cada línia ↓'));
      a.href = '#trens';
      const p = element('p', 'mitja-motiu');
      p.append(a);
      li.append(p);
    }
    const r = roba(clau, tram, v.nivell !== 'be' && [tram[0], tram[tram.length - 1]].some(mulla));
    if (r) li.append(element('p', 'mitja-roba', T`Roba: ${r}`));
    llista.append(li);
  }
  const parts = llista.children.length ? [llista]
    : [element('p', 'nota', T('Tria a dalt els mitjans que vols veure.'))];
  const cs = consells(tram, ara);
  if (cs.length) {
    const ul = element('ul', 'consells');
    for (const c of cs) ul.append(element('li', null, c));
    parts.push(ul);
  }
  cont.replaceChildren(...parts);
}

function pintaTrens(trens) {
  const sec = $('trens');
  if (!trens || !trens.linies || !trens.linies.length || amagats().has('public')) {
    sec.hidden = true;
    return;
  }
  const llista = $('llista-trens');
  llista.replaceChildren();
  for (const l of trens.linies) {
    const li = element('li', 'tren ' + COLOR_ESTAT[l.estat]);
    const cap = element('p', 'tren-cap');
    cap.append(element('span', 'tren-linia', l.linia), ' ', element('span', 'tren-estacio', TD(l.estacio)),
      ' ', element('span', 'tren-estat', TD(TEXT_ESTAT[l.estat])));
    li.append(cap);
    // Els avisos, tal com els publica l'operador: no es tradueixen.
    const textos = (l.avisos || []).map((a) => (IDIOMA.codi === 'es' ? a.es : a.ca) || a.ca || a.es);
    if (textos.length) {
      const plec = element('details', 'tren-avisos');
      plec.append(element('summary', null, l.operador === 'fgc' ? T('Avís d’FGC') : T('Avís de Rodalies')));
      for (const t of textos) plec.append(element('p', null, t));
      li.append(plec);
    }
    llista.append(li);
  }
  $('hora-trens').textContent = T`Dades de Renfe i d’FGC de les ${horaCurta(trens.hora)}, consultades automàticament: l’autor no es fa responsable de la seva exactitud.`;
  // On publiquen els operadors l'estat del servei.
  const p = $('estat-operadors');
  p.replaceChildren(T('Estat del servei: '));
  Object.values(ESTAT_OPERADOR).forEach((e, n) => {
    const a = element('a', null, e.text());
    a.href = e.href();
    a.target = '_blank';
    a.rel = 'noopener';
    p.append(...(n ? [' · ', a] : [a]));
  });
  sec.hidden = false;
}

function pinta(dades) {
  DADES = dades;
  const avisos = $('avisos');
  avisos.replaceChildren();
  const plans = blocPlans(dades.plans);
  if (plans) avisos.append(plans);
  if (dades.avisos && dades.avisos.length) avisos.append(element('p', 'avis', textAvisos(dades.avisos)));
  if (dades.hores && dades.hores.length >= 2) pintaSelectors(dades.hores, new Date());
  pintaTrens(dades.trens);
  pintaSortida();
  pintaHorari(dades);
  posaVersio(dades.versio);
}

pintaTriats();
$('surto').addEventListener('change', () => {
  pintaSelectors(DADES.hores, new Date());
  pintaSortida();
});
$('torno').addEventListener('change', pintaSortida);
$('hores').addEventListener('submit', (e) => e.preventDefault());

carrega(FITXER_DADES, pinta, () => {
  $('sortida').replaceChildren(element('p', 'avis', T('No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.')));
});
