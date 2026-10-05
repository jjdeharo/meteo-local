// SPDX-License-Identifier: AGPL-3.0-or-later
// Peces comunes de les dues pàgines: utilitats, horari d'actualització,
// versió i commutador de tema.

// Marge abans de dir que una actualització prevista no s'ha fet.
const MARGE_RETARD_MIN = 20;

const $ = (id) => document.getElementById(id);

function horaCurta(data) {
  return new Date(data).toLocaleTimeString('ca', { hour: '2-digit', minute: '2-digit' });
}

function element(etiqueta, classe, text) {
  const el = document.createElement(etiqueta);
  if (classe) el.className = classe;
  if (text) el.textContent = text;
  return el;
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
      : ` (${horari.trams.map(([a, b]) => `${a}\u2013${b}`).join(' i ')})`;
    return `Mode avís: dades cada ${horari.cada_min} min${trams}.`;
  }
  // Tot el dia: no cal dir de quina hora a quina.
  if (horari.trams.length === 1 && inici === '00:00') {
    return `Dades en directe cada ${horari.cada_min} min.`;
  }
  return `Dades en directe cada ${horari.cada_min} min (${horari.trams.map(([a, b]) => `${a}–${b}`).join(' i ')}).`;
}

// «Dades en directe… Darrera: 07:07 · propera: 07:30.» i, si cal, l'avís de
// retard quan una actualització prevista no ha arribat.
function pintaHorari(dades) {
  const ara = new Date();
  const generat = new Date(dades.generat);
  const hores = horesActualitzacio(dades.horari);
  const propera = hores.find((t) => t > ara);
  const darreraPrevista = hores.filter((t) => t <= ara).pop();
  $('horari').textContent = `${textHorari(dades.horari)} Darrera: ${horaCurta(generat)}`
    + (generat.toDateString() === ara.toDateString() ? '' : ` del ${generat.toLocaleDateString('ca')}`)
    + ` · propera: ${propera ? horaCurta(propera) : 'demà a les ' + dades.horari.trams[0][0]}.`;
  const avisos = [];
  if (darreraPrevista && generat < darreraPrevista - 5 * 60000
      && ara - darreraPrevista > MARGE_RETARD_MIN * 60000) {
    avisos.push(`L’actualització de les ${horaCurta(darreraPrevista)} no s’ha fet: `
      + `les dades són de les ${horaCurta(generat)}.`);
  }
  if (dades.errors.length) {
    avisos.push('No s’han pogut llegir totes les fonts: la informació és menys segura.');
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
    fetch(`${url}?t=${Date.now()}`, { cache: 'no-store' })
      .then((r) => {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
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

// Plans de Protecció Civil activats (inundacions, vent, neu): avís destacat
// a dalt de la pàgina, amb l'enllaç al comunicat.
const NOM_FASE = { prealerta: 'prealerta', alerta: 'alerta', 'emergència': 'emergència' };

function blocPlans(plans) {
  if (!plans || !plans.length) return null;
  const caixa = element('section', 'avis avis-pc');
  caixa.setAttribute('aria-label', 'Avís de Protecció Civil');
  for (const p of plans) {
    const par = element('p', null,
      `Protecció Civil: pla ${p.nom} (${p.pla}) en fase d\u2019${NOM_FASE[p.fase] || p.fase}.`);
    if (p.fase === 'emergència') {
      par.append(' Eviteu els desplaçaments que no siguin necessaris.');
    }
    if (p.comunicat) {
      const a = element('a', null, 'Comunicat (PDF)');
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
  $('versio').textContent = 'versió ' + versio;
  $('versio').href = 'https://github.com/jjdeharo/meteo-local/releases/tag/v' + versio;
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
