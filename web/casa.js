// SPDX-License-Identifier: AGPL-3.0-or-later
// Llegeix casa.json (el genera casa.py) i pinta el temps a casa: el que mesuren
// ara l'estació de casa i la de Montflorit i la previsió hora a hora per a 24 hores.

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
  if (f.codi === 45 || f.codi === 48) return [T('Boira'), 'i-cloud-fog'];
  if (f.nuvols == null) return ['', null];
  // Si algun model hi posa pluja (0,2 mm o més, el que ja mulla), el cel no
  // pot sortir serè encara que la probabilitat sigui baixa: com a mínim, núvols.
  const nuvols = (f.pluja_mm || 0) >= 0.2 ? Math.max(f.nuvols, 50) : f.nuvols;
  // Per vuitens de cel tapat: serè 0, poc 1-2, mig 3-5, molt 6-7, cobert 8.
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

// Temperatura, humitat i pressió, de l'estació de casa; pluja i vent, de
// Montflorit. Plou si qualsevol de les dues en marca (la de casa, només quan
// en marca: el seu zero no és fiable). Si en falla una, l'altra. Cada dada,
// amb la seva icona, perquè es llegeixi d'una ullada.
function dada(id, text) {
  const li = element('li');
  li.append(icona(id), document.createTextNode(text));
  return li;
}

// Resum del que ve per trams del dia (matí 7–14, tarda 14–21, nit 21–7), per
// a la targeta d'ara (Juanjo, 08-10-2026): probabilitat de pluja i
// temperatures sempre; els fenòmens, només quan es donen, amb els llindars
// grocs del Pla Meteoalerta que ja usa config.RISC_LLINDARS, més neu i gel.
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

function resumTrams(hores, ara) {
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
  return grups.slice(0, 3).map((g) => {
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
    return {
      nom: (esDema ? NOM_TRAM_DEMA : NOM_TRAM)[g.nom](),
      hores: actual ? T`fins a les ${g.fi} h` : `${g.ini}–${g.fi} h`,
      prob: Math.max(...g.files.map((f) => f.probabilitat || 0)),
      mm: g.files.reduce((s, f) => s + (f.pluja_mm || 0), 0),
      tMin: temps.length ? Math.min(...temps) : null, tMax: temps.length ? Math.max(...temps) : null,
      fenomens,
    };
  });
}

function blocTrams(hores, ara) {
  const trams = resumTrams(hores, ara);
  if (!trams.length) return null;
  const cont = element('ul', 'trams-dia');
  cont.setAttribute('aria-label', T('Pròxims trams del dia'));
  for (const t of trams) {
    const li = element('li', 'tram');
    li.append(element('strong', null, t.nom), element('span', 'quan', ` (${t.hores})`));
    const pluja = element('span', 'dada');
    const mm = t.mm >= 1 ? T`, uns ${coma(t.mm, 0)} mm` : '';
    pluja.append(icona('i-umbrella'), `${Math.round(t.prob * 100)} %${mm}`);
    li.append(pluja);
    for (const [text, id] of t.fenomens) {
      const s = element('span', 'dada fenomen');
      s.append(icona(id), text);
      li.append(s);
    }
    if (t.tMin != null) li.append(element('span', 'dada', `${Math.round(t.tMin)}–${Math.round(t.tMax)} °C`));
    cont.append(li);
  }
  return cont;
}

