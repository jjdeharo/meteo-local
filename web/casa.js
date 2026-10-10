// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix casa.json (el genera casa.py) i pinta el temps a casa: el que mesura
// ara l'estació de casa i la previsió hora a hora, 24 hores com a mínim i
// fins a les 21 h de demà (ADR 0041).

// La pàgina pública («Temps a Montflorit», ADR 0024) és aquesta mateixa amb
// tres coses canviades a l'etiqueta <html>: el nom del lloc, com s'anomena
// l'estació pròpia i el fitxer de dades.
const LLOC = document.documentElement.dataset.lloc || 'casa';
const ESTACIO_PROPIA = document.documentElement.dataset.estacio || 'l\u2019estació de casa';
const FITXER_DADES = document.documentElement.dataset.dades || 'casa.json';

// Si l'hora és de pluja, segons la probabilitat i no segons els mil·límetres
// del model més plujós: «pluja» si és més probable que plogui que no (50 % o
// més) i «possible» des del 20 %, els mateixos llindars que config.py. Sense
// probabilitat, manen els mil·límetres.
const PROB_PLUJA = 0.5;
const PROB_POSSIBLE = 0.2;
function plujaHora(f) {
  const p = f.probabilitat;
  if (f.plou_ara || (p == null ? f.pluja_mm >= 0.2 : p >= PROB_PLUJA)) return 'pluja';
  return p != null && p >= PROB_POSSIBLE ? 'possible' : null;
}

// Descripció del cel i la icona que hi correspon. Els mil·límetres diuen com
// seria la pluja, no si n'hi haurà: sense prou probabilitat, només els
// núvols. De nit, la lluna en lloc del sol (a mitja hora del tram).
// Les paraules són les del manual d'estil de Meteocat (ADR 0043). Intensitat
// en una hora (el manual la dona per 30 minuts, aquí el doble): pluja
// moderada des de 6 mm, forta des de 40, torrencial des de 80; neu moderada
// des de 2 cm, forta des de 10. Tipus pels codis de temps d'Open-Meteo.
const INTENSITAT_PLUJA = [6, 40, 80];
const INTENSITAT_NEU = [2, 10];
const esNeu = (c) => (c >= 71 && c <= 77) || c === 85 || c === 86;
const esGelant = (c) => c === 56 || c === 57 || c === 66 || c === 67;
const esCalamarsa = (c) => c === 96 || c === 99;

function cel(f) {
  const nit = alturaSol(new Date(new Date(f.hora).getTime() + 18e5)) < 0;
  const pluja = plujaHora(f);
  const tempesta = f.codi >= 95;
  if (pluja === 'pluja') {
    if (tempesta) return esCalamarsa(f.codi) ? [T('Tempesta amb calamarsa'), 'i-cloud-hail'] : [T('Tempesta'), 'i-cloud-lightning'];
    if (esNeu(f.codi)) {
      const cm = f.neu || 0;
      return [cm >= INTENSITAT_NEU[1] ? T('Neu forta') : cm >= INTENSITAT_NEU[0] ? T('Neu moderada') : T('Neu feble'), 'i-cloud-snow'];
    }
    if (esGelant(f.codi)) return [T('Pluja gelant'), 'i-cloud-rain'];
    const mm = f.pluja_mm || 0;
    if (mm >= INTENSITAT_PLUJA[2]) return [T('Pluja torrencial'), 'i-cloud-rain-wind'];
    if (mm >= INTENSITAT_PLUJA[1]) return [T('Pluja forta'), 'i-cloud-rain-wind'];
    if (mm >= INTENSITAT_PLUJA[0]) return [T('Pluja moderada'), 'i-cloud-rain'];
    return [T('Pluja feble'), 'i-cloud-drizzle'];
  }
  if (pluja === 'possible') {
    if (esNeu(f.codi)) return [T('Possible neu'), 'i-cloud-snow'];
    return [tempesta ? T('Possible tempesta') : T('Possible pluja'), nit ? 'i-cloud-moon-rain' : 'i-cloud-sun-rain'];
  }
  if (esBoira(f)) return [T('Boira'), 'i-cloud-fog'];
  if (f.nuvols == null) return ['', null];
  // Si algun model hi posa pluja (0,2 mm o més, el que ja mulla), el cel no
  // pot sortir serè encara que la probabilitat sigui baixa: com a mínim, núvols.
  return celNuvols(nuvolsHora(f), nit);
}

const nuvolsHora = (f) => ((f.pluja_mm || 0) >= 0.2 ? Math.max(f.nuvols, 50) : f.nuvols);
const esBoira = (f) => f.codi === 45 || f.codi === 48;

