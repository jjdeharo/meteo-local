// SPDX-License-Identifier: AGPL-3.0-or-later
// «Avisos» (ADR 0048): els avisos del temps com a notificacions del navegador,
// sense Telegram. Les mateixes opcions que el bot (ADR 0034). El servidor
// (subscripcio.php, a IONOS) desa l'adreça de notificacions del dispositiu i
// el que s'hi tria; bot/push.py els envia. Els canvis es desen sols.

const SERVIDOR = DADES_URL + 'subscripcio.php';
const TIPUS_PUSH = [
  ['perill', T('Situacions de perill'), 'i-triangle-alert'],
  ['riera', T('Desbordament de la riera de Sant Cugat (en proves)'), 'i-waves'],
  ['pluja', T('Pluja a punt de començar (15 min abans)'), 'i-cloud-rain'],
];
// Per començar, com al bot: la riera i el perill.
const PER_DEFECTE_PUSH = ['riera', 'perill'];
// Com al bot (ADR 0055): una hora al matí, o cap, i, a part, la de demà a les 21 h.
const HORES_PUSH = [['', T('Cap')], ['6', T('6 h')], ['7', T('7 h')], ['8', T('8 h')]];
const IDIOMA_PUSH = document.documentElement.lang === 'es' ? 'es' : 'ca';

let registrePush = null;
let subscripcioPush = null;

async function crida(cos) {
  const r = await fetch(SERVIDOR, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cos),
  });
  const dades = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(dades.error || r.status), { estat: r.status });
  return dades;
}

// La clau pública del servidor, en bytes, com la vol el navegador.
async function clauServidor() {
  const r = await fetch(SERVIDOR, { cache: 'no-store' });
  if (!r.ok) throw new Error(r.status);
  const b64 = (await r.json()).clau.replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(b64 + '='.repeat((4 - (b64.length % 4)) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function estat(text, error) {
  const p = $('push-estat');
  p.textContent = text;
  p.classList.toggle('error', Boolean(error));
}

function triat() {
  const form = $('push');
  return {
    avisos: [...form.querySelectorAll('input[name="tipus"]:checked')].map((c) => c.value),
    resum: form.elements.resum.value,
    nit: form.elements.nit.checked,
  };
}

function desa() {
  return crida({ accio: 'desa', subscripcio: subscripcioPush.toJSON(), ...triat(), idioma: IDIOMA_PUSH });
}

// Els canvis, d'un en un i sempre amb el que hi ha marcat en aquell moment: si
// dos guardats surten alhora, el que arriba l'últim pot dur menys canvis.
let desant = null;
let tornaADesar = false;

async function desaEnOrdre() {
  if (desant) {
    tornaADesar = true;
    return desant;
  }
  desant = (async () => {
    do {
      tornaADesar = false;
      await desa();
    } while (tornaADesar);
  })();
  try {
    await desant;
  } finally {
    desant = null;
  }
}

async function activa(e) {
  e.currentTarget.disabled = true;
  estat(T('Demanant permís…'));
  try {
    if ((await Notification.requestPermission()) !== 'granted') {
      estat(T('El navegador té bloquejades les notificacions d’aquesta web. Permet-les a la configuració del navegador (al cadenat, al costat de l’adreça) i torna-ho a provar.'), true);
      return;
    }
    const clau = await clauServidor();
    try {
      subscripcioPush = await registrePush.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: clau });
    } catch (ex) {
      // Una subscripció d'abans amb una altra clau: es treu i es torna a fer.
      const vella = await registrePush.pushManager.getSubscription();
      if (!vella) throw ex;
      await vella.unsubscribe();
      subscripcioPush = await registrePush.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: clau });
    }
    await desa();
    pinta(triat());
    estat(T('Fet: els avisos que has triat t’arribaran a aquest dispositiu. Pots enviar-te una prova.'));
  } catch (_) {
    estat(T('No s’han pogut activar els avisos. Torna-ho a provar d’aquí a una estona.'), true);
  } finally {
    const b = $('push').querySelector('button');
    if (b) b.disabled = false;
  }
}

async function desactiva() {
  try {
    await crida({ accio: 'baixa', endpoint: subscripcioPush.endpoint });
  } catch (_) { /* si no arriba, el servidor l'esborrarà quan el navegador li digui que ja no existeix */ }
  try { await subscripcioPush.unsubscribe(); } catch (_) {}
  subscripcioPush = null;
  pinta(triat());
  estat(T('Avisos desactivats en aquest dispositiu: ja no se’n desa res.'));
}

