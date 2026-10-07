// SPDX-License-Identifier: AGPL-3.0-or-later
// Llista les claus de tots els textos que passen per T a web/comu.js,
// web/casa.js i web/sortir.js, tal com les calcula T: el text amb {0}, {1}…
// on van els valors. Ho fan servir les proves per comprovar que no en falta cap a
// montflorit/es.js (ADR 0025).
//
//   node i18n/claus.js [carpeta de web]   → JSON amb les claus
const fs = require('fs');
const vm = require('vm');
const path = require('path');

const web = process.argv[2] || path.join(__dirname, '..', 'web');
const claus = new Set();
for (const fitxer of ['comu.js', 'casa.js', 'sortir.js']) {
  // Sense comentaris de línia, que també parlen de T`…`.
  const codi = fs.readFileSync(path.join(web, fitxer), 'utf8').replace(/^\s*\/\/.*$/gm, '');
  for (const m of codi.matchAll(/\bT`((?:[^`\\]|\\.)*)`/g)) {
    let n = 0;
    const plantilla = m[1].replace(/\$\{[^{}]*\}/g, () => `{${n++}}`);
    if (plantilla.includes('${')) throw new Error(`${fitxer}: expressió massa complicada dins de T\`${m[1]}\``);
    claus.add(vm.runInNewContext('`' + plantilla + '`'));
  }
  for (const m of codi.matchAll(/\bT\('((?:[^'\\]|\\.)*)'\)/g)) claus.add(vm.runInNewContext(`'${m[1]}'`));
}
console.log(JSON.stringify([...claus]));
