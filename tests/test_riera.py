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
        self.assertEqual(r["mm_1h"], 13.4)       # 22:00-23:00 UTC, per al registre (ADR 0042)
        self.assertEqual(r["index"], 40.7)
        self.assertEqual(r["index_6h"], 48.7)
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
        self.assertGreaterEqual(r["index_6h"], C.RIERA_PERILL_6H_MM)
        self.assertEqual(r["index_d_aqui_a_min"], 60)

    def test_perill_nomes_amb_3_i_6_hores_del_mateix_moment(self):
        # Auditoria del 09-10-2026: el màxim de 3 hores (ara: 50 mm sobre sòl sec)
        # i el de 6 (d'aquí a una hora: 60) eren de moments diferents i donaven
        # perill, i en cap moment es complien les dues condicions.
        from unittest.mock import patch
        ara = dt.datetime(2026, 10, 9, 12, 0, tzinfo=UTC)
        files = lambda pluja: [(ara - RI.MITJA_HORA * (12 - i), mm) for i, mm in enumerate(pluja)]
        with patch.object(RI, "files", return_value=files([0] * 6 + [20, 0, 0, 0, 15, 15])):
            r = RI.calcula(ara, nowcast(ara, 10))
        self.assertEqual((r["nivell"], r["index"], r["index_6h"], r["index_d_aqui_a_min"]), ("atencio", 50.0, 50.0, 0))
        # Amb 10 mm més abans del xàfec, les dues condicions es donen alhora: perill.
        with patch.object(RI, "files", return_value=files([0, 0, 0, 0, 10, 0, 20, 0, 0, 0, 15, 15])):
            r = RI.calcula(ara, nowcast(ara, 10))
        self.assertEqual((r["nivell"], r["index"], r["index_6h"]), ("perill", 50.0, 60.0))

    def test_l_hora_seguent_es_compta_des_d_ara(self):
        # Auditoria del 08-10-2026: amb l'estació mitja hora endarrerida, un xàfec
        # de 37,5 mm entre d'aquí a 35 i 60 minuts quedava fora de l'«hora següent».
        from unittest.mock import patch
        ara = dt.datetime(2026, 10, 8, 10, 0, tzinfo=UTC)
        fins = ara - dt.timedelta(minutes=30)
        filas = [(fins - RI.MITJA_HORA * (12 - i), 0.0) for i in range(12)]
        nc = {"hora": (ara - dt.timedelta(minutes=15)).isoformat(timespec="minutes"),
              "llocs": {"conca": [{"min": k, "mm_h": 90 if 50 <= k < 75 else 0, "prob": 1 if 50 <= k < 75 else 0}
                                  for k in range(0, 125, 5)]}}
        with patch.object(RI, "files", return_value=filas):
            r = RI.calcula(ara, nc)
        self.assertEqual(r["index"], 37.5)
        self.assertEqual(r["nivell"], "atencio")
        self.assertEqual(r["index_d_aqui_a_min"], 60)
        self.assertEqual(r["radar_1h"], 37.5)
        self.assertEqual(RI.horitzo(fins, ara), 90)
        self.assertIn("des de llavors fins d'aquí a una hora", RI.missatge(r, "atencio"))

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

    def test_forats_a_l_estacio(self):
        # Auditoría del 07-10-2026: las medias horas que faltan contaban como
        # cero. Con todas, completo; sin una de las 6 de 3 h, aún; sin dos, no.
        fins = dt.datetime(2026, 10, 4, 0, 0, tzinfo=UTC)
        # La tabla de Meteocat trae todas las medias horas, con 0,0 si no llueve.
        filas = [(dt.datetime(2026, 10, 3, 18, m, tzinfo=UTC), 0.0) for m in (0, 30)] \
            + [(dt.datetime(2026, 10, 3, 19, 0, tzinfo=UTC), 0.0)] + files_xv(fins)
        self.assertEqual(RI.cobertura(filas, fins, 3), 6)
        self.assertEqual(RI.cobertura(filas, fins, 6), 12)
        self.assertFalse(RI.incomplet(filas, fins))
        sense_una = [f for f in filas if f[0].hour != 22 or f[0].minute != 0]
        self.assertFalse(RI.incomplet(sense_una, fins))
        sense_dues = [f for f in sense_una if f[0].hour != 21 or f[0].minute != 30]
        self.assertTrue(RI.incomplet(sense_dues, fins))
        # En 6 horas se admiten dos huecos; tres, no.
        sense_dues_de_6h = [f for f in filas if (f[0].hour, f[0].minute) not in ((18, 30), (19, 30))]
        self.assertFalse(RI.incomplet(sense_dues_de_6h, fins))
        sense_tres_de_6h = [f for f in sense_dues_de_6h if (f[0].hour, f[0].minute) != (20, 30)]
        self.assertTrue(RI.incomplet(sense_tres_de_6h, fins))

    def test_calcula_marca_incomplet_i_el_missatge_ho_diu(self):
        fins = dt.datetime(2026, 10, 3, 23, 0, tzinfo=UTC)
        ara = fins + dt.timedelta(minutes=30)
        import prevision as P
        original = P.taula_meteocat
        # Faltan las medias horas de las 21:30 y las 22:00: 2 huecos en 3 h.
        P.taula_meteocat = lambda codi, dia=None, lector=None: [
            f for f in files_xv(fins) if f[0].date() == dia and (f[0].hour, f[0].minute) not in ((21, 30), (22, 0))
        ] if codi == C.RIERA_ESTACIO else []
        try:
            r = RI.calcula(ara, None)
        finally:
            P.taula_meteocat = original
        self.assertTrue(r["incomplet"])
        self.assertEqual(r["mm_3h"], 22.7)      # 40,7 menos las dos medias horas que faltan (9,1 y 8,9)
        self.assertIn("li falten mesures", RI.missatge(r, "registre"))

    def test_canvi_de_dia_utc_sense_forats(self):
        # Ventana de 3 h que cruza la medianoche UTC (filas de dos días): completa.
        fins = dt.datetime(2026, 10, 4, 1, 0, tzinfo=UTC)
        filas = files_xv(dt.datetime(2026, 10, 4, 0, 0, tzinfo=UTC)) + [
            (dt.datetime(2026, 10, 4, 0, 0, tzinfo=UTC), 3.0), (dt.datetime(2026, 10, 4, 0, 30, tzinfo=UTC), 1.0)]
        self.assertEqual(RI.cobertura(filas, fins, 3), 6)
        self.assertFalse(RI.incomplet(filas, fins))
        self.assertEqual(RI.acumulat(filas, fins, 3), 47.0)   # 22:00-01:00 UTC

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

    def riera(self, index, index_6h=None):
        index_6h = index + 20 if index_6h is None else index_6h
        return {"fins": self.T0.isoformat(timespec="minutes"), "mm_3h": index, "mm_6h": index_6h,
                "radar_1h": 4.0, "index": index, "index_6h": index_6h, "capcalera": {"mm_3h": 30.0}}

    def passades(self, indexs, cada=30, index_6h=None):
        estat, textos, files = {"episodi": None}, [], []
        for i, index in enumerate(indexs):
            ara = self.T0 + dt.timedelta(minutes=cada * i)
            text, fila = RI.compara(estat, self.riera(index, index_6h) if index is not None else None, ara)
            textos.append(text)
            if fila:
                files.append(fila)
        return textos, files, estat

    def test_un_avis_per_nivell(self):
        textos, _, _ = self.passades([10, 22, 36, 40, 52, 60, 45, 55])
        self.assertEqual([bool(t) for t in textos], [False, False, True, False, True, False, False, False])
        self.assertIn("atenció", textos[2])
        self.assertIn("perill de desbordament", textos[4])
        self.assertIn("En 3 hores, al Fabra (Collserola), 30 mm.", textos[2])
        self.assertIn("el radar en preveu uns 4,0 més", textos[2])

    def test_xafec_sobre_sol_sec_nomes_atencio(self):
        # 13-09-2025: 52 mm en 3 horas y nada antes (52 en 6); no se desbordó.
        textos, _, estat = self.passades([40, 52, 52], index_6h=52)
        self.assertEqual(sum(bool(t) for t in textos), 1)
        self.assertIn("atenció", textos[0])
        self.assertIn("S'ha desbordat amb 50 mm o més en 3 hores i 60 en 6", textos[0])
        self.assertNotIn("perill", estat["episodi"]["avisos"])

    def test_nivells(self):
        self.assertEqual(RI.nivell(53, 75), "perill")      # 29-04-2024
        self.assertEqual(RI.nivell(67, 67), "perill")      # 29-09-2026
        self.assertEqual(RI.nivell(52, 52), "atencio")     # 13-09-2025
        self.assertEqual(RI.nivell(25, 90), "registre")
        self.assertIsNone(RI.nivell(10, 70))

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
        self.assertTrue(f["avis_atencio"])
        self.assertEqual(f["avis_perill"], "")
        self.assertEqual(f["desbordament"], "")
        self.assertIsNone(estat["episodi"])
        # En tancar-se, un sol missatge de final (Juanjo, 08-10-2026), del nivell que es va avisar.
        self.assertEqual([t for t in textos if t][-1], "Riera de Sant Cugat: ja no hi ha risc de desbordament. A Sant Cugat fa 3 hores "
                                     "que no plou amb força (5,0 mm en les últimes 3 hores) i el radar no hi veu pluja forta. "
                                     "Si torna a ploure fort, tornarà l'avís.")
        self.assertEqual(sum(bool(t) for t in textos), 2)

    def test_el_final_diu_perill_si_n_hi_va_haver_i_res_sense_avis(self):
        textos, files, _ = self.passades([55, 60, 10, 5, 5, 5, 5, 5, 5], index_6h=70)
        self.assertTrue([t for t in textos if t][-1].startswith("Riera de Sant Cugat: ha passat el perill de desbordament."))
        self.assertEqual(len(files), 1)
        # Un episodi només de registre (20-35 mm) s'apunta sense cap missatge.
        textos, files, _ = self.passades([25, 28, 10, 5, 5, 5, 5, 5, 5])
        self.assertEqual(len(files), 1)
        self.assertEqual([t for t in textos if t], [])

    def test_sense_dades_no_canvia_res(self):
        textos, files, estat = self.passades([38, None, None])
        self.assertEqual(sum(bool(t) for t in textos), 1)
        self.assertIsNotNone(estat["episodi"])
        self.assertEqual(files, [])

    def test_amb_forats_l_episodi_no_es_tanca(self):
        # Tras el aviso, 4 horas de índice bajo pero con huecos en la estación:
        # el episodio sigue abierto; con los datos completos, se cierra.
        estat, files = {"episodi": None}, []
        for i, (index, forats) in enumerate([(38, False), (5, True), (5, True), (5, True), (5, True), (5, True),
                                             (5, True), (5, True), (5, True), (5, False)]):
            riera = dict(self.riera(index), incomplet=forats)
            _, fila = RI.compara(estat, riera, self.T0 + dt.timedelta(minutes=30 * i))
            if fila:
                files.append(fila)
            if i == 8:
                self.assertIsNotNone(estat["episodi"])
        self.assertIsNone(estat["episodi"])
        self.assertEqual(len(files), 1)

    def test_pluja_feble_no_obre_episodi(self):
        _, files, estat = self.passades([5, 12, 19, 8])
        self.assertIsNone(estat["episodi"])
        self.assertEqual(files, [])


class Privacitat(unittest.TestCase):
    def test_la_web_publica_no_porta_la_riera(self):
        self.assertIn("riera", M.PRIVADES)


if __name__ == "__main__":
    unittest.main()