// Per vuitens de cel tapat: serè 0, poc 1-2, mig 3-5, molt 6-7, cobert 8.
function celNuvols(nuvols, nit) {
  if (nuvols < 20) return [T('Serè'), nit ? 'i-moon-cel' : 'i-sun'];
  if (nuvols < 45) return [T('Poc ennuvolat'), nit ? 'i-cloud-moon' : 'i-cloud-sun'];
  if (nuvols < 70) return [T('Mig ennuvolat'), 'i-cloud'];
  if (nuvols < 85) return [T('Molt ennuvolat'), 'i-cloudy'];
  return [T('Cobert'), 'i-cloudy'];
}

// Com canvia la pressió en tres hores, amb els llindars habituals: menys d'1
// hPa és estable; 3,6 hPa o més, un canvi ràpid.
function textPressio(casa) {
  const p = T`Pressió ${coma(casa.pressio, 0)} hPa`;
  const d = casa.pressio_3h;
  if (d == null) return p;
  if (Math.abs(d) < 1) return T`${p}, estable`;
  const sentit = d > 0 ? T('pujant') : T('baixant');
  const rapid = Math.abs(d) >= 3.6 ? T(' ràpid') : '';
  const signe = d > 0 ? '+' : '\u2212';
  return T`${p}, ${sentit}${rapid} (${signe}${coma(Math.abs(d))} en 3 h)`;
}

// Temperatura, humitat, pressió i pluja, de l'estació de casa (plou només
// quan en marca: el seu zero no és fiable, ADR 0017); el vent, de Meteocat.
// Cada dada, amb la seva icona, perquè es llegeixi d'una ullada.
function dada(id, text) {
  const li = element('li');
  li.append(icona(id), document.createTextNode(text));
  return li;
}

// Resum del que ve per trams del dia (matí 7–14, tarda 14–21, nit 21–7): el
// cel i les temperatures sempre; la pluja, només si alguna hora en té com a
// mínim de possible (Juanjo, 09-10-2026: «símbolo de lluvia solo si va a
// llover»); els fenòmens, només quan es donen, amb els llindars grocs del Pla
// Meteoalerta que ja usa config.RISC_LLINDARS, més neu i gel. Cada tram és un
// desplegable de la taula, amb aquest resum a la capçalera (Juanjo,
// 09-10-2026: «dividir la lista del tiempo en mañana, tarde, noche como
// desplegables»).
const TRAMS = [[7, 14, 'Matí'], [14, 21, 'Tarda'], [21, 7, 'Nit']];
const FENOMENS = { pluja_forta: INTENSITAT_PLUJA[1], pluja_torrencial: INTENSITAT_PLUJA[2], ratxa: 70, calor: 36, glaçada: 0 };
// Els noms, amb T() literal perquè les proves de traducció els trobin.
const NOM_TRAM = { Matí: () => T('Matí'), Tarda: () => T('Tarda'), Nit: () => T('Nit') };
const NOM_TRAM_DEMA = { Matí: () => T('Demà matí'), Tarda: () => T('Demà tarda'), Nit: () => T('Demà nit') };
const NOM_FENOMEN = {
  tempesta: () => T('tempesta'), pluja_forta: () => T('pluja forta'), pluja_torrencial: () => T('pluja torrencial'),
  neu: () => T('neu'), calor: () => T('calor'), glaçada: () => T('glaçada'),
};

function tramDe(f) {
  const d = new Date(f.hora);
  const h = d.getHours();
  const [ini, fi, nom] = TRAMS.find(([a, b]) => (a < b ? h >= a && h < b : h >= a || h < b));
  // La nit comença el dia anterior si som a la matinada.
  const dia = new Date(d);
  if (nom === 'Nit' && h < 7) dia.setDate(dia.getDate() - 1);
  return { clau: `${dia.toDateString()}|${nom}`, nom, ini, fi, dia };
}

// El cel del tram: boira si n'hi ha la major part de les hores; si no, la
// mitjana dels núvols. Només el cel: la pluja la diu el paraigua.
function celTram(files, nit) {
  if (files.filter(esBoira).length * 2 > files.length) return [T('Boira'), 'i-cloud-fog'];
  const n = files.filter((f) => f.nuvols != null).map(nuvolsHora);
  return n.length ? celNuvols(n.reduce((a, b) => a + b, 0) / n.length, nit) : null;
}

