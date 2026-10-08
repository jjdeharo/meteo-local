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

# Lo mismo, pero la expresión puede devolver una promesa, «fetch» se puede
# sustituir desde la expresión y los temporizadores largos de la página (un
# minuto o más) se disparan enseguida, para seguir el ciclo de «carrega» sin
# esperar; los cortos (los de la propia prueba) se respetan.
ARNES_ASYNC = ARNES.replace("fetch: () => new Promise(() => {}), setTimeout: () => 0, clearTimeout() {},",
                            "fetch: () => new Promise(() => {}), setTimeout: (f, ms) => setTimeout(f, ms >= 1000 ? 0 : ms),"
                            " clearTimeout() {},") \
    .replace("console.log(JSON.stringify(vm.runInContext(expr, ctx)));",
             "Promise.resolve(vm.runInContext(expr, ctx)).then((v) => console.log(JSON.stringify(v)));")


def avis(inicio, fin, tipo, nivel="groc"):
    return {"inicio": inicio, "fin": fin, "tipo": tipo, "nivel": nivel,
            "zona": "Prelitoral de Barcelona"}


@unittest.skipUnless(shutil.which("node"), "cal Node")
class Web(unittest.TestCase):
    def avalua(self, ara, expr, pagina="casa.js", arnes=ARNES):
        r = subprocess.run(["node", "-e", arnes, WEB, ara, expr, pagina], capture_output=True,
                           text=True, check=True, env={**os.environ, "TZ": "Europe/Madrid"})
        return json.loads(r.stdout)

    # Un «fetch» de mentira: a cada petición (por orden) le toca una respuesta:
    # un objeto (JSON con 200), «null» (error de red) o «'penja'» (no contesta).
    def fetch_fals(self, respostes):
        return (f"peticions = []; respostes = {json.dumps(respostes)};"
                "fetch = (url) => { peticions.push(url.split('?')[0]); const r = respostes.shift();"
                " if (r === 'penja') return new Promise(() => {});"
                " if (r === null) return Promise.reject(new Error('xarxa'));"
                " return Promise.resolve({ ok: true, json: () => Promise.resolve(r) }); };")

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

    def test_fase_de_proteccio_civil_amb_apostrof(self):
        # «d’alerta» i «d’emergència», però «de prealerta» (abans sortia «d’prealerta»).
        ara = "2026-10-07T13:00:00+02:00"
        self.assertEqual(self.avalua(ara, "deFase('prealerta')"), "de prealerta")
        self.assertEqual(self.avalua(ara, "deFase('alerta')"), "d’alerta")
        self.assertEqual(self.avalua(ara, "deFase('emergència')"), "d’emergència")

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
        # Amb pluja d'algun model (0,2 mm o més), mai «Serè»: com a mínim núvols
        # (el cas del 07-10-2026: «Serè» amb 0,4 mm i un 13 %).
        self.assertEqual(cel(pluja_mm=0.4, probabilitat=0.13, nuvols=0), "Núvols")
        self.assertEqual(cel(pluja_mm=0.4, probabilitat=0.13, nuvols=90), "Cobert")
        self.assertEqual(cel(pluja_mm=0.1, probabilitat=0.05, nuvols=0), "Serè")
        self.assertEqual(cel(pluja_mm=0, probabilitat=0.01, nuvols=10), "Serè")
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

    def test_les_franges_acabades_no_compten(self):
        hores = [{"hora": "2026-10-08T06:00", "fins": "2026-10-08T07:00"}, {"hora": "2026-10-08T07:00", "fins": "2026-10-08T08:00"},
                 {"hora": "2026-10-08T08:00", "fins": "2026-10-08T09:00"}]
        r = self.avalua("2026-10-08T07:44:00+02:00", f"horesVigents({json.dumps(hores)}, new Date()).map((f) => f.hora)", "sortir.js")
        self.assertEqual(r, ["2026-10-08T07:00", "2026-10-08T08:00"])
        self.assertEqual(self.avalua("2026-10-08T07:44:00+02:00", "horesVigents(null, new Date())", "sortir.js"), [])

    def test_public_amb_linies_sense_dades(self):
        # Auditoria del 08-10-2026: amb Renfe caigut i la S2 circulant deia «cap incidència».
        def public(linies):
            return self.avalua("2026-10-08T12:00:00+02:00", f"estatPublic({json.dumps(linies)})", "sortir.js")
        sd = [{"linia": x, "estat": "sense_dades"} for x in ("R4", "R7", "R8")]
        r = public(sd + [{"linia": "S2", "estat": "circula"}])
        self.assertEqual((r["nivell"], r["etiqueta"]), ("neutre", "Dades parcials"))
        self.assertEqual(r["motius"], ["S2 sense incidències; de R4, R7, R8 ara no hi ha dades."])
        r = public(sd + [{"linia": "S2", "estat": "incidencies"}])
        self.assertEqual(r["nivell"], "compte")
        self.assertEqual(r["motius"], ["Trens: S2 amb incidències.", "De R4, R7, R8 ara no hi ha dades."])
        self.assertEqual(public(sd)["etiqueta"], "Sense dades")
        self.assertEqual(public([{"linia": "S2", "estat": "circula"}])["nivell"], "be")

    def test_cotxe_amb_pluja(self):
        # Auditoria del 08-10-2026: amb 90 mm/h el cotxe sortia «bé, sense pluja».
        def tram(mm, prob, t=20):
            return [{"hora": f"2026-10-08T{h:02d}:00", "fins": f"2026-10-08T{h + 1:02d}:00", "temperatura": t,
                     "ratxa": 10, "pluja_mm": mm, "probabilitat": prob, "avisos": []} for h in (12, 13)]
        def cotxe(mm, prob, t=20):
            return self.avalua("2026-10-08T12:00:00+02:00",
                               f"avalua('cotxe', {json.dumps(tram(mm, prob, t))}, [], false)", "sortir.js")
        self.assertEqual(cotxe(90, 1), {"nivell": "no", "motius": [
            "Pluja molt forta prevista a l’anada i a la tornada: millor no agafar el cotxe."]})
        self.assertEqual(cotxe(25, 0.9), {"nivell": "compte", "motius": [
            "Pluja forta prevista a l’anada i a la tornada: condueix amb compte."]})
        self.assertEqual(cotxe(2, 0.7), {"nivell": "compte", "motius": [
            "Pluja probable a l’anada i a la tornada: condueix amb compte."]})
        self.assertEqual(cotxe(0.3, 0.25), {"nivell": "be", "motius": ["Pot ploure a l’anada i a la tornada."]})
        self.assertEqual(cotxe(0, 0.05), {"nivell": "be", "motius": ["Sense pluja ni vent fort."]})
        self.assertEqual(cotxe(0, 0.05, 0)["motius"], ["0\u00a0°C: compte amb el gel a primera hora."])

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

    def test_pluja_nomes_per_l_avis_de_l_aemet(self):
        # El cas del 07-10-2026 a les 18 h: avís groc fins a les 20 h, cel serè i un 1 %.
        # Es manté el que diu l'avís, però es diu que cap altra dada hi veu pluja (ADR 0008 i 0029).
        avis = [{"nivell": "groc", "tipus": ["pluja", "tempestes"]}]
        def tram(prob):
            return [{"hora": f"2026-10-07T{h:02d}:00", "probabilitat": prob, "pluja_mm": 0,
                     "temperatura": 22, "avisos": avis if h < 20 else []} for h in (18, 19, 20, 21)]
        def avalua(mitja, prob):
            return self.avalua("2026-10-07T18:10:00+02:00",
                               f"avalua({json.dumps(mitja)}, {json.dumps(tram(prob))}, [])", "sortir.js")
        bici = avalua("bici", 0.01)
        self.assertEqual(bici["nivell"], "no")
        self.assertEqual(bici["motius"], ["Avís de l’AEMET per pluja a l’anada (18\u00a0h): ni el radar, "
                                          "ni les estacions, ni els models hi veuen pluja."])
        self.assertTrue(avalua("peu", 0.01)["motius"][0].startswith("Avís de l’AEMET per pluja mentre ets fora"))
        # Si els models també hi veuen pluja, com sempre.
        self.assertEqual(avalua("bici", 0.6)["motius"], ["Pluja probable a l’anada i a la tornada."])
        consells = self.avalua("2026-10-07T18:10:00+02:00",
                               f"consells({json.dumps(tram(0.01))}, new Date())", "sortir.js")
        self.assertIn("Cap a les 20\u00a0h s’acaba l’avís de l’AEMET.", consells)

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

    def test_copia_de_github_si_ionos_serveix_dades_velles(self):
        # Auditoria del 07-10-2026: IONOS contestava amb dades de fa 3 hores i
        # la còpia de GitHub, més nova, no es mirava.
        ara = "2026-10-08T09:00:00+02:00"
        velles, noves = {"generat": "2026-10-08T06:00+02:00"}, {"generat": "2026-10-08T08:51+02:00"}
        expr = self.fetch_fals([velles, noves]) + "llegeixDades('casa.json').then((d) => [d.generat, peticions])"
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC),
                         [noves["generat"], ["https://bilateria.org/app/meteo-local/casa.json", "casa.json"]])
        # Si la còpia és més vella, es queden les d'IONOS; si falla, també.
        expr = self.fetch_fals([noves, velles]) + "llegeixDades('casa.json').then((d) => d.generat)"
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC), noves["generat"])
        expr = self.fetch_fals([velles, None]) + "llegeixDades('casa.json').then((d) => d.generat)"
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC), velles["generat"])
        # Amb dades d'IONOS de fa menys de 45 minuts, una sola petició.
        recents = {"generat": "2026-10-08T08:30+02:00"}
        expr = self.fetch_fals([recents, noves]) + "llegeixDades('casa.json').then((d) => [d.generat, peticions.length])"
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC), [recents["generat"], 1])
        # Si IONOS no respon, la còpia, com sempre.
        expr = self.fetch_fals([None, noves]) + "llegeixDades('casa.json').then((d) => d.generat)"
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC), noves["generat"])

    def test_en_fallar_una_lectura_es_torna_a_pintar(self):
        # Auditoria del 07-10-2026: amb la pestanya oberta i la xarxa caiguda,
        # les dades velles es quedaven a la pantalla. Ara cada lectura fallida
        # torna a pintar el que hi ha (i dadesVelles decideix).
        # Lectura bona (dades recents: una sola petició), dues lectures fallides
        # (IONOS i la còpia) i la següent que no contesta: dues pintades.
        dades = {"generat": "2026-10-08T08:40+02:00", "horari": {"trams": [["00:00", "23:50"]], "cada_min": 15}}
        expr = (self.fetch_fals([dades, None, None, 'penja']) + "pintats = 0;"
                "carrega('casa.json', () => { pintats += 1; }, () => {});"
                "new Promise((r) => setTimeout(() => r([pintats, peticions.length]), 50))")
        self.assertEqual(self.avalua("2026-10-08T09:00:00+02:00", expr, arnes=ARNES_ASYNC), [2, 4])

    def test_si_surts_trens_d_ara_i_pla_de_proteccio_civil(self):
        trens = [{"linia": "R4", "estat": "circula"}, {"linia": "S2", "estat": "circula"}]
        ara = "2026-10-08T09:00:00+02:00"
        self.assertEqual(self.avalua(ara, f"avaluaPublic({json.dumps(trens)}, false).motius", "sortir.js"),
                         ["Cap incidència als trens de Cerdanyola."])
        self.assertEqual(self.avalua(ara, f"avaluaPublic({json.dumps(trens)}, true).motius", "sortir.js"),
                         ["Cap incidència als trens de Cerdanyola.", "Són els trens d’ara, no els de l’hora triada."])
        plans = [{"pla": "INUNCAT", "nom": "d'inundacions", "fase": "emergència"}]
        self.assertEqual(self.avalua(ara, f"avisPlaSortida({json.dumps(plans)})", "sortir.js"),
                         "Protecció Civil té el pla d'inundacions (INUNCAT) en fase d’emergència i demana evitar els "
                         "desplaçaments que no siguin necessaris. Els veredictes de sota només miren la pluja i el vent previstos.")
        plans[0]["fase"] = "alerta"
        self.assertTrue(self.avalua(ara, f"avisPlaSortida({json.dumps(plans)})", "sortir.js").startswith(
            "Protecció Civil té el pla d'inundacions (INUNCAT) en fase d’alerta: segueix"))
        plans[0]["fase"] = "prealerta"
        self.assertIsNone(self.avalua(ara, f"avisPlaSortida({json.dumps(plans)})", "sortir.js"))
        self.assertIsNone(self.avalua(ara, "avisPlaSortida(undefined)", "sortir.js"))


if __name__ == "__main__":
    unittest.main()
