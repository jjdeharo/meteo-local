// SPDX-License-Identifier: AGPL-3.0-or-later
// Peces comunes de les dues pàgines: utilitats, horari d'actualització,
// versió i commutador de tema.

// Marge abans de dir que una actualització prevista no s'ha fet.
const MARGE_RETARD_MIN = 20;

const $ = (id) => document.getElementById(id);

// Idioma. La pàgina és en català; la pública en castellà (ADR 0025) carrega
// abans es.js, que deixa a IDIOMA les traduccions. Cada text que es veu passa
// per T, i cada paraula que ve a les dades (nivells, tipus d'avís, rumbs),
// per TD. Sense traducció, surt el text tal com està escrit aquí.
var IDIOMA = IDIOMA || { codi: 'ca', textos: {}, dades: {} };

// T`Ara a ${lloc}` o T('No plou'): el text en l'idioma de la pàgina. La clau
// és el text català amb {0}, {1}… on van els valors; la traducció pot ser un
// text amb les mateixes marques o una funció que rep els valors.
function T(parts, ...valors) {
  const trossos = typeof parts === 'string' ? [parts] : parts;
  const clau = trossos.reduce((acc, tros, i) => `${acc}{${i - 1}}${tros}`);
  const traduccio = IDIOMA.textos[clau];
  if (typeof traduccio === 'function') return traduccio(...valors);
  return (traduccio === undefined ? clau : traduccio).replace(/\{(\d+)\}/g, (_, i) => valors[i]);
}

function TD(paraula) {
  return IDIOMA.dades[paraula] || paraula;
}

// On són els fitxers comuns: la pàgina en castellà és en una subcarpeta.
const ARREL = document.documentElement.dataset.arrel || '';

function horaCurta(data) {
  return new Date(data).toLocaleTimeString(IDIOMA.codi, { hour: '2-digit', minute: '2-digit' });
}

function element(etiqueta, classe, text) {
  const el = document.createElement(etiqueta);
  if (classe) el.className = classe;
  if (text) el.textContent = text;
  return el;
}

// Icona del full de símbols de la pàgina (Lucide).
function icona(id) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', '#' + id);
  svg.append(use);
  return svg;
}

// Data d'avui (hora local) a l'hora «HH:MM».
function avuiA(hhmm) {
  const [h, m] = hhmm.split(':').map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d;
}

// Totes les hores d'actualització d'avui, segons l'horari de les dades.
function horesActualitzacio(horari) {
  const hores = [];
  const desfase = (horari.desfase_min || 0) * 60000;
  for (const [inici, fi] of horari.trams) {
    const fins = avuiA(fi).getTime() + desfase;
    for (let t = new Date(avuiA(inici).getTime() + desfase); t <= fins;
      t = new Date(t.getTime() + horari.cada_min * 60000)) {
      hores.push(t);
    }
  }
  return hores;
}

function textHorari(horari) {
  const [[inici]] = horari.trams;
  // Les raons del mode avís ja es veuen a la pàgina (avisos, pluja): aquí no
  // es repeteixen.
  if (horari.mode_avis && horari.mode_avis.length) {
    const trams = horari.trams.length === 1 && inici === '00:00' ? ''
      : ` (${horari.trams.map(([a, b]) => `${a}\u2013${b}`).join(T(' i '))})`;
    return T`Mode avís: dades cada ${horari.cada_min} min${trams}.`;
  }
  // Tot el dia: no cal dir de quina hora a quina.
  if (horari.trams.length === 1 && inici === '00:00') {
    return T`Dades en directe cada ${horari.cada_min} min.`;
  }
  const trams = horari.trams.map(([a, b]) => `${a}–${b}`).join(T(' i '));
  return T`Dades en directe cada ${horari.cada_min} min (${trams}).`;
}

// «Dades en directe… Darrera: 07:07 · propera: 07:30.» i, si cal, l'avís de
// retard quan una actualització prevista no ha arribat.
function pintaHorari(dades) {
  const ara = new Date();
  const generat = new Date(dades.generat);
  const hores = horesActualitzacio(dades.horari);
  const propera = hores.find((t) => t > ara);
  const darreraPrevista = hores.filter((t) => t <= ara).pop();
  // L'hora d'actualització, destacada, just després dels avisos.
  const dia = generat.toDateString() === ara.toDateString() ? '' : T` del ${generat.toLocaleDateString(IDIOMA.codi)}`;
  $('horari').replaceChildren(T('Actualitzat a les '), element('strong', null, horaCurta(generat) + dia),
    T(' · propera: '), element('strong', null, propera ? horaCurta(propera) : T`demà a les ${dades.horari.trams[0][0]}`),
    '. ', element('span', 'mode', textHorari(dades.horari)));
  const avisos = [];
  if (darreraPrevista && generat < darreraPrevista - 5 * 60000
      && ara - darreraPrevista > MARGE_RETARD_MIN * 60000) {
    avisos.push(T`L’actualització de les ${horaCurta(darreraPrevista)} no s’ha fet: les dades són de les ${horaCurta(generat)}.`);
  }
  // La previsió que falla i s'ha substituït per l'anterior ja té el seu avís.
  if (dades.errors.some((e) => !(dades.previsio_de && e.startsWith('previsió')))) {
    avisos.push(T('No s’han pogut llegir totes les fonts: la informació és menys segura.'));
  }
  $('avis-dades').textContent = avisos.join(' ');
  $('avis-dades').hidden = !avisos.length;
}

