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
    const etiqueta = element('label', 'consulta-opcio');
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

// Els trossos d'una línia, com a elements.
function nodesLinia(linia) {
  return linia.map((tros) => {
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
    return node;
  });
}

// Paràgrafs separats per les línies en blanc, com al bot.
function pintaText(text) {
  const peces = [];
  let p = null;
  for (const linia of trossos(text)) {
    if (!linia.length) { p = null; continue; }
    if (p) p.append(element('br'));
    else { p = element('p'); peces.push(p); }
    p.append(...nodesAmbMarques(ambMarques(linia)));
  }
  return peces;
}

// El pol·len, a la web amb una barra de nivell per tipus (de 0 a 4, com
// l'escala del PIA) i la tendència; al bot, el text (Juanjo, 09-10-2026: «es
// una seccion un poco aburrida»). Els que són a zero i estables, en una línia.
const NIVELLS_POLLEN = () => [T('Nul'), T('Baix'), T('Mig'), T('Alt'), T('Màxim')];
const TENDENCIES = () => ({ A: ['↑', T('En augment')], D: ['↓', T('En descens')], '!': ['!', T('Situació excepcional')] });

function dataCurta(iso) {
  const [, m, d] = iso.split('-').map(Number);
  return `${d}/${m}`;
}

function filesPollen(tipus, idioma) {
  const nivells = NIVELLS_POLLEN();
  const tend = TENDENCIES();
  const llista = element('ul', 'pollen');
  const nuls = [];
  for (const t of [...tipus].sort((a, b) => b.nivell - a.nivell)) {
    const nom = t.nom[idioma] || t.nom.ca;
    if (t.nivell === 0 && !tend[t.tendencia]) { nuls.push(nom); continue; }
    const li = element('li', `pollen-fila nivell-${t.nivell}`);
    const barra = element('span', 'pollen-barra');
    barra.setAttribute('aria-hidden', 'true');
    for (let n = 1; n <= 4; n += 1) barra.append(element('span', n <= t.nivell ? 'ple' : null));
    li.append(element('span', 'pollen-nom', nom), barra, element('span', 'pollen-nivell', nivells[t.nivell]));
    const tt = tend[t.tendencia];
    if (tt) {
      const fletxa = element('span', 'pollen-tendencia', tt[0]);
      fletxa.title = tt[1];
      fletxa.setAttribute('aria-label', tt[1]);
      li.append(fletxa);
    }
    llista.append(li);
  }
  const peces = [llista];
  if (nuls.length) peces.push(element('p', 'pollen-nuls', T`${nuls.join(', ')}: nivell nul.`));
  return peces;
}

function pintaPollen(p) {
  const idioma = IDIOMA.codi === 'es' ? 'es' : 'ca';
  const cap = element('p');
  cap.append(element('strong', null, T('Pol·len a Bellaterra')),
    T` (setmana del ${dataCurta(p.inici)} al ${dataCurta(p.fi)}, a ${coma(p.km)} km)`);
  const peces = [cap];
  if (new Date(p.fi + 'T23:59') < new Date()) peces.push(element('p', 'nota', T('Són les dades de l’última setmana publicada.')));
  peces.push(element('h2', 'pollen-grup', T('Pol·len')), ...filesPollen(p.pollens || [], idioma));
  peces.push(element('h2', 'pollen-grup', T('Espores de fongs')), ...filesPollen(p.espores || [], idioma));
  const peu = element('p', 'nota');
  const a = element('a', null, 'Punt d’Informació Aerobiològica (UAB)');
  a.href = (p.url || {})[idioma] || (p.url || {}).ca || 'https://aerobiologia.cat/';
  a.target = '_blank';
  a.rel = 'noopener';
  peu.append(a, ' · CC BY-NC-SA 4.0');
  peces.push(peu);
  return peces;
}

