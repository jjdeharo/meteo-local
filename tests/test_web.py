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
  document: { querySelectorAll: () => [], getElementById: el, createElement: el, createElementNS: el, addEventListener() {},
    documentElement: { dataset: {} } },
  matchMedia: () => ({ matches: false, addEventListener() {} }), addEventListener() {}, AbortController,
  localStorage: { getItem: () => null, setItem() {} }, navigator: {}, location: { pathname: '/', hash: '' },
  history: { replaceState() {} }, window: { addEventListener() {} },
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


# Carga sw.js con un «self» de mentira y evalúa una expresión con la hora «ara».
ARNES_SW = r"""
const vm = require('vm');
const fs = require('fs');
const [web, ara, expr] = process.argv.slice(1);
const RealDate = Date;
class FakeDate extends RealDate {
  constructor(...a) { super(...(a.length ? a : [ara])); }
  static now() { return new RealDate(ara).getTime(); }
}
const ctx = vm.createContext({ Date: FakeDate, URL, JSON, String, console, location: { origin: 'https://m.test' },
  self: { addEventListener() {}, registration: { scope: 'https://m.test/' } } });
vm.runInContext(fs.readFileSync(`${web}/sw.js`, 'utf8'), ctx);
console.log(JSON.stringify(vm.runInContext(expr, ctx)));
"""


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
        # Intensitats del manual d'estil de Meteocat, en una hora (ADR 0043).
        self.assertEqual(cel(pluja_mm=5, probabilitat=0.6), "Pluja feble")
        self.assertEqual(cel(pluja_mm=8, probabilitat=0.9), "Pluja moderada")
        self.assertEqual(cel(pluja_mm=45, probabilitat=0.9), "Pluja forta")
        self.assertEqual(cel(pluja_mm=90, probabilitat=0.9), "Pluja torrencial")
        self.assertEqual(cel(pluja_mm=5, probabilitat=0.9, codi=95), "Tempesta")
        self.assertEqual(cel(pluja_mm=5, probabilitat=0.9, codi=96), "Tempesta amb calamarsa")
        self.assertEqual(cel(pluja_mm=1, probabilitat=0.9, codi=73, neu=0.5), "Neu feble")
        self.assertEqual(cel(pluja_mm=5, probabilitat=0.9, codi=75, neu=3), "Neu moderada")
        self.assertEqual(cel(pluja_mm=12, probabilitat=0.9, codi=75, neu=12), "Neu forta")
        self.assertEqual(cel(pluja_mm=1, probabilitat=0.3, codi=71, neu=0.5), "Possible neu")
        self.assertEqual(cel(pluja_mm=2, probabilitat=0.9, codi=66), "Pluja gelant")
        self.assertEqual(cel(pluja_mm=0, probabilitat=0.01, nuvols=30), "Poc ennuvolat")
        self.assertEqual(cel(pluja_mm=0, probabilitat=0.01, nuvols=60), "Mig ennuvolat")
        self.assertEqual(cel(pluja_mm=0, probabilitat=0.01, nuvols=75), "Molt ennuvolat")
        self.assertEqual(cel(pluja_mm=2, probabilitat=0.3, codi=95), "Possible tempesta")
        self.assertEqual(cel(pluja_mm=2, probabilitat=0.05, codi=95), "Cobert")
        # Amb pluja d'algun model (0,2 mm o més), mai «Serè»: com a mínim núvols
        # (el cas del 07-10-2026: «Serè» amb 0,4 mm i un 13 %).
        self.assertEqual(cel(pluja_mm=0.4, probabilitat=0.13, nuvols=0), "Mig ennuvolat")
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

    def test_resum_per_trams_del_dia(self):
        # Juanjo, 08-10-2026: probabilitat de pluja i fenòmens destacables per matí, tarda i nit.
        def fila(h, prob, mm, t, ratxa=10, codi=0, neu=0):
            dia = "2026-10-08" if h < 24 else "2026-10-09"
            return {"hora": f"{dia}T{h % 24:02d}:00", "fins": f"{'2026-10-09' if h + 1 >= 24 else dia}T{(h + 1) % 24:02d}:00",
                    "probabilitat": prob, "pluja_mm": mm, "temperatura": t, "ratxa": ratxa, "codi": codi, "neu": neu, "avisos": []}
        hores = ([fila(h, 0.1, 0.2, 17 + h - 9) for h in range(9, 14)]      # matí: 17–21 °C
                 + [fila(h, 0.8 if h == 16 else 0.3, 45 if h == 16 else 2, 22, 75 if h == 15 else 20, 95 if h == 16 else 0) for h in range(14, 21)]
                 + [fila(h, 0.05, 0, -1 if h == 23 else 5, 10, 0, 0.5 if h == 22 else 0) for h in range(21, 31)]
                 + [fila(31, 0.2, 0.5, 37)])
        r = self.avalua("2026-10-08T09:30:00+02:00", f"resumTrams({json.dumps(hores)}, new Date())")
        # Juanjo, 09-10-2026: tots els trams de la previsió, cadascun desplegable; l'últim, fins on arriben les hores.
        self.assertEqual([(t["nom"], t["hores"]) for t in r],
                         [("Matí", "fins a les 14 h"), ("Tarda", "14–21 h"), ("Nit", "21–7 h"), ("Demà matí", "7–8 h")])
        self.assertEqual((r[0]["prob"], r[0]["tMin"], r[0]["tMax"], r[0]["fenomens"]), (0.1, 17, 21, []))
        # Juanjo, 09-10-2026: la pluja, només si va a ploure (alguna hora amb un 20 % o més).
        self.assertEqual([t["plou"] for t in r], [False, True, False, True])
        self.assertEqual([f[0] for f in r[1]["fenomens"]], ["tempesta", "pluja forta", "ratxes de 75\u00a0km/h"])
        self.assertEqual(r[1]["mm"], 57)
        self.assertEqual([f[0] for f in r[2]["fenomens"]], ["neu", "glaçada"])
        # A la nit, surten la nit i els trams de demà.
        r = self.avalua("2026-10-08T22:30:00+02:00", f"resumTrams({json.dumps(hores)}, new Date())")
        self.assertEqual([t["nom"] for t in r], ["Nit", "Demà matí"])
        self.assertEqual([f[0] for f in r[1]["fenomens"]], ["calor"])
        self.assertEqual(self.avalua("2026-10-08T22:30:00+02:00", f"resumTrams({json.dumps(hores)}, new Date())", "casa.js", ARNES)[0]["hores"], "fins a les 7 h")

    def test_trams_oberts_de_sortida(self):
        # Juanjo, 09-10-2026: «no debería ser persistente?»: el primer tram i els de perill; amb «Desplega-ho tot» desat, tots.
        trams = [{"clau": "a", "avis": False, "fenomens": []}, {"clau": "b", "avis": True, "fenomens": []},
                 {"clau": "c", "avis": False, "fenomens": [["calor", "i"]]}, {"clau": "d", "avis": False, "fenomens": []}]
        expr = f"{json.dumps(trams)}.map((t, i) => obertDeSortida(t, i))"
        self.assertEqual(self.avalua("2026-10-09T18:00:00+02:00", expr), [True, True, True, False])
        self.assertEqual(self.avalua("2026-10-09T18:00:00+02:00", "localStorage.getItem = () => '1'; " + expr), [True] * 4)
        # El que s'ha obert o tancat a mà mana mentre la pàgina és oberta.
        self.assertEqual(self.avalua("2026-10-09T18:00:00+02:00", "obertsAMa.set('a', false); obertsAMa.set('d', true); " + expr),
                         [False, True, True, True])

    def test_cel_de_cada_tram(self):
        # El cel del tram, amb el seu nom i la seva icona: la mitjana dels núvols, i de nit, la lluna.
        def fila(h, nuvols, codi=0, mm=0):
            return {"hora": f"2026-10-08T{h:02d}:00", "fins": f"2026-10-08T{h + 1:02d}:00", "probabilitat": 0,
                    "pluja_mm": mm, "temperatura": 20, "nuvols": nuvols, "codi": codi, "avisos": []}
        hores = ([fila(h, 10) for h in range(9, 14)] + [fila(h, 40, 45 if h < 18 else 0) for h in range(14, 21)]
                 + [fila(h, 30) for h in range(21, 23)])
        r = self.avalua("2026-10-08T09:30:00+02:00", f"resumTrams({json.dumps(hores)}, new Date()).map((t) => t.cel)")
        self.assertEqual(r, [["Serè", "i-sun"], ["Boira", "i-cloud-fog"], ["Poc ennuvolat", "i-cloud-moon"]])
        # Si algun model hi posa pluja, com a mínim mig ennuvolat, com a la taula.
        r = self.avalua("2026-10-08T09:30:00+02:00",
                        f"resumTrams({json.dumps([fila(10, 10, mm=0.5)])}, new Date())[0].cel")
        self.assertEqual(r, ["Mig ennuvolat", "i-cloud"])

    def test_plans_del_color_de_la_fase_i_amb_el_que_vol_dir(self):
        # ADR 0051: la prealerta no espanta; el «?» desplega què vol dir cada fase.
        plans = [{"pla": "VENTCAT", "nom": "de vent", "fase": f} for f in ("prealerta", "alerta", "emergència")]
        r = self.avalua("2026-10-09T10:00:00+02:00", f"blocPlans({json.dumps(plans)}).map((p) => p.className)")
        self.assertEqual(r, ["avis-item prealerta", "avis-item taronja", "avis-item vermell"])
        r = self.avalua("2026-10-09T10:00:00+02:00",
                        "ajudaFase('prealerta').map((e) => [e.className, e.textContent, e.hidden === true])")
        self.assertEqual(r[0][:2], ["ajuda-fase", "?"])
        self.assertEqual(r[1], ["sentit-fase", "Es preveu un risc a mitjà termini. El pla no està activat: "
                                "només cal estar-ne pendent.", True])

    def test_les_franges_acabades_no_compten(self):
        hores = [{"hora": "2026-10-08T06:00", "fins": "2026-10-08T07:00"}, {"hora": "2026-10-08T07:00", "fins": "2026-10-08T08:00"},
                 {"hora": "2026-10-08T08:00", "fins": "2026-10-08T09:00"}]
        r = self.avalua("2026-10-08T07:44:00+02:00", f"horesVigents({json.dumps(hores)}, new Date()).map((f) => f.hora)", "sortir.js")
        self.assertEqual(r, ["2026-10-08T07:00", "2026-10-08T08:00"])
        self.assertEqual(self.avalua("2026-10-08T07:44:00+02:00", "horesVigents(null, new Date())", "sortir.js"), [])

    def test_graus_mes_o_menys_que_ahir_igual_que_el_bot(self):
        # ADR 0061: la web i el bot fan el mateix compte.
        sys.path.insert(0, os.path.join(os.path.dirname(WEB), "bot"))
        import bot as B
        def fila(dia, h, t):
            return {"hora": f"2026-10-{dia}T{h:02d}:00", "fins": f"2026-10-{dia}T{h + 1:02d}:00", "temperatura": t}
        avui = [fila(10, 14, 20.0), fila(10, 15, 23.4)]
        dema = [fila(11, 15, 18.0)]
        mes = {"2026-10-09T14:00": 19.0, "2026-10-09T15:00": 20.0, "2026-10-09T16:00": 21.0}
        casos = [(avui, False, mes), (avui, True, mes), (dema, False, mes), (dema, False, {}),
                 (avui, False, {"2026-10-09T14:00": 19.0})]
        for files, nit, m in casos:
            js = self.avalua("2026-10-10T13:00:00+02:00", f"comparaTemp({json.dumps(files)}, {json.dumps(nit)}, {json.dumps(m)}, {json.dumps(avui + dema)})")
            self.assertEqual(js, B.compara_temp({"temperatura_mesurada": m, "hores": avui + dema}, files, nit))
        self.assertEqual(self.avalua("2026-10-10T13:00:00+02:00", "[textComparacio(3, false), textComparacio(-2, true), textComparacio(1, false), textComparacio(null, false)]"),
                         ["3° més que ahir", "2° menys que avui", "semblant a ahir", None])
        # A la capçalera del tram, al costat de la temperatura.
        hores = [{**fila(10, h, 20.0 + h - 14), "codi": 0, "nuvols": 0} for h in range(14, 21)]
        mes = {f"2026-10-09T{h:02d}:00": 15.0 for h in range(14, 22)}
        r = self.avalua("2026-10-10T13:30:00+02:00", f"resumTrams({json.dumps(hores)}, new Date(), {json.dumps(mes)}).map((t) => t.compara)")
        self.assertEqual(r, ["11° més que ahir"])                          # 26,5 contra 15

    def test_el_cel_del_bot_es_el_de_la_web(self):
        # ADR 0065: la icona del cel als missatges del bot surt de la mateixa
        # regla que la taula de la web (cel de casa.js): les dues han de coincidir.
        sys.path.insert(0, os.path.join(os.path.dirname(WEB), "bot"))
        import bot as B
        files = []
        # De dia, al vespre (la posta, cap a les 19:15 l'octubre) i de nit.
        for dia, h in (("2026-10-10", 12), ("2026-10-10", 18), ("2026-10-10", 19), ("2026-10-10", 23),
                       ("2026-10-11", 7), ("2026-01-15", 17), ("2026-06-21", 21)):
            base = {"hora": f"{dia}T{h:02d}:00", "fins": f"{dia}T{h:02d}:59"}
            for nuvols in (0, 30, 60, 80, 95, None):
                files.append({**base, "nuvols": nuvols, "codi": 3, "probabilitat": 0.05, "pluja_mm": 0})
            files.append({**base, "nuvols": 10, "codi": 3, "probabilitat": 0.1, "pluja_mm": 0.4})   # mulla: núvols
            files.append({**base, "nuvols": 50, "codi": 45, "probabilitat": 0.0, "pluja_mm": 0})    # boira
            for p, mm, codi in ((0.3, 0.5, 61), (0.3, 0, 95), (0.3, 1, 73), (0.6, 0.5, 61), (0.6, 7, 63),
                                (0.6, 45, 65), (0.6, 90, 65), (0.6, 2, 95), (0.6, 2, 96), (0.6, 2, 75),
                                (0.6, 2, 66), (None, 0.3, 61), (None, 0.1, 61)):
                files.append({**base, "nuvols": 90, "codi": codi, "probabilitat": p, "pluja_mm": mm, "neu": 3})
            files.append({**base, "nuvols": 20, "codi": 1, "probabilitat": 0.0, "pluja_mm": 0, "plou_ara": True})
        js = self.avalua("2026-10-10T13:00:00+02:00", f"{json.dumps(files)}.map((f) => cel(f)[1])")
        self.assertEqual(js, [B.icona_cel(f) for f in files])
        # Cada icona de la web té el seu emoji, i de nit no surt el sol.
        self.assertTrue(set(js) - {None} <= set(B.EMOJI_CEL))
        self.assertEqual(B.emoji_cel(files[0]), "☀️")                      # dia 10, 12 h, serè
        nit = next(f for f in files if f["hora"] == "2026-10-10T23:00" and f["nuvols"] == 60)
        self.assertEqual(B.emoji_cel(nit), "☁️")

    def test_la_previsio_de_dema_tocada_despres_de_mitjanit(self):
        # La de les 21 h porta a «Demà»; si es toca quan aquell dia ja ha arribat, a «Avui».
        def desti(ara, url, dia):
            r = subprocess.run(["node", "-e", ARNES_SW, WEB, ara, f"destiAvis({json.dumps(url)}, {json.dumps(dia)})"],
                               capture_output=True, text=True, check=True, env={**os.environ, "TZ": "Europe/Madrid"})
            return json.loads(r.stdout)
        dema = "https://m.test/consultes.html#dema"
        self.assertEqual(desti("2026-10-10T21:30:00+02:00", dema, "2026-10-11"), dema)
        self.assertEqual(desti("2026-10-11T00:20:00+02:00", dema, "2026-10-11"), "https://m.test/consultes.html#avui")
        self.assertEqual(desti("2026-10-12T08:00:00+02:00", dema, "2026-10-11"), "https://m.test/consultes.html#avui")
        self.assertEqual(desti("2026-10-11T00:20:00+02:00", dema, None), dema)        # avisos d'abans, sense dia
        self.assertEqual(desti("2026-10-11T07:00:00+02:00", "https://m.test/", None), "https://m.test/")

    def test_cada_pagina_avisa_de_les_seves_fonts(self):
        # Juanjo, 09-10-2026: «cada pagina solo avisa de lo que usa»; un 503 del sol no fa menys segura la previsió.
        def falla(errors, fonts, pagina="casa.js", previsio_de=None):
            d = json.dumps({"errors": errors, "previsio_de": previsio_de})
            return self.avalua("2026-10-09T18:05:00+02:00", f"fontsFallades({d}, {fonts})", pagina)
        sol = ["sol: HTTP Error 503: Service Unavailable"]
        self.assertFalse(falla(sol, "FONTS_TEMPS"))
        self.assertFalse(falla(sol, "FONTS_SORTIR", "sortir.js"))
        self.assertTrue(falla(["radar: timeout"], "FONTS_TEMPS"))
        self.assertTrue(falla(["estació de casa: 500"], "FONTS_TEMPS"))
        self.assertFalse(falla(["trens: 500"], "FONTS_TEMPS"))
        self.assertTrue(falla(["trens: 500"], "FONTS_SORTIR", "sortir.js"))
        self.assertTrue(falla(["índex UV: 500"], "FONTS_SORTIR", "sortir.js"))
        # La previsió substituïda per l'anterior ja té el seu avís.
        self.assertFalse(falla(["previsió: 503"], "FONTS_TEMPS", previsio_de="2026-10-09T17:00+02:00"))
        # A «Consultes», segons la fitxa: el sol no avisa enlloc; els trens, només a «Avui».
        def consulta(triada, errors):
            return self.avalua("2026-10-09T18:05:00+02:00",
                               f"triada = '{triada}'; fontsFallades({json.dumps({'errors': errors})}, fontsConsulta())",
                               "consultes.js")
        self.assertEqual([consulta(t, sol) for t in ("avui", "dema", "sol")], [False, False, False])
        self.assertEqual([consulta(t, ["trens: 500"]) for t in ("avui", "dema", "trens")], [True, False, False])
        self.assertEqual([consulta(t, ["radar: x"]) for t in ("avui", "dema", "aire")], [True, True, False])

    def test_hores_de_si_surts_amb_el_dia(self):
        # La previsió pot arribar a l'endemà de demà al matí (ADR 0041): no és «demà».
        hores = ["2026-10-08T23:00", "2026-10-09T17:00", "2026-10-10T06:00"]
        r = self.avalua("2026-10-08T22:10:00+02:00",
                        f"{json.dumps(hores)}.map((h) => etiquetaHora({{hora: h}}, new Date()))", "sortir.js")
        self.assertEqual(r, ["23:00", "demà 17:00", "dissabte 06:00"])

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
            "Fins a 90\u00a0mm de pluja en una hora a l’anada i a la tornada: millor no agafar el cotxe."]})
        self.assertEqual(cotxe(25, 0.9), {"nivell": "compte", "motius": [
            "Fins a 25\u00a0mm de pluja en una hora a l’anada i a la tornada: condueix amb compte."]})
        self.assertEqual(cotxe(2, 0.7), {"nivell": "compte", "motius": [
            "Pluja probable a l’anada i a la tornada: condueix amb compte."]})
        self.assertEqual(cotxe(0.3, 0.25), {"nivell": "be", "motius": ["Pot ploure a l’anada i a la tornada."]})
        # Un sol model amb 1 mm i poca probabilitat: el nivell no canvia, però no és «probable» (ADR 0047).
        self.assertEqual(cotxe(1.7, 0.25), {"nivell": "compte", "motius": [
            "Pot ploure a l’anada i a la tornada: condueix amb compte."]})
        self.assertEqual(cotxe(0, 0.05), {"nivell": "be", "motius": ["Sense pluja ni vent fort."]})
        self.assertEqual(cotxe(0, 0.05, 0)["motius"], ["0\u00a0°C: compte amb el gel a primera hora."])

    def test_transit_al_cotxe_i_la_moto(self):
        # ADR 0052: si surts ara, retencions o talls a prop posen el cotxe i la moto en «compte».
        tram = [{"hora": f"2026-10-09T{h:02d}:00", "fins": f"2026-10-09T{h + 1:02d}:00", "temperatura": 20,
                 "ratxa": 10, "pluja_mm": 0, "probabilitat": 0.02, "avisos": []} for h in (9, 10)]
        transit = [{"tipus": "retencio", "nivell": 3, "carretera": "C-58"},
                   {"tipus": "retencio", "nivell": 4, "carretera": "C-58"},
                   {"tipus": "retencio", "nivell": 2, "carretera": "AP-7"},
                   {"tipus": "obres", "nivell": 5, "carretera": "BV-1414"}]
        def v(mitja, futur, t=transit):
            return self.avalua("2026-10-09T09:30:00+02:00",
                               f"avalua('{mitja}', {json.dumps(tram)}, [], {json.dumps(futur)}, {json.dumps(t)})",
                               "sortir.js")
        self.assertEqual(v("cotxe", False), {"nivell": "compte", "motius": [
            "Sense pluja ni vent fort.", "Ara hi ha retencions o talls a prop: C-58."]})
        self.assertEqual(v("moto", False)["nivell"], "compte")
        # Més tard, el trànsit d'ara no compta; a peu o en bici, tampoc.
        self.assertEqual(v("cotxe", True), {"nivell": "be", "motius": ["Sense pluja ni vent fort."]})
        self.assertEqual(v("bici", False)["nivell"], "be")
        # Només circulació intensa i obres: es llisten, però no canvien el consell.
        self.assertEqual(v("cotxe", False, transit[2:])["nivell"], "be")
        self.assertEqual(v("cotxe", False, None)["nivell"], "be")

    def test_distancia_del_transit(self):
        # Igual que el bot: en metres per sota d'1 km (Juanjo, 09-10-2026).
        r = self.avalua("2026-10-09T09:30:00+02:00", "[0.01, 0.73, 1.0, 4.04, 4.35].map(distancia)", "sortir.js")
        self.assertEqual(r, ["50\u00a0m", "750\u00a0m", "1\u00a0km", "4\u00a0km", "4,4\u00a0km"])

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
        # En bici i en moto, l'avís tot sol és «compte», no «no» (08-10-2026, ADR 0047).
        bici = avalua("bici", 0.01)
        self.assertEqual(bici["nivell"], "compte")
        self.assertEqual(bici["motius"], ["Avís de l’AEMET per pluja a l’anada (18\u00a0h): ni el radar, "
                                          "ni les estacions, ni els models hi veuen pluja."])
        moto = avalua("moto", 0.01)
        self.assertEqual(moto["nivell"], "compte")
        self.assertTrue(moto["motius"][0].endswith("Per si de cas, porta l’impermeable."))
        cotxe = avalua("cotxe", 0.01)
        self.assertEqual(cotxe["nivell"], "compte")
        self.assertTrue(cotxe["motius"][0].startswith("Avís de l’AEMET per pluja a l’anada (18\u00a0h)"))
        # El cas del 08-10-2026 a les 17 h: avís i un 10 %. Com la moto, «pot ploure».
        self.assertEqual(avalua("cotxe", 0.1)["motius"], ["Pot ploure a l’anada i a la tornada: condueix amb compte."])
        self.assertTrue(avalua("peu", 0.01)["motius"][0].startswith("Avís de l’AEMET per pluja mentre ets fora"))
        # Si els models també hi veuen pluja, com sempre.
        self.assertEqual(avalua("bici", 0.6)["motius"], ["Pluja probable a l’anada i a la tornada."])
        consells = self.avalua("2026-10-07T18:10:00+02:00",
                               f"consells({json.dumps(tram(0.01))}, new Date())", "sortir.js")
        self.assertIn("Cap a les 20\u00a0h s’acaba l’avís de l’AEMET.", consells)

    def test_pluja_en_moto_per_la_probabilitat(self):
        # El cas del 08-10-2026: avís groc des de les 10 h, cap dada hi veia pluja
        # a les 10 i a les 17 h només ICON-EU donava 1,7 mm (un 25 %). Va dir «no»
        # i no va ploure. Ara, en moto i en bici, decideix la probabilitat (ADR 0047).
        avis = [{"nivell": "groc", "tipus": ["pluja"]}]
        def viatge(prob, mm, avisos=avis):
            return [{"hora": f"2026-10-08T{h:02d}:00", "probabilitat": p, "pluja_mm": m,
                     "temperatura": 18, "avisos": avisos} for h, p, m in ((10, 0.0, 0.0), (17, prob, mm))]
        def avalua(mitja, tram):
            return self.avalua("2026-10-08T09:50:00+02:00",
                               f"avalua({json.dumps(mitja)}, {json.dumps(tram)}, [])", "sortir.js")
        moto = avalua("moto", viatge(0.25, 1.7))
        self.assertEqual(moto["nivell"], "compte")
        self.assertEqual(moto["motius"], ["Pot ploure a l’anada i a la tornada: porta l’impermeable."])
        self.assertEqual(avalua("moto", viatge(0.45, 0.3))["nivell"], "no")
        self.assertEqual(avalua("moto", viatge(0.12, 0.0, []))["nivell"], "compte")
        self.assertEqual(avalua("moto", viatge(0.05, 0.6, []))["nivell"], "be")
        # Sense probabilitat, manen els mil·límetres.
        self.assertEqual(avalua("bici", viatge(None, 1.2, []))["nivell"], "no")
        # El cotxe no canvia: un sol model amb 1 mm o més és pluja probable.
        self.assertEqual(avalua("cotxe", viatge(0.25, 1.7, []))["nivell"], "compte")

    def test_nou_al_costat_dels_avisos(self):
        # «Nou!» fins que s'entra a la pàgina «Avisos» i, per a tothom, fins al
        # 15-10-2026 (ADR 0048).
        def nou(ara, vist=None, pagina="/"):
            expr = ("posats = []; enllac = { append: (e) => posats.push(e.textContent) };"
                    "document.querySelectorAll = (s) => s === '.boto-avisos' ? [enllac] : [];"
                    f"location.pathname = {json.dumps(pagina)};"
                    f"desat = {json.dumps(vist)}; localStorage.getItem = () => desat;"
                    "localStorage.setItem = (k, v) => { desat = v; };"
                    "element = (e, c, t) => ({ textContent: t }); marcaNouAvisos(new Date()); posats")
            return self.avalua(ara, expr)
        self.assertEqual(nou("2026-10-09T10:00:00+02:00"), ["Nou!"])
        self.assertEqual(nou("2026-10-09T10:00:00+02:00", "1"), [])
        self.assertEqual(nou("2026-10-09T10:00:00+02:00", pagina="/es/avisos.html"), [])
        self.assertEqual(nou("2026-10-16T00:00:00+02:00"), [])

    def test_final_de_la_pluja_en_entrenament(self):
        # «Pluja a sobre» amb l'hora en què pararia, marcat «en entrenament» (ADR 0049).
        r = {"arriba": "2026-10-08T19:00", "fi": "2026-10-08T20:10:00+02:00"}
        ara = "2026-10-08T19:02:00+02:00"
        self.assertEqual(self.avalua(ara, f"textRadar({json.dumps(r)}, true)"),
                         ["arriba", "Pluja a sobre · pararia cap a les\u00a020:10", True])
        self.assertEqual(self.avalua(ara, f"textRadar({json.dumps({**r, 'fi': None, 'sense_fi': True})}, true)"),
                         ["arriba", "Pluja a sobre · no s’acaba en 2 hores", True])
        # Ja plou però el radar només veu pluja possible: mana el que es mesura (08-10-2026, 20:04).
        possible = {"arriba": None, "possible": "2026-10-08T20:00", "fi": "2026-10-08T20:10:00+02:00"}
        les20 = "2026-10-08T20:04:00+02:00"
        self.assertEqual(self.avalua(les20, f"textRadar({json.dumps(possible)}, true)"),
                         ["arriba", "Pluja a sobre · pararia cap a les\u00a020:10", True])
        self.assertEqual(self.avalua(les20, f"textRadar({json.dumps(possible)}, false)")[1], "Pluja a prop: pot arribar")
        # Plou i el radar no en veu gens: sense hora.
        self.assertEqual(self.avalua(ara, 'textRadar({"arriba": null, "possible": null, "fi": null, "sense_fi": false}, true)'),
                         ["arriba", "Pluja a sobre", False])
        self.assertEqual(self.avalua(ara, 'textRadar({"arriba": null, "possible": null}, false)')[1],
                         "No s’acosta pluja en 2 hores")
        # Sense dada (dades d'abans), com sempre.
        self.assertEqual(self.avalua(ara, 'textRadar({"arriba": "2026-10-08T19:00"}, true)'),
                         ["arriba", "Pluja a sobre", False])

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

    def test_la_descarrega_es_talla_tambe_a_mig_cos(self):
        # Auditoria del 09-10-2026: «fetch» es resol amb les capçaleres i el
        # temporitzador s'aturava abans de llegir el cos: un cos que no acabava
        # mai deixava la lectura penjada i no s'anava a la còpia.
        ara = "2026-10-09T18:00:00+02:00"
        expr = ("fetch = (url, opts) => Promise.resolve({ ok: true, json: () => new Promise((_, no) => "
                "opts.signal.addEventListener('abort', () => no(new Error('abortat')))) });"
                "baixa('x.json').then(() => 'ok', (e) => e.message)")
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC), "abortat")
        expr = "fetch = () => Promise.resolve({ ok: true, json: () => Promise.resolve({ a: 1 }) }); baixa('x.json')"
        self.assertEqual(self.avalua(ara, expr, arnes=ARNES_ASYNC), {"a": 1})

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
        # El pla ja surt a «Avisos actius»: aquí, una línia sense repetir-lo (08-10-2026).
        self.assertEqual(self.avalua(ara, f"avisPlaSortida({json.dumps(plans)})", "sortir.js"),
                         "El consell de cada mitjà surt del temps previst i del trànsit: no té en compte l’emergència de Protecció Civil (vegeu l’avís de dalt).")
        plans[0]["fase"] = "alerta"
        self.assertIn("no té en compte l’alerta de Protecció Civil", self.avalua(ara, f"avisPlaSortida({json.dumps(plans)})", "sortir.js"))
        plans[0]["fase"] = "prealerta"
        self.assertIsNone(self.avalua(ara, f"avisPlaSortida({json.dumps(plans)})", "sortir.js"))
        self.assertIsNone(self.avalua(ara, "avisPlaSortida(undefined)", "sortir.js"))

    def test_la_franja_del_radar_nomes_si_diu_alguna_cosa(self):
        # «No s'acosta pluja» només surt si la previsió en dona en les dues
        # hores que venen (Juanjo, 10-10-2026; ADR 0019).
        ara = "2026-10-10T10:20:00+02:00"
        hora = lambda h, p: {"hora": f"2026-10-10T{h:02d}:00", "fins": f"2026-10-10T{h + 1:02d}:00",
                             "probabilitat": p, "pluja_mm": 0}
        sec = [hora(10, 0), hora(11, 0), hora(12, 0.1), hora(13, 0.6)]
        self.assertFalse(self.avalua(ara, f"plujaPrevistaAviat({json.dumps(sec)}, new Date())"))
        aviat = [hora(10, 0), hora(11, 0), hora(12, 0.25)]
        self.assertTrue(self.avalua(ara, f"plujaPrevistaAviat({json.dumps(aviat)}, new Date())"))
        # Una hora que comença passades les dues hores no compta.
        self.assertFalse(self.avalua(ara, f"plujaPrevistaAviat({json.dumps([hora(13, 0.9)])}, new Date())"))
        self.assertFalse(self.avalua(ara, "plujaPrevistaAviat(undefined, new Date())"))

    def test_icones_del_cel_amb_els_seus_colors(self):
        # ADR 0063: cada icona del temps que posa la pàgina de casa té les
        # peces pintades amb els colors del cel (sol, núvol, aigua, neu, lluna);
        # i la paleta és als dos temes.
        import re
        with open(os.path.join(WEB, "casa.js"), encoding="utf-8") as f:
            usades = set(re.findall(r"'(i-(?:cloud[a-z-]*|sun|moon-cel|snowflake|umbrella|droplets))'", f.read()))
        with open(os.path.join(WEB, "casa.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertIn("i-cloud-sun", usades)
        for id_ in usades:
            simbol = re.search(rf'<symbol id="{id_}"[^>]*>(.*?)</symbol>', html).group(1)
            self.assertIn("var(--ic-", simbol, id_)
        with open(os.path.join(WEB, "estil.css"), encoding="utf-8") as f:
            css = f.read()
        temes = css.split(':root[data-theme="dark"]')
        for color in ("--c-sol:", "--c-nuvol:", "--c-aigua:", "--c-aigua-text:", "--c-neu:", "--c-lluna:", "--c-maxima:", "--c-minima:"):
            self.assertIn(color, temes[0], color)
            self.assertIn(color, temes[1].split("}")[0], color)


if __name__ == "__main__":
    unittest.main()