// La pàgina oberta es posa al dia sola: torna a llegir les dades després de
// cada actualització prevista. La publicació (càlcul i GitHub Pages) tarda
// un minut o dos: es mira ESPERA_PUBLICACIO_MIN després de l'hora i, si les
// dades encara no són noves, cada minut fins a REINTENTS vegades.
const ESPERA_PUBLICACIO_MIN = 2;
const REINTENTS = 10;

// Propera actualització segons l'horari: avui o, si ja no n'hi ha cap, la
// primera de demà.
function properaActualitzacio(horari, ara = new Date()) {
  const propera = horesActualitzacio(horari).find((t) => t > ara);
  if (propera) return propera;
  const dema = avuiA(horari.trams[0][0]);
  dema.setDate(dema.getDate() + 1);
  return new Date(dema.getTime() + (horari.desfase_min || 0) * 60000);
}

// Les dades les puja el NAS a IONOS a cada actualització; la còpia de GitHub
// (al costat de la pàgina) es renova cada mitja hora com a molt i és la
// reserva si IONOS no respon (ADR 0020).
const DADES_URL = 'https://bilateria.org/app/meteo-local/';
const ESPERA_DADES_MS = 6000;

function baixa(url) {
  const control = new AbortController();
  const temps = setTimeout(() => control.abort(), ESPERA_DADES_MS);
  return fetch(`${url}?t=${Date.now()}`, { cache: 'no-store', signal: control.signal })
    .then((r) => {
      clearTimeout(temps);
      if (!r.ok) throw new Error(r.status);
      return r.json();
    });
}

function llegeixDades(nom) {
  return baixa(DADES_URL + nom).catch(() => baixa(ARREL + nom));
}

function carrega(url, pinta, error) {
  let dades = null;
  let reintents = 0;
  let temporitzador = null;
  let previst = 0;

  function programa() {
    clearTimeout(temporitzador);
    previst = reintents && reintents <= REINTENTS ? Date.now() + 60000
      : properaActualitzacio(dades.horari).getTime() + ESPERA_PUBLICACIO_MIN * 60000;
    temporitzador = setTimeout(llegeix, previst - Date.now());
  }

  function llegeix() {
    clearTimeout(temporitzador);
    llegeixDades(url)
      .then((noves) => {
        // Les mateixes dades d'abans: la publicació encara no ha arribat.
        reintents = dades && noves.generat === dades.generat ? reintents + 1 : 0;
        dades = noves;
        // Es torna a pintar sempre: l'hora també canvia el que es mostra.
        pinta(dades);
        programa();
      })
      .catch(() => {
        if (!dades) {
          error();
          return;
        }
        reintents += 1;
        programa();
      });
  }

  // Amb la pestanya amagada (sobretot al mòbil) els temporitzadors s'aturen:
  // en tornar-hi, es mira si ja tocava.
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && dades && Date.now() >= previst) llegeix();
  });
  llegeix();
}

// Avisos de l'AEMET al Vallès, amb el dia i la franja de cadascun.

// «avui», «demà» o el dia de la setmana.
function nomDiaCurt(data, ara) {
  const dies = Math.round((new Date(data).setHours(0, 0, 0, 0) - new Date(ara).setHours(0, 0, 0, 0)) / 864e5);
  if (dies === 0) return T('avui');
  if (dies === 1) return T('demà');
  return new Date(data).toLocaleDateString(IDIOMA.codi, { weekday: 'long' });
}

// «a les 18:00», «a la 01:00» o «a mitjanit».
function aLaHora(data) {
  const h = horaCurta(data);
  if (h === '00:00') return T('a mitjanit');
  return h.startsWith('01:') ? T`a la ${h}` : T`a les ${h}`;
}

