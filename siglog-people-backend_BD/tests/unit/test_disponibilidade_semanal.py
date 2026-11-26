import unittest
from datetime import date, datetime, time

from src.domain.entities import Periodo
from src.infrastructure import disponibilidade_semanal as ds
from src.infrastructure.disponibilidade_semanal import FIM_DO_DIA
from src.domain import rules as R
from src.config.settings import Settings
from src.domain.entities import Motorista
from tests.factories import dt


def linhas_com_ids(segmentos, disponivel=True):
    """Simula as linhas que o banco devolveria para os segmentos gravados."""
    return [{"id": i + 1, "dia_semana": s["dia_semana"], "hora_inicio": s["hora_inicio"],
             "hora_fim": s["hora_fim"], "vigencia_inicio": s["vigencia"], "vigencia_fim": s["vigencia"],
             "disponivel": disponivel} for i, s in enumerate(segmentos)]


class SegmentarTest(unittest.TestCase):
    def test_janela_de_varios_dias_vira_uma_linha_por_dia(self):
        seg = ds.segmentar(Periodo(dt(1, 0), dt(5, 23)))
        self.assertEqual(len(seg), 5)
        self.assertEqual(seg[0]["hora_fim"], FIM_DO_DIA)
        self.assertEqual(seg[-1]["hora_fim"], time(23, 0))
        self.assertTrue(all(s["hora_fim"] > s["hora_inicio"] for s in seg))   # CHECK do banco

    def test_janela_dentro_de_um_dia(self):
        seg = ds.segmentar(Periodo(dt(2, 6), dt(2, 14)))
        self.assertEqual(seg, [{"dia_semana": 1, "hora_inicio": time(6), "hora_fim": time(14),
                                "vigencia": date(2026, 3, 2)}])   # 02/03/2026 = segunda → 1

    def test_dia_da_semana_domingo_zero(self):
        self.assertEqual(ds.dia_semana(date(2026, 3, 1)), 0)      # domingo
        self.assertEqual(ds.dia_semana(date(2026, 3, 7)), 6)      # sábado

    def test_janela_que_termina_exatamente_a_meia_noite(self):
        seg = ds.segmentar(Periodo(dt(2, 20), dt(3, 0)))
        self.assertEqual(len(seg), 1)
        self.assertEqual(seg[0]["hora_fim"], FIM_DO_DIA)


class RoundTripTest(unittest.TestCase):
    def test_gravar_e_ler_devolve_a_mesma_janela(self):
        original = Periodo(dt(1, 0), dt(5, 23))
        linhas = linhas_com_ids(ds.segmentar(original))
        lidas = ds.mesclar([ds.janela_de_linha_pontual(l, "7") for l in linhas])
        self.assertEqual(len(lidas), 1)
        self.assertEqual(lidas[0].periodo, original)

    def test_janela_atravessando_meia_noite_round_trip(self):
        original = Periodo(dt(2, 22), dt(3, 6))
        lidas = ds.mesclar([ds.janela_de_linha_pontual(l, "7") for l in linhas_com_ids(ds.segmentar(original))])
        self.assertEqual([j.periodo for j in lidas], [original])

    def test_mesclar_nao_une_flags_diferentes(self):
        a = ds.janela_de_linha_pontual(linhas_com_ids(ds.segmentar(Periodo(dt(2, 0), dt(2, 10))))[0], "7")
        b = ds.janela_de_linha_pontual(linhas_com_ids(ds.segmentar(Periodo(dt(2, 10), dt(2, 12))), False)[0], "7")
        self.assertEqual(len(ds.mesclar([a, b])), 2)


class ExpandirTest(unittest.TestCase):
    def test_linha_recorrente_semanal_expande_nos_dias_certos(self):
        # toda segunda (1), 06:00-18:00, vigência aberta
        linha = {"id": 9, "dia_semana": 1, "hora_inicio": time(6), "hora_fim": time(18),
                 "vigencia_inicio": date(2026, 1, 1), "vigencia_fim": None, "disponivel": True}
        janelas = ds.expandir([linha], Periodo(dt(2, 6), dt(9, 14)), "7")
        self.assertEqual([j.periodo.inicio.day for j in janelas], [2, 9])   # segundas 02 e 09

    def test_respeita_vigencia(self):
        linha = {"id": 9, "dia_semana": 1, "hora_inicio": time(6), "hora_fim": time(18),
                 "vigencia_inicio": date(2026, 3, 5), "vigencia_fim": date(2026, 3, 8), "disponivel": True}
        self.assertEqual(ds.expandir([linha], Periodo(dt(2, 6), dt(9, 14)), "7"), [])

    def test_turno_noturno_coberto_por_linhas_de_dois_dias(self):
        seg = ds.segmentar(Periodo(dt(2, 20), dt(3, 8)))
        periodo = Periodo(dt(2, 22), dt(3, 6))
        janelas = ds.expandir(linhas_com_ids(seg), periodo, "7")
        m = Motorista(nome="X", cpf="1", id="7")
        ctx = R.ContextoAlocacao(m, None, periodo, janelas, [], [], [], Settings())
        self.assertTrue(R.RegraDisponibilidade().avaliar(ctx) == [])

    def test_buraco_entre_dias_nao_cobre(self):
        seg = ds.segmentar(Periodo(dt(2, 0), dt(2, 10))) + ds.segmentar(Periodo(dt(2, 11), dt(2, 20)))
        periodo = Periodo(dt(2, 8), dt(2, 14))
        janelas = ds.expandir(linhas_com_ids(seg), periodo, "7")
        m = Motorista(nome="X", cpf="1", id="7")
        ctx = R.ContextoAlocacao(m, None, periodo, janelas, [], [], [], Settings())
        self.assertEqual(R.RegraDisponibilidade().avaliar(ctx)[0].codigo, R.MOTORISTA_INDISPONIVEL)


if __name__ == "__main__":
    unittest.main()