// Tots els trams que toca la previsió, sense les hores ja passades. Les hores
// diuen les que hi ha de veritat: el tram en curs, «fins a les…», i l'últim,
// sencer (casa.py arriba fins a les 21 h de demà i acaba amb un tram), o fins
// on arribin les dades si en falten.
// Quants graus més o menys que el dia abans (Juanjo, 10-10-2026; ADR 0061):
// el tram d'avui, amb les mateixes hores d'ahir, mesurades a l'estació; el de
// demà, amb avui (el mesurat fins ara i la previsió de la resta). La màxima de
// dia i la mínima de nit; la xifra, només des de COMPARA_MIN graus. Igual que
// bot.compara_temp, que les proves comparen.
const COMPARA_MIN = 2;

function diaAbans(clau) {
  const [dia, hora] = clau.split('T');
  const t = new Date(`${dia}T12:00`);
  t.setDate(t.getDate() - 1);
  const dos = (n) => String(n).padStart(2, '0');
  return `${t.getFullYear()}-${dos(t.getMonth() + 1)}-${dos(t.getDate())}T${hora}`;
}

function comparaTemp(files, nit, mesurada, totes) {
  if (!mesurada || !Object.keys(mesurada).length || !files.length) return null;
  const previstes = Object.fromEntries((totes || []).map((f) => [f.hora, f]));
  const abans = [];
  for (const f of files) {
    const a = mesurada[diaAbans(f.hora)];
    const b = mesurada[diaAbans(f.fins)];
    const p = previstes[diaAbans(f.hora)];
    const v = a != null && b != null ? (a + b) / 2 : (p ? p.temperatura : null);
    if (v == null || f.temperatura == null) return null;
    abans.push(v);
  }
  const ara = files.map((f) => f.temperatura);
  const d = nit ? Math.min(...ara) - Math.min(...abans) : Math.max(...ara) - Math.max(...abans);
  return Math.sign(d) * Math.floor(Math.abs(d) + 0.5);
}

function textComparacio(n, esDema) {
  if (n == null) return null;
  if (Math.abs(n) < COMPARA_MIN) return esDema ? T('semblant a avui') : T('semblant a ahir');
  if (esDema) return n > 0 ? T`${Math.abs(n)}° més que avui` : T`${Math.abs(n)}° menys que avui`;
  return n > 0 ? T`${Math.abs(n)}° més que ahir` : T`${Math.abs(n)}° menys que ahir`;
}

function resumTrams(hores, ara, mesurada) {
  const grups = [];
  for (const f of hores || []) {
    if (new Date(f.fins) <= ara) continue;
    const t = tramDe(f);
    let g = grups.find((x) => x.clau === t.clau);
    if (!g) grups.push(g = { ...t, files: [] });
    g.files.push(f);
  }
  const dema = new Date(ara);
  dema.setDate(dema.getDate() + 1);
  return grups.map((g) => {
    const temps = g.files.map((f) => f.temperatura).filter((t) => t != null);
    const fenomens = [];
    const tempesta = (f) => f.codi >= 95 || (f.avisos || []).some((a) => (a.tipus || []).includes('tempestes'));
    if (g.files.some(tempesta)) fenomens.push([NOM_FENOMEN.tempesta(), 'i-cloud-lightning']);
    if (g.files.some((f) => (f.pluja_mm || 0) >= FENOMENS.pluja_torrencial)) fenomens.push([NOM_FENOMEN.pluja_torrencial(), 'i-cloud-rain-wind']);
    else if (g.files.some((f) => (f.pluja_mm || 0) >= FENOMENS.pluja_forta)) fenomens.push([NOM_FENOMEN.pluja_forta(), 'i-cloud-rain-wind']);
    if (g.files.reduce((s, f) => s + (f.neu || 0), 0) >= 0.1) fenomens.push([NOM_FENOMEN.neu(), 'i-snowflake']);
    const ratxa = Math.max(...g.files.map((f) => f.ratxa || 0));
    if (ratxa >= FENOMENS.ratxa) fenomens.push([T`ratxes de ${Math.round(ratxa)}\u00a0km/h`, 'i-wind']);
    if (temps.length && Math.max(...temps) >= FENOMENS.calor) fenomens.push([NOM_FENOMEN.calor(), 'i-thermometer-sun']);
    if (temps.length && Math.min(...temps) <= FENOMENS.glaçada) fenomens.push([NOM_FENOMEN.glaçada(), 'i-thermometer-snowflake']);
    const esDema = g.dia.toDateString() === dema.toDateString();
    const actual = new Date(g.files[0].hora) <= ara;
    const fi = new Date(g.files[g.files.length - 1].fins).getHours();
    return {
      clau: g.clau,
      nom: (esDema ? NOM_TRAM_DEMA : NOM_TRAM)[g.nom](),
      hores: actual ? T`fins a les ${fi} h` : `${g.ini}–${fi} h`,
      cel: celTram(g.files, g.nom === 'Nit'),
      plou: g.files.some((f) => plujaHora(f) !== null),
      prob: Math.max(...g.files.map((f) => f.probabilitat || 0)),
      mm: g.files.reduce((s, f) => s + (f.pluja_mm || 0), 0),
      tMin: temps.length ? Math.min(...temps) : null, tMax: temps.length ? Math.max(...temps) : null,
      compara: textComparacio(comparaTemp(g.files, g.nom === 'Nit', mesurada, hores), esDema),
      fenomens,
      avis: g.files.some((f) => (f.avisos || []).length),
      files: g.files,
    };
  });
}

