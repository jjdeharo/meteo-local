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

function coma(x, decimals = 1) {
  return Number(x).toFixed(decimals).replace('.', ',');
}

// Altura del sol (graus) a Cerdanyola en un moment donat, amb la fórmula
// aproximada de la NOAA: n'hi ha prou per saber si és de dia o de nit.
const CASA_COORD = [41.5, 2.1];
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

// Amb dades de més de DADES_VELLES_H hores, la previsió, els veredictes i els
// trens ja no es mostren: algú que no llegeixi l'avís s'hi podria fiar
// (ADR 0031). Es diu de quan són i on mirar mentrestant.
const DADES_VELLES_H = 2;

function dadesVelles(dades, ara = new Date()) {
  return ara - new Date(dades.generat) > DADES_VELLES_H * 3600000;
}

function blocDadesVelles(dades) {
  const generat = new Date(dades.generat);
  const dia = generat.toDateString() === new Date().toDateString() ? ''
    : T` del ${generat.toLocaleDateString(IDIOMA.codi)}`;
  const caixa = element('section', 'avis avis-velles');
  caixa.append(element('p', null,
    T`Les dades són de les ${horaCurta(generat) + dia}: fa més de ${DADES_VELLES_H} hores que no s’actualitzen. La previsió i l’estat dels trens no es mostren fins que tornin.`));
  const p = element('p', null, T('Mentrestant: '));
  [[T('previsió de Meteocat'), 'https://www.meteo.cat/prediccio/municipal/082665'],
    [T('radar'), 'https://www.meteo.cat/observacions/radar'],
    ['Rodalies', `https://rodalies.gencat.cat/${IDIOMA.codi === 'es' ? 'es' : 'ca'}/inici/`],
    ['FGC', 'https://x.com/fgc']].forEach(([text, href], n) => {
    const a = element('a', null, text);
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener';
    p.append(...(n ? [' · ', a] : [a]));
  });
  caixa.append(p);
  return caixa;
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

// La línia del mode, a sobre de «Actualitzat a les… · propera…»: «Mode
// normal» o «Mode vigilància» amb el motiu entre parèntesis (el mode avís,
// ADR 0010), i un «?» que explica els dos. Abans «Mode avís» i «Seguiment de
// prop» (Juanjo, 10-10-2026: «no me gusta de prop, no dice nada»).
function modeHorari(horari) {
  const [[inici]] = horari.trams;
  const totElDia = horari.trams.length === 1 && inici === '00:00';
  const trams = totElDia ? [] : [horari.trams.map(([a, b]) => `${a}\u2013${b}`).join(T(' i '))];
  const vigilancia = Boolean(horari.mode_avis && horari.mode_avis.length);
  const motius = vigilancia ? horari.mode_avis.map((m) => TD(m).replace(/'/g, '\u2019')) : [];
  return { vigilancia, nom: vigilancia ? T('Mode vigilància') : T('Mode normal'), detall: [...motius, ...trams].join(', ') };
}

function textHorari(horari) {
  const { nom, detall } = modeHorari(horari);
  return detall ? `${nom} (${detall})` : nom;
}

function textModeAvis(horari) {
  const vigilancia = horari.mode_avis && horari.mode_avis.length;
  const normal = horari.normal_min || (vigilancia ? 15 : horari.cada_min);
  const avis = horari.avis_min || (vigilancia ? horari.cada_min : 6);
  return T`Mode normal: la pàgina s’actualitza cada ${normal} minuts. Mode vigilància: s’actualitza cada ${avis} minuts, just després de cada imatge nova del radar de Meteocat. La pàgina es posa en mode vigilància quan hi ha un avís de l’AEMET, un pla de Protecció Civil en alerta o emergència, pluja a Montflorit o pluja al radar a menys de ${horari.radar_km || 15} km. Quan ja no hi ha res d’això, torna al mode normal.`;
}

// Un «?» que mostra o amaga una explicació al costat (els plans de Protecció
// Civil i el mode avís). Torna [botó, explicació].
function botoAjuda(text, etiqueta, obert = false, enCanviar = () => {}) {
  const id = `ajuda-${++numAjuda}`;
  const boto = element('button', 'ajuda-fase', '?');
  boto.type = 'button';
  boto.setAttribute('aria-expanded', String(obert));
  boto.setAttribute('aria-controls', id);
  boto.setAttribute('aria-label', etiqueta);
  boto.title = etiqueta;
  const sentit = element('span', 'sentit-fase', text);
  sentit.id = id;
  sentit.hidden = !obert;
  boto.addEventListener('click', () => {
    sentit.hidden = !sentit.hidden;
    boto.setAttribute('aria-expanded', String(!sentit.hidden));
    enCanviar(!sentit.hidden);
  });
  return [boto, sentit];
}
let numAjuda = 0;
// L'explicació del mode avís segueix oberta quan la línia es torna a pintar.
let ajudaModeOberta = false;

// Les fonts de «El temps»: la previsió, el que es mesura i els avisos. Cada
// pàgina avisa només de les fonts que fa servir (Juanjo, 09-10-2026: «cada
// pagina solo avisa de lo que usa»): un error del sol, per exemple, no fa
// menys segura la previsió. Els noms són els que posa casa.py davant de «:».
const FONTS_TEMPS = ['previsió', 'ensemble', 'estació', 'estació de casa', 'estacions veïnes', 'vent', 'radar',
  'final de la pluja', 'avisos', 'plans', 'riera', 'entorn'];

// Si ha fallat alguna de les fonts de la pàgina. La previsió que falla i
// s'ha substituït per l'anterior ja té el seu avís.
function fontsFallades(dades, fonts) {
  return (dades.errors || []).some((e) => fonts.includes(e.split(':')[0])
    && !(dades.previsio_de && e.startsWith('previsió')));
}

function pintaHorari(dades, fonts = FONTS_TEMPS) {
  const ara = new Date();
  const generat = new Date(dades.generat);
  const hores = horesActualitzacio(dades.horari);
  const propera = hores.find((t) => t > ara);
  const darreraPrevista = hores.filter((t) => t <= ara).pop();
  // L'hora d'actualització, destacada, al capdamunt de la pàgina (Juanjo, 09-10-2026:
  // «visible nada más abrir»).
  const dia = generat.toDateString() === ara.toDateString() ? '' : T` del ${generat.toLocaleDateString(IDIOMA.codi)}`;
  // El mode i el seu «?» en una línia pròpia, igual en els dos modes perquè la
  // pàgina no salti quan canvia; l'explicació, a sota; després, les hores.
  // El nom, en una etiqueta del color del mode (verd el normal, ambre el de
  // vigilància); al costat, el motiu i el «?», enganxat a l'última paraula
  // perquè no baixi sol a una altra línia.
  const { vigilancia, nom, detall } = modeHorari(dades.horari);
  const [boto, sentit] = botoAjuda(textModeAvis(dades.horari), T('Què vol dir el mode?'), ajudaModeOberta,
    (obert) => { ajudaModeOberta = obert; });
  const mode = element('span', 'mode');
  const etiqueta = element('span', `mode-nom ${vigilancia ? 'vigilancia' : 'normal'}`, nom);
  if (detall) {
    const text = ` (${detall})`;
    const tall = text.lastIndexOf(' ') + 1;
    const final = element('span', 'sense-tall', text.slice(tall));
    final.append(boto);
    mode.append(etiqueta, text.slice(0, tall), final);
  } else {
    const final = element('span', 'sense-tall');
    final.append(etiqueta, boto);
    mode.append(final);
  }
  const linia = element('span', 'hores');
  linia.append(T('Actualitzat a les '), element('strong', null, horaCurta(generat) + dia),
    T(' · propera: '), element('strong', null, propera ? horaCurta(propera) : T`demà a les ${dades.horari.trams[0][0]}`),
    '.');
  $('horari').replaceChildren(mode, sentit, linia);
  // Calculades fora de casa perquè el servidor habitual no publica (ADR 0032).
  if (dades.reserva) linia.append(' ', element('span', 'reserva', T('Dades del servidor de reserva.')));
  const avisos = [];
  if (darreraPrevista && generat < darreraPrevista - 5 * 60000
      && ara - darreraPrevista > MARGE_RETARD_MIN * 60000) {
    avisos.push(T`L’actualització de les ${horaCurta(darreraPrevista)} no s’ha fet: les dades són de les ${horaCurta(generat)}.`);
  }
  if (fontsFallades(dades, fonts)) {
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
// reserva si IONOS no respon (ADR 0020) o si el que serveix és vell: quan la
// pujada a IONOS falla, publica.sh publica a GitHub, i IONOS es queda amb les
// dades d'abans (auditoria del 07-10-2026, ADR 0038).
const DADES_URL = 'https://bilateria.org/app/meteo-local/';
const ESPERA_DADES_MS = 6000;
const DADES_RESERVA_MIN = 45;

// Baixa un JSON amb un temps màxim que cobreix tota la descàrrega, també el
// cos: «fetch» es resol amb les capçaleres, i el temporitzador s'aturava
// abans de llegir el cos, de manera que una connexió penjada a mig cos no es
// tallava mai (auditoria del 09-10-2026).
function baixa(url) {
  const control = new AbortController();
  const temps = setTimeout(() => control.abort(), ESPERA_DADES_MS);
  return fetch(`${url}?t=${Date.now()}`, { cache: 'no-store', signal: control.signal })
    .then((r) => {
      if (!r.ok) throw new Error(r.status);
      return r.json();
    })
    .finally(() => clearTimeout(temps));
}

function llegeixDades(nom) {
  return baixa(DADES_URL + nom).then((dades) => {
    if (Date.now() - new Date(dades.generat) <= DADES_RESERVA_MIN * 60000) return dades;
    // IONOS respon, però amb dades velles: es mira la còpia de GitHub i es
    // fa servir la més nova de les dues.
    return baixa(ARREL + nom)
      .then((copia) => (new Date(copia.generat) > new Date(dades.generat) ? copia : dades), () => dades);
  }, () => baixa(ARREL + nom));
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
          // Sense cap dada encara (cobertura fluixa, per exemple): s'avisa i
          // es torna a provar al cap d'un minut, sense que calgui recarregar.
          error();
          previst = Date.now() + 60000;
          temporitzador = setTimeout(llegeix, 60000);
          return;
        }
        // Les d'abans es tornen a pintar: si ja tenen massa hores, la pàgina
        // ho diu i amaga la previsió (dadesVelles) encara que no arribi res
        // de nou (auditoria del 07-10-2026).
        pinta(dades);
        reintents += 1;
        programa();
      });
  }

  // Amb la pestanya amagada (sobretot al mòbil) els temporitzadors s'aturen:
  // en tornar-hi, es mira si ja tocava (o si encara no hi ha dades) i, si no,
  // es torna a pintar el que hi ha, perquè l'edat de les dades es comprovi.
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) return;
    if (!dades || Date.now() >= previst) llegeix();
    else pinta(dades);
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
// Els avisos de l'AEMET, un element per nivell i tipus, amb el seu text tal
// com el publica: en castellà, citat i marcat com a tal, agrupat per dia
// (ADR 0033). El dia només es diu si n'hi ha més d'un.
function blocAvisosAemet(avisos, ara = new Date()) {
  return frasesAvisos(avisos, ara).map((f) => {
    const item = element('p', `avis-item ${f.nivell}`);
    item.append(element('strong', null, f.titol), `: ${f.quan}.`);
    const perDia = [];
    for (const a of [...avisos].sort((x, y) => new Date(x.inicio) - new Date(y.inicio))) {
      if (a.nivel !== f.nivell || !f.tipus.has(a.tipo) || !a.descripcio) continue;
      if (new Date(a.fin).getTime() + 1000 <= ara.getTime()) continue;
      const dia = nomDiaCurt(new Date(Math.max(new Date(a.inicio).getTime(), ara.getTime())), ara);
      let d = perDia.find((x) => x.dia === dia);
      if (!d) perDia.push(d = { dia, textos: [] });
      if (!d.textos.includes(a.descripcio)) d.textos.push(a.descripcio);
    }
    perDia.forEach((d, n) => {
      item.append(n ? '; ' : ' ', ...(perDia.length > 1 ? [`${d.dia}: `] : []));
      d.textos.forEach((t, m) => {
        const cita = element('q', null, t);
        cita.lang = 'es';
        item.append(...(m ? [' ', cita] : [cita]));
      });
    });
    return item;
  });
}

function textAvisos(avisos, ara = new Date()) {
  return frasesAvisos(avisos, ara).map((f) => `${f.titol}: ${f.quan}.`).join(' ');
}

// Una frase per nivell i tipus: {nivell, tipus (Set), titol, quan}, del més
// greu al més lleu.
function frasesAvisos(avisos, ara = new Date()) {
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
  const tipusDe = {};
  for (const [k, tipus] of Object.entries(perFranja)) {
    const [nivell, inici, fi] = k.split('|');
    const clau = `${nivell}|${[...tipus].sort().map((x) => TD(x)).join(T(' i '))}`;
    (frases[clau] = frases[clau] || []).push([Number(inici), Number(fi)]);
    (tipusDe[clau] = tipusDe[clau] || new Set()); tipus.forEach((t) => tipusDe[clau].add(t));
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
      return { nivell, tipus: tipusDe[clau], titol: T`Avís ${TD(nivell)} de l’AEMET per ${tipus} al Vallès`, quan };
    });
}

