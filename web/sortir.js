// SPDX-License-Identifier: AGPL-3.0-or-later
// «Si surts» (ADR 0029): per a qui surt de Montflorit a una hora i torna a una
// altra, com anirà cada mitjà, quina roba cal, consells, si circulen els
// trens i el trànsit de prop. Tot surt de la previsió hora a hora de casa.json
// (o, a la web pública, montflorit.json): no cal res més del servidor que
// l'índex UV, l'estat dels trens i les incidències de trànsit (ADR 0052).

const FITXER_DADES = document.documentElement.dataset.dades || 'casa.json';
const TORNADA_PER_DEFECTE_H = 3;

// Llindars de pluja, iguals per a tots els mitjans (ADR 0069): només la
// probabilitat, que ja porta els models, el radar, les estacions i el que
// aprèn el programa; sense probabilitat, els mil·límetres. Amb «millor no» ha
// de ploure almenys 2 de cada 3 vegades, i amb «bé», com a molt 1 de cada 100:
// el NAS els aprèn cada dia amb el que passa a Montflorit i arriben a les dades
// (sortir_llindars); aquests, els de partida (config.SORTIR_LLINDARS_PLUJA),
// per si no hi són. Dos jocs: per d'aquí a CURT_H hores o menys, i per a més
// tard, quan la previsió és menys segura. «pluja»: «millor no» en bici i moto,
// «compte» en cotxe; «risc»: «compte» en bici i moto i el paraigua a peu.
const LLINDARS_PLUJA_INICI = { curt: { pluja: 0.4, risc: 0.1 }, llarg: { pluja: 0.6, risc: 0.1 } };
const CURT_H = 3;
const MM_RISC = 0.2;
const MM_PLUJA = 1;
let llindarsPluja = LLINDARS_PLUJA_INICI;

// Els llindars d'una hora, segons quant falta perquè acabi (com antelacio_h del registre).
function llindars(f) {
  const h = (new Date(f.fins) - Date.now()) / 3.6e6;
  const banda = h <= CURT_H ? 'curt' : 'llarg';
  return { ...LLINDARS_PLUJA_INICI[banda], ...((llindarsPluja || {})[banda] || {}) };
}
// Vent (ratxes, km/h) i fred (°C) per mitjà: [compte, millor no].
const LLINDARS = {
  peu: { ratxa: [null, 70], fred: [null, null] },
  bici: { ratxa: [40, 50], fred: [3, 1] },
  moto: { ratxa: [50, 70], fred: [3, 1] },
  cotxe: { ratxa: [90, null], fred: [1, null] },
  public: { ratxa: [null, null], fred: [null, null] },
};
// Pluja en una hora (mm) per al cotxe: els llindars groc i taronja d'AEMET
// (config.RISC_LLINDARS pluja_1h): compte i millor no (auditoria del 08-10-2026).
const PLUJA_COTXE = [20, 40];
const VELOCITAT = { peu: 0, bici: 18, moto: 45, cotxe: 0, public: 0 };
const CANVI_TEMPERATURA = 6;
const CALOR = 32;
const UV_MINIM = 3;
const ORDRE = ['neutre', 'be', 'compte', 'no'];
const MITJANS_TRANSIT = ['cotxe', 'moto'];

function avisPluja(f) {
  return (f.avisos || []).some((a) => a.tipus.some((t) => t === 'pluja' || t === 'tempestes'));
}

// Risc de pluja en una hora: el mateix que «moja» de casa.py.
function mulla(f) {
  return sobre(f, llindars(f).risc, MM_RISC) || f.plou_ara || avisPluja(f);
}

// Una hora amb risc de pluja només per l'avís de l'AEMET: ni la probabilitat
// (que ja porta el radar), ni els models, ni les estacions hi veuen pluja. Es
// manté el que diu l'avís, però es diu clar (ADR 0008 i 0029).
function senseDades(f) {
  return !sobre(f, llindars(f).risc, MM_RISC) && !f.plou_ara;
}