// La capçalera del desplegable: el nom del tram, les hores i el resum.
function resumTram(t) {
  const sum = element('summary');
  sum.append(element('strong', null, t.nom), element('span', 'quan', ` (${t.hores})`));
  const peca = (id, text, classe = 'dada') => {
    const s = element('span', classe);
    const contingut = element('span');
    contingut.append(...[].concat(text));
    s.append(icona(id), typeof text === 'string' ? text : contingut);
    sum.append(s);
  };
  if (t.cel) peca(t.cel[1], t.cel[0]);
  if (t.tMin != null) {
    // La mínima en blau i la màxima en vermell, com Meteocat (ADR 0063).
    const [min, max] = [Math.round(t.tMin), Math.round(t.tMax)];
    const xifres = min === max ? [`${min}`] : [element('span', 'temp-min', `${min}`), '–', element('span', 'temp-max', `${max}`)];
    peca('i-thermometer', [...xifres, ' °C' + (t.compara ? ` · ${t.compara}` : '')]);
  }
  if (t.plou) peca('i-umbrella', `${Math.round(t.prob * 100)} %` + (t.mm >= 1 ? T`, uns ${coma(t.mm, 0)} mm` : ''));
  for (const [text, id] of t.fenomens) peca(id, text, 'dada fenomen');
  return sum;
}

function blocAra(casa, radarDades, vent, veines, hores) {
  const sec = element('section', 'decisio targeta ara');
  sec.setAttribute('aria-label', T`El temps ara a ${LLOC}`);
  sec.append(element('h2', 'data', T`Ara a ${LLOC} (${horaCurta(casa.hora)})`));
  const temp = element('p', 'veredicte');
  const termometre = icona('i-thermometer');
  termometre.classList.add('vehicle');
  temp.append(termometre, `${coma(casa.temperatura)} °C`);
  sec.append(temp);
  // Plou si el pluviòmetre ha recollit res en els últims 15 minuts
  // (config.PLOU_ARA_MIN, ecowitt.resum_ara) o si ho ha fet alguna de les
  // estacions veïnes de Weather Underground que compten (ADR 0060).
  const plouCasa = !!casa.plou;
  const plouVeines = (veines || []).some((v) => v.plou && v.compta);
  const plou = plouCasa || plouVeines;
  const intensitat = (plouCasa && casa.intensitat) || 0;
  const llista = element('ul', 'dades-ara');
  llista.append(plouCasa ? dada('i-umbrella', T`Plou: ${coma(intensitat)} mm/h`)
    : plouVeines ? dada('i-umbrella', T('Plou en una estació veïna'))
      : dada('i-umbrella-off', T('No plou')));
  llista.append(dada('i-cloud-rain', T`${coma(casa.pluja_avui || 0)} mm avui`));
  llista.append(dada('i-droplets', T`Humitat ${coma(casa.humitat, 0)} %`));
  if (casa.pressio != null) llista.append(dada('i-gauge', textPressio(casa)));
  // El vent, de l'estació de Meteocat més propera, per mitges hores (ADR 0037).
  if (vent && vent.mitja != null) {
    const ratxa = vent.ratxa != null ? T` (ratxes de ${coma(vent.ratxa, 0)})` : '';
    // Si ve de les estacions veïnes (ADR 0064), es diu així, no amb el nom d'una estació.
    const lloc = vent.font === 'veines' ? T('estacions veïnes') : vent.estacio;
    llista.append(dada('i-wind', T`Vent ${coma(vent.mitja, 0)} km/h${ratxa}, ${lloc} ${horaCurta(vent.fins)}`));
  }
  sec.append(llista);
  const radar = blocRadar(radarDades, plou, hores);
  if (radar) sec.append(radar);
  return sec;
}

