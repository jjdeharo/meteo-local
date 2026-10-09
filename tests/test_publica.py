# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas de publica.sh con un python3 y un git de mentira (sin red)."""
import os
import shutil
import subprocess
import tempfile
import unittest

ARREL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PYTHON3 = """#!/bin/sh
case "$1 $2" in
  "casa.py --json") echo '{}' > "$3" ;;
  "montflorit.py dades") echo '{}' > "$4" ;;
  "montflorit.py web") [ "$WEB_FALLA" = 1 ] && exit 9; mkdir -p "$3" && echo '<html>' > "$3/index.html" ;;
esac
exit 0
"""
GIT = """#!/bin/sh
echo "$*" >> "$GIT_REGISTRE"
[ "$1" = rev-parse ] && echo abc123
exit 0
"""


@unittest.skipUnless(shutil.which("bash"), "cal bash")
class Publica(unittest.TestCase):
    def executa(self, web_falla):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        binari, estat = os.path.join(d, "bin"), os.path.join(d, "estat")
        os.makedirs(binari)
        os.makedirs(estat)
        for nom, cos in (("python3", PYTHON3), ("git", GIT)):
            with open(os.path.join(binari, nom), "w") as f:
                f.write(cos)
            os.chmod(os.path.join(binari, nom), 0o755)
        registre, marca = os.path.join(d, "git.log"), os.path.join(estat, "gh-darrer")
        env = {**os.environ, "PATH": binari + os.pathsep + os.environ["PATH"], "ESTAT_DIR": estat,
               "ESTAT_GH": marca, "CLAU_IONOS": os.path.join(d, "no"), "CONF_IONOS": os.path.join(d, "no"),
               "DESTINO_MONTFLORIT": "git@exemple:web.git", "GIT_REGISTRE": registre,
               "WEB_FALLA": "1" if web_falla else "0", "HOME": d}
        r = subprocess.run(["bash", os.path.join(ARREL, "publica.sh")], env=env, capture_output=True,
                           text=True, timeout=60)
        git = open(registre).read() if os.path.exists(registre) else ""
        return r, git, os.path.exists(marca)

    def test_si_falla_el_generador_no_es_publica(self):
        # Auditoría del 09-10-2026: dentro de la condición de un «if» Bash no
        # aplica «set -e», y un fallo de montflorit.py seguía con el push.
        r, git, marca = self.executa(web_falla=True)
        self.assertNotIn("push", git)
        self.assertFalse(marca)
        self.assertIn("no s'ha pogut publicar", r.stderr)

    def test_si_tot_va_be_es_publica_i_es_marca(self):
        r, git, marca = self.executa(web_falla=False)
        self.assertIn("push -q -f git@exemple:web.git gh-pages", git)
        self.assertTrue(marca)
        self.assertIn("publicada la web", r.stdout)


if __name__ == "__main__":
    unittest.main()