// Franja d'un avís, amb el dia: «avui fins a les 20:00», «demà de 09:00 a
// 18:00», «demà de 22:00 a mitjanit». Si ja ha començat, només el final.
function textFranja(inici, fi, ara) {
  // Mitjanit és el final del dia de l'avís, no el començament del següent.
  const diaFi = nomDiaCurt(new Date(fi - 1), ara);
  if (inici <= ara) return diaFi === T('avui') ? T`avui fins ${aLaHora(fi)}` : T`fins ${diaFi} ${aLaHora(fi)}`;
  const h = horaCurta(inici);
  const de = /^(01|11):/.test(h) ? T`d\u2019${h}` : T`de ${h}`;
  const dia = nomDiaCurt(inici, ara);
  if (diaFi !== dia) return T`${dia} ${de} fins ${diaFi} ${aLaHora(fi)}`;
  // «de 09:00 a 18:00», «de 22:00 a mitjanit».
  const fins = horaCurta(fi) === '00:00' ? T('a mitjanit') : T`a ${horaCurta(fi)}`;
  return `${dia} ${de} ${fins}`;
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
    const clau = `${nivell}|${[...tipus].sort().map((x) => TD(x)).join(T(' i '))}`;
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
      const quan = dies.map((d) => d.parts.join(T(' i '))).join('; ');
      return T`Avís ${TD(nivell)} de l’AEMET per ${tipus} al Vallès: ${quan}.`;
    }).join(' ');
}

// Quan Open-Meteo no respon, la previsió és l'última bona (ADR 0016).
function textPrevisioAnterior(dades) {
  if (!dades || !dades.previsio_de) return '';
  const de = new Date(dades.previsio_de);
  const dia = de.toDateString() === new Date().toDateString() ? '' : T` del ${de.toLocaleDateString(IDIOMA.codi)}`;
  return T`Open-Meteo, d\u2019on surten els models, ara no respon: la previsió és la de les ${horaCurta(de)}${dia}.`;
}

// Plans de Protecció Civil activats (inundacions, vent, neu): avís destacat
// a dalt de la pàgina, amb l'enllaç al comunicat.
const NOM_FASE = { prealerta: 'prealerta', alerta: 'alerta', 'emergència': 'emergència' };

function blocPlans(plans) {
  if (!plans || !plans.length) return null;
  const caixa = element('section', 'avis avis-pc');
  caixa.setAttribute('aria-label', T('Avís de Protecció Civil'));
  for (const p of plans) {
    const par = element('p', null,
      T`Protecció Civil: pla ${TD(p.nom)} (${p.pla}) en fase d\u2019${TD(NOM_FASE[p.fase] || p.fase)}.`);
    if (p.fase === 'emergència') {
      par.append(T(' Eviteu els desplaçaments que no siguin necessaris.'));
    }
    if (p.comunicat) {
      const a = element('a', null, T('Comunicat (PDF)'));
      a.href = p.comunicat;
      a.target = '_blank';
      a.rel = 'noopener';
      par.append(' ', a);
    }
    caixa.append(par);
  }
  return caixa;
}

function posaVersio(versio) {
  $('versio').textContent = T`versió ${versio}`;
  // La pàgina pública enllaça el seu propi repositori (ADR 0024).
  $('versio').href = document.documentElement.dataset.notes
    || 'https://github.com/jjdeharo/meteo-local/releases/tag/v' + versio;
}

// Tema: segueix el del dispositiu mentre no se'n triï un altre; si es tria
// el mateix que el del dispositiu, es torna a seguir-lo (com a Sirena).
const sistemaFosc = matchMedia('(prefers-color-scheme: dark)');

function aplicaFosc(fosc, manual) {
  document.documentElement.dataset.theme = fosc ? 'dark' : 'light';
  if (manual) {
    try {
      if (fosc === sistemaFosc.matches) localStorage.removeItem('meteo.fosc');
      else localStorage.setItem('meteo.fosc', fosc ? '1' : '0');
    } catch (_) {}
  }
  $('btn-fosc').querySelector('use').setAttribute('href', fosc ? '#i-sun' : '#i-moon');
}

function segueixSistema() {
  try { return localStorage.getItem('meteo.fosc') === null; } catch (_) { return true; }
}

aplicaFosc(document.documentElement.dataset.theme === 'dark', false);
$('btn-fosc').addEventListener('click', () => {
  aplicaFosc(document.documentElement.dataset.theme !== 'dark', true);
});
sistemaFosc.addEventListener('change', (e) => {
  if (segueixSistema()) aplicaFosc(e.matches, false);
});

// Per poder instal·lar la web com a aplicació (sw.js).
if ('serviceWorker' in navigator) navigator.serviceWorker.register(ARREL + 'sw.js').catch(() => {});