// La pluja del radar portada endavant (ADR 0019): quan arribaria a casa i,
// si ja hi és, quan pararia, «en entrenament» mentre aprèn (ADR 0049): el
// tercer valor diu si cal la marca.
function textRadar(r, plou) {
  if (!r) return null;
  const aviat = (t) => new Date(t) <= new Date(Date.now() + 5 * 60e3);
  // El que es mesura mana: si ja plou, «Pluja a sobre», encara que el radar
  // només en vegi una part; si no en veu gens, sense hora (Juanjo, 08-10-2026).
  if ((plou && (r.arriba || r.possible)) || (r.arriba && aviat(r.arriba))) {
    const fi = r.fi ? T` · pararia cap a les\u00a0${horaCurta(r.fi)}`
      : r.sense_fi ? T(' · no s’acaba en 2 hores') : '';
    return ['arriba', T('Pluja a sobre') + fi, Boolean(fi)];
  }
  if (plou) return ['arriba', T('Pluja a sobre'), false];
  if (r.arriba) return ['arriba', T`Arribaria pluja cap a les\u00a0${horaCurta(r.arriba)}`];
  if (r.possible) {
    if (aviat(r.possible)) return ['possible', T('Pluja a prop: pot arribar')];
    return ['possible', T`Pot arribar pluja cap a les\u00a0${horaCurta(r.possible)}`];
  }
  return ['res', T('No s\u2019acosta pluja en 2 hores')];
}

// On veure el radar en directe, centrat a Montflorit quan es pot.
const RADAR_EN_DIRECTE = {
  rainviewer: 'https://www.rainviewer.com/map.html?loc=41.482,2.135,9&layer=radar',
  meteocat: 'https://www.meteo.cat/observacions/radar',
};

// Si la previsió dona pluja, com a mínim possible, en alguna de les dues
// hores que venen: llavors que el radar no en vegi és notícia.
function plujaPrevistaAviat(hores, ara = new Date()) {
  const fins = new Date(ara.getTime() + 2 * 3600e3);
  return (hores || []).some((f) => new Date(f.fins) > ara && new Date(f.hora) < fins && plujaHora(f));
}

// Franja pròpia dins «Ara a casa», amb el color del que diu: ambre si la
// pluja arriba, blau si és possible, neutre si no se n'acosta. Que no se
// n'acosti només surt si la previsió en dona aviat; si no, no diu res que no
// digui ja la previsió (Juanjo, 10-10-2026: «si no anuncia nada como ahora
// mejor que no salga»; ADR 0019).
function blocRadar(r, plou, hores) {
  const t = textRadar(r, plou);
  if (!t) return null;
  if (t[0] === 'res' && !plujaPrevistaAviat(hores)) return null;
  const [estat, text, proves] = t;
  const caixa = element('div', `radar-ara ${estat}`);
  caixa.append(icona('i-radar'));
  const cos = element('div');
  const p = element('p', 'radar-text', text);
  if (proves) {
    const marca = element('span', 'en-proves', T(' (en entrenament)'));
    marca.title = T('Hora estimada amb el radar. Encara s’està entrenant amb la pluja real: pot fallar.');
    p.append(marca);
  }
  cos.append(p);
  // La font i l'hora de la imatge, com demana Meteocat per reutilitzar-la,
  // amb l'enllaç al radar en directe (Juanjo, 08-10-2026).
  const font = r.imatge === 'rainviewer' ? 'RainViewer' : 'Meteocat';
  const mov = r.cap_a ? T` \u00b7 va cap ${TD(r.cap_a)} a ${r.velocitat_kmh}\u00a0km/h` : '';
  const detall = element('p', 'radar-detall');
  const [abans, despres] = T`Radar de ${font} de les ${horaCurta(r.hora)}${mov}`.split(font);
  const enllac = element('a', null, font);
  enllac.href = RADAR_EN_DIRECTE[r.imatge === 'rainviewer' ? 'rainviewer' : 'meteocat'];
  enllac.target = '_blank';
  enllac.rel = 'noopener';
  detall.append(abans, enllac, despres);
  cos.append(detall);
  caixa.append(cos);
  return caixa;
}

// Situacions de perill segons el que mesuren les estacions i el que preveu
// la pàgina (riscos.py, ADR 0018), amb el color del nivell de l'AEMET.
function blocRiscos(riscos) {
  if (!riscos || !riscos.length) return null;
  const pitjor = riscos[0].nivell;
  const caixa = element('section', `avis risc-previst ${pitjor}`);
  caixa.setAttribute('aria-label', T('Risc previst'));
  const titol = element('p', 'titol-risc');
  titol.append(icona('i-triangle-alert'), T`Risc ${TD(pitjor)}`);
  caixa.append(titol);
  const llista = element('ul');
  for (const r of riscos) {
    // El text ve fet en català a les dades; en un altre idioma es torna a fer.
    const li = element('li', null, IDIOMA.risc ? IDIOMA.risc(r) : r.text);
    const llindar = coma(r.llindar, 0).replace('-', '\u2212');
    li.append(' ', element('span', 'detall', T`(llindar ${TD(r.nivell)} de l\u2019AEMET: ${llindar} ${r.unitat})`));
    llista.append(li);
  }
  caixa.append(llista);
  return caixa;
}