// Quan Open-Meteo no respon, la previsió és l'última bona (ADR 0016).
function textPrevisioAnterior(dades) {
  if (!dades || !dades.previsio_de) return '';
  const de = new Date(dades.previsio_de);
  const dia = de.toDateString() === new Date().toDateString() ? '' : T` del ${de.toLocaleDateString(IDIOMA.codi)}`;
  return T`Open-Meteo, d\u2019on surten els models, ara no respon: la previsió és la de les ${horaCurta(de)}${dia}.`;
}

// Plans de Protecció Civil que depenen del temps (inundacions, vent, neu,
// onades de calor i de fred, contaminació), en prealerta, alerta o emergència:
// avís destacat a dalt de la pàgina, amb l'enllaç al comunicat (ADR 0051).
const NOM_FASE = { prealerta: 'prealerta', alerta: 'alerta', 'emergència': 'emergència' };
// La franja, del color de la fase: la prealerta no ha d'espantar.
const COLOR_FASE = { prealerta: 'prealerta', alerta: 'taronja', 'emergència': 'vermell' };
// Què vol dir cada fase, resumit de la definició oficial del conjunt de dades
// de Protecció Civil; es desplega amb el «?» (Juanjo, 09-10-2026).
const SENTIT_FASE = {
  prealerta: () => T('Es preveu un risc a mitjà termini. El pla no està activat: només cal estar-ne pendent.'),
  alerta: () => T('El pla està activat: es preveu un risc important a curt termini, o hi ha afectacions que no són greus.'),
  'emergència': () => T('El pla està activat per un risc greu per a la població: segueix les indicacions de Protecció Civil.'),
};