function plouClar(f) {
  return plouRodes(f) || avisPluja(f);
}

// Sense probabilitat, manen els mil·límetres, com a la pàgina del temps.
// L'avís de l'AEMET tot sol porta a «compte», no a «no» (ADR 0047).
function sobre(f, prob, mm) {
  return f.probabilitat == null ? (f.pluja_mm || 0) >= mm : f.probabilitat >= prob;
}

function plouRodes(f) {
  return sobre(f, llindars(f).pluja, MM_PLUJA) || f.plou_ara;
}

function mullaRodes(f) {
  return mulla(f);
}

function nomesAvisRodes(f) {
  return senseDades(f);
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
function avalua(mitja, tram, trens, futur, transit) {
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

  const nomesAvis = (cond) => viatge.filter(cond).every(senseDades);
  if (mitja === 'bici' || mitja === 'moto') {
    if (viatge.some(plouRodes)) {
      puja('no', T`Pluja probable ${quan(anada, tornada, plouRodes)}.`);
    } else if (viatge.some(mullaRodes)) {
      const moto = mitja === 'moto';
      if (viatge.filter(mullaRodes).every(nomesAvisRodes)) {
        puja('compte', moto
          ? T`Avís de l’AEMET per pluja ${quan(anada, tornada, mullaRodes)}: ni el radar, ni les estacions, ni els models hi veuen pluja. Per si de cas, porta l’impermeable.`
          : T`Avís de l’AEMET per pluja ${quan(anada, tornada, mullaRodes)}: ni el radar, ni les estacions, ni els models hi veuen pluja.`);
      } else {
        puja('compte', moto ? T`Pot ploure ${quan(anada, tornada, mullaRodes)}: porta l’impermeable.`
          : T`Pot ploure ${quan(anada, tornada, mullaRodes)}.`);
      }
    }
  }
  if (mitja === 'cotxe') {
    // Amb pluja el cotxe no surt «bé» per defecte: forta o molt forta segons
    // AEMET, probable, o possible (que no puja el nivell però es diu).
    // Amb la xifra, no amb «forta»: per a Meteocat la pluja forta comença a 40 mm (ADR 0043).
    const forta = (n) => (f) => (f.pluja_mm || 0) >= PLUJA_COTXE[n];
    const mmMax = Math.round(Math.max(...viatge.map((f) => f.pluja_mm || 0)));
    if (viatge.some(forta(1))) puja('no', T`Fins a ${mmMax}\u00a0mm de pluja en una hora ${quan(anada, tornada, forta(1))}: millor no agafar el cotxe.`);
    else if (viatge.some(forta(0))) puja('compte', T`Fins a ${mmMax}\u00a0mm de pluja en una hora ${quan(anada, tornada, forta(0))}: condueix amb compte.`);
    else if (viatge.some(plouClar)) {
      // El nivell, el de sempre; el text, el mateix que en moto (ADR 0047): «Pluja
      // probable» només si la probabilitat ho diu, i l'avís, si és l'únic que la veu.
      const dades = (f) => sobre(f, llindars(f).risc, MM_RISC) || f.plou_ara;
      if (viatge.some(plouRodes)) puja('compte', T`Pluja probable ${quan(anada, tornada, plouRodes)}: condueix amb compte.`);
      else if (viatge.some(dades)) puja('compte', T`Pot ploure ${quan(anada, tornada, dades)}: condueix amb compte.`);
      else if (viatge.some(avisPluja)) {
        puja('compte', T`Avís de l’AEMET per pluja ${quan(anada, tornada, avisPluja)}: ni el radar, ni les estacions, ni els models hi veuen pluja. Condueix amb compte.`);
      } else puja('compte', T`Pot ploure ${quan(anada, tornada, plouClar)}: condueix amb compte.`);
    } else if (viatge.some(mullaRodes)) res.motius.push(T`Pot ploure ${quan(anada, tornada, mullaRodes)}.`);
  }
  if (ll.ratxa[1] != null && ratxa >= ll.ratxa[1]) puja('no', T`Ratxes de vent de fins a ${Math.round(ratxa)} km/h.`);
  else if (ll.ratxa[0] != null && ratxa >= ll.ratxa[0]) puja('compte', T`Ratxes de vent de fins a ${Math.round(ratxa)} km/h.`);
  if (tMin != null && ll.fred[1] != null && tMin <= ll.fred[1]) puja('no', T`${graus(tMin)}: hi pot haver gel.`);
  else if (tMin != null && ll.fred[0] != null && tMin <= ll.fred[0]) puja('compte', T`${graus(tMin)}: compte amb el gel a primera hora.`);
  if (mitja === 'peu' && tram.some(mulla)) {
    puja('compte', tram.filter(mulla).every(senseDades)
      ? T('Avís de l’AEMET per pluja mentre ets fora: ni el radar, ni les estacions, ni els models hi veuen pluja. Per si de cas, porta paraigua.')
      : T('Pot ploure mentre ets fora: porta paraigua.'));
  }
  if (mitja === 'public') return avaluaPublic(trens, futur);
  if (!res.motius.length) res.motius.push(T('Sense pluja ni vent fort.'));
  // El trànsit és el d'ara: només compta si surts ara (ADR 0052).
  if (MITJANS_TRANSIT.includes(mitja) && !futur) {
    const greus = (transit || []).filter((i) => i.tipus === 'retencio' && i.nivell >= NIVELL_TRANSIT);
    if (greus.length) {
      const carreteres = [...new Set(greus.map((i) => i.carretera))].join(', ');
      puja('compte', T`Ara hi ha retencions o talls a menys de 5\u00a0km: ${carreteres}.`);
    }
  }
  return res;
}

// El transport públic, segons els trens de Cerdanyola: tots circulen, algun
// té incidències o no en circula cap. Dels busos no hi ha dades en temps real.
function avaluaPublic(trens, futur) {
  const res = estatPublic(trens);
  // Les dades dels trens són les d'ara: si la sortida triada és més tard, es diu
  // (auditoria del 07-10-2026).
  if (futur) res.motius.push(T('Són els trens d’ara, no els de l’hora triada.'));
  return res;
}

function estatPublic(trens) {
  const senseDades = (trens || []).filter((l) => l.estat === 'sense_dades');
  const deDia = (trens || []).filter((l) => l.estat !== 'fora_horari' && l.estat !== 'sense_dades');
  const noms = (ls) => ls.map((l) => l.linia).join(', ');
  if (!deDia.length) {
    const nit = (trens || []).some((l) => l.estat === 'fora_horari');
    return { nivell: 'neutre', etiqueta: nit ? 'Fora d’horari' : 'Sense dades',
      motius: [nit ? T('A aquesta hora no circulen trens.') : T('Ara no hi ha dades dels trens.')] };
  }
  const malament = deDia.filter((l) => l.estat !== 'circula');
  // Si falten dades d'alguna línia, no es pot dir que tot vagi bé (auditoria del 08-10-2026).
  if (!malament.length) {
    if (!senseDades.length) return { nivell: 'be', motius: [T('Cap incidència als trens de Cerdanyola.')] };
    return { nivell: 'neutre', etiqueta: 'Dades parcials',
      motius: [T`${noms(deDia)} sense incidències; de ${noms(senseDades)} ara no hi ha dades.`] };
  }
  const quines = malament.map((l) => `${l.linia} ${TD(TEXT_ESTAT[l.estat]).toLowerCase()}`).join(', ');
  const cap = deDia.every((l) => l.estat === 'sense_trens' || l.estat === 'bus');
  const motius = [T`Trens: ${quines}.`];
  if (senseDades.length) motius.push(T`De ${noms(senseDades)} ara no hi ha dades.`);
  return { nivell: cap ? 'no' : 'compte', etiqueta: cap ? 'Sense trens' : 'Amb incidències', motius };
}

// Peça per a una temperatura que es nota (arrodonida) i un mitjà.
function peca(mitja, s) {
  if (mitja === 'moto') {
    if (s < 0) return T('Roba de moto d’hivern tèrmica, guants d’hivern i tub de coll.');
    if (s <= 10) return T('Jaqueta de moto d’hivern, guants d’hivern i tub de coll.');
    if (s <= 17) return T('Jaqueta de moto amb folre i guants d’entretemps.');
    if (s <= 24) return T('Jaqueta de moto de mitja temporada i guants d’entretemps.');
    return T('Jaqueta de moto d’estiu, ventilada, i guants d’estiu.');
  }
  if (mitja === 'bici') {
    if (s <= 0) return T('Jaqueta d’abric, guants i tub de coll.');
    if (s <= 10) return T('Jaqueta tallavent amb una capa a sota, i guants.');
    if (s <= 17) return T('Jaqueta tallavent lleugera.');
    if (s <= 20) return T('Màniga llarga o una jaqueta molt lleugera.');
    return T('Màniga curta.');
  }
  if (s <= 0) return T('Abric, gorro, bufanda i guants.');
  if (s <= 5) return T('Abric, bufanda i guants.');
  if (s <= 10) return T('Abric.');
  if (s <= 14) return T('Jaqueta.');
  if (s <= 17) return T('Jaqueta lleugera o jersei.');
  if (s <= 20) return T('Màniga llarga o jersei fi.');
  if (s <= 24) return T('Màniga curta o màniga llarga fina.');
  return T('Màniga curta.');
}

// Roba per a un mitjà, a l'anada i a la tornada, amb el fred que es nota: a la
// velocitat del mitjà en bici i en moto, i amb el vent previst a peu (també
// fins al cotxe o a l'estació). Si la tornada demana una altra peça, es diu a
// part; en moto, una sola jaqueta per a tota la sortida, la del moment més fred.
function roba(mitja, tram, pluja) {
  const extrems = [tram[0], tram[tram.length - 1]]
    .filter((f) => f.temperatura != null)
    .map((f) => {
      const kmh = VELOCITAT[mitja] || f.vent || 0;
      return { f, t: f.temperatura, kmh, s: Math.round(esNota(f.temperatura, kmh)) };
    });
  if (!extrems.length) return '';
  const fred = extrems.reduce((a, b) => (b.s < a.s ? b : a));
  const [anada, tornada] = mitja === 'moto' ? [fred, fred] : [extrems[0], extrems[extrems.length - 1]];
  const parts = [peca(mitja, anada.s)];
  const altra = peca(mitja, tornada.s);
  if (tram.length > 1 && altra !== parts[0]) {
    parts.push(T`A la tornada (${hora(tornada.f)} h, ${graus(tornada.t)}): ${altra[0].toLowerCase() + altra.slice(1)}`);
  }
  if (fred.s < Math.round(fred.t)) {
    parts.push(VELOCITAT[mitja] ? T`A ${VELOCITAT[mitja]} km/h, ${graus(fred.t)} es noten com ${graus(fred.s)}.`
      : T`Amb vent de ${Math.round(fred.kmh)} km/h, ${graus(fred.t)} es noten com ${graus(fred.s)}.`);
  }
  if (pluja && (mitja === 'moto' || mitja === 'bici')) parts.push(T('Impermeable.'));
  return parts.join(' ');
}

const NIVELL_UV = [[11, 'extrem'], [8, 'molt alt'], [6, 'alt'], [3, 'moderat']];

// Consells per a tota la sortida: pluja que comença o s'acaba, canvi de
// temperatura, sol, nit i calor.
function consells(tram, ara) {
  const res = [];
  const mullat = tram.map(mulla);
  const avis = tram.filter(mulla).every(senseDades);
  if (!mullat[0] && mullat.some(Boolean)) {
    const f = tram[mullat.indexOf(true)];
    res.push(avis ? T`A partir de les ${hora(f)} h, avís de l’AEMET per pluja.`
      : T`A partir de les ${hora(f)} h, risc de pluja.`);
  } else if (mullat[0] && !mullat.every(Boolean)) {
    const h = hora(tram[mullat.indexOf(false)]);
    res.push(avis ? T`Cap a les ${h} h s’acaba l’avís de l’AEMET.` : T`Cap a les ${h} h s’acaba el risc de pluja.`);
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
    res.push(T`Protector solar, gorra i ulleres de sol: índex UV ${TD(nivell)} (${Math.round(uv.uv)}) cap a les ${hora(uv)} h.`);
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

// Les hores poden arribar a l'endemà de demà al matí (la previsió acaba el
// tram de nit, ADR 0041): llavors, amb el dia de la setmana.
function etiquetaHora(f, ara) {
  const d = new Date(f.hora);
  const text = horaCurta(d);
  if (d.toDateString() === ara.toDateString()) return text;
  const dia = nomDiaCurt(d, ara);
  return dia === T('demà') ? T`demà ${text}` : `${dia} ${text}`;
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
      if (DADES) pintaSortida();
    });
    etiqueta.append(casella, icona(icon), element('span', null, TD(nom)));
    caixa.append(etiqueta);
  }
  caixa.after(explica);
}
const TEXT_NIVELL = { be: 'Bé', compte: 'Compte', no: 'Millor no' };

