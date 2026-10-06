# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del JavaScript de la web (sin red ni navegador): el texto de los
avisos de la página de casa y la hora en que la página vuelve a leer los
datos. Necesita Node."""
import json
import os
import shutil
import subprocess
import unittest

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

# Carga comu.js y casa.js con un DOM mínimo y evalúa una expresión con la
# hora «ara» fijada.
ARNES = r"""
const vm = require('vm');
const fs = require('fs');
const [web, ara, expr, pagina] = process.argv.slice(1);
const RealDate = Date;
class FakeDate extends RealDate {
  constructor(...a) { super(...(a.length ? a : [ara])); }
  static now() { return new RealDate(ara).getTime(); }
}
const el = () => ({ setAttribute() {}, addEventListener() {}, append() {}, replaceChildren() {},
  querySelector: () => ({ setAttribute() {} }), dataset: {}, style: { setProperty() {} } });
const ctx = vm.createContext({
  Date: FakeDate, Math, JSON, Number, Object, Set, console,
  document: { getElementById: el, createElement: el, addEventListener() {},
    documentElement: { dataset: {} } },
  matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {}, AbortController,
  localStorage: { getItem: () => null }, navigator: {},
  fetch: () => new Promise(() => {}), setTimeout: () => 0, clearTimeout() {},
});
for (const f of ['comu.js', pagina]) vm.runInContext(fs.readFileSync(`${web}/${f}`, 'utf8'), ctx);
console.log(JSON.stringify(vm.runInContext(expr, ctx)));
"""


def avis(inicio, fin, tipo, nivel="groc"):
    return {"inicio": inicio, "fin": fin, "tipo": tipo, "nivel": nivel,
            "zona": "Prelitoral de Barcelona"}


@unittest.skipUnless(shutil.which("node"), "cal Node")
class Web(unittest.TestCase):
    def avalua(self, ara, expr, pagina="casa.js"):
        r = subprocess.run(["node", "-e", ARNES, WEB, ara, expr, pagina], capture_output=True,
                           text=True, check=True, env={**os.environ, "TZ": "Europe/Madrid"})
        return json.loads(r.stdout)

    def text(self, ara, avisos):
        return self.avalua(ara, f"textAvisos({json.dumps(avisos)}, new Date())")

    def test_avisos_de_avui_i_dema(self):
        # El cas del 05-10-2026: un avís avui i dos demà, que la pàgina
        # donava com tres avisos d'avui.
        avisos = [
            avis("2026-10-05T05:00:00+02:00", "2026-10-05T19:59:59+02:00", "tempestes"),
            avis("2026-10-05T10:00:00+02:00", "2026-10-05T19:59:59+02:00", "pluja"),
            avis("2026-10-06T09:00:00+02:00", "2026-10-06T17:59:59+02:00", "pluja"),
            avis("2026-10-06T09:00:00+02:00", "2026-10-06T17:59:59+02:00", "tempestes"),
            avis("2026-10-06T22:00:00+02:00", "2026-10-06T23:59:59+02:00", "pluja"),
            avis("2026-10-06T22:00:00+02:00", "2026-10-06T23:59:59+02:00", "tempestes"),
        ]
        self.assertEqual(
            self.text("2026-10-05T16:41:00+02:00", avisos),
            "Avís groc de l’AEMET per pluja i tempestes al Vallès: avui fins a les 20:00; "
            "demà de 09:00 a 18:00 i de 22:00 a mitjanit.")

    def test_tipus_i_nivells_diferents(self):
        avisos = [
            avis("2026-10-05T18:00:00+02:00", "2026-10-05T23:59:59+02:00", "pluja", "taronja"),
            avis("2026-10-05T10:00:00+02:00", "2026-10-06T11:59:59+02:00", "tempestes"),
            avis("2026-10-07T11:00:00+02:00", "2026-10-07T13:59:59+02:00", "pluja"),
        ]
        self.assertEqual(
            self.text("2026-10-05T16:41:00+02:00", avisos),
            "Avís taronja de l’AEMET per pluja al Vallès: avui de 18:00 a mitjanit. "
            "Avís groc de l’AEMET per tempestes al Vallès: fins demà a les 12:00. "
            "Avís groc de l’AEMET per pluja al Vallès: dimecres d’11:00 a 14:00.")

    def test_franges_seguides_i_acabades(self):
        # Dues franges que es toquen fan una sola; la que ja ha acabat no surt.
        avisos = [
            avis("2026-10-05T07:00:00+02:00", "2026-10-05T09:59:59+02:00", "pluja", "vermell"),
            avis("2026-10-05T18:00:00+02:00", "2026-10-05T19:59:59+02:00", "pluja"),
            avis("2026-10-05T20:00:00+02:00", "2026-10-05T22:59:59+02:00", "pluja"),
        ]
        self.assertEqual(
            self.text("2026-10-05T16:41:00+02:00", avisos),
            "Avís groc de l’AEMET per pluja al Vallès: avui de 18:00 a 23:00.")

    def test_el_cel_surt_de_la_probabilitat(self):
        # ADR 0021: els mil·límetres del model més plujós no fan «pluja» si la
        # probabilitat és baixa (el cas del 06-10-2026: «Pluja feble» amb un 2 %).
        def cel(**f):
            fila = {"hora": "2026-10-06T15:00", "codi": 3, "nuvols": 100, **f}
            return self.avalua("2026-10-06T13:00:00+02:00", f"cel({json.dumps(fila)})[0]")
        self.assertEqual(cel(pluja_mm=0.3, probabilitat=0.02), "Cobert")
        self.assertEqual(cel(pluja_mm=0.3, probabilitat=0.2), "Possible pluja")
        self.assertEqual(cel(pluja_mm=0.3, probabilitat=0.5), "Pluja feble")
        self.assertEqual(cel(pluja_mm=1.3, probabilitat=0.6), "Pluja")
        self.assertEqual(cel(pluja_mm=5, probabilitat=0.9), "Pluja forta")
        self.assertEqual(cel(pluja_mm=5, probabilitat=0.9, codi=95), "Tempesta")
        self.assertEqual(cel(pluja_mm=2, probabilitat=0.3, codi=95), "Possible tempesta")
        self.assertEqual(cel(pluja_mm=2, probabilitat=0.05, codi=95), "Cobert")
        # Sense probabilitat, manen els mil·límetres, com abans.
        self.assertEqual(cel(pluja_mm=0.3, probabilitat=None), "Pluja feble")
        self.assertEqual(self.avalua("2026-10-06T13:00:00+02:00",
                                     "plujaHora({plou_ara: true, probabilitat: 1, pluja_mm: 0})"), "pluja")

    def test_propera_lectura(self):
        horari = {"trams": [["00:00", "23:50"]], "cada_min": 10, "desfase_min": 1}
        expr = f"properaActualitzacio({json.dumps(horari)}).toISOString()"
        self.assertEqual(self.avalua("2026-10-05T16:41:30+02:00", expr), "2026-10-05T14:51:00.000Z")
        # Després de la darrera del dia, la primera de demà.
        self.assertEqual(self.avalua("2026-10-05T23:55:00+02:00", expr), "2026-10-05T22:01:00.000Z")
        trajecte = {"trams": [["05:00", "07:30"], ["13:00", "15:30"]], "cada_min": 30}
        expr = f"properaActualitzacio({json.dumps(trajecte)}).toISOString()"
        self.assertEqual(self.avalua("2026-10-05T09:00:00+02:00", expr), "2026-10-05T11:00:00.000Z")

    def test_franja_del_trajecte(self):
        horari = json.dumps({"trams": [["05:00", "07:30"], ["13:00", "15:30"]], "cada_min": 30,
                             "desfase_min": 0})
        def franja(ara):
            return self.avalua(ara, f"[!!franjaActiva({horari}), properaFranja({horari})]", "app.js")
        self.assertEqual(franja("2026-10-05T06:10:00+02:00")[0], True)
        # Fins que s'ha publicat la darrera de les 7:30.
        self.assertEqual(franja("2026-10-05T07:31:00+02:00")[0], True)
        self.assertEqual(franja("2026-10-05T07:33:00+02:00"), [False, {"dia": "avui", "hora": "13:00"}])
        # Acabada de començar, sense dades: torna a la mateixa franja, no demà.
        self.assertEqual(franja("2026-10-05T13:01:00+02:00"), [True, {"dia": "avui", "hora": "13:00"}])
        self.assertEqual(franja("2026-10-05T16:00:00+02:00"), [False, {"dia": "demà", "hora": "05:00"}])
        self.assertEqual(franja("2026-10-05T03:00:00+02:00"), [False, {"dia": "avui", "hora": "05:00"}])

    def test_tornada_triada(self):
        casa = {"sortides": [{"surt": "2026-10-05T19:00", "tornades": [
            {"hora": "2026-10-05T23:00"}, {"hora": "2026-10-06T08:00"}]}]}
        expr = f"(() => {{ const s = sortidaAra({json.dumps(casa)}); return [s && s.surt, "
        expr += "tornadaTriada(s, '23:00').hora, tornadaTriada(s, '08:30').hora, tornadaTriada(s, '12:00')]; })()"
        self.assertEqual(self.avalua("2026-10-05T19:20:00+02:00", expr, "app.js"),
                         ["2026-10-05T19:00", "2026-10-05T23:00", "2026-10-06T08:00", None])
        # Dades d'una hora que ja ha passat: cap sortida.
        self.assertIsNone(self.avalua("2026-10-05T20:05:00+02:00",
                                      f"sortidaAra({json.dumps(casa)})", "app.js"))


if __name__ == "__main__":
    unittest.main()