// El «?» de la fase: obre i tanca, a sota, una línia amb què vol dir.
function ajudaFase(fase) {
  if (!SENTIT_FASE[fase]) return [];
  return botoAjuda(SENTIT_FASE[fase](), T`Què vol dir ${TD(NOM_FASE[fase])}?`);
}

// «de prealerta», però «d’alerta» i «d’emergència»; en castellà, sempre «de».
function deFase(fase) {
  if (IDIOMA.codi.startsWith('es')) return `de ${fase}`;
  return /^[aeiouàèéíòóúh]/i.test(fase) ? `d’${fase}` : `de ${fase}`;
}

// Si Meteocat té avís de perill per a la comarca (ADR 0067): els plans no
// diuen quina zona abasten. Els textos vénen fets a les dades (smp.py), amb
// el meteor i el llindar com els publica Meteocat.
function liniesSmp(smp) {
  if (!smp || !smp.linies) return [];
  const es = IDIOMA.codi.startsWith('es');
  return smp.linies.map((l) => element('span', 'smp-linia', es ? l.es : l.ca));
}

// Els plans de Protecció Civil, un element per pla, del color de la fase.
function blocPlans(plans, smp) {
  return (plans || []).map((p) => {
    const item = element('p', `avis-item ${COLOR_FASE[p.fase] || 'vermell'}`);
    item.setAttribute('aria-label', T('Avís de Protecció Civil'));
    item.append(element('strong', null,
      T`Protecció Civil: pla ${TD(p.nom)} (${p.pla}) en fase ${deFase(TD(NOM_FASE[p.fase] || p.fase))}.`),
    ...ajudaFase(p.fase));
    if (p.fase === 'emergència') {
      item.append(T(' Evita els desplaçaments que no siguin necessaris.'));
    }
    if (p.comunicat) {
      const a = element('a', null, T('Comunicat (PDF)'));
      a.href = p.comunicat;
      a.target = '_blank';
      a.rel = 'noopener';
      item.append(' ', a);
    }
    item.append(...liniesSmp(smp));
    return item;
  });
}

