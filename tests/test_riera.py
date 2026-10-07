# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pruebas del aviso de la riera de Sant Cugat (sin red ni Telegram)."""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config as C  # noqa: E402
import montflorit as M  # noqa: E402
import riera as RI  # noqa: E402

UTC = dt.timezone.utc
# Lluvia de Sant Cugat (Meteocat XV) el 04-10-2026, por medias horas que
# empiezan a la hora UTC indicada: la del desbordamiento de la 1-2 en Montflorit.
EPISODI = [(19, 30, 8.0), (20, 0, 4.6), (20, 30, 4.9), (21, 0, 8.7), (21, 30, 9.1),
           (22, 0, 8.9), (22, 30, 4.5), (23, 0, 10.0), (23, 30, 19.6)]


def files_xv(fins_utc):
    """Las medias horas del episodio publicadas hasta fins_utc (03-10 y 04-10 UTC)."""
    res = []
    for h, m, mm in EPISODI:
        t = dt.datetime(2026, 10, 3, h, m, tzinfo=UTC)
        if t + RI.MITJA_HORA <= fins_utc:
            res.append((t, mm))
    return res


def nowcast(hora, mm_h):
    """Radar con la misma lluvia sobre la cuenca durante 2 horas."""
    return {"hora": hora.isoformat(timespec="minutes"),
            "llocs": {"conca": [{"min": m, "mm_h": mm_h, "prob": 1.0 if mm_h else 0.0}
                                for m in range(0, 121, 5)]}}


class Index(unittest.TestCase):
    def test_acumulat_nomes_mitges_hores_senceres(self):
        fins = dt.datetime(2026, 10, 4, 0, 0, tzinfo=UTC)
        filas = files_xv(fins)
        self.assertEqual(RI.acumulat(filas, fins, 3), 60.8)   # 21:00-24:00 UTC
        self.assertEqual(RI.acumulat(filas, fins, 1), 29.6)

    def test_index_sense_radar_es_el_mesurat(self):
        fins = dt.datetime(2026, 10, 3, 23, 0, tzinfo=UTC)
        ara = fins + dt.timedelta(minutes=30)
        r = self.calcula(ara, fins, None)
        self.assertEqual(r["mm_3h"], 40.7)
        self.assertEqual(r["index"], 40.7)
        self.assertEqual(r["nivell"], "atencio")
        self.assertIsNone(r["radar_1h"])

    def test_el_radar_avanca_el_perill(self):
        # Con 40,7 mm medidos y el radar viendo 20 mm/h en la cuenca, la
        # lluvia de 3 horas pasará de 50 en la hora siguiente.
        fins = dt.datetime(2026, 10, 3, 23, 0, tzinfo=UTC)
        ara = fins + dt.timedelta(minutes=30)
        r = self.calcula(ara, fins, nowcast(ara - dt.timedelta(minutes=15), 20))
        self.assertEqual(r["nivell"], "perill")
        self.assertGreaterEqual(r["index"], C.RIERA_PERILL_MM)
        self.assertEqual(r["index_d_aqui_a_min"], 60)

    def test_forat_entre_estacio_i_radar(self):
        # Imagen 15 minutos más nueva que la estación, 12 mm/h: el hueco
        # cuenta 3 mm y la media hora siguiente, 3 más.
        desde = dt.datetime(2026, 10, 3, 23, 0, tzinfo=UTC)
        nc = nowcast(desde + dt.timedelta(minutes=15), 12)
        self.assertEqual(RI.previst(nc, desde, 15), 3.0)
        self.assertEqual(RI.previst(nc, desde, 30), 6.0)
        self.assertEqual(RI.previst(None, desde, 30), 0.0)

    def test_estacio_endarrerida(self):
        fins = dt.datetime(2026, 10, 3, 23, 0, tzinfo=UTC)
        self.assertIsNone(self.calcula(fins + dt.timedelta(hours=3), fins, None))

    def calcula(self, ara, fins, nc):
        import prevision as P
        original = P.taula_meteocat
        P.taula_meteocat = lambda codi, dia=None, lector=None: [
            f for f in files_xv(fins) if f[0].date() == dia] if codi == C.RIERA_ESTACIO else []
        try:
            return RI.calcula(ara, nc)
        finally:
            P.taula_meteocat = original


class Avisos(unittest.TestCase):
    T0 = dt.datetime(2026, 10, 3, 22, 0).astimezone()

    def riera(self, index, mm_3h=None):
        return {"fins": self.T0.isoformat(timespec="minutes"), "mm_3h": mm_3h or index, "mm_6h": index,
                "radar_1h": 4.0, "index": index, "capcalera": {"mm_3h": 30.0}, "montflorit_3h": 41.0}

    def passades(self, indexs, cada=30):
        estat, textos, files = {"episodi": None}, [], []
        for i, index in enumerate(indexs):
            ara = self.T0 + dt.timedelta(minutes=cada * i)
            text, fila = RI.compara(estat, self.riera(index) if index is not None else None, ara)
            textos.append(text)
            if fila:
                files.append(fila)
        return textos, files, estat

    def test_un_avis_per_nivell(self):
        textos, _, _ = self.passades([10, 22, 36, 40, 52, 60, 45, 55])
        self.assertEqual([bool(t) for t in textos], [False, False, True, False, True, False, False, False])
        self.assertIn("atenció", textos[2])
        self.assertIn("perill de desbordament", textos[4])
        self.assertIn("al Fabra (Collserola), 30 mm i a Montflorit, 41 mm", textos[2])
        self.assertIn("el radar en preveu uns 4,0 més", textos[2])

    def test_perill_de_cop_no_envia_tambe_atencio(self):
        textos, _, estat = self.passades([55, 60])
        self.assertEqual(sum(bool(t) for t in textos), 1)
        self.assertIn("perill", textos[0])
        self.assertEqual(set(estat["episodi"]["avisos"]), {"atencio", "perill"})

    def test_episodi_es_tanca_i_s_apunta(self):
        # 3 horas por debajo de 20 mm cierran el episodio con sus máximos.
        textos, files, estat = self.passades([25, 38, 30, 15, 10, 5, 5, 5, 5, 5])
        self.assertEqual(len(files), 1)
        f = files[0]
        self.assertEqual(f["index_max"], 38)
        self.assertEqual(f["montflorit_3h_max"], 41.0)
        self.assertTrue(f["avis_atencio"])
        self.assertEqual(f["avis_perill"], "")
        self.assertEqual(f["desbordament"], "")
        self.assertIsNone(estat["episodi"])

    def test_sense_dades_no_canvia_res(self):
        textos, files, estat = self.passades([38, None, None])
        self.assertEqual(sum(bool(t) for t in textos), 1)
        self.assertIsNotNone(estat["episodi"])
        self.assertEqual(files, [])

    def test_pluja_feble_no_obre_episodi(self):
        _, files, estat = self.passades([5, 12, 19, 8])
        self.assertIsNone(estat["episodi"])
        self.assertEqual(files, [])


class Privacitat(unittest.TestCase):
    def test_la_web_publica_no_porta_la_riera(self):
        self.assertIn("riera", M.PRIVADES)


if __name__ == "__main__":
    unittest.main()
