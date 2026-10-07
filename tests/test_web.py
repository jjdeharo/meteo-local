# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del JavaScript de la web (sin red ni navegador): el texto de los
avisos de la página de casa, la hora en que la página vuelve a leer los
datos y la ropa de «Si surts». Necesita Node."""
import json
import os
import shutil
import subprocess
import sys
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
const el = () => ({ setAttribute() {}, addEventListener() {}, append() {}, after() {}, replaceChildren() {},
  querySelector: () => ({ setAttribute() {} }), dataset: {}, style: { setProperty() {} } });
const ctx = vm.createContext({
  Date: FakeDate, Math, JSON, Number, Object, Set, console,
  document: { getElementById: el, createElement: el, createElementNS: el, addEventListener() {},
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

    def roba(self, mitja, anada, tornada, pluja=False):
        tram = [{"hora": f"2026-10-07T{h:02d}:00", "temperatura": t, "vent": v}
                for h, t, v in (anada, tornada)]
        return self.avalua("2026-10-07T08:00:00+02:00",
                           f"roba({json.dumps(mitja)}, {json.dumps(tram)}, {json.dumps(pluja)})", "sortir.js")

    def test_roba_a_peu(self):
        # Trams de la temperatura que es nota, sense vent.
        casos = [(28, "Màniga curta."), (23, "Màniga curta o màniga llarga fina."),
                 (19, "Màniga llarga o jersei fi."), (16, "Jaqueta lleugera o jersei."),
                 (12, "Jaqueta."), (8, "Abric."), (3, "Abric, bufanda i guants."),
                 (-1, "Abric, gorro, bufanda i guants.")]
        for t, text in casos:
            self.assertEqual(self.roba("peu", (9, t, 0), (11, t, 0)), text)

    def test_roba_amb_vent_a_peu(self):
        # 8 °C amb 30 km/h es noten com 4 °C (índex d'Environment Canada).
        self.assertEqual(self.roba("peu", (9, 8, 30), (11, 8, 30)),
                         "Abric, bufanda i guants. Amb vent de 30\u00a0km/h, 8\u00a0°C es noten com 4\u00a0°C.")

    def test_roba_diferent_a_la_tornada(self):
        self.assertEqual(self.roba("peu", (16, 26, 5), (21, 15, 5)),
                         "Màniga curta. A la tornada (21\u00a0h, 15\u00a0°C): jaqueta lleugera o jersei.")
        # En moto, una sola jaqueta: la del moment més fred.
        self.assertEqual(self.roba("moto", (16, 26, 5), (21, 15, 5)),
                         "Jaqueta de moto amb folre i guants d’entretemps.")

    def test_roba_bici(self):
        self.assertEqual(self.roba("bici", (9, 22, 0), (11, 22, 0)), "Màniga curta.")
        self.assertEqual(self.roba("bici", (9, 19, 0), (11, 19, 0), pluja=True),
                         "Màniga llarga o una jaqueta molt lleugera. Impermeable.")

    def test_la_roba_del_bot_es_la_de_la_web(self):
        # El bot (Python, a IONOS) repeteix la taula de «Si surts»: han de dir el mateix.
        sys.path.insert(0, os.path.join(os.path.dirname(WEB), "bot"))
        import bot
        graus = list(range(-5, 36))
        web = self.avalua("2026-10-07T08:00:00+02:00",
                          f"{json.dumps(graus)}.map((s) => peca('peu', s))", "sortir.js")
        self.assertEqual(web, [bot.peca(s, "ca") + "." for s in graus])

    def test_propera_lectura(self):
        horari = {"trams": [["00:00", "23:50"]], "cada_min": 10, "desfase_min": 1}
        expr = f"properaActualitzacio({json.dumps(horari)}).toISOString()"
        self.assertEqual(self.avalua("2026-10-05T16:41:30+02:00", expr), "2026-10-05T14:51:00.000Z")
        # Després de la darrera del dia, la primera de demà.
        self.assertEqual(self.avalua("2026-10-05T23:55:00+02:00", expr), "2026-10-05T22:01:00.000Z")
        trajecte = {"trams": [["05:00", "07:30"], ["13:00", "15:30"]], "cada_min": 30}
        expr = f"properaActualitzacio({json.dumps(trajecte)}).toISOString()"
        self.assertEqual(self.avalua("2026-10-05T09:00:00+02:00", expr), "2026-10-05T11:00:00.000Z")

    def test_dades_velles(self):
        # Amb més de 2 hores, la previsió ja no es mostra (ADR 0031).
        expr = ("[dadesVelles({generat: '2026-10-07T06:50:00+02:00'}), "
                "dadesVelles({generat: '2026-10-07T07:10:00+02:00'})]")
        self.assertEqual(self.avalua("2026-10-07T09:00:00+02:00", expr), [True, False])


if __name__ == "__main__":
    unittest.main()