// Tots els avisos vigents en un sol bloc, «Avisos actius»: Protecció Civil,
// el risc calculat (si n'hi ha) i l'AEMET, cadascun amb la franja del seu
// nivell. Sense cap, res (proposta del 08-10-2026: amb dos avisos, al mòbil
// la temperatura quedava fora de la pantalla).
// Incendis forestals en curs a prop (Bombers) i el Pla Alfa de Cerdanyola des
// del nivell 3, amb els tancaments que toquen Collserola (Agents Rurals, ADR 0046).
const ALFA_NIVELL_MOSTRAR = 3;

function blocEntorn(entorn) {
  const items = [];
  const nouItem = (nivell, titol, resta, href) => {
    const item = element('p', `avis-item ${nivell}`);
    item.append(element('strong', null, titol), resta);
    if (href) {
      const a = element('a', null, T('Mapa'));
      a.href = href;
      a.target = '_blank';
      a.rel = 'noopener';
      item.append(' ', a);
    }
    return item;
  };
  for (const i of (entorn && entorn.incendis) || []) {
    const km = i.km != null ? T`, a ${coma(i.km)}\u00a0km de Montflorit` : '';
    items.push(nouItem('vermell', T`Bombers: incendi forestal a ${i.municipi}`,
      T`${km}, des de les ${horaCurta(i.inici)}.`,
      'https://interior.gencat.cat/ca/arees_dactuacio/bombers/actuacions-de-bombers/'));
  }
  const alfa = (entorn && entorn.pla_alfa) || {};
  for (const [dia, nom] of [['avui', () => T('avui')], ['dema', () => T('demà')]]) {
    const n = alfa[dia];
    if (n != null && n >= ALFA_NIVELL_MOSTRAR) {
      items.push(nouItem(n >= 4 ? 'vermell' : 'taronja', T`Pla Alfa de Cerdanyola: nivell ${n} ${nom()}`,
        T(': accés restringit als espais forestals.'),
        'https://interior.gencat.cat/ca/arees_dactuacio/agents-rurals/pla-alfa/'));
    }
  }
  for (const t of alfa.tancaments || []) {
    items.push(nouItem('vermell', T`Agents Rurals: tancat ${t.espai}`, '.', null));
  }
  return items;
}

