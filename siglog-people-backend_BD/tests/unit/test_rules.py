import unittest
from datetime import date

from src.config.settings import Settings
from src.domain import rules as R
from src.domain.entities import (Alocacao, Certificacao, Disponibilidade, Jornada,
                                 Motorista, Periodo, Turno, Veiculo)
from src.domain.validators import cnh_compativel, cpf_valido
from datetime import time
from tests.factories import dt


def ctx(motorista=None, veiculo=None, periodo=None, disp=None, am=None, av=None, jor=None):
    m = motorista or Motorista(nome="X", cpf="1", cnh_categoria="C")
    p = periodo or Periodo(dt(2, 6), dt(2, 14))
    d = disp if disp is not None else [Disponibilidade(m.id, Periodo(dt(1, 0), dt(5, 0)))]
    return R.ContextoAlocacao(m, veiculo, p, d, am or [], av or [], jor or [], Settings())


def codigos(res): return {v.codigo for v in res.violacoes}


class ValidatorsTest(unittest.TestCase):
    def test_cpf(self):
        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertFalse(cpf_valido("111.111.111-11"))
        self.assertFalse(cpf_valido("123"))

    def test_hierarquia_cnh(self):
        self.assertTrue(cnh_compativel("E", "C"))
        self.assertTrue(cnh_compativel("C", "C"))
        self.assertFalse(cnh_compativel("B", "C"))
        self.assertFalse(cnh_compativel("C", "A"))
        self.assertTrue(cnh_compativel("A", "A"))


class TurnoTest(unittest.TestCase):
    def test_turno_noturno_cruza_meia_noite(self):
        p = Turno("Noite", time(22), time(6)).periodo_em(dt(1, 0).date())
        self.assertEqual(p.horas, 8)
        self.assertEqual(p.fim.day, 2)


class RegraDisponibilidadeTest(unittest.TestCase):
    def test_disponivel_ok(self):
        self.assertTrue(R.MotorDeRegras([R.RegraDisponibilidade()]).validar(ctx()).permitido)

    def test_inativo(self):
        m = Motorista(nome="X", cpf="1", ativo=False)
        self.assertIn(R.MOTORISTA_INATIVO, codigos(R.MotorDeRegras([R.RegraDisponibilidade()]).validar(ctx(motorista=m))))

    def test_sem_janela(self):
        res = R.MotorDeRegras([R.RegraDisponibilidade()]).validar(ctx(disp=[]))
        self.assertIn(R.MOTORISTA_INDISPONIVEL, codigos(res))

    def test_bloqueio_explicito_sobreposto(self):
        m = Motorista(nome="X", cpf="1")
        disp = [Disponibilidade(m.id, Periodo(dt(1, 0), dt(5, 0))),
                Disponibilidade(m.id, Periodo(dt(2, 10), dt(2, 12)), disponivel=False)]
        res = R.MotorDeRegras([R.RegraDisponibilidade()]).validar(ctx(motorista=m, disp=disp))
        self.assertIn(R.MOTORISTA_INDISPONIVEL, codigos(res))

    def test_janelas_adjacentes_cobrem_periodo(self):
        m = Motorista(nome="X", cpf="1")
        disp = [Disponibilidade(m.id, Periodo(dt(2, 0), dt(2, 10))),
                Disponibilidade(m.id, Periodo(dt(2, 10), dt(2, 20)))]
        self.assertTrue(R.MotorDeRegras([R.RegraDisponibilidade()]).validar(ctx(motorista=m, disp=disp)).permitido)

    def test_janela_com_buraco(self):
        m = Motorista(nome="X", cpf="1")
        disp = [Disponibilidade(m.id, Periodo(dt(2, 0), dt(2, 9))),
                Disponibilidade(m.id, Periodo(dt(2, 10), dt(2, 20)))]
        self.assertFalse(R.MotorDeRegras([R.RegraDisponibilidade()]).validar(ctx(motorista=m, disp=disp)).permitido)


