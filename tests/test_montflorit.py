# SPDX-License-Identifier: AGPL-3.0-or-later
"""La web pública «Temps a Montflorit» (ADR 0024)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import montflorit as M  # noqa: E402


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
        self.assertNotIn('class="pagines"', index)
        self.assertIn('data-dades="montflorit.json"', index)
        for nom in ("index.html", "fonts.html", "manifest.webmanifest", "README.md"):
            M.comprova(nom, self.llegeix(nom))        # no lanza
        self.assertEqual(json.loads(self.llegeix("manifest.webmanifest"))["name"], "Temps a Montflorit")

    def test_la_comprovacio_troba_el_que_no_hi_ha_de_ser(self):
        for dolent in ("<p>Temps a casa</p>", '<a href="./">Trajecte</a>', '<p title="Moto o cotxe?">x</p>',
                       '<a href="https://github.com/jjdeharo/meteo-local">codi</a>'):
            with self.assertRaises(ValueError):
                M.comprova("prova", dolent)
        M.comprova("prova", '<script src="casa.js"></script><div id="casa">Montflorit</div>')

    def test_si_la_pagina_canvia_falla(self):
        with self.assertRaises(ValueError):
            M.index("<html><title>Una altra cosa</title></html>")

    def test_service_worker_propi(self):
        sw = self.llegeix("sw.js")
        self.assertIn("'meteo-montflorit'", sw)
        self.assertNotIn("app.js", sw)
        self.assertNotIn("casa.html", sw)


class Dades(unittest.TestCase):
    def test_sense_el_trajecte(self):
        casa = {"versio": "1", "hores": [{"hora": "x"}], "ara_casa": {"temperatura": 20},
                "sortides": [{"mitja": "cotxe"}], "sortida_per_defecte_h": 4}
        publiques = M.dades_publiques(casa)
        self.assertEqual(set(publiques), {"versio", "hores", "ara_casa"})
        self.assertNotIn("cotxe", json.dumps(publiques))


if __name__ == "__main__":
    unittest.main()