function blocAvisos(dades, extres = [], ara = new Date()) {
  const items = [...blocPlans(dades.plans, dades.smp), ...blocEntorn(dades.entorn), ...extres.filter(Boolean),
    ...(dades.avisos && dades.avisos.length ? blocAvisosAemet(dades.avisos, ara) : [])];
  if (!items.length) return null;
  const sec = element('section', 'avisos-actius');
  sec.setAttribute('aria-label', T('Avisos actius'));
  sec.append(element('h2', 'seccio', T('Avisos actius')), ...items);
  return sec;
}

function posaVersio(versio) {
  $('versio').textContent = T`versió ${versio}`;
  // La pàgina pública enllaça el seu propi repositori (ADR 0024).
  $('versio').href = document.documentElement.dataset.notes
    || 'https://github.com/meteo-montflorit/meteo-local/releases/tag/v' + versio;
}

// --- Trens i trànsit (ADR 0029 i 0052): les fitxes que fan servir «Si surts» i
// «Consultes» (ADR 0054). ---

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

// Trànsit (config.TRANSIT_NIVELL_SORTIDA): des d'aquest nivell (3, retencions;
// 4, congestió; 5, calçada tallada), si surts ara, el cotxe i la moto passen a
// «compte». La circulació intensa (2) només es llista (ADR 0052).
const NIVELL_TRANSIT = 3;

