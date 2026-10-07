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
function cel(f) {
  const nit = alturaSol(new Date(new Date(f.hora).getTime() + 18e5)) < 0;
  const pluja = plujaHora(f);
  const tempesta = f.codi >= 95;
  if (pluja === 'pluja') {
    if (tempesta) return [T('Tempesta'), 'i-cloud-lightning'];
    if (f.pluja_mm >= 4) return [T('Pluja forta'), 'i-cloud-rain-wind'];
    if (f.pluja_mm >= 1) return [T('Pluja'), 'i-cloud-rain'];
    return [T('Pluja feble'), 'i-cloud-drizzle'];
  }
  if (pluja === 'possible') {
    return [tempesta ? T('Possible tempesta') : T('Possible pluja'), nit ? 'i-cloud-moon-rain' : 'i-cloud-sun-rain'];
  }
  if (f.codi === 45 || f.codi === 48) return [T('Boira'), 'i-cloud-fog'];
  if (f.nuvols == null) return ['', null];
  // Si algun model hi posa pluja (0,2 mm o més, el que ja mulla), el cel no
  // pot sortir serè encara que la probabilitat sigui baixa: com a mínim, núvols.
  const nuvols = (f.pluja_mm || 0) >= 0.2 ? Math.max(f.nuvols, 50) : f.nuvols;
  if (nuvols < 20) return [T('Serè'), nit ? 'i-moon-cel' : 'i-sun'];
  if (nuvols < 50) return [T('Poc núvol'), nit ? 'i-cloud-moon' : 'i-cloud-sun'];
  if (nuvols < 85) return [T('Núvols'), 'i-cloud'];
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

function blocAra(ara, casa, radarDades, vent) {
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
  const plouMont = !!ara && ((ara.intensitat || 0) > 0 || (ara.pluja_30min || 0) > 0);
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
  return sec;
}

// La pluja del radar portada endavant (ADR 0019): quan arribaria a casa.
function textRadar(r, plou) {
  if (!r) return null;
  const aviat = (t) => new Date(t) <= new Date(Date.now() + 5 * 60e3);
  if (r.arriba) {
    if (plou || aviat(r.arriba)) return ['arriba', T('Pluja a sobre')];
    return ['arriba', T`Arribaria pluja cap a les\u00a0${horaCurta(r.arriba)}`];
  }
  if (r.possible) {
    if (aviat(r.possible)) return ['possible', T('Pluja a prop: pot arribar')];
    return ['possible', T`Pot arribar pluja cap a les\u00a0${horaCurta(r.possible)}`];
  }
  return ['res', T('No s\u2019acosta pluja en 2 hores')];
}

// Franja pròpia dins «Ara a casa», amb el color del que diu: ambre si la
// pluja arriba, blau si és possible, neutre si no se n'acosta.
function blocRadar(r, plou) {
  const t = textRadar(r, plou);
  if (!t) return null;
  const [estat, text] = t;
  const caixa = element('div', `radar-ara ${estat}`);
  caixa.append(icona('i-radar'));
  const cos = element('div');
  cos.append(element('p', 'radar-text', text));
  // La font i l'hora de la imatge, com demana Meteocat per reutilitzar-la.
  const font = r.imatge === 'rainviewer' ? 'RainViewer' : 'Meteocat';
  const mov = r.cap_a ? T` \u00b7 va cap ${TD(r.cap_a)} a ${r.velocitat_kmh}\u00a0km/h` : '';
  cos.append(element('p', 'radar-detall', T`Radar de ${font} de les ${horaCurta(r.hora)}${mov}`));
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
    cont.append(blocDadesVelles(dades));
    pintaHorari(dades);
    posaVersio(dades.versio);
    return;
  }
  // Tots els avisos junts, a dalt; després, l'hora d'actualització.
  const avisos = $('avisos');
  avisos.replaceChildren();
  const plans = blocPlans(dades.plans);
  if (plans) avisos.append(plans);
  const riscos = blocRiscos(dades.riscos);
  if (riscos) avisos.append(riscos);
  if (dades.avisos && dades.avisos.length) avisos.append(blocAvisosAemet(dades.avisos));
  if (dades.previsio_de) avisos.append(element('p', 'avis', textPrevisioAnterior(dades)));
  if (dades.models && dades.models.no_encerten) {
    const m = dades.models;
    avisos.append(element('p', 'avis', T`Avui els models no veuen aquesta pluja: en les darreres ${m.hores} hores han caigut ${coma(m.mesurada_mm)}\u00a0mm a Montflorit i en preveien ${coma(m.prevista_mm)}. Les primeres hores de la taula parteixen del que mesura l\u2019estació; per a la resta, fes més cas dels avisos.`));
  }
  if (dades.ara || dades.ara_casa) cont.append(blocAra(dades.ara, dades.ara_casa, dades.radar, dades.vent));
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