// --- Aire (ADR 0054): l'escala europea amb els seus colors oficials (els de
// l'Agència Europea de Medi Ambient), on és ara, cada contaminant i cada hora
// del que queda del dia. ---
const CATEGORIES_AIRE = ['bona', 'raonablement_bona', 'regular', 'desfavorable', 'molt_desfavorable',
  'extremadament_desfavorable'];
const NOMS_AIRE = () => ({
  bona: T('Bona'), raonablement_bona: T('Raonablement bona'), regular: T('Regular'), desfavorable: T('Desfavorable'),
  molt_desfavorable: T('Molt desfavorable'), extremadament_desfavorable: T('Extremadament desfavorable'),
});
const CONTAMINANTS_AIRE = () => ({ pm2_5: T('Partícules fines (PM2,5)'), pm10: T('Partícules (PM10)'),
  nitrogen_dioxide: T('Diòxid de nitrogen (NO₂)'), ozone: T('Ozó (O₃)'), sulphur_dioxide: T('Diòxid de sofre (SO₂)') });
const categoriaAire = (i) => CATEGORIES_AIRE[[20, 40, 60, 80, 100].filter((l) => i > l).length];
const MESURES_AIRE = () => `https://mediambient.gencat.cat/${IDIOMA.codi === 'es' ? 'es' : 'ca'}/05_ambits_dactuacio/atmosfera/qualitat_de_laire/vols-saber-que-respires/`;

function escalaAire(index) {
  const escala = element('div', 'aire-escala');
  escala.setAttribute('aria-hidden', 'true');
  for (const c of CATEGORIES_AIRE) escala.append(element('span', 'aire-' + c));
  const marca = element('span', 'aire-marca');
  marca.style.left = `${Math.min(index, 120) / 120 * 100}%`;
  escala.append(marca);
  return escala;
}

function pintaAire(a) {
  const noms = NOMS_AIRE();
  const cat = a.categoria || categoriaAire(a.index);
  const cap = element('p');
  cap.append(element('strong', null, T('Qualitat de l’aire a Montflorit')));
  const ara = element('p', 'aire-ara');
  ara.append(element('span', 'aire-xip aire-' + cat, noms[cat]), ' ', T`índex europeu ${a.index}`);
  const peces = [cap, ara, escalaAire(a.index)];
  // Cada contaminant, amb el seu índex, de més a menys.
  const llista = element('ul', 'pollen');
  for (const [c, v] of Object.entries(a.contaminants || {}).sort((x, y) => y[1] - x[1])) {
    const k = categoriaAire(v);
    const li = element('li', 'aire-fila');
    const barra = element('span', 'aire-barra');
    barra.setAttribute('aria-hidden', 'true');
    const ple = element('span', 'aire-' + k);
    ple.style.width = `${Math.max(4, Math.min(v, 100))}%`;
    barra.append(ple);
    li.append(element('span', 'pollen-nom', CONTAMINANTS_AIRE()[c] || c), barra, element('span', 'pollen-nivell', noms[k]));
    llista.append(li);
  }
  if (llista.children.length) peces.push(element('h2', 'pollen-grup', T('Per contaminant')), llista);
  // La resta del dia, hora a hora.
  const hores = a.hores || [];
  if (hores.length > 1) {
    const tira = element('div', 'aire-hores');
    for (const h of hores) {
      const k = categoriaAire(h.index);
      const cel = element('span', 'aire-hora');
      const color = element('span', 'aire-' + k);
      color.title = `${horaCurta(h.hora)} · ${noms[k]} (${h.index})`;
      cel.append(color, element('span', null, h.hora.slice(11, 13)));
      tira.append(cel);
    }
    tira.setAttribute('aria-hidden', 'true');
    peces.push(element('h2', 'pollen-grup', T('La resta del dia')), tira);
    if (a.pitjor && a.pitjor.index > a.index && a.pitjor.categoria !== cat) {
      peces.push(element('p', 'nota', T`El pitjor moment: ${noms[a.pitjor.categoria].toLowerCase()} cap a les ${horaCurta(a.pitjor.hora)}.`));
    }
  }
  // Que és una estimació d'una zona, i què s'ha corregit amb les estacions
  // (Juanjo, 09-10-2026: «¿realmente es la de Montflorit?»).
  const curts = CURT_AIRE();
  const corregits = ORDRE_AIRE.filter((c) => (a.factors || {})[c]).map((c) => curts[c]);
  let nota = T('Estimació del model europeu CAMS per a una zona d’uns 10 km al voltant de Bellaterra, no mesurada a Montflorit');
  if (corregits.length) {
    const llista = corregits.length > 1 ? `${corregits.slice(0, -1).join(', ')} ${T('i')} ${corregits.at(-1)}` : corregits[0];
    nota += T`; ${llista}, corregits amb les mesures de les estacions dels últims 30 dies.`;
  } else nota += '.';
  peces.push(element('p', 'nota', nota));
  const peu = element('p', 'nota');
  peu.append(enllacExtern(T('Mesures de les estacions (Generalitat)'), MESURES_AIRE()));
  peces.push(peu);
  return peces;
}

