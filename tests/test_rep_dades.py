# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del receptor de datos de IONOS (reserva/rep-dades.sh), en local."""
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REP = os.path.join(ARREL, "reserva", "rep-dades.sh")


def paquet(entrades):
    """Un tar.gz en memoria con (nombre, contenido) por entrada."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for nom, cos in entrades:
            info = tarfile.TarInfo(nom)
            info.size = len(cos)
            t.addfile(info, io.BytesIO(cos))
    return buf.getvalue()


@unittest.skipUnless(shutil.which("tar") and shutil.which("sh"), "cal tar i sh")
class RepDades(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def rep(self, dades):
        return subprocess.run(["sh", REP], input=dades, env={**os.environ, "REP_DIR": self.dir},
                              capture_output=True, timeout=60)

    def test_accepta_els_dos_json(self):
        r = self.rep(paquet([("montflorit.json", b'{"a": 1}'), ("avisos.json", b'{"avisos": []}')]))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.load(open(os.path.join(self.dir, "montflorit.json"))), {"a": 1})

    def test_rebutja_el_que_es_fa_gran_en_descomprimir(self):
        # Auditoría del 09-10-2026: un tar.gz de 5 KB traía un JSON de 5 MB y
        # el límite de 2 MB solo miraba el comprimido.
        gran = b'{"a": "' + b"x" * 5_000_000 + b'"}'
        d = paquet([("montflorit.json", gran)])
        self.assertLess(len(d), 20_000)
        r = self.rep(d)
        self.assertEqual(r.returncode, 1)
        self.assertIn(b"descomprimit", r.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.dir, "montflorit.json")))

    def test_rebutja_noms_repetits_i_de_mes(self):
        r = self.rep(paquet([("montflorit.json", b"{}"), ("montflorit.json", b"{}")]))
        self.assertEqual(r.returncode, 1)
        self.assertIn(b"repetit", r.stderr)
        r = self.rep(paquet([("montflorit.json", b"{}"), ("avisos.json", b"{}"), ("avisos.json", b"{}")]))
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
