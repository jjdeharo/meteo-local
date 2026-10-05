// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix dades.json (el genera prevision.py) i pinta la pàgina.
// Fins a les 7:30 recomana un sol mitjà per a tot el dia (qui va en moto torna
// en moto). Després ja no en recomana cap: només diu el temps de la tornada.

const TEXT_MITJA = {
  moto: { titol: 'Moto', frase: 'Pots anar i tornar en moto.' },
  compte: { titol: 'Moto, amb impermeable', frase: 'Pots anar en moto, però porta l\u2019impermeable: pot caure algun ruixat.' },
  cotxe: { titol: 'Cotxe', frase: 'Agafa el cotxe per anar i per tornar.' },
};
const TEXT_RISC = { moto: 'baix', compte: 'moderat', cotxe: 'alt' };
// Marge abans de dir que una actualització prevista no s'ha fet.
const MARGE_RETARD_MIN = 20;

const $ = (id) => document.getElementById(id);

function nomDia(iso) {
  const data = new Date(iso + 'T12:00:00');
  return 'Avui, ' + data.toLocaleDateString('ca', { weekday: 'long', day: 'numeric', month: 'long' });
}

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

// Totes les hores d'actualització d'avui, segons l'horari de dades.json.
function horesActualitzacio(horari) {
  const hores = [];
  for (const [inici, fi] of horari.trams) {
    for (let t = avuiA(inici); t <= avuiA(fi); t = new Date(t.getTime() + horari.cada_min * 60000)) {
      hores.push(t);
    }
  }
  return hores;
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

function llistaMotius(motius) {
  const llista = element('ul', 'motius');
  for (const motiu of motius) {
    const li = element('li', 'motiu ' + motiu.nivell);
    li.append(element('span', 'visualment-amagat', `Risc ${TEXT_RISC[motiu.nivell]}: `));
    li.append(document.createTextNode(motiu.text));
    llista.append(li);
  }
  return llista;
}

// Matí: el mitjà del dia.
function blocDecisio(dades) {
  const v = TEXT_MITJA[dades.decisio.mitja];
  const sec = element('section', 'decisio targeta ' + dades.decisio.mitja);
  sec.setAttribute('aria-label', `Recomanació d\u2019avui: ${v.titol}`);
  sec.append(element('h2', 'data', nomDia(dades.dia)));
  sec.append(element('p', 'veredicte', v.titol));
  sec.append(element('p', 'frase', v.frase));
  sec.append(element('p', 'nota', notaDecisio(dades.decisio, dades.anada.fi)));
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
  sec.append(element('h3', 'perque', 'Per què'), llistaMotius(t.motius));
  return sec;
}

function targeta(nom, trajecte) {
  const risc = TEXT_RISC[trajecte.nivell];
  const art = element('article', 'targeta ' + trajecte.nivell + (trajecte.passat ? ' passat' : ''));
  art.setAttribute('aria-label', `${nom}: risc de pluja ${risc}`);
  const cap = element('h3', 'trajecte', `${nom} · ${trajecte.inici}\u2013${trajecte.fi}`);
  if (trajecte.passat) cap.append(element('span', 'etiqueta-passat', 'Ja ha passat'));
  art.append(cap);
  art.append(element('p', 'risc', 'Risc de pluja: ' + risc));
  const temps = liniaTemps(trajecte.temps);
  if (temps) art.append(element('p', 'temps', temps));
  art.append(llistaMotius(trajecte.motius));
  return art;
}

// «S'actualitza… Darrera: 07:07. Propera: 07:30.» i, si cal, l'avís de
// retard quan una actualització prevista no ha arribat.
function pintaHorari(dades) {
  const ara = new Date();
  const generat = new Date(dades.generat);
  const trams = dades.horari.trams.map(([a, b]) => `de ${a} a ${b}`).join(' i ');
  const hores = horesActualitzacio(dades.horari);
  const propera = hores.find((t) => t > ara);
  const darreraPrevista = hores.filter((t) => t <= ara).pop();
  $('horari').textContent = `S\u2019actualitza amb dades en directe cada ${dades.horari.cada_min} minuts, ${trams}. `
    + `Darrera actualització: ${horaCurta(generat)}`
    + (generat.toDateString() === ara.toDateString() ? '' : ` del ${generat.toLocaleDateString('ca')}`)
    + `. Propera: ${propera ? horaCurta(propera) : 'demà a les ' + dades.horari.trams[0][0]}.`;
  const avisos = [];
  if (darreraPrevista && generat < darreraPrevista - 5 * 60000
      && ara - darreraPrevista > MARGE_RETARD_MIN * 60000) {
    avisos.push(`L\u2019actualització de les ${horaCurta(darreraPrevista)} no s\u2019ha fet: `
      + `les dades són de les ${horaCurta(generat)}.`);
  }
  if (dades.errors.length) {
    avisos.push('No s\u2019han pogut llegir totes les fonts: la informació és menys segura.');
  }
  $('avis-dades').textContent = avisos.join(' ');
  $('avis-dades').hidden = !avisos.length;
}

function pinta(dades) {
  const cont = $('dies');
  const tarda = new Date() >= avuiA(dades.anada.fi) && dades.dia === new Date().toLocaleDateString('sv');
  if (tarda) {
    cont.replaceChildren(blocTornada(dades));
  } else {
    cont.replaceChildren(blocDecisio(dades));
    cont.append(element('h2', 'perque', 'Per què'));
    const graella = element('div', 'graella');
    graella.append(targeta('Anada', dades.anada), targeta('Tornada', dades.tornada));
    cont.append(graella);
  }
  pintaHorari(dades);
  $('versio').textContent = 'versió ' + dades.versio;
  $('versio').href = 'https://github.com/jjdeharo/meteo-local/releases/tag/v' + dades.versio;
}

fetch('dades.json', { cache: 'no-store' })
  .then((r) => r.json())
  .then(pinta)
  .catch(() => {
    $('dies').replaceChildren(element('p', 'avis', 'No s\u2019ha pogut carregar la previsió. Torna-ho a provar d\u2019aquí a una estona.'));
  });

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
