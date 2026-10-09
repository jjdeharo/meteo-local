// SPDX-License-Identifier: AGPL-3.0-or-later
// «Consultes» (ADR 0054): les consultes del bot a la web. Es tria què es vol veure
// i surt només això, com al bot (Juanjo, 09-10-2026: «no quiero una pagina
// enorme… se elige lo que se quiere ver y entonces sale»). Els textos són els
// del bot, fets per les mateixes funcions al servidor (montflorit.py,
// consultes): la web i el bot diuen sempre el mateix.

const FITXER_DADES = document.documentElement.dataset.dades || 'casa.json';
// L'ordre i les claus, les del menú del bot.
// Sense «Ara», «Radar» ni «Avisos actius», que ja surten a «El temps»; amb el
// sol, l'aire i el pol·len, que no surten enlloc més (Juanjo, 09-10-2026).
const OPCIONS = [
  ['avui', () => T('Avui'), 'i-calendar-check'], ['dema', () => T('Demà'), 'i-calendar-plus'],
  ['sol', () => T('Sol'), 'i-sunrise'], ['aire', () => T('Aire'), 'i-factory'], ['pollen', () => T('Pol·len'), 'i-flower'],
  ['trens', () => T('Trens'), 'i-train-front'], ['transit', () => T('Trànsit'), 'i-traffic-cone'],
];
const CLAU_TRIADA = 'meteo.consultes';
let DADES = null;

// La triada: la de l'adreça (consultes.html#transit), la de l'última vegada en
// aquest dispositiu o, la primera vegada, «Avui».
function triadaInicial() {
  const delHash = location.hash.slice(1);
  if (OPCIONS.some(([c]) => c === delHash)) return delHash;
  try {
    const desada = localStorage.getItem(CLAU_TRIADA);
    if (OPCIONS.some(([c]) => c === desada)) return desada;
  } catch (_) {}
  return 'avui';
}
let triada = triadaInicial();

function tria(clau) {
  triada = clau;
  try { localStorage.setItem(CLAU_TRIADA, clau); } catch (_) {}
  history.replaceState(null, '', '#' + clau);
  pintaConsulta();
}

function pintaOpcions() {
  const caixa = $('opcions');
  for (const [clau, nom, icon] of OPCIONS) {
    const etiqueta = element('label', 'opcio');
    const boto = element('input');
    boto.type = 'radio';
    boto.name = 'consulta';
    boto.value = clau;
    boto.checked = clau === triada;
    boto.addEventListener('change', () => tria(clau));
    etiqueta.append(boto, icona(icon), element('span', null, nom()));
    caixa.append(etiqueta);
  }
}

// El text del bot porta l'HTML de Telegram: <b>, <i> i <a href="…">, amb la
// resta escapat. Es parteix en línies de trossos {t, b, i, href} i es pinta
// amb elements, sense innerHTML: el que no sigui això surt com a text.
const ENTITATS = { '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"', '&#x27;': "'", '&#39;': "'" };
const desescapa = (t) => t.replace(/&(amp|lt|gt|quot|#x27|#39);/g, (e) => ENTITATS[e]);
const ADRECA = /(https:\/\/[^\s<]+[^\s<.,;:)»])/;

function trossos(text) {
  const linies = [];
  let linia = [];
  let b = false;
  let i = false;
  let href = null;
  const afegeix = (t) => {
    const parts = t.split('\n');
    parts.forEach((part, n) => {
      if (n > 0) { linies.push(linia); linia = []; }
      // Les adreces soltes (el radar en directe), també enllaçades.
      for (const tros of desescapa(part).split(ADRECA)) {
        if (!tros) continue;
        const esAdreca = !href && ADRECA.test(tros) && tros.match(ADRECA)[0] === tros;
        linia.push({ t: tros, b, i, href: esAdreca ? tros : href });
      }
    });
  };
  const etiqueta = /<(\/?)(b|i)>|<a href="([^"]*)">|<\/a>/g;
  let pos = 0;
  for (const m of text.matchAll(etiqueta)) {
    afegeix(text.slice(pos, m.index));
    pos = m.index + m[0].length;
    if (m[2] === 'b') b = !m[1];
    else if (m[2] === 'i') i = !m[1];
    else if (m[3] !== undefined) href = /^https:\/\//.test(desescapa(m[3])) ? desescapa(m[3]) : null;
    else href = null;
  }
  afegeix(text.slice(pos));
  linies.push(linia);
  return linies;
}

// Paràgrafs separats per les línies en blanc, com al bot.
function pintaText(text) {
  const peces = [];
  let p = null;
  for (const linia of trossos(text)) {
    if (!linia.length) { p = null; continue; }
    if (p) p.append(element('br'));
    else { p = element('p'); peces.push(p); }
    for (const tros of linia) {
      let node = document.createTextNode(tros.t);
      if (tros.href) {
        const a = element('a');
        a.href = tros.href;
        a.target = '_blank';
        a.rel = 'noopener';
        a.append(node);
        node = a;
      }
      if (tros.i) { const em = element('em'); em.append(node); node = em; }
      if (tros.b) { const st = element('strong'); st.append(node); node = st; }
      p.append(node);
    }
  }
  return peces;
}

function pintaConsulta() {
  const caixa = $('consulta');
  if (!DADES) return;
  const textos = (DADES.consultes || {})[IDIOMA.codi === 'es' ? 'es' : 'ca'] || {};
  const text = textos[triada];
  caixa.replaceChildren(...(text ? pintaText(text)
    : [element('p', 'nota', T('Ara aquesta consulta no està disponible.'))]));
}

function pinta(dades) {
  DADES = dades;
  // Dades de fa massa: només l'avís i on mirar (ADR 0031).
  const velles = dadesVelles(dades);
  $('opcions').hidden = velles;
  if (velles) $('consulta').replaceChildren(blocDadesVelles(dades));
  else pintaConsulta();
  pintaHorari(dades);
  posaVersio(dades.versio);
}

pintaOpcions();
window.addEventListener('hashchange', () => {
  const clau = location.hash.slice(1);
  if (clau === triada || !OPCIONS.some(([c]) => c === clau)) return;
  triada = clau;
  for (const r of document.querySelectorAll('#opcions input')) r.checked = r.value === clau;
  pintaConsulta();
});
carrega(FITXER_DADES, pinta, () => {
  $('consulta').replaceChildren(element('p', 'avis', T('No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.')));
});
