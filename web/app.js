// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix dades.json (el genera prevision.py) i pinta la recomanació.

const TEXT_VEREDICTE = {
  moto: { titol: 'Moto', frase: 'Pots anar en moto.' },
  compte: { titol: 'Moto, amb impermeable', frase: 'Probablement no plourà, però porta l’impermeable.' },
  cotxe: { titol: 'Cotxe', frase: 'Millor agafa el cotxe.' },
};
const TEXT_NIVELL = { moto: 'A favor de la moto', compte: 'Compte', cotxe: 'A favor del cotxe' };
const HORES_DADES_ANTIGUES = 3;

const $ = (id) => document.getElementById(id);

function nomDia(iso, index) {
  const data = new Date(iso + 'T12:00:00');
  const llarg = data.toLocaleDateString('ca', { weekday: 'long', day: 'numeric', month: 'long' });
  return (index === 0 ? 'Avui, ' : 'Demà, ') + llarg;
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

function targeta(nom, trajecte) {
  const v = TEXT_VEREDICTE[trajecte.veredicte];
  const art = element('article', 'targeta ' + trajecte.veredicte + (trajecte.passat ? ' passat' : ''));
  art.setAttribute('aria-label', `${nom}: ${v.titol}`);
  const cap = element('p', 'trajecte', `${nom} · ${trajecte.inici}–${trajecte.fi}`);
  if (trajecte.passat) cap.append(element('span', 'etiqueta-passat', 'Ja ha passat'));
  art.append(cap);
  art.append(element('p', 'veredicte', v.titol));
  art.append(element('p', 'frase', v.frase));
  const perque = element('h3', 'perque', 'Per què');
  const llista = element('ul', 'motius');
  for (const motiu of trajecte.motius) {
    const li = element('li', 'motiu ' + motiu.nivell);
    li.append(element('span', 'visualment-amagat', TEXT_NIVELL[motiu.nivell] + ': '));
    li.append(document.createTextNode(motiu.text));
    llista.append(li);
  }
  art.append(perque, llista);
  return art;
}

function pinta(dades) {
  const cont = $('dies');
  cont.replaceChildren();
  dades.dies.forEach((dia, i) => {
    const sec = element('section', 'dia');
    sec.append(element('h2', null, nomDia(dia.dia, i)));
    const graella = element('div', 'graella');
    graella.append(targeta('Anada', dia.anada), targeta('Tornada', dia.tornada));
    sec.append(graella);
    cont.append(sec);
  });

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
    avisos.push('No s’han pogut llegir totes les fonts: la recomanació és menys segura.');
  }
  $('avis-dades').textContent = avisos.join(' ');
  $('avis-dades').hidden = !avisos.length;
}

fetch('dades.json', { cache: 'no-store' })
  .then((r) => r.json())
  .then(pinta)
  .catch(() => {
    $('dies').replaceChildren(element('p', 'avis', 'No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.'));
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