// Avisos de l'AEMET en trams d'hores seguides del mateix tram del dia amb el
// mateix avís: per a cada hora, el tram que hi comença ({nivell, tipus, hores}),
// undefined si la cobreix un tram que ha començat abans, o null si no n'hi ha.
const ORDRE_NIVELL = ['groc', 'taronja', 'vermell'];

function avisHora(f) {
  const avisos = f.avisos || [];
  if (!avisos.length) return null;
  const nivell = avisos.map((a) => a.nivell).sort((a, b) => ORDRE_NIVELL.indexOf(b) - ORDRE_NIVELL.indexOf(a))[0];
  const tipus = [...new Set(avisos.flatMap((a) => a.tipus))].sort();
  return { nivell, tipus, clau: `${nivell}|${tipus.join(',')}` };
}

function tramsAvis(hores) {
  const res = [];
  let obert = null;
  for (const f of hores) {
    const a = avisHora(f);
    if (a && obert && obert.clau === a.clau) {
      obert.hores += 1;
      res.push(undefined);
    } else {
      obert = a && { ...a, hores: 1 };
      res.push(obert);
    }
  }
  return res;
}

// Barra vertical del color de l'avís al llarg de les hores que cobreix. El
// text, tan llarg com hi càpiga; el complet, per als lectors de pantalla.
function franjaAvis(tram) {
  const td = element('td', `col-avis franja-avis ${tram.nivell}`);
  td.rowSpan = tram.hores;
  const nivell = TD(tram.nivell);
  const tipus = tram.tipus.map((x) => TD(x)).join(T(' i '));
  const complet = T`Avís ${nivell} de l\u2019AEMET per ${tipus}`;
  td.title = complet;
  const barra = element('span', 'barra-avis');
  barra.append(element('span', 'text-avis'));
  barra.dataset.textos = JSON.stringify([T`Avís ${nivell} · ${tipus}`, T`Avís ${nivell}`, T('Avís'), '']);
  barra.setAttribute('aria-hidden', 'true');
  td.append(barra, element('span', 'visualment-amagat', complet));
  return td;
}

// El text més llarg que hi cap, mesurat ja a la pàgina (l'alçada de les
// files canvia amb la pantalla).
function ajustaFranges() {
  for (const barra of document.querySelectorAll('.barra-avis')) {
    const text = barra.querySelector('.text-avis');
    for (const t of JSON.parse(barra.dataset.textos)) {
      text.textContent = t;
      if (text.offsetHeight <= barra.clientHeight - 6) break;
    }
  }
}
addEventListener('resize', ajustaFranges);

// Quins trams surten oberts (Juanjo, 09-10-2026: «no debería ser
// persistente?»). Els trams canvien de nom al llarg del dia, així que no es
// recorda cadascun sinó com ho vol veure cadascú: amb «Desplega-ho tot», tots
// oberts, desat en aquest dispositiu; si no, el primer i els que tenen un avís
// o un fenomen, perquè el perill no quedi plegat. El que s'obre o es tanca a
// mà es manté mentre la pàgina és oberta, encara que es torni a pintar amb
// dades noves, però no es desa.
const CLAU_TOT_OBERT = 'meteo.previsio-tot-obert';
function totObert() {
  try { return localStorage.getItem(CLAU_TOT_OBERT) === '1'; } catch (_) { return false; }
}
const obertsAMa = new Map();
function obertDeSortida(t, i) {
  if (obertsAMa.has(t.clau)) return obertsAMa.get(t.clau);
  return totObert() || i === 0 || t.avis || t.fenomens.length > 0;
}

