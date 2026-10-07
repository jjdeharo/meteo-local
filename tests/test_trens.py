# SPDX-License-Identifier: AGPL-3.0-or-later
"""Proves de l'estat dels trens (sense xarxa)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import trens as T  # noqa: E402

ARA = dt.datetime(2026, 10, 7, 7, 50).astimezone()
R7 = C.TRENS_ESTACIONS["R7"]


def camp(num, valor):
    """Un camp protobuf de longitud variable (o un enter)."""
    def varint(n):
        res = b""
        while True:
            b = n & 0x7F
            n >>= 7
            res += bytes([b | (0x80 if n else 0)])
            if not n:
                return res
    if isinstance(valor, int):
        return varint(num << 3) + varint(valor)
    if isinstance(valor, str):
        valor = valor.encode()
    return varint(num << 3 | 2) + varint(len(valor)) + valor


def traduccio(text, idioma):
    return camp(1, camp(1, text) + camp(2, idioma))


class Protobuf(unittest.TestCase):
    def test_avis_gtfs_rt(self):
        alerta = (camp(1, camp(1, 1791350000)) + camp(5, camp(2, "S2")) + camp(5, camp(2, "S1"))
                  + camp(11, traduccio("Obres a Bellaterra.", "ca") + traduccio("Obras en Bellaterra.", "es")))
        feed = camp(1, camp(1, "2.0")) + camp(2, camp(1, "a1") + camp(5, alerta))
        self.assertEqual(T.avisos_pb(feed), [{"rutes": ["S2", "S1"], "text": {
            "ca": "Obres a Bellaterra.", "es": "Obras en Bellaterra."}}])


class Idiomes(unittest.TestCase):
    def test_renfe_marca_els_dos_com_a_castella(self):
        r = T.idiomes(["Per causes alienes a Rodalies no es pot garantir la prestació del servei.\r\n",
                       "Por causas ajenas a Rodalies no se puede garantizar la prestación del servicio."])
        self.assertTrue(r["ca"].startswith("Per causes"))
        self.assertTrue(r["es"].startswith("Por causas"))

    def test_un_sol_idioma_es_queda_tal_qual(self):
        r = T.idiomes(["Servicio alternativo por carretera en todo su recorrido."])
        self.assertEqual(r["ca"], r["es"])

    def test_linia_renfe(self):
        self.assertEqual(T.linia_renfe("51T0037R7"), "R7")
        self.assertEqual(T.linia_renfe("51T0094R2N"), "R2N")
        self.assertIsNone(T.linia_renfe("10T0001C1"))


def tren(linia, lat, lon, aturat=False, ident="1"):
    return {"id": ident, "linia": linia, "lat": lat, "lon": lon, "aturat": aturat}


class Estat(unittest.TestCase):
    def test_aturat_a_l_estacio_no_circula(self):
        # 07-10-2026: dos trens de l'R7 «a l'estació», sense moure's.
        abans = {"hora": (ARA - dt.timedelta(minutes=15)).isoformat(), "posicions": {"1": R7}}
        self.assertEqual(T.es_mouen([tren("R7", *R7, aturat=True)], abans, ARA), [])
        # Sense passada anterior, l'aturat tampoc no compta.
        self.assertEqual(T.es_mouen([tren("R7", *R7, aturat=True)], None, ARA), [])

    def test_lluny_de_l_estacio_no_compta(self):
        # L'R4 pel tram sud (Martorell) no serveix a qui surt de Cerdanyola.
        self.assertEqual(T.es_mouen([tren("R4", 41.47, 1.93)], None, ARA), [])

    def test_es_mou(self):
        abans = {"hora": (ARA - dt.timedelta(minutes=15)).isoformat(), "posicions": {"1": (41.48, 2.12)}}
        self.assertEqual(len(T.es_mouen([tren("R7", *R7)], abans, ARA)), 1)

    def avis(self, linies, ca, es=None):
        return {"linies": set(linies), "text": {"ca": ca, "es": es or ca}}

    def test_estats(self):
        bus = self.avis(["R8"], "Servei alternatiu per carretera en tot el seu recorregut.")
        general = self.avis(["R4", "R7", "R8"], "No es pot garantir la prestació del servei.")
        mou = [tren("R7", *R7)]
        self.assertEqual(T.estat_linia("R8", [], None, [bus, general], ARA)["estat"], "bus")
        self.assertEqual(T.estat_linia("R7", mou, None, [general], ARA)["estat"], "incidencies")
        self.assertEqual(T.estat_linia("R7", mou, None, [], ARA)["estat"], "circula")
        self.assertEqual(T.estat_linia("R4", [], None, [general], ARA)["estat"], "sense_trens")
        nit = ARA.replace(hour=2)
        self.assertEqual(T.estat_linia("R4", [], None, [], nit)["estat"], "fora_horari")

    def test_vist_fa_poc_circula(self):
        # Amb trens cada 30 minuts, en una passada pot no haver-n'hi cap a prop.
        fa_poc = (ARA - dt.timedelta(minutes=20)).isoformat()
        fa_molt = (ARA - dt.timedelta(minutes=C.TRENS_VIST_MIN + 5)).isoformat()
        self.assertEqual(T.estat_linia("R4", [], fa_poc, [], ARA)["estat"], "circula")
        self.assertEqual(T.estat_linia("R4", [], fa_molt, [], ARA)["estat"], "sense_trens")

    def test_l_avis_propi_va_primer(self):
        bus = self.avis(["R8"], "Servei alternatiu per carretera.")
        general = self.avis(["R4", "R8"], "No es pot garantir el servei.")
        r = T.estat_linia("R8", [], None, [general, bus, bus], ARA)
        self.assertEqual([a["ca"] for a in r["avisos"]], ["Servei alternatiu per carretera.",
                                                          "No es pot garantir el servei."])


if __name__ == "__main__":
    unittest.main()