// Amb un pla de Protecció Civil en alerta o emergència, els veredictes no
// canvien (surten de la pluja i el vent previstos, ADR 0008), però a sobre es
// diu ben clar què demana el pla (Juanjo, 07-10-2026). Null si no n'hi ha cap.
function avisPlaSortida(plans) {
  const pla = (plans || []).find((p) => p.fase === 'emergència') || (plans || []).find((p) => p.fase === 'alerta');
  if (!pla) return null;
  // El pla ja surt sencer a «Avisos actius»: aquí només el que cal saber
  // dels veredictes (Juanjo, 08-10-2026: «sale repetido»).
  return pla.fase === 'emergència'
    ? T('El consell de cada mitjà surt del temps previst i del trànsit: no té en compte l’emergència de Protecció Civil (vegeu l’avís de dalt).')
    : T('El consell de cada mitjà surt del temps previst i del trànsit: no té en compte l’alerta de Protecció Civil (vegeu l’avís de dalt).');
}

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
  const transit = dades.transit && dades.transit.incidencies;
  const llista = element('ul', 'mitjans');
  const fora = amagats();
  for (const [clau, nom, icon] of MITJANS) {
    if (fora.has(clau)) continue;
    const v = avalua(clau, tram, trens, i > 0, transit);
    const li = element('li', 'mitja ' + v.nivell);
    const cap = element('p', 'mitja-cap');
    const titol = element('span', 'mitja-nom');
    titol.append(icona(icon), TD(nom));
    cap.append(titol, ' ', element('span', 'mitja-nivell', TD(v.etiqueta || TEXT_NIVELL[v.nivell])));
    li.append(cap, element('p', 'mitja-motiu', v.motius.join(' ')));
    const plujaViatge = clau === 'moto' || clau === 'bici' ? mullaRodes : mulla;
    const r = roba(clau, tram, v.nivell !== 'be' && [tram[0], tram[tram.length - 1]].some(plujaViatge));
    if (r) li.append(element('p', 'mitja-roba', T`Roba: ${r}`));
    // Les incidències, dins de la fitxa i plegades, sempre al final: no cal
    // anar a cap altre lloc de la pàgina (Juanjo, 09-10-2026).
    if (clau === 'public' && trens && trens.length) {
      li.append(plec('trens', T('Estat de cada línia'), blocTrens(dades.trens)));
    }
    if (MITJANS_TRANSIT.includes(clau) && dades.transit) {
      const n = (transit || []).length;
      if (!n) li.append(element('p', 'mitja-roba', T('Trànsit ara: cap incidència a menys de 5\u00a0km.')));
      else {
        li.append(plec(`transit-${clau}`, n === 1 ? T('Trànsit ara: 1 incidència a menys de 5\u00a0km') : T`Trànsit ara: ${n} incidències a menys de 5\u00a0km`,
          blocTransit(dades.transit)));
      }
    }
    llista.append(li);
  }
  const parts = llista.children.length ? [llista]
    : [element('p', 'nota', T('Tria a dalt els mitjans que vols veure.'))];
  const pla = avisPlaSortida(dades.plans);
  if (pla) parts.unshift(element('p', 'avis avis-pc', pla));
  const cs = consells(tram, ara);
  if (cs.length) {
    const ul = element('ul', 'consells');
    for (const c of cs) ul.append(element('li', null, c));
    parts.push(ul);
  }
  cont.replaceChildren(...parts);
}