// Una taula per tram, amb les mateixes columnes.
function taulaTram(t, obert) {
  const det = element('details', 'tram-hores');
  det.open = obert;
  det.dataset.clau = t.clau;
  det.append(resumTram(t));
  const contenidor = element('div', 'taula-contenidor');
  // Al mòbil la taula es desplaça de costat: s'hi ha de poder arribar amb el teclat (axe-core).
  contenidor.tabIndex = 0;
  contenidor.setAttribute('role', 'region');
  contenidor.setAttribute('aria-label', `${t.nom} (${t.hores})`);
  const taula = element('table', 'taula-hores');
  const cols = element('colgroup');
  for (const c of ['hora', 'col-avis', 'cel', 'temp', 'mm', 'prob', 'vent']) cols.append(element('col', `c-${c}`));
  taula.append(cols);
  const cap = element('thead');
  const fila = element('tr');
  // Les unitats van a la capçalera perquè la taula càpiga al mòbil.
  for (const [text, classe] of [[T('Hora'), ''], [T('Avisos'), 'col-avis'], [T('Cel'), ''], ['°C', 'num'],
    [T('Pluja (mm)'), 'num'], [T('Prob.'), 'num'], [T('Vent'), 'num']]) {
    const th = element('th', classe);
    // La columna dels avisos no porta títol a la vista: la barra ja ho diu.
    th.append(classe === 'col-avis' ? element('span', 'visualment-amagat', text) : text);
    th.scope = 'col';
    fila.append(th);
  }
  cap.append(fila);
  taula.append(cap);
  const cos = element('tbody');
  const avisos = tramsAvis(t.files);
  t.files.forEach((f, i) => {
    const tr = element('tr', { pluja: 'amb-pluja', possible: 'pluja-possible' }[plujaHora(f)] || '');
    const h0 = new Date(f.hora).getHours();
    const hora = element('th', 'hora', `${h0}–${(h0 + 1) % 24}`);
    hora.scope = 'row';
    tr.append(hora);
    const avis = avisos[i];
    if (avis === null) tr.append(element('td', 'col-avis'));
    else if (avis) tr.append(franjaAvis(avis));
    const [textCel, iconaCel] = f.plou_ara ? [T('Plou ara'), 'i-umbrella'] : cel(f);
    const celCel = element('td', 'cel');
    const linia = element('span', 'cel-text');
    if (iconaCel) linia.append(icona(iconaCel));
    linia.append(textCel);
    celCel.append(linia);
    tr.append(celCel);
    tr.append(element('td', 'num', f.temperatura == null ? '' : `${Math.round(f.temperatura)}`));
    tr.append(element('td', 'num', f.pluja_mm >= 0.1 ? coma(f.pluja_mm) : '\u2013'));
    const prob = element('td', 'num prob');
    if (f.probabilitat != null) {
      const pct = Math.round(f.probabilitat * 100);
      prob.textContent = `${pct} %${f.segons_estacio ? '*' : f.segons_radar ? '\u2020' : ''}`;
      prob.style.setProperty('--prob', `${pct}%`);
    }
    tr.append(prob);
    tr.append(element('td', 'num', f.vent == null ? ''
      : `${Math.round(f.vent)}${f.ratxa ? ` (${Math.round(f.ratxa)})` : ''}`));
    cos.append(tr);
  });
  taula.append(cos);
  contenidor.append(taula);
  det.append(contenidor);
  // Plegada, la barra de l'avís no té alçada: s'ajusta en obrir-la.
  det.addEventListener('toggle', () => {
    obertsAMa.set(t.clau, det.open);
    ajustaFranges();
    posaBotoTot();
  });
  return det;
}

function taula(hores, aprenentatge, mesurada) {
  const trams = resumTrams(hores, new Date(), mesurada);
  if (!trams.length) return null;
  const sec = element('section', 'previsio');
  const cap = element('div', 'cap-previsio');
  const boto = element('button', 'boto-tot');
  boto.type = 'button';
  boto.id = 'boto-tot';
  boto.addEventListener('click', () => {
    const obrir = boto.dataset.accio === 'obre';
    try { localStorage.setItem(CLAU_TOT_OBERT, obrir ? '1' : '0'); } catch (_) {}
    for (const d of document.querySelectorAll('.tram-hores')) {
      d.open = obrir;
      obertsAMa.set(d.dataset.clau, obrir);
    }
    posaBotoTot();
  });
  cap.append(element('h2', 'perque', T('Previsió')), boto);
  sec.append(cap);
  trams.forEach((t, i) => sec.append(taulaTram(t, obertDeSortida(t, i))));
  // Les notes, plegades: només les que diuen alguna cosa de les hores d'ara.
  const visibles = trams.flatMap((t) => t.files);
  const notes = element('details', 'com notes-taula');
  notes.append(element('summary', null, T('Com es llegeix la taula')));
  if (visibles.some((f) => f.segons_estacio)) {
    notes.append(element('p', 'nota', T('* Segons la pluja que mesura ara l\u2019estació i el que va passar en casos semblants a Sabadell i Sant Cugat entre el 2024 i el 2026.')));
  }
  if (visibles.some((f) => f.segons_radar)) {
    notes.append(element('p', 'nota', T('\u2020 Segons el radar: la pluja que hi ha ara, portada endavant a la velocitat i en la direcció que porta.')));
  }
  if (visibles.some((f) => (f.avisos || []).length)) {
    notes.append(element('p', 'nota', T('La barra de color al costat de l\u2019hora marca les hores amb avís de l\u2019AEMET, del color del nivell.')));
  }
  notes.append(element('p', 'nota', T('Vent en km/h: mitjana i, entre parèntesis, les ratxes.')));
  // La taula arriba fins a les 21 h de demà (ADR 0041): més enllà d'un dia, menys fina.
  if (visibles.length && new Date(visibles[visibles.length - 1].fins) - new Date() > 24 * 3600e3) {
    notes.append(element('p', 'nota', T('Més enllà de les 24 hores la previsió és menys precisa: alguns models no hi arriben i la probabilitat apresa és la d\u2019un dia abans.')));
  }
  const apres = textAprenentatge(aprenentatge);
  if (apres) notes.append(element('p', 'nota', apres));
  sec.append(notes);
  return sec;
}