const ORDRE_AIRE = ['nitrogen_dioxide', 'ozone', 'pm10', 'pm2_5', 'sulphur_dioxide'];
const CURT_AIRE = () => ({ nitrogen_dioxide: 'NO₂', ozone: T('ozó'), pm10: 'PM10', pm2_5: 'PM2,5', sulphur_dioxide: 'SO₂' });


// --- Sol: el dia en una barra (la llum entre la sortida i la posta, i ara), i
// l'índex UV amb els colors de l'OMS. ---
const UV = () => [[2, 'uv-baix', T('baix')], [5, 'uv-moderat', T('moderat')], [7, 'uv-alt', T('alt')],
  [10, 'uv-molt-alt', T('molt alt')], [99, 'uv-extrem', T('extrem')]];
const minutsDelDia = (iso) => Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16));

function pintaSol(dies) {
  const avui = dies[0];
  const peces = [element('p', null, '')];
  peces[0].append(element('strong', null, T('El sol avui a Montflorit')));
  const s = minutsDelDia(avui.sortida);
  const p = minutsDelDia(avui.posta);
  const dia = element('div', 'sol-dia');
  dia.setAttribute('aria-hidden', 'true');
  const llum = element('span', 'sol-llum');
  llum.style.left = `${s / 1440 * 100}%`;
  llum.style.width = `${(p - s) / 1440 * 100}%`;
  dia.append(llum);
  dia.title = T`Hores de llum: de ${horaCurta(avui.sortida)} a ${horaCurta(avui.posta)}`;
  // A sota, l'escala del dia: 0 h, la sortida i la posta just on comença i
  // acaba la llum, i 24 h; a sobre, «ara» (Juanjo, 09-10-2026: amb les hores
  // als extrems «no se entiende»).
  const posa = (classe, text, minuts) => {
    const e = element('span', classe, text);
    if (minuts != null) e.style.left = `${minuts / 1440 * 100}%`;
    return e;
  };
  const hores = element('div', 'sol-hores');
  hores.setAttribute('aria-hidden', 'true');
  // «0 h» i «24 h» només si no toquen la sortida o la posta (a l'estiu, la
  // posta és cap a les 21:30, prop del final).
  if (s > 1440 * 0.14) hores.append(posa('sol-extrem', '0 h'));
  hores.append(posa('sol-punt', `↑ ${horaCurta(avui.sortida)}`, s), posa('sol-punt', `↓ ${horaCurta(avui.posta)}`, p));
  if (p < 1440 * 0.84) hores.append(posa('sol-extrem sol-fi', '24 h'));
  const sobre = element('div', 'sol-sobre');
  sobre.setAttribute('aria-hidden', 'true');
  const ara = new Date();
  const dataLocal = `${ara.getFullYear()}-${String(ara.getMonth() + 1).padStart(2, '0')}-${String(ara.getDate()).padStart(2, '0')}`;
  if (dataLocal === avui.dia) {
    const minuts = ara.getHours() * 60 + ara.getMinutes();
    const m = element('span', 'sol-ara');
    m.style.left = `${minuts / 1440 * 100}%`;
    dia.append(m);
    sobre.append(posa('sol-punt', T('ara'), minuts));
  }
  peces.push(sobre);
  // Per als lectors de pantalla, en text.
  peces.push(element('p', 'visualment-amagat', T`Surt a les ${horaCurta(avui.sortida)} i es pon a les ${horaCurta(avui.posta)}.`));
  const llumMin = p - s;
  peces.push(dia, hores, element('p', null, T`${Math.floor(llumMin / 60)} h ${llumMin % 60} min de llum.`));
  if (avui.uv_max != null) {
    const uv = Math.round(avui.uv_max);
    const [, classe, nom] = UV().find(([lim]) => uv <= lim);
    const linia = element('p', 'sol-uv');
    linia.append(element('span', 'uv-xip ' + classe, T`UV ${uv}`), ' ', T`Índex UV màxim ${nom}.`);
    if (uv >= 3) linia.append(' ', T('A les hores centrals, protector solar, gorra i ulleres de sol.'));
    peces.push(linia);
  }
  if (dies[1]) peces.push(element('p', 'nota', T`Demà surt a les ${horaCurta(dies[1].sortida)} i es pon a les ${horaCurta(dies[1].posta)}.`));
  return peces;
}

