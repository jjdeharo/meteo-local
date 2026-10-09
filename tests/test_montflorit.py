# SPDX-License-Identifier: AGPL-3.0-or-later
"""La web pública «Temps a Montflorit» (ADR 0024)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import config as C  # noqa: E402
import montflorit as M  # noqa: E402
import nowcast as N  # noqa: E402
import riscos as R  # noqa: E402

ARREL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
NODE = shutil.which("node")

# Carga es.js, comu.js y casa.js con un DOM mínimo, como la página en
# castellano, y evalúa una expresión con la hora «ara» fijada.
ARNES = r"""
const vm = require('vm');
const fs = require('fs');
const [arrel, ara, expr] = process.argv.slice(1);
const RealDate = Date;
class FakeDate extends RealDate {
  constructor(...a) { super(...(a.length ? a : [ara])); }
  static now() { return new RealDate(ara).getTime(); }
}
const el = () => ({ setAttribute() {}, addEventListener() {}, append() {}, replaceChildren() {},
  querySelector: () => ({ setAttribute() {} }), dataset: {}, style: { setProperty() {} } });
const ctx = vm.createContext({
  Date: FakeDate, Math, JSON, Number, Object, Set, String, console,
  document: { querySelectorAll: () => [], getElementById: el, createElement: el, addEventListener() {},
    documentElement: { dataset: { lloc: 'Montflorit', estacio: 'la estación particular' } } },
  matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {}, AbortController,
  localStorage: { getItem: () => null, setItem() {} }, navigator: {}, location: { pathname: '/' },
  fetch: () => new Promise(() => {}), setTimeout: () => 0, clearTimeout() {},
});
for (const f of ['montflorit/es.js', 'web/comu.js', 'web/casa.js']) {
  vm.runInContext(fs.readFileSync(`${arrel}/${f}`, 'utf8'), ctx);
}
console.log(JSON.stringify(vm.runInContext(expr, ctx)));
"""


def js(expr, ara="2026-10-06T10:00:00+02:00"):
    r = subprocess.run([NODE, "-e", ARNES, ARREL, ara, expr], capture_output=True, text=True,
                       env={**os.environ, "TZ": "Europe/Madrid"})
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class Web(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        M.construeix(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def llegeix(self, nom):
        with open(os.path.join(self.tmp.name, nom), encoding="utf-8") as f:
            return f.read()

    def test_es_genera_sencera(self):
        for nom in ("index.html", "fonts.html", "estil.css", "comu.js", "casa.js", "sw.js",
                    "manifest.webmanifest", "icones/icona-192.png", "icones/icona-512.png",
                    "icones/apple-touch-icon.png", "README.md", "LICENSE", "LICENSE-CONTINGUTS.md",
                    ".nojekyll"):
            self.assertTrue(os.path.exists(os.path.join(self.tmp.name, nom)), nom)
        # Nada de la página del trayecto.
        for nom in ("app.js", "casa.html", "dades.json", "casa.json"):
            self.assertFalse(os.path.exists(os.path.join(self.tmp.name, nom)), nom)

    def test_no_parla_del_trajecte_ni_de_casa(self):
        index = self.llegeix("index.html")
        self.assertIn("<h1>Temps a Montflorit</h1>", index)
        # El menú público: el tiempo ahora y «Si surts», sin el trayecto (ADR 0029).
        self.assertIn('<a href="./" aria-current="page"><svg aria-hidden="true"><use href="#i-cloud-sun"></use></svg>El temps</a>', index)
        self.assertNotIn("Trajecte", index)
        self.assertIn('data-dades="montflorit.json"', index)
        for nom in ("index.html", "manifest.webmanifest"):
            M.comprova(nom, self.llegeix(nom))        # no lanza
        # Los créditos y el README enlazan el código fuente y los ADR (meteo-montflorit/meteo-local).
        M.comprova("fonts.html", self.llegeix("fonts.html"), M.PROHIBIDES_FONTS)
        self.assertIn("https://github.com/meteo-montflorit/meteo-local/tree/main/docs/adr", self.llegeix("fonts.html"))
        # «Si surts» usa la icona de la moto de Tabler: el crèdit s'hi queda; els de la pàgina retirada, no.
        self.assertIn("La icona de la moto de «Si surts», de <a href=\"https://tabler.io/icons\"", self.llegeix("fonts.html"))
        self.assertNotIn("MingCute", self.llegeix("fonts.html"))
        M.comprova("README.md", self.llegeix("README.md"), M.PROHIBIDES_README)
        self.assertIn("docs/adr", self.llegeix("README.md"))
        # «Si surts» habla de motos y coches, pero no de casa ni del trayecto.
        sortir = self.llegeix("sortir.html")
        self.assertIn('aria-current="page"><svg aria-hidden="true"><use href="#i-door-open"></use></svg>Si surts</a>', sortir)
        self.assertIn('data-dades="montflorit.json"', sortir)
        M.comprova("sortir.html", sortir, M.PROHIBIDES_SORTIR)
        self.assertIn(">Si sales</a>", self.llegeix("es/sortir.html"))
        self.assertIn('<script src="../sortir.js"></script>', self.llegeix("es/sortir.html"))
        self.assertEqual(json.loads(self.llegeix("manifest.webmanifest"))["name"], "Temps a Montflorit")

    def test_la_comprovacio_troba_el_que_no_hi_ha_de_ser(self):
        for dolent in ("<p>Temps a casa</p>", '<a href="./">Trajecte</a>', '<p title="Moto o cotxe?">x</p>'):
            with self.assertRaises(ValueError):
                M.comprova("prova", dolent)
        M.comprova("prova", '<script src="casa.js"></script><div id="casa">Montflorit</div>')
        # El repositori del codi sí pot sortir: els crèdits l'enllacen i la versió enllaça les seves notes.
        M.comprova("prova", '<a href="https://github.com/meteo-montflorit/meteo-local">codi</a>')

    def test_si_la_pagina_canvia_falla(self):
        with self.assertRaises(ValueError):
            M.index("<html><title>Una altra cosa</title></html>")

    def test_service_worker_propi(self):
        sw = self.llegeix("sw.js")
        self.assertIn("'meteo-montflorit'", sw)
        self.assertNotIn("app.js", sw)
        self.assertNotIn("casa.html", sw)
        self.assertIn("'es/'", sw)


    def test_fonts_amb_capcalera_comuna_i_lligams_entre_llengues(self):
        fonts = self.llegeix("fonts.html")
        self.assertIn('id="btn-fosc"', fonts)
        self.assertIn('<nav class="pagines"', fonts)
        # L'idioma, al costat del botó del tema: la llengua triada marcada i l'altra, a la mateixa pàgina.
        self.assertIn(M.selector_idioma("ca", "fonts.html"), fonts)
        self.assertIn(M.selector_idioma("es", "fonts.html"), self.llegeix("es/fonts.html"))
        self.assertIn('id="i-languages"', fonts)
        self.assertIn('<a href="es/fonts.html" lang="es" hreflang="es"', fonts)
        self.assertIn('<span lang="ca" aria-current="page"', fonts)
        self.assertIn('<a href="../fonts.html" lang="ca" hreflang="ca"', self.llegeix("es/fonts.html"))
        self.assertIn('<script src="comu.js"></script>', fonts)
        self.assertIn('data-notes="https://github.com/meteo-montflorit/meteo-local/releases/tag/v', fonts)
        self.assertIn('<script src="../es.js"></script>', self.llegeix("es/fonts.html"))
        for nom, ca in (("index.html", ""), ("sortir.html", "sortir.html")):
            for html in (self.llegeix(nom), self.llegeix("es/" + nom)):
                self.assertIn(f'<link rel="alternate" hreflang="ca" href="https://meteo-montflorit.github.io/{ca}">', html)
                self.assertIn(f'<link rel="alternate" hreflang="es" href="https://meteo-montflorit.github.io/es/{ca}">', html)
        self.assertIn('media="(prefers-color-scheme: dark)"', self.llegeix("index.html"))
    def test_en_castella(self):
        index, fonts = self.llegeix("es/index.html"), self.llegeix("es/fonts.html")
        for html in (index, fonts):
            self.assertIn('<html lang="es"', html)
            self.assertIn('href="../estil.css"', html)
        self.assertIn("<h1>El tiempo en Montflorit</h1>", index)
        self.assertIn('data-arrel="../"', index)
        # El diccionario, antes que el programa de la página.
        self.assertLess(index.index('src="../es.js"'), index.index('src="../comu.js"'))
        self.assertIn("traducida con IA", fonts)
        self.assertIn("El icono de la moto de «Si sales»", fonts)
        # Cada versión enlaza la otra.
        self.assertIn(M.selector_idioma("es", ""), index)
        self.assertIn(M.selector_idioma("ca", ""), self.llegeix("index.html"))
        # Sota el títol, què hi ha a la web.
        self.assertIn(f'<p class="ruta">{M.DESCRIPCIO}</p>', self.llegeix("index.html"))
        # No queda catalán en lo que se lee.
        for nom, html in (("es/index.html", index), ("es/fonts.html", fonts)):
            M.comprova(nom, html, M.PROHIBIDES_FONTS if "fonts" in nom else M.PROHIBIDES)
            visible = M.text_visible(html).lower()
            for paraula in ("pluja", "avui", "temps", "amb", "dels", "és", "hores"):
                self.assertIsNone(re.search(rf"\b{paraula}\b", visible), f"{nom}: «{paraula}»")

    def test_un_text_nou_sense_traduir_falla(self):
        with self.assertRaises(ValueError):
            M.tradueix("<p>Un paràgraf nou</p>", {}, "prova")
        self.assertEqual(M.tradueix('<p class="x">Hola</p><p>12</p>', {"Hola": "Buenas"}, "prova"),
                         '<p class="x">Buenas</p><p>12</p>')


class Dades(unittest.TestCase):
    def test_sense_el_trajecte(self):
        casa = {"versio": "1", "hores": [{"hora": "x"}], "ara_casa": {"temperatura": 20},
                "sortides": [{"mitja": "cotxe"}], "sortida_per_defecte_h": 4}
        publiques = M.dades_publiques(casa)
        self.assertEqual(set(publiques), {"versio", "hores", "ara_casa"})
        self.assertNotIn("cotxe", json.dumps(publiques))


@unittest.skipUnless(NODE, "sin Node")
class Castella(unittest.TestCase):
    """Los textos que pone el programa de la página, con montflorit/es.js."""

    def test_no_falta_cap_traduccio(self):
        claus = set(json.loads(subprocess.run([NODE, os.path.join(ARREL, "i18n", "claus.js")],
                                              capture_output=True, text=True, check=True).stdout))
        traduides = set(js("Object.keys(IDIOMA.textos)"))
        self.assertEqual(claus - traduides, set(), "textos de la pàgina sense traducció a montflorit/es.js")
        self.assertEqual(traduides - claus, set(), "traduccions de textos que ja no hi són")

    def test_paraules_de_les_dades(self):
        dades = js("IDIOMA.dades")
        paraules = list(R.NIVELLS) + list(C.PLANES_PC.values()) + list(C.PROCICAT_PC.values()) + list(N.RUMBS) + ["pluja", "tempestes",
                                                                                 "prealerta", "alerta", "emergència"]
        self.assertEqual([p for p in paraules if p not in dades], [])
        self.assertEqual(set(js("Object.keys(IDIOMA.riscos)")), set(R.TEXTOS))

    def test_el_catala_no_canvia_sense_diccionari(self):
        self.assertEqual(js("IDIOMA.codi"), "es")
        self.assertEqual(js("T`Ara a ${'Montflorit'} (${'10:00'})`"), "Ahora en Montflorit (10:00)")
        self.assertEqual(js("T('Un text que no hi és')"), "Un text que no hi és")
        # En castellà, la fase sempre amb «de».
        self.assertEqual(js("deFase(TD('emergència'))"), "de emergencia")
        self.assertEqual(js("deFase(TD('alerta'))"), "de alerta")

    def test_avisos(self):
        avisos = [{"inicio": "2026-10-06T08:00:00+02:00", "fin": "2026-10-06T19:59:59+02:00", "tipo": "pluja", "nivel": "groc"},
                  {"inicio": "2026-10-06T08:00:00+02:00", "fin": "2026-10-06T19:59:59+02:00", "tipo": "tempestes", "nivel": "groc"},
                  {"inicio": "2026-10-07T09:00:00+02:00", "fin": "2026-10-07T17:59:59+02:00", "tipo": "pluja", "nivel": "taronja"},
                  {"inicio": "2026-10-07T22:00:00+02:00", "fin": "2026-10-07T23:59:59+02:00", "tipo": "pluja", "nivel": "taronja"},
                  {"inicio": "2026-10-06T22:00:00+02:00", "fin": "2026-10-07T00:59:59+02:00", "tipo": "pluja", "nivel": "vermell"}]
        self.assertEqual(js(f"textAvisos({json.dumps(avisos)})"),
                         "Aviso rojo de la AEMET por lluvia en el Vallès: hoy de 22:00 hasta mañana a la 01:00. "
                         "Aviso naranja de la AEMET por lluvia en el Vallès: mañana de 09:00 a 18:00 y de 22:00 a medianoche. "
                         "Aviso amarillo de la AEMET por lluvia y tormentas en el Vallès: hoy hasta las 20:00.")
        self.assertEqual(js("textFranja(new Date('2026-10-06T08:00:00+02:00'), new Date('2026-10-09T06:00:00+02:00'), new Date())"),
                         "hasta el viernes a las 06:00")

    def test_ara_i_radar(self):
        self.assertEqual(js("cel({hora: '2026-10-06T12:00', probabilitat: 0.6, pluja_mm: 45, codi: 61})[0]"), "Lluvia fuerte")
        self.assertEqual(js("cel({hora: '2026-10-06T12:00', probabilitat: 0.1, pluja_mm: 0, codi: 3, nuvols: 10})[0]"), "Despejado")
        self.assertEqual(js("textPressio({pressio: 1008.2, pressio_3h: -4})"), "Presión 1008\u00a0hPa, bajando rápido (\u22124,0 en 3\u00a0h)")
        self.assertEqual(js("textRadar({arriba: null, possible: null}, false)[1]"), "No se acerca lluvia en 2 horas")
        self.assertEqual(js("textRadar({arriba: '2026-10-06T11:15:00+02:00'}, false)[1]"), "Llegaría lluvia hacia las\u00a011:15")
        self.assertEqual(js("TD('al nord-est')"), "el nordeste")
        self.assertEqual(js("textHorari({trams: [['00:00', '23:54']], cada_min: 6, mode_avis: ['pluja al radar']})"), "Modo aviso")
        # Juanjo, 09-10-2026: el ritmo normal no se dice (la próxima hora ya lo dice) y el modo aviso se explica con un «?».
        self.assertEqual(js("textHorari({trams: [['00:00', '23:45']], cada_min: 15, mode_avis: []})"), "")
        self.assertEqual(js("textModeAvis({cada_min: 6, normal_min: 15, radar_km: 15})"),
                         "Cuando hay un aviso de la AEMET, un plan de Protección Civil en alerta o emergencia, lluvia en "
                         "Montflorit o lluvia en el radar a menos de 15 km, la página se actualiza más a menudo: cada 6 "
                         "minutos en lugar de cada 15, al ritmo de las imágenes del radar.")
        self.assertEqual(js("textAprenentatge({pluja: {origen: 'arxiu', des_de: '2024-01-01'}, temperatura: {origen: 'arxiu', des_de: '2025-10-08'}})"),
                         "Probabilidad de lluvia aprendida de lo que llovió de verdad en Sabadell y Sant Cugat desde 2024, "
                         "cuando los modelos decían lo mismo. Temperatura corregida con lo que ha medido la estación particular desde el 8/10/2025.")

    def test_riscos(self):
        ara = "2026-10-06T10:00:00+02:00"
        for tipus, origen, valor, espera in (
                ("ratxa", "previsio", 75.2, "Viento muy fuerte previsto: rachas de hasta 75 km/h, hoy de 15 a 16 h."),
                ("pluja_1h", "estacio", 24.6, "Ahora llueve muy fuerte: 25 mm en la última hora."),
                ("fred", "previsio", -5, "Frío intenso previsto: hasta \u22125 °C, mañana de 15 a 16 h.")):
            dia = "2026-10-07" if "mañana" in espera else "2026-10-06"
            r = {"tipus": tipus, "origen": origen, "valor": valor, "text": "en català",
                 "des_de": f"{dia}T15:00" if origen == "previsio" else None,
                 "fins": f"{dia}T16:00" if origen == "previsio" else None}
            self.assertEqual(js(f"IDIOMA.risc({json.dumps(r)})", ara), espera)
        # Un tipo que no conoce: el texto de las datos, antes que nada.
        self.assertEqual(js("IDIOMA.risc({tipus: 'nou', origen: 'previsio', valor: 1, text: 'en català'})"), "en català")


if __name__ == "__main__":
    unittest.main()
