# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del despliegue solo con las pruebas de GitHub en verde (ADR 0038),
con un repositorio git local y sin red."""
import os
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import desplegament as D  # noqa: E402


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, "GIT_AUTHOR_NAME": "p", "GIT_AUTHOR_EMAIL": "p@p",
                               "GIT_COMMITTER_NAME": "p", "GIT_COMMITTER_EMAIL": "p@p"}).stdout.strip()


class Desplegament(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.origen = os.path.join(self.dir.name, "origen")
        self.copia = os.path.join(self.dir.name, "copia")
        self.treball = os.path.join(self.dir.name, "treball")
        git("init", "-q", "--bare", "-b", "main", self.origen, cwd=self.dir.name)
        git("clone", "-q", self.origen, self.treball, cwd=self.dir.name)
        self.commit("1")
        git("clone", "-q", self.origen, self.copia, cwd=self.dir.name)
        self.registre = []

    def tearDown(self):
        self.dir.cleanup()

    def commit(self, text):
        with open(os.path.join(self.treball, "f.txt"), "w") as f:
            f.write(text)
        git("add", "f.txt", cwd=self.treball)
        git("commit", "-q", "-m", text, cwd=self.treball)
        git("push", "-q", "origin", "HEAD:main", cwd=self.treball)
        return git("rev-parse", "HEAD", cwd=self.treball)

    def head(self):
        return git("rev-parse", "HEAD", cwd=self.copia)

    def actualitza(self, estat, resultat):
        return D.actualitza(self.copia, estat, self.registre.append, proves=lambda sha: resultat)

    def test_sense_canvis(self):
        self.assertEqual(self.actualitza({}, "ok"), "igual")
        self.assertEqual(self.registre, [])

    def test_en_verd_es_desplega(self):
        nou = self.commit("2")
        self.assertEqual(self.actualitza({}, "ok"), "ok")
        self.assertEqual(self.head(), nou)
        self.assertIn("pruebas en verde", self.registre[-1])

    def test_fallides_no_es_desplega_i_s_apunta_un_cop(self):
        vell = self.head()
        self.commit("2")
        estat = {}
        self.assertEqual(self.actualitza(estat, "fallit"), "fallit")
        self.assertEqual(self.actualitza(estat, "fallit"), "fallit")
        self.assertEqual(self.head(), vell)
        self.assertEqual(len([l for l in self.registre if "han fallado" in l]), 1)
        # Repetidas las pruebas y en verde, se despliega al volver a preguntar.
        estat["proves_fallides"]["hora"] -= D.REPREGUNTA_MIN * 60 + 1
        self.assertEqual(self.actualitza(estat, "ok"), "ok")
        self.assertNotEqual(self.head(), vell)
        self.assertNotIn("proves_fallides", estat)

    def test_pendents_s_espera_i_despres_es_desplega(self):
        vell = self.head()
        nou = self.commit("2")
        estat = {}
        self.assertEqual(self.actualitza(estat, "pendent"), "pendent")
        self.assertEqual(self.head(), vell)
        self.assertEqual(estat["proves_pendents"]["sha"], nou)
        self.assertEqual(self.actualitza(estat, "ok"), "ok")
        self.assertEqual(self.head(), nou)
        self.assertNotIn("proves_pendents", estat)

    def test_pendents_massa_temps_es_desplega_igualment(self):
        nou = self.commit("2")
        estat = {}
        self.actualitza(estat, "pendent")
        estat["proves_pendents"]["des_de"] = time.time() - D.ESPERA_MAX_MIN * 60 - 1
        self.assertEqual(self.actualitza(estat, "pendent"), "desconegut")
        self.assertEqual(self.head(), nou)
        self.assertTrue(any("sin acabar" in l for l in self.registre))

    def test_github_no_respon_es_desplega(self):
        nou = self.commit("2")
        self.assertEqual(self.actualitza({}, "desconegut"), "desconegut")
        self.assertEqual(self.head(), nou)
        self.assertIn("GitHub no responde", self.registre[-1])

    def test_estat_proves(self):
        import json
        import urllib.request
        original = urllib.request.urlopen

        class Resposta:
            def __init__(self, dades):
                self.dades = dades

            def __enter__(self):
                return self

            def __exit__(self, *a):
                pass

            def read(self):
                return json.dumps(self.dades).encode()

        def amb(dades):
            urllib.request.urlopen = lambda req, timeout=0: Resposta(dades)
            return D.estat_proves("abc")
        try:
            self.assertEqual(amb({"total_count": 0, "check_runs": []}), "pendent")
            self.assertEqual(amb({"check_runs": [{"status": "in_progress", "conclusion": None}]}), "pendent")
            self.assertEqual(amb({"check_runs": [{"status": "completed", "conclusion": "success"}]}), "ok")
            self.assertEqual(amb({"check_runs": [{"status": "completed", "conclusion": "success"},
                                                 {"status": "completed", "conclusion": "failure"}]}), "fallit")

            def cau(req, timeout=0):
                raise OSError("sense xarxa")
            urllib.request.urlopen = cau
            self.assertEqual(D.estat_proves("abc"), "desconegut")
        finally:
            urllib.request.urlopen = original


if __name__ == "__main__":
    unittest.main()
