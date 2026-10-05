// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix dades.json (el genera prevision.py) i pinta la recomanació.
// Hi ha un sol mitjà per a tot el dia: qui va en moto torna en moto.

const TEXT_MITJA = {
  moto: { titol: 'Moto', frase: 'Pots anar i tornar en moto.' },
  compte: { titol: 'Moto, amb impermeable', frase: 'Pots anar en moto, però porta l\u2019impermeable: pot caure algun ruixat.' },
  cotxe: { titol: 'Cotxe', frase: 'Agafa el cotxe per anar i per tornar.' },
};
const TEXT_RISC = { moto: 'baix', compte: 'moderat', cotxe: 'alt' };
const HORES_DADES_ANTIGUES = 3;

const $ = (id) => document.getElementById(id);

function nomDia(iso) {
  const data = new Date(iso + 'T12:00:00');
  return 'Avui, ' + data.toLocaleDateString('ca', { weekday: 'long', day: 'numeric', month: 'long' });
}

function horaCurta(iso) {
  return new Date(iso).toLocaleTimeString('ca', { hour: '2-digit', minute: '2-digit' });
}

function element(etiqueta, classe, text) {
  const el = document.createElement(etiqueta);
  if (classe) el.className = classe;
  if (text) el.textContent = text;
  return el;
}

// Quan es va decidir i si encara pot canviar.
function notaDecisio(decisio, sortida) {
  const hora = horaCurta(decisio.decidit);
  // Passada l'hora de sortida, la decisió d'abans ja és la definitiva encara
  // que no hi hagi hagut cap actualització posterior.
  const [h, m] = sortida.split(':').map(Number);
  const araMateix = new Date();
  const jaHaSortit = araMateix.getHours() * 60 + araMateix.getMinutes() >= h * 60 + m
    && new Date(decisio.decidit).toDateString() === araMateix.toDateString();
  if (decisio.abans_de_sortir && (decisio.mantinguda || jaHaSortit)) {
    return `Decidit a les ${hora}, abans de sortir. Ja no canvia.`;
  }
  if (decisio.mantinguda || !decisio.abans_de_sortir) {
    return `Decidit a les ${hora}: no hi havia dades d\u2019abans de les ${sortida}.`;
  }
  return `Recomanació de les ${hora}. Es pot actualitzar fins a les ${sortida}; després ja no canvia.`;
}

function blocDecisio(dades) {
  const v = TEXT_MITJA[dades.decisio.mitja];
  const sec = element('section', 'decisio targeta ' + dades.decisio.mitja);
  sec.setAttribute('aria-label', `Recomanació d\u2019avui: ${v.titol}`);
  sec.append(element('h2', 'data', nomDia(dades.dia)));
  sec.append(element('p', 'veredicte', v.titol));
  sec.append(element('p', 'frase', v.frase));
  sec.append(element('p', 'nota', notaDecisio(dades.decisio, dades.anada.inici)));
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
  const llista = element('ul', 'motius');
  for (const motiu of trajecte.motius) {
    const li = element('li', 'motiu ' + motiu.nivell);
    li.append(element('span', 'visualment-amagat', `Risc ${TEXT_RISC[motiu.nivell]}: `));
    li.append(document.createTextNode(motiu.text));
    llista.append(li);
  }
  art.append(llista);
  return art;
}

function pinta(dades) {
  const cont = $('dies');
  cont.replaceChildren(blocDecisio(dades));
  if (dades.avis_tornada) cont.append(element('p', 'avis', dades.avis_tornada));
  cont.append(element('h2', 'perque', 'Per què'));
  const graella = element('div', 'graella');
  graella.append(targeta('Anada', dades.anada), targeta('Tornada', dades.tornada));
  cont.append(graella);

  const generat = new Date(dades.generat);
  $('generat').textContent = generat.toLocaleDateString('ca', { weekday: 'long', day: 'numeric' })
    + ' a les ' + horaCurta(dades.generat);
  $('versio').textContent = 'versió ' + dades.versio;
  $('versio').href = 'https://github.com/jjdeharo/meteo-local/releases/tag/v' + dades.versio;

  const avisos = [];
  const hores = (Date.now() - generat) / 3600000;
  if (hores > HORES_DADES_ANTIGUES) {
    avisos.push(`Aquestes dades són de fa ${Math.floor(hores)} hores. Mira el radar abans de sortir.`);
  }
  if (dades.errors.length) {
    avisos.push('No s\u2019han pogut llegir totes les fonts: la recomanació és menys segura.');
  }
  $('avis-dades').textContent = avisos.join(' ');
  $('avis-dades').hidden = !avisos.length;
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