class RegraCertificacaoTest(unittest.TestCase):
    rule = [R.RegraCertificacao()]

    def test_cnh_incompativel(self):
        m = Motorista(nome="X", cpf="1", cnh_categoria="B")
        res = R.MotorDeRegras(self.rule).validar(ctx(motorista=m, veiculo=Veiculo("A", "C")))
        self.assertEqual(codigos(res), {R.CNH_INCOMPATIVEL})

    def test_certificacao_ausente(self):
        res = R.MotorDeRegras(self.rule).validar(ctx(veiculo=Veiculo("A", "C", ["MOPP"])))
        self.assertEqual(codigos(res), {R.CERTIFICACAO_AUSENTE})

    def test_certificacao_vencida_antes_do_fim_do_periodo(self):
        m = Motorista(nome="X", cpf="1", certificacoes=[Certificacao("MOPP", date(2026, 3, 1))])
        res = R.MotorDeRegras(self.rule).validar(ctx(motorista=m, veiculo=Veiculo("A", "C", ["MOPP"])))
        self.assertEqual(codigos(res), {R.CERTIFICACAO_VENCIDA})

    def test_certificacao_vigente_no_ultimo_dia(self):
        m = Motorista(nome="X", cpf="1", certificacoes=[Certificacao("mopp", date(2026, 3, 2))])
        self.assertTrue(R.MotorDeRegras(self.rule).validar(ctx(motorista=m, veiculo=Veiculo("A", "C", ["MOPP"]))).permitido)


class RegraDescansoTest(unittest.TestCase):
    rule = [R.RegraDescanso()]

    def aloc(self, ini, fim):
        return Alocacao("f", "v", Periodo(ini, fim))

    def test_descanso_insuficiente_apos_jornada_anterior(self):
        am = [self.aloc(dt(1, 14), dt(2, 0))]            # termina 00:00 dia 2; nova começa 06:00 → 6h
        self.assertEqual(codigos(R.MotorDeRegras(self.rule).validar(ctx(am=am))), {R.DESCANSO_INSUFICIENTE})

    def test_exatamente_11h_e_permitido(self):
        am = [self.aloc(dt(1, 8), dt(1, 19))]            # 19:00 → 06:00 = 11h
        self.assertTrue(R.MotorDeRegras(self.rule).validar(ctx(am=am)).permitido)

    def test_descanso_ate_proxima_alocacao_futura(self):
        am = [self.aloc(dt(2, 20), dt(3, 4))]            # nova termina 14:00; próxima 20:00 → 6h
        self.assertEqual(codigos(R.MotorDeRegras(self.rule).validar(ctx(am=am))), {R.DESCANSO_INSUFICIENTE})

    def test_jornada_fechada_conta_como_trabalho(self):
        j = [Jornada("f", dt(1, 12), dt(1, 22))]         # 22:00 → 06:00 = 8h
        self.assertEqual(codigos(R.MotorDeRegras(self.rule).validar(ctx(jor=j))), {R.DESCANSO_INSUFICIENTE})


class RegraJornadaConflitoTest(unittest.TestCase):
    def test_jornada_excedida(self):
        res = R.MotorDeRegras([R.RegraJornada()]).validar(ctx(periodo=Periodo(dt(2, 6), dt(2, 18))))
        self.assertEqual(codigos(res), {R.JORNADA_EXCEDIDA})

    def test_jornada_no_limite(self):
        self.assertTrue(R.MotorDeRegras([R.RegraJornada()]).validar(ctx(periodo=Periodo(dt(2, 6), dt(2, 16)))).permitido)

    def test_conflito_motorista_e_veiculo(self):
        a = Alocacao("f", "v", Periodo(dt(2, 10), dt(2, 20)))
        res = R.MotorDeRegras([R.RegraConflito()]).validar(ctx(am=[a], av=[a]))
        self.assertEqual(codigos(res), {R.CONFLITO_MOTORISTA, R.CONFLITO_VEICULO})

    def test_periodos_encostados_nao_conflitam(self):
        a = Alocacao("f", "v", Periodo(dt(2, 14), dt(2, 20)))
        self.assertTrue(R.MotorDeRegras([R.RegraConflito()]).validar(ctx(am=[a])).permitido)


class MotorCompletoTest(unittest.TestCase):
    def test_tudo_valido_permite(self):
        m = Motorista(nome="X", cpf="1", cnh_categoria="C", certificacoes=[Certificacao("MOPP", date(2027, 1, 1))])
        res = R.MotorDeRegras().validar(ctx(motorista=m, veiculo=Veiculo("A", "C", ["MOPP"])))
        self.assertTrue(res.permitido)

    def test_acumula_multiplas_violacoes(self):
        m = Motorista(nome="X", cpf="1", cnh_categoria="B")
        res = R.MotorDeRegras().validar(ctx(motorista=m, veiculo=Veiculo("A", "C", ["MOPP"]), disp=[]))
        self.assertEqual(codigos(res), {R.MOTORISTA_INDISPONIVEL, R.CNH_INCOMPATIVEL, R.CERTIFICACAO_AUSENTE})


if __name__ == "__main__":
    unittest.main()