// --- Avui i demà: el text del bot. Les icones, només les que porta el text
// (ADR 0065): el bot hi posa emojis i, per a la web, marques («⟦i-sun⟧»,
// «⟦alt⟧») que aquí es dibuixen amb les icones de colors de la web. La que
// obre la línia va a la columna de les icones; les altres línies hi porten la
// del seu tema. ---
const MARCA = /⟦([a-z-]+)⟧ ?/;
const NOM_CEL = () => ({
  'i-sun': T('Serè'), 'i-moon-cel': T('Serè'), 'i-cloud-sun': T('Poc ennuvolat'), 'i-cloud-moon': T('Poc ennuvolat'),
  'i-cloud': T('Mig ennuvolat'), 'i-cloudy': T('Molt ennuvolat'), 'i-cloud-fog': T('Boira'),
  'i-cloud-sun-rain': T('Possible pluja'), 'i-cloud-moon-rain': T('Possible pluja'), 'i-cloud-drizzle': T('Pluja feble'),
  'i-cloud-rain': T('Pluja'), 'i-cloud-rain-wind': T('Pluja forta'), 'i-cloud-snow': T('Neu'),
  'i-cloud-lightning': T('Tempesta'), 'i-cloud-hail': T('Tempesta amb calamarsa'), 'i-umbrella': T('Plou ara'),
});
const NIVELLS_MARCA = ['nul', 'baix', 'mig', 'alt', 'maxim', 'extrem'];
// Les línies sense marca també en porten una, perquè la columna no quedi amb
// forats (Juanjo, 10-10-2026: «haría falta 1 icono por línea»): sense pluja,
// el paraigua tancat, com «No plou» de la web; la resta, la del tema, en gris.
const ICONA_LINIA = [
  [/^(Sense pluja|Sin lluvia)/, 'i-umbrella-off'],
  [/^Temperatura/, 'i-thermometer'],
  [/^(Trens|Trenes)/, 'i-train-front'],
  [/^(Roba|Ropa)/, 'i-shirt'],
];

// Una marca, com a element: el cel, amb la icona i el seu nom per a qui no la
// veu; el nivell, un cercle del seu color (el text ja diu quin és).
function nodeMarca(clau) {
  if (NIVELLS_MARCA.includes(clau)) {
    const punt = element('span', 'punt-nivell punt-' + clau);
    punt.setAttribute('aria-hidden', 'true');
    return punt;
  }
  const nom = NOM_CEL()[clau];
  const s = element('span', 'icona-cel');
  s.append(icona(clau));
  if (nom) {
    s.setAttribute('role', 'img');
    s.setAttribute('aria-label', nom);
    s.title = nom;
  }
  return s;
}