// El botó diu el que farà: desplegar-ho tot si en queda algun de plegat.
function posaBotoTot() {
  const boto = $('boto-tot');
  if (!boto) return;
  const obre = [...document.querySelectorAll('.tram-hores')].some((d) => !d.open);
  boto.dataset.accio = obre ? 'obre' : 'plega';
  boto.replaceChildren(icona(obre ? 'i-chevrons-up-down' : 'i-chevrons-down-up'), obre ? T('Desplega-ho tot') : T('Plega-ho tot'));
}

// En imprimir, tots els trams oberts; després, com estaven.
addEventListener('beforeprint', () => {
  for (const d of document.querySelectorAll('.previsio details:not([open])')) {
    d.dataset.plegat = '1';
    d.open = true;
  }
});
addEventListener('afterprint', () => {
  for (const d of document.querySelectorAll('.previsio details[data-plegat]')) {
    d.open = false;
    delete d.dataset.plegat;
  }
});

// Com s'ha après la probabilitat de pluja i, si cal, la correcció de la
// temperatura (aprenentatge.py, ADR 0012).
function textAprenentatge(a) {
  if (!a || !a.pluja) return '';
  const data = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString(IDIOMA.codi);
  const on = LLOC;
  const any = new Date(a.pluja.des_de).getFullYear();
  let t = a.pluja.origen !== 'arxiu'
    ? T`Probabilitat de pluja apresa del que ha plogut de veritat a ${on} des del ${data(a.pluja.des_de)}, quan els models deien el mateix.`
    : T`Probabilitat de pluja apresa del que va ploure de veritat a Sabadell i Sant Cugat des del ${any}, quan els models deien el mateix.`;
  if (a.temperatura) {
    t += a.temperatura.origen === 'arxiu'
      ? T` Temperatura corregida amb el que ha mesurat ${ESTACIO_PROPIA} des del ${data(a.temperatura.des_de)}.`
      : T` Temperatura corregida amb el registre propi de ${ESTACIO_PROPIA} des del ${data(a.temperatura.des_de)}.`;
  }
  return t;
}

function pinta(dades) {
  const cont = $('casa');
  cont.replaceChildren();
  // Dades de fa massa: només l'avís i on mirar (ADR 0031).
  if (dadesVelles(dades)) {
    $('avisos').replaceChildren();
    cont.append(blocDadesVelles(dades));
    pintaHorari(dades);
    posaVersio(dades.versio);
    return;
  }
  // Tots els avisos vigents en un sol bloc, a dalt; les notes, després.
  const avisos = $('avisos');
  avisos.replaceChildren();
  const actius = blocAvisos(dades, [blocRiscos(dades.riscos)]);
  if (actius) avisos.append(actius);
  if (dades.previsio_de) avisos.append(element('p', 'avis', textPrevisioAnterior(dades)));
  if (dades.models && dades.models.no_encerten) {
    const m = dades.models;
    avisos.append(element('p', 'avis', T`Avui els models no veuen aquesta pluja: en les darreres ${m.hores} hores han caigut ${coma(m.mesurada_mm)}\u00a0mm a Montflorit i en preveien ${coma(m.prevista_mm)}. Les primeres hores de la taula parteixen del que mesura l\u2019estació; per a la resta, fes més cas dels avisos.`));
  }
  if (dades.ara_casa) cont.append(blocAra(dades.ara_casa, dades.radar, dades.vent, dades.veines, dades.hores));
  const previsio = dades.hores && taula(dades.hores, dades.aprenentatge, dades.temperatura_mesurada);
  if (previsio) {
    cont.append(previsio);
    ajustaFranges();
    posaBotoTot();
  }
  pintaHorari(dades);
  posaVersio(dades.versio);
}

carrega(FITXER_DADES, pinta, () => {
  $('casa').replaceChildren(element('p', 'avis', T('No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.')));
});
