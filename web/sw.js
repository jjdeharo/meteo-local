// SPDX-License-Identifier: AGPL-3.0-or-later
// Service worker perquè la web es pugui instal·lar com a aplicació (ADR 0015).
// Primer la xarxa: amb connexió es veu sempre la versió publicada. Sense
// connexió, les pàgines i els estils guardats. Les dades (.json) no es guarden
// mai: una previsió vella no s'ha de mostrar com si fos d'ara.
const MAGATZEM = 'meteo-local';
const PECES = ['casa.html', 'sortir.html', 'consultes.html', 'avisos.html', 'fonts.html', 'estil.css', 'comu.js', 'casa.js', 'sortir.js', 'consultes.js', 'avisos.js',
  'manifest.webmanifest', 'icones/icona-192.png'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(MAGATZEM).then((c) => c.addAll(PECES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin || url.pathname.endsWith('.json')) return;
  e.respondWith(
    fetch(e.request)
      .then((resposta) => {
        if (resposta.ok) {
          const copia = resposta.clone();
          caches.open(MAGATZEM).then((c) => c.put(e.request, copia));
        }
        return resposta;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true })),
  );
});

// Els avisos al navegador (ADR 0048): bot/push.py envia {title, body, url,
// tag}; tocar la notificació obre la web (o la porta al davant, si ja hi és).
self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data.json(); } catch (_) { d = { title: e.data ? e.data.text() : '' }; }
  // Un avís que arriba quan ja ha caducat (el mòbil apagat una estona) no es
  // mostra: push.py hi posa «expira» (auditoria del 09-10-2026).
  if (d.expira && Date.now() > Date.parse(d.expira)) return;
  e.waitUntil(self.registration.showNotification(d.title || 'Temps a Montflorit', {
    body: d.body || '',
    icon: 'icones/icona-192.png',
    tag: d.tag,
    data: { url: new URL(d.url || './', self.registration.scope).href },
  }));
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = e.notification.data && e.notification.data.url;
  e.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((finestres) => {
    const oberta = finestres.find((f) => f.url.split('#')[0] === url.split('#')[0]);
    return oberta ? oberta.focus() : self.clients.openWindow(url);
  }));
});