// Els trossos d'una línia amb les marques separades: [{marca}] o el tros.
function ambMarques(linia) {
  const res = [];
  for (const tros of linia) {
    tros.t.split(MARCA).forEach((part, n) => {
      if (n % 2) res.push({ marca: part });
      else if (part) res.push({ ...tros, t: part });
    });
  }
  return res;
}

function nodesAmbMarques(trossos) {
  const nodes = [];
  for (const tros of trossos) nodes.push(...(tros.marca ? [nodeMarca(tros.marca)] : nodesLinia([tros])));
  return nodes;
}

function pintaResum(text) {
  const peces = [];
  for (const linia of trossos(text)) {
    if (!linia.length) continue;
    const trs = ambMarques(linia);
    const fila = element('p', 'resum-linia');
    if (peces.length) {
      const primera = trs[0] && trs[0].marca ? trs.shift() : null;
      const pla = trs.map((t) => t.t || '').join('');
      const tema = (ICONA_LINIA.find(([re]) => re.test(pla)) || [])[1];
      fila.append(primera ? nodeMarca(primera.marca) : tema ? icona(tema) : element('span', 'resum-buit'));
    }
    const cos = element('span');
    cos.append(...nodesAmbMarques(trs));
    fila.append(cos);
    peces.push(fila);
  }
  return peces;
}

// El títol de la fitxa, com al bot.
function titol(text) {
  const p = element('p', 'consulta-titol');
  p.append(element('strong', null, text));
  return p;
}

// Només avisa de les fonts de la fitxa triada: «Avui» i «Demà» surten de la
// previsió (i «Avui», també dels trens); les altres fitxes ja diuen soles
// «Ara aquesta consulta no està disponible» si els falta la dada.
function fontsConsulta() {
  if (triada === 'avui') return [...FONTS_TEMPS, 'trens'];
  return triada === 'dema' ? FONTS_TEMPS : [];
}

function pintaConsulta() {
  const caixa = $('consulta');
  if (!DADES) return;
  if (!dadesVelles(DADES)) pintaHorari(DADES, fontsConsulta());
  let peces = null;
  if (triada === 'pollen' && DADES.pollen) peces = pintaPollen(DADES.pollen);
  else if (triada === 'aire' && DADES.aire && DADES.aire.index != null) peces = pintaAire(DADES.aire);
  else if (triada === 'sol' && DADES.sol && DADES.sol.length) peces = pintaSol(DADES.sol);
  else if (triada === 'trens' && DADES.trens && (DADES.trens.linies || []).length) {
    peces = [titol(T('Trens de Cerdanyola')), ...blocTrens(DADES.trens)];
  } else if (triada === 'transit' && DADES.transit) {
    peces = [titol(T('Trànsit a menys de 5\u00a0km de Montflorit')), ...blocTransit(DADES.transit)];
    if (!DADES.transit.incidencies.length) peces.splice(1, 0, element('p', null, T('Cap incidència a menys de 5\u00a0km de Montflorit.')));
  }
  if (peces) {
    caixa.replaceChildren(...peces);
    return;
  }
  const textos = (DADES.consultes || {})[IDIOMA.codi === 'es' ? 'es' : 'ca'] || {};
  const text = textos[triada];
  if (!text) caixa.replaceChildren(element('p', 'nota', T('Ara aquesta consulta no està disponible.')));
  else caixa.replaceChildren(...((triada === 'avui' || triada === 'dema') ? pintaResum(text) : pintaText(text)));
}

function pinta(dades) {
  DADES = dades;
  // Dades de fa massa: només l'avís i on mirar (ADR 0031).
  const velles = dadesVelles(dades);
  $('opcions').hidden = velles;
  if (velles) $('consulta').replaceChildren(blocDadesVelles(dades));
  else pintaConsulta();
  pintaHorari(dades, fontsConsulta());
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
