// SPDX-License-Identifier: AGPL-3.0-or-later
// La web privada s'ha retirat (ADR 0030): aquest service worker substitueix
// l'antic, esborra el seu magatzem (només el seu: l'origen és compartit amb
// altres webs) i es dona de baixa.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.delete('meteo-local').then(() => self.registration.unregister()));
});