// Plec d'una fitxa. Es recorda quins estan oberts mentre no es recarrega la
// pàgina: canviar l'hora o els mitjans torna a pintar les fitxes.
const PLECS_OBERTS = new Set();
function plec(clau, titol, peces) {
  const d = element('details', 'mitja-plec');
  d.id = clau;
  d.open = PLECS_OBERTS.has(clau);
  d.addEventListener('toggle', () => (d.open ? PLECS_OBERTS.add(clau) : PLECS_OBERTS.delete(clau)));
  d.append(element('summary', null, titol), ...peces);
  return d;
}

// Les franges que encara no han acabat: la primera és «Ara». Sense això, amb
// dades endarrerides (menys de 2 hores) «Ara» podia ser una hora ja passada
// (auditoria del 08-10-2026).
// «Si surts» fa servir el temps i, a més, l'índex UV (la roba), els trens i el trànsit.
const FONTS_SORTIR = [...FONTS_TEMPS, 'índex UV', 'trens', 'trànsit'];

function horesVigents(hores, ara) {
  return (hores || []).filter((f) => new Date(f.fins) > ara);
}

function pinta(dades) {
  dades = { ...dades, hores: horesVigents(dades.hores, new Date()) };
  DADES = dades;
  llindarsPluja = dades.sortir_llindars || LLINDARS_PLUJA_INICI;
  // A «Com es decideix», els llindars d'ara, que s'aprenen (ADR 0069).
  for (const banda of ['curt', 'llarg']) {
    for (const k of ['pluja', 'risc']) {
      const el = $(`ll-${banda}-${k}`);
      const v = ((llindarsPluja || {})[banda] || LLINDARS_PLUJA_INICI[banda])[k];
      if (el && v != null) el.textContent = String(Math.round(v * 100));
    }
  }
  // Dades de fa massa: només l'avís i on mirar (ADR 0031).
  const velles = dadesVelles(dades);
  for (const id of ['hores', 'triats']) $(id).hidden = velles;
  const explica = document.querySelector('.explica-triats');
  if (velles) {
    if (explica) explica.hidden = true;
    $('avisos').replaceChildren();
    $('sortida').replaceChildren(blocDadesVelles(dades));
    pintaHorari(dades, FONTS_SORTIR);
    posaVersio(dades.versio);
    return;
  }
  if (explica) explica.hidden = explicat() || amagats().size > 0;
  const avisos = $('avisos');
  avisos.replaceChildren();
  const actius = blocAvisos(dades);
  if (actius) avisos.append(actius);
  if (dades.hores && dades.hores.length >= 2) pintaSelectors(dades.hores, new Date());
  pintaSortida();
  obreDelEnllac();
  pintaHorari(dades, FONTS_SORTIR);
  posaVersio(dades.versio);
}

// Un enllaç a un plec (els avisos dels trens porten a «sortir.html#trens»):
// s'obre i s'hi va, només la primera vegada que es pinta.
let enllacFet = false;
function obreDelEnllac() {
  if (enllacFet) return;
  enllacFet = true;
  const desti = location.hash && document.getElementById(location.hash.slice(1));
  if (!desti || desti.tagName !== 'DETAILS') return;
  desti.open = true;
  desti.scrollIntoView({ block: 'center' });
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