function enllacExtern(text, href) {
  const a = element('a', null, text);
  a.href = href;
  a.target = '_blank';
  a.rel = 'noopener';
  return a;
}

// L'estat de cada línia de tren, per al plec del transport públic.
function blocTrens(trens) {
  const llista = element('ul', 'llista-trens');
  for (const l of trens.linies) {
    const li = element('li', 'tren ' + COLOR_ESTAT[l.estat]);
    const cap = element('p', 'tren-cap');
    cap.append(element('span', 'tren-linia', l.linia), ' ', element('span', 'tren-estacio', TD(l.estacio)),
      ' ', element('span', 'tren-estat', TD(TEXT_ESTAT[l.estat])));
    li.append(cap);
    // L'avís oficial diu que hi ha trens, però no se n'ha vist cap (trens.py).
    if (l.no_vist) {
      li.append(element('p', 'tren-nota', l.operador === 'fgc'
        ? T('FGC diu que hi ha circulació, però a l’última hora no s’ha vist cap tren a prop de l’estació.')
        : T('Rodalies diu que hi ha circulació ferroviària, però a l’última hora no s’ha vist cap tren a prop de l’estació.')));
    }
    // Els avisos, tal com els publica l'operador: no es tradueixen.
    const textos = (l.avisos || []).map((a) => (IDIOMA.codi === 'es' ? a.es : a.ca) || a.ca || a.es);
    if (textos.length) {
      const plecAvisos = element('details', 'tren-avisos');
      plecAvisos.append(element('summary', null, l.operador === 'fgc' ? T('Avís d’FGC') : T('Avís de Rodalies')));
      for (const t of textos) plecAvisos.append(element('p', null, t));
      li.append(plecAvisos);
    }
    llista.append(li);
  }
  // On publiquen els operadors l'estat del servei.
  const estat = element('p', 'nota');
  estat.append(T('Estat del servei: '));
  Object.values(ESTAT_OPERADOR).forEach((e, n) => estat.append(...(n ? [' · '] : []), enllacExtern(e.text(), e.href())));
  return [llista, estat, element('p', 'nota',
    T`Dades de Renfe i d’FGC de les ${horaCurta(trens.hora)}, consultades automàticament: l’autor no es fa responsable de la seva exactitud.`)];
}

// Les incidències de trànsit de prop (ADR 0052), tal com les publica el Servei
// Català de Trànsit, en català: no es tradueixen. Es veuen si es mira el cotxe
// o la moto.
const COLOR_TRANSIT = (nivell) => (nivell >= 5 ? 'no' : nivell >= NIVELL_TRANSIT ? 'compte' : 'neutre');
const ESTAT_TRANSIT = () => `https://transit.gencat.cat/${IDIOMA.codi === 'es' ? 'es' : 'ca'}/informacio-viaria/estat-transit/`;

// Sense hora per incidència: la del fitxer és la de l'última actualització, no
// la de l'inici, i semblava que no estigués al dia. El que surt és el que el
// Servei Català de Trànsit dona com a vigent a l'hora de la consulta, que es
// diu a sota (Juanjo, 09-10-2026; ADR 0052).
// La distància en línia recta fins al punt que dona la font per al tram: en
// metres (de 50 en 50) per sota d'1 km; si no, en km amb un decimal.
function distancia(km) {
  if (km == null) return null;
  if (km < 1) return `${Math.max(50, Math.round(km * 20) * 50)}\u00a0m`;
  const x = Math.round(km * 10) / 10;
  return `${Number.isInteger(x) ? x : coma(x)}\u00a0km`;
}