function blocAra(ara, casa, radarDades, vent, hores) {
  const base = casa || ara;
  const sec = element('section', 'decisio targeta ara');
  const lloc = casa ? LLOC : 'Montflorit';
  sec.setAttribute('aria-label', T`El temps ara a ${lloc}`);
  sec.append(element('h2', 'data', T`Ara a ${lloc} (${horaCurta(base.hora)})`));
  const temp = element('p', 'veredicte');
  const termometre = icona('i-thermometer');
  termometre.classList.add('vehicle');
  temp.append(termometre, `${coma(base.temperatura)} °C`);
  sec.append(temp);
  // Plou si ha caigut res en els últims 15 minuts (config.PLOU_ARA_MIN); amb
  // dades d'abans, sense aquest valor, com llavors.
  const plouMont = !!ara && ('pluja_15min' in ara ? (ara.pluja_15min || 0) > 0
    : (ara.intensitat || 0) > 0 || (ara.pluja_30min || 0) > 0);
  const plou = plouMont || !!(casa && casa.plou);
  const intensitat = Math.max((ara && ara.intensitat) || 0, (casa && casa.plou && casa.intensitat) || 0);
  const llista = element('ul', 'dades-ara');
  llista.append(plou ? dada('i-umbrella', T`Plou: ${coma(intensitat)} mm/h`) : dada('i-umbrella-off', T('No plou')));
  if (ara) llista.append(dada('i-cloud-rain', T`${coma(ara.pluja_avui || 0)} mm avui`));
  llista.append(dada('i-droplets', T`Humitat ${coma(base.humitat, 0)} %`));
  if (casa && casa.pressio != null) llista.append(dada('i-gauge', textPressio(casa)));
  // El vent, de l'estació de Meteocat més propera, per mitges hores (ADR 0037).
  if (vent && vent.mitja != null) {
    const ratxa = vent.ratxa != null ? T` (ratxes de ${coma(vent.ratxa, 0)})` : '';
    llista.append(dada('i-wind', T`Vent ${coma(vent.mitja, 0)} km/h${ratxa}, ${vent.estacio} ${horaCurta(vent.fins)}`));
  }
  sec.append(llista);
  const radar = blocRadar(radarDades, plou);
  if (radar) sec.append(radar);
  const trams = blocTrams(hores, new Date());
  if (trams) sec.append(trams);
  sec.append(elementHorari());    // «Actualitzat a les…», al peu de la targeta
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

// Franja pròpia dins «Ara a casa», amb el color del que diu: ambre si la
// pluja arriba, blau si és possible, neutre si no se n'acosta.
function blocRadar(r, plou) {
  const t = textRadar(r, plou);
  if (!t) return null;
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

function nomDia(iso) {
  return new Date(iso).toLocaleDateString(IDIOMA.codi, { weekday: 'long', day: 'numeric', month: 'long' });
}

// Avisos de l'AEMET en trams d'hores seguides del mateix dia amb el mateix
// avís: per a cada hora, el tram que hi comença ({nivell, tipus, hores}),
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
  let dia = null;
  for (const f of hores) {
    const a = avisHora(f);
    const d = new Date(f.hora).toDateString();
    if (a && obert && obert.clau === a.clau && d === dia) {
      obert.hores += 1;
      res.push(undefined);
    } else {
      obert = a && { ...a, hores: 1 };
      res.push(obert);
    }
    dia = d;
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

function taula(hores, aprenentatge) {
  const sec = element('section', 'previsio');
  sec.append(element('h2', 'perque', T('Pròximes 24 hores')));
  const contenidor = element('div', 'taula-contenidor');
  // Al mòbil la taula es desplaça de costat: s'hi ha de poder arribar amb el teclat (axe-core).
  contenidor.tabIndex = 0;
  contenidor.setAttribute('role', 'region');
  contenidor.setAttribute('aria-label', T('Pròximes 24 hores'));
  const t = element('table', 'taula-hores');
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
  t.append(cap);
  const cos = element('tbody');
  const trams = tramsAvis(hores);
  let diaAnterior = new Date().toDateString();
  hores.forEach((f, i) => {
    const inici = new Date(f.hora);
    if (inici.toDateString() !== diaAnterior) {
      diaAnterior = inici.toDateString();
      const separador = element('tr', 'dia-nou');
      const td = element('th', '', nomDia(f.hora));
      td.colSpan = 7;
      td.scope = 'rowgroup';
      separador.append(td);
      cos.append(separador);
    }
    const tr = element('tr', { pluja: 'amb-pluja', possible: 'pluja-possible' }[plujaHora(f)] || '');
    const h0 = inici.getHours();
    const hora = element('th', 'hora', `${h0}–${(h0 + 1) % 24}`);
    hora.scope = 'row';
    tr.append(hora);
    const tram = trams[i];
    if (tram === null) tr.append(element('td', 'col-avis'));
    else if (tram) tr.append(franjaAvis(tram));
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
      prob.textContent = `${pct} %${f.segons_estacio ? '*' : f.segons_radar ? '\u2020' : ''}`;
      prob.style.setProperty('--prob', `${pct}%`);
    }
    tr.append(prob);
    tr.append(element('td', 'num', f.vent == null ? ''
      : `${Math.round(f.vent)}${f.ratxa ? ` (${Math.round(f.ratxa)})` : ''}`));
    cos.append(tr);
  });
  t.append(cos);
  contenidor.append(t);
  sec.append(contenidor);
  if (hores.some((f) => f.segons_estacio)) {
    sec.append(element('p', 'nota', T('* Segons la pluja que mesura ara l\u2019estació i el que va passar en casos semblants a Sabadell i Sant Cugat entre el 2024 i el 2026.')));
  }
  if (hores.some((f) => f.segons_radar)) {
    sec.append(element('p', 'nota', T('\u2020 Segons el radar: la pluja que hi ha ara, portada endavant a la velocitat i en la direcció que porta.')));
  }
  if (trams.some((t) => t)) {
    sec.append(element('p', 'nota', T('La barra de color al costat de l\u2019hora marca les hores amb avís de l\u2019AEMET, del color del nivell.')));
  }
  sec.append(element('p', 'nota', T('Vent en km/h: mitjana i, entre parèntesis, les ratxes.')));
  const apres = textAprenentatge(aprenentatge);
  if (apres) sec.append(element('p', 'nota', apres));
  return sec;
}

// Com s'ha après la probabilitat de pluja i, si cal, la correcció de la
// temperatura (aprenentatge.py, ADR 0012).
function textAprenentatge(a) {
  if (!a || !a.pluja) return '';
  const data = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString(IDIOMA.codi);
  const on = LLOC === 'casa' ? 'Montflorit i a casa' : LLOC;
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
    cont.append(blocDadesVelles(dades), elementHorari());
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
  if (dades.ara || dades.ara_casa) cont.append(blocAra(dades.ara, dades.ara_casa, dades.radar, dades.vent, dades.hores));
  else cont.append(elementHorari());
  if (dades.hores) {
    cont.append(taula(dades.hores, dades.aprenentatge));
    ajustaFranges();
  }
  pintaHorari(dades);
  posaVersio(dades.versio);
}

carrega(FITXER_DADES, pinta, () => {
  $('casa').replaceChildren(element('p', 'avis', T('No s’ha pogut carregar la previsió. Torna-ho a provar d’aquí a una estona.')));
});
