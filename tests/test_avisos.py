# SPDX-License-Identifier: AGPL-3.0-or-later
"""Texto de los avisos de AEMET (ADR 0033), sin red."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import prevision as P  # noqa: E402

FICHA = """<alert><info><language>es-ES</language><event>Aviso de tormentas</event>
<description>Pueden ir acompañadas de granizo,
 en general inferior a 2 cm.</description><instruction>Esté atento.</instruction></info>
<info><language>en-GB</language><description>Pueden ir acompañadas de granizo, en general inferior a 2 cm.
</description><instruction>Be aware.</instruction></info></alert>"""


class Descripcio(unittest.TestCase):
    def setUp(self):
        self.original = P.get_recent

    def tearDown(self):
        P.get_recent = self.original

    def test_text_en_castella_tal_qual(self):
        P.get_recent = lambda url, segons=120: FICHA
        self.assertEqual(P.descripcion_aviso("https://x"), "Pueden ir acompañadas de granizo, en general inferior a 2 cm.")

    def test_sense_text(self):
        P.get_recent = lambda url, segons=120: "<alert><info><language>es-ES</language></info></alert>"
        self.assertIsNone(P.descripcion_aviso("https://x"))


if __name__ == "__main__":
    unittest.main()