function filaTransit(i) {
  const li = element('li', 'tren ' + COLOR_TRANSIT(i.nivell));
  const cap = element('p', 'tren-cap');
  cap.append(element('span', 'tren-linia', i.carretera));
  const lloc = [i.municipi, i.km != null && T`a ${distancia(i.km)}`].filter(Boolean).join(', ');
  if (lloc) cap.append(' ', element('span', 'tren-estacio', lloc));
  cap.append(' ', element('span', 'tren-estat', i.descripcio || ''));
  // «Circulació» com a causa no diu res que no digui ja l'estat.
  const causa = i.tipus === 'obres' ? T`Obres: ${i.causa}` : i.causa !== 'Circulació' && i.causa;
  const detall = [causa, i.sentit, i.pk && T`km ${i.pk}`].filter(Boolean);
  li.append(cap, element('p', 'transit-detall', detall.join(' · ')));
  return li;
}

// Les incidències de trànsit de prop, per al plec del cotxe i de la moto.
function blocTransit(transit) {
  const llista = element('ul', 'llista-trens');
  for (const i of transit.incidencies) llista.append(filaTransit(i));
  const estat = element('p', 'nota');
  estat.append(T('Estat del trànsit: '), enllacExtern('Servei Català de Trànsit', ESTAT_TRANSIT()));
  return [llista, estat, element('p', 'nota',
    T`Dades del Servei Català de Trànsit de les ${horaCurta(transit.hora)}, consultades automàticament: l’autor no es fa responsable de la seva exactitud.`)];
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

// Visor d'imatges: a l'ordinador, una imatge enllaçada amb la classe «amplia»
// s'obre a sobre de la pàgina, tan gran com hi càpiga, amb una X per tancar
// (també Esc o un clic fora). Al mòbil s'obre sola, on es pot ampliar
// amb els dits (Juanjo, 07-10-2026).
const pantallaGran = matchMedia('(min-width: 900px) and (pointer: fine)');

function obreVisor(enllac) {
  const visor = element('dialog', 'visor');
  const imatge = element('img');
  imatge.src = enllac.href;
  imatge.alt = enllac.querySelector('img')?.alt || '';
  // Tancar: la X de sempre, a dalt a la dreta (icona «x» de Lucide).
  const tanca = element('button', 'visor-tanca');
  tanca.type = 'button';
  tanca.title = T('Tanca');
  tanca.setAttribute('aria-label', T('Tanca'));
  tanca.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>';
  tanca.addEventListener('click', () => visor.close());
  visor.append(imatge, tanca);
  visor.setAttribute('aria-label', imatge.alt);
  visor.addEventListener('click', (e) => { if (e.target === visor) visor.close(); });
  visor.addEventListener('close', () => visor.remove());
  document.body.append(visor);
  visor.showModal();
  tanca.focus();
}

document.addEventListener('click', (e) => {
  const enllac = e.target.closest('a.amplia');
  if (!enllac || !pantallaGran.matches || e.ctrlKey || e.metaKey || e.shiftKey) return;
  e.preventDefault();
  obreVisor(enllac);
});

// «Nou!» damunt la campana d'«Avisos al mòbil» (ADR 0048): fins que s'entra a la
// pàgina «Avisos» (ho recorda el navegador) i, per a tothom, fins al 15-10-2026,
// una setmana després de publicar-la. El «Nou:» de la pàgina, igual
// (Juanjo, 08-10-2026).
const NOU_AVISOS_FINS = new Date('2026-10-16T00:00:00+02:00');

function marcaNouAvisos(ara = new Date()) {
  let vist = false;
  try {
    if (/(^|\/)avisos\.html$/.test(location.pathname)) localStorage.setItem('meteo.avisos-vist', '1');
    vist = localStorage.getItem('meteo.avisos-vist') === '1';
  } catch (_) {}
  if (ara >= NOU_AVISOS_FINS) {
    document.querySelectorAll('.novetat').forEach((p) => {
      p.classList.remove('novetat');
      p.querySelector('.nou')?.remove();
    });
  }
  if (vist || ara >= NOU_AVISOS_FINS) return;
  for (const a of document.querySelectorAll('.boto-avisos')) a.append(element('span', 'xip-nou', T('Nou!')));
}

marcaNouAvisos();

// Per poder instal·lar la web com a aplicació (sw.js).
if ('serviceWorker' in navigator) navigator.serviceWorker.register(ARREL + 'sw.js').catch(() => {});