async function prova() {
  try {
    await crida({ accio: 'prova', endpoint: subscripcioPush.endpoint });
    estat(T('D’aquí a un minut t’ha d’arribar una notificació de prova.'));
  } catch (_) {
    estat(T('No s’ha pogut demanar la prova. Torna-ho a provar d’aquí a una estona.'), true);
  }
}

function boto(text, classe, accio) {
  const b = element('button', classe, text);
  b.type = 'button';
  b.addEventListener('click', accio);
  return b;
}

function pinta(opcions) {
  const form = $('push');
  const tipus = element('fieldset', 'push-tipus');
  tipus.append(element('legend', null, T('Què vols rebre')));
  for (const [clau, nom, icon] of TIPUS_PUSH) {
    const etiqueta = element('label', 'xip');
    const casella = element('input');
    casella.type = 'checkbox';
    casella.name = 'tipus';
    casella.value = clau;
    casella.checked = opcions.avisos.includes(clau);
    etiqueta.append(casella, icona(icon), element('span', null, nom));
    tipus.append(etiqueta);
  }
  const resum = element('label', 'push-resum', T('Previsió del dia, al matí, a les:'));
  const select = element('select');
  select.name = 'resum';
  for (const [valor, text] of HORES_PUSH) {
    const o = element('option', null, text);
    o.value = valor;
    select.append(o);
  }
  select.value = opcions.resum || '';
  resum.append(select);
  const nit = element('label', 'xip push-nit');
  const casellaNit = element('input');
  casellaNit.type = 'checkbox';
  casellaNit.name = 'nit';
  casellaNit.checked = Boolean(opcions.nit);
  nit.append(casellaNit, element('span', null, T('A les 21 h, la previsió de demà')));
  const botons = element('p', 'push-botons');
  if (subscripcioPush) {
    botons.append(boto(T('Envia’m una prova'), 'boto', prova), boto(T('Desactiva'), 'boto secundari', desactiva));
  } else {
    botons.append(boto(T('Activa els avisos'), 'boto', activa));
  }
  form.replaceChildren(tipus, resum, nit, botons);
  form.hidden = false;
  estat(subscripcioPush ? T('Avisos activats en aquest dispositiu. Si canvies què reps, es desa sol.')
    : T('Tria què vols rebre i toca «Activa els avisos». El navegador et demanarà permís.'));
}

async function iniciaPush() {
  const ios = /iPhone|iPad|iPod/.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
    $(ios ? 'push-iphone' : 'push-no').hidden = false;
    return;
  }
  // A Android, el consell d'instal·lar-la: Chrome pot deixar de mostrar els
  // avisos de les webs que fa temps que no s'obren, però no els de les
  // instal·lades (Juanjo, 08-10-2026).
  const installada = matchMedia('(display-mode: standalone)').matches;
  $('push-instala').hidden = !/Android/.test(navigator.userAgent) || installada;
  let opcions = { avisos: PER_DEFECTE_PUSH, resum: '', nit: false };
  try {
    // El registra comu.js; dos registres alhora encallen WebKit. Si no està
    // a punt en 15 s, no s'espera més.
    registrePush = await Promise.race([navigator.serviceWorker.ready,
      new Promise((_, no) => { setTimeout(() => no(new Error('sw')), 15000); })]);
    subscripcioPush = await registrePush.pushManager.getSubscription();
  } catch (_) {
    // El navegador diu que en té, però no les pot fer servir.
    $('push-no').hidden = false;
    return;
  }
  if (subscripcioPush) {
    try {
      opcions = await crida({ accio: 'estat', endpoint: subscripcioPush.endpoint });
    } catch (ex) {
      if (ex.estat === 404) {
        // El servidor ja no la té: com si no s'haguessin activat.
        await subscripcioPush.unsubscribe().catch(() => {});
        subscripcioPush = null;
      } else {
        pinta(opcions);
        estat(T('Ara no es pot connectar amb el servidor dels avisos. Torna-ho a provar d’aquí a una estona.'), true);
        return;
      }
    }
  }
  pinta(opcions);
  $('push').addEventListener('change', async () => {
    if (!subscripcioPush) return;
    try {
      await desaEnOrdre();
      estat(T`Desat a les ${horaCurta(new Date())}.`);
    } catch (_) {
      estat(T('No s’ha pogut desar el canvi. Torna-ho a provar d’aquí a una estona.'), true);
    }
  });
}

iniciaPush();
llegeixDades(document.documentElement.dataset.dades || 'casa.json').then((d) => posaVersio(d.versio)).catch(() => {});
