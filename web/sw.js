// SPDX-License-Identifier: AGPL-3.0-or-later
// Service worker perquè la web es pugui instal·lar com a aplicació (ADR 0015).
// Primer la xarxa: amb connexió es veu sempre la versió publicada. Sense
// connexió, les pàgines i els estils guardats. Les dades (.json) no es guarden
// mai: una previsió vella no s'ha de mostrar com si fos d'ara.
const MAGATZEM = 'meteo-local';
const PECES = ['./', 'index.html', 'casa.html', 'fonts.html', 'estil.css', 'comu.js', 'app.js',
  'casa.js', 'manifest.webmanifest', 'icones/icona-192.png'];

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
