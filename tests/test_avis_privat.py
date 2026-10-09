# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de la cola de avisos privados a Juanjo (ADR 0038), sin Telegram:
avisar-juanjo es un script que falla las veces que se le diga."""
import datetime as dt
import os
import stat
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import avis_privat as AP  # noqa: E402
import riera as RI  # noqa: E402

ARA = dt.datetime(2026, 10, 8, 7, 0).astimezone()


class Cua(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.enviats = os.path.join(self.dir.name, "enviats.txt")
        self.fallades = os.path.join(self.dir.name, "fallades")
        AP.PENDENTS = os.path.join(self.dir.name, "avisos-pendents.jsonl")
        AP.ORDRE = os.path.join(self.dir.name, "avisar-juanjo")
        # Falla mientras quede algún archivo en «fallades»; cada fallo consume uno.
        with open(AP.ORDRE, "w") as f:
            f.write("#!/bin/sh\n"
                    f"f=$(ls {self.fallades} 2>/dev/null | head -1)\n"
                    f"if [ -n \"$f\" ]; then rm {self.fallades}/$f; exit 1; fi\n"
                    f"printf '%s\\n' \"$*\" >> {self.enviats}\n")
        os.chmod(AP.ORDRE, stat.S_IRWXU)
        os.makedirs(self.fallades)

    def tearDown(self):
        self.dir.cleanup()

    def falla(self, vegades):
        for i in range(vegades):
            open(os.path.join(self.fallades, str(i)), "w").close()

    def rebuts(self):
        try:
            with open(self.enviats) as f:
                return f.read().splitlines()
        except FileNotFoundError:
            return []

    def test_entrega_directa(self):
        self.assertTrue(AP.envia("Hola", ara=ARA))
        self.assertEqual(self.rebuts(), ["--asunto meteo-local Hola"])
        self.assertEqual(AP.pendents(), [])

    def test_primer_rebutjat_segon_acceptat_una_sola_entrega(self):
        self.falla(1)
        self.assertFalse(AP.envia("Perill", ara=ARA))
        self.assertEqual(self.rebuts(), [])
        self.assertEqual(len(AP.pendents()), 1)
        entregats, caducats, queden = AP.reintenta(ARA + dt.timedelta(minutes=6))
        self.assertEqual((len(entregats), caducats, queden), (1, [], []))
        self.assertEqual(self.rebuts(), ["--asunto meteo-local Perill"])
        # Otra pasada no lo repite.
        self.assertEqual(AP.reintenta(ARA + dt.timedelta(minutes=12)), ([], [], []))
        self.assertEqual(self.rebuts(), ["--asunto meteo-local Perill"])

    def test_segueix_pendent_mentre_falli_i_caduca(self):
        self.falla(3)
        AP.envia("Pluja", vigencia_min=20, ara=ARA)
        _, caducats, queden = AP.reintenta(ARA + dt.timedelta(minutes=6))
        self.assertEqual((caducats, len(queden)), ([], 1))
        _, caducats, queden = AP.reintenta(ARA + dt.timedelta(minutes=25))
        self.assertEqual((len(caducats), queden), (1, []))
        self.assertEqual(self.rebuts(), [])
        self.assertEqual(AP.pendents(), [])

    def test_sense_programa_queda_pendent(self):
        AP.ORDRE = os.path.join(self.dir.name, "no-existeix")
        self.assertFalse(AP.envia("Riera", ara=ARA))
        self.assertEqual(len(AP.pendents()), 1)

    def test_la_riera_ja_no_envia_res_a_juanjo(self):
        # Des del 08-10-2026 l'avís de la riera arriba pel bot, el canal i les
        # notificacions; riera.py només apunta l'episodi.
        RI.ESTADO = os.path.join(self.dir.name, "riera.json")
        casa = os.path.join(self.dir.name, "casa.json")
        riera = {"fins": ARA.isoformat(timespec="minutes"), "mm_3h": 40, "mm_6h": 55, "radar_1h": 0,
                 "index": 40, "index_6h": 55, "capcalera": None}
        with open(casa, "w") as f:
            f.write('{"generat": "%s", "riera": %s}' % (ARA.isoformat(timespec="minutes"),
                                                        __import__("json").dumps(riera)))
        self.assertIn("atenció", RI.avisa(casa, ARA))
        self.assertEqual(self.rebuts(), [])
        self.assertEqual(AP.pendents(), [])


if __name__ == "__main__":
    unittest.main()
