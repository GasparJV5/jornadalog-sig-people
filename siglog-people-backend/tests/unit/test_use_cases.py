import unittest
from datetime import date, time

from src.application.use_cases import AlocacaoNegada
from src.domain import events as ev
from src.domain import rules as R
from src.domain.entities import Periodo
from src.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError
from tests.factories import CPF_OK, CPF_OK_2, cenario_basico, dt, novo_container


class CadastroTest(unittest.TestCase):
    def setUp(self): self.c = novo_container()

    def test_uc01_cadastra_motorista(self):
        m = self.c.cadastrar_funcionario.execute("Ana", CPF_OK, "motorista", "c")
        self.assertEqual(m.cpf, "52998224725"); self.assertEqual(m.cnh_categoria, "C")

    def test_uc01_operador_nao_exige_cnh(self):
        o = self.c.cadastrar_funcionario.execute("Bia", CPF_OK, "OPERADOR")
        self.assertEqual(o.tipo.value, "OPERADOR")

    def test_uc01_validacoes(self):
        ex = self.c.cadastrar_funcionario.execute
        with self.assertRaises(ValidationError): ex("", CPF_OK, "MOTORISTA", "C")
        with self.assertRaises(ValidationError): ex("A", "123", "MOTORISTA", "C")
        with self.assertRaises(ValidationError): ex("A", CPF_OK, "GERENTE")
        with self.assertRaises(ValidationError): ex("A", CPF_OK, "MOTORISTA")          # sem CNH
        ex("A", CPF_OK, "MOTORISTA", "C")
        with self.assertRaises(ConflictError): ex("B", "529.982.247-25", "MOTORISTA", "C")  # CPF duplicado

    def test_uc02_registra_e_atualiza_certificacao_publica_evento(self):
        m, _ = cenario_basico(self.c)
        self.c.registrar_certificacao.execute(m.id, "mopp", date(2028, 1, 1))
        self.assertEqual(len(m.certificacoes), 1)                       # atualizou, não duplicou
        self.assertEqual(m.certificacao("MOPP").validade, date(2028, 1, 1))
        self.assertEqual(len(self.c.publisher.of(ev.CERTIFICACAO_ATUALIZADA)), 2)

    def test_uc02_datas_incoerentes(self):
        m, _ = cenario_basico(self.c)
        with self.assertRaises(ValidationError):
            self.c.registrar_certificacao.execute(m.id, "NR-11", date(2025, 1, 1), date(2026, 1, 1))
        with self.assertRaises(NotFoundError):
            self.c.registrar_certificacao.execute("x", "NR-11", date(2030, 1, 1))

    def test_uc03_disponibilidade_ordenada_e_validada(self):
        m = self.c.cadastrar_funcionario.execute("Ana", CPF_OK, "MOTORISTA", "C")
        self.c.registrar_disponibilidade.execute(m.id, dt(3, 0), dt(4, 0))
        self.c.registrar_disponibilidade.execute(m.id, dt(1, 0), dt(2, 0))
        lista = self.c.consultar_disponibilidade.execute(m.id)
        self.assertEqual([d.periodo.inicio.day for d in lista], [1, 3])
        with self.assertRaises(ValidationError):
            self.c.registrar_disponibilidade.execute(m.id, dt(2, 0), dt(1, 0))


class TurnoEscalaTest(unittest.TestCase):
    def setUp(self): self.c = novo_container()

    def test_uc04_turno(self):
        t = self.c.criar_turno.execute("Manhã", time(6), time(14))
        self.assertEqual(t.nome, "Manhã")
        with self.assertRaises(ValidationError): self.c.criar_turno.execute("X", time(6), time(6))
        with self.assertRaises(ValidationError): self.c.criar_turno.execute("Longo", time(6), time(20))

    def test_uc05_escala_unica_por_data_e_turno(self):
        t = self.c.criar_turno.execute("Manhã", time(6), time(14))
        self.c.criar_escala.execute(date(2026, 3, 2), t.id)
        with self.assertRaises(ConflictError): self.c.criar_escala.execute(date(2026, 3, 2), t.id)
        with self.assertRaises(NotFoundError): self.c.criar_escala.execute(date(2026, 3, 2), "nope")


class JornadaDescansoTest(unittest.TestCase):
    def setUp(self):
        self.c = novo_container()
        self.m, _ = cenario_basico(self.c)

    def test_uc06_validar_jornada(self):
        self.assertTrue(self.c.validar_jornada.execute(self.m.id, dt(2, 6), dt(2, 16)).permitido)
        res = self.c.validar_jornada.execute(self.m.id, dt(2, 6), dt(2, 20))
        self.assertEqual(res.violacoes[0].codigo, R.JORNADA_EXCEDIDA)

    def test_ciclo_de_jornada_publica_eventos(self):
        j = self.c.iniciar_jornada.execute(self.m.id, dt(2, 6))
        with self.assertRaises(ConflictError): self.c.iniciar_jornada.execute(self.m.id, dt(2, 7))
        self.c.finalizar_jornada.execute(j.id, dt(2, 18))
        fim = self.c.publisher.of(ev.JORNADA_FINALIZADA)[0].payload
        self.assertEqual(fim["horas"], 12); self.assertTrue(fim["excedeu_limite"])
        with self.assertRaises(ConflictError): self.c.finalizar_jornada.execute(j.id, dt(2, 19))

    def test_nao_inicia_jornada_sem_descanso(self):
        j = self.c.iniciar_jornada.execute(self.m.id, dt(2, 6))
        self.c.finalizar_jornada.execute(j.id, dt(2, 14))
        with self.assertRaises(AlocacaoNegada): self.c.iniciar_jornada.execute(self.m.id, dt(2, 20))
        self.c.iniciar_jornada.execute(self.m.id, dt(3, 1))     # 11h depois → ok

    def test_uc07_descanso(self):
        self.assertFalse(self.c.validar_descanso.execute(self.m.id, dt(2, 0), dt(2, 8)).permitido)
        d = self.c.registrar_descanso.execute(self.m.id, dt(2, 0), dt(2, 11))
        self.assertEqual(d.periodo.horas, 11)
        self.assertEqual(len(self.c.publisher.of(ev.DESCANSO_REGISTRADO)), 1)
        with self.assertRaises(AlocacaoNegada): self.c.registrar_descanso.execute(self.m.id, dt(2, 0), dt(2, 8))

    def test_uc07_descanso_nao_pode_sobrepor_trabalho(self):
        _, v = self.m, self.c.repos.veiculos.list()[0]
        self.c.alocar_motorista.execute(self.m.id, v.id, dt(2, 6), dt(2, 14))
        res = self.c.validar_descanso.execute(self.m.id, dt(1, 20), dt(2, 8))
        self.assertIn("DESCANSO_SOBREPOE_TRABALHO", {x.codigo for x in res.violacoes})


class AlocacaoTest(unittest.TestCase):
    def setUp(self):
        self.c = novo_container()
        self.m, self.v = cenario_basico(self.c)

    def test_uc08_aloca_e_publica_motorista_escalado(self):
        a = self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(2, 6), dt(2, 14), viagem_id="V-9")
        e = self.c.publisher.of(ev.MOTORISTA_ESCALADO)
        self.assertEqual(len(e), 1)
        self.assertEqual(e[0].payload["alocacao_id"], a.id)
        self.assertEqual(e[0].payload["viagem_id"], "V-9")

    def test_uc08_aloca_via_escala_usa_periodo_do_turno(self):
        t = self.c.criar_turno.execute("Manhã", time(6), time(14))
        esc = self.c.criar_escala.execute(date(2026, 3, 2), t.id)
        a = self.c.alocar_motorista.execute(self.m.id, self.v.id, escala_id=esc.id)
        self.assertEqual((a.periodo.inicio, a.periodo.fim), (dt(2, 6), dt(2, 14)))
        self.assertEqual(self.c.consultar_escala.execute(esc.id)["alocacoes"][0].id, a.id)   # UC10

    def test_uc08_nega_indisponivel_sem_publicar_escalado(self):
        with self.assertRaises(AlocacaoNegada) as cm:
            self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(10, 6), dt(10, 14))
        self.assertIn(R.MOTORISTA_INDISPONIVEL, {x.codigo for x in cm.exception.resultado.violacoes})
        self.assertEqual(self.c.publisher.of(ev.MOTORISTA_ESCALADO), [])

    def test_uc08_nega_certificacao_incompativel(self):
        v2 = self.c.cadastrar_veiculo.execute("XYZ9K88", "E", ["MOPP"])
        with self.assertRaises(AlocacaoNegada) as cm:
            self.c.alocar_motorista.execute(self.m.id, v2.id, dt(2, 6), dt(2, 14))
        self.assertEqual({x.codigo for x in cm.exception.resultado.violacoes}, {R.CNH_INCOMPATIVEL})

    def test_uc08_nega_descanso_insuficiente(self):
        self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(2, 6), dt(2, 14))
        v2 = self.c.cadastrar_veiculo.execute("DEF4G56", "C", ["MOPP"])
        with self.assertRaises(AlocacaoNegada) as cm:
            self.c.alocar_motorista.execute(self.m.id, v2.id, dt(2, 20), dt(3, 4))
        self.assertEqual({x.codigo for x in cm.exception.resultado.violacoes}, {R.DESCANSO_INSUFICIENTE})

    def test_uc09_conflito_publica_evento(self):
        self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(2, 6), dt(2, 14))
        with self.assertRaises(AlocacaoNegada):
            self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(2, 10), dt(2, 16))
        ev_c = self.c.publisher.of(ev.CONFLITO_DE_JORNADA_DETECTADO)
        self.assertEqual(len(ev_c), 1)
        self.assertEqual({x["codigo"] for x in ev_c[0].payload["conflitos"]},
                         {R.CONFLITO_MOTORISTA, R.CONFLITO_VEICULO})

    def test_uc09_detectar_conflito_direto(self):
        self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(2, 6), dt(2, 14))
        r = self.c.detectar_conflito.execute(self.m.id, self.v.id, Periodo(dt(2, 12), dt(2, 18)))
        self.assertEqual({x.codigo for x in r}, {R.CONFLITO_MOTORISTA, R.CONFLITO_VEICULO})
        self.assertEqual(self.c.detectar_conflito.execute(self.m.id, self.v.id, Periodo(dt(3, 6), dt(3, 14))), [])

    def test_uc09_escala_sem_conflitos(self):
        t = self.c.criar_turno.execute("Manhã", time(6), time(14))
        esc = self.c.criar_escala.execute(date(2026, 3, 2), t.id)
        self.c.alocar_motorista.execute(self.m.id, self.v.id, escala_id=esc.id)
        self.assertEqual(self.c.detectar_conflitos_escala.execute(esc.id), [])

    def test_validar_nao_persiste(self):
        r = self.c.validar_alocacao.execute(self.m.id, self.v.id, dt(2, 6), dt(2, 14))
        self.assertTrue(r.permitido)
        self.assertEqual(self.c.repos.alocacoes.list(), [])

    def test_operador_nao_pode_ser_alocado_como_motorista(self):
        o = self.c.cadastrar_funcionario.execute("Bia", CPF_OK_2, "OPERADOR")
        with self.assertRaises(DomainError):
            self.c.alocar_motorista.execute(o.id, self.v.id, dt(2, 6), dt(2, 14))

    def test_entradas_invalidas(self):
        with self.assertRaises(NotFoundError): self.c.alocar_motorista.execute("x", self.v.id, dt(2, 6), dt(2, 14))
        with self.assertRaises(NotFoundError): self.c.alocar_motorista.execute(self.m.id, "x", dt(2, 6), dt(2, 14))
        with self.assertRaises(ValidationError): self.c.alocar_motorista.execute(self.m.id, self.v.id)
        with self.assertRaises(ValidationError): self.c.alocar_motorista.execute(self.m.id, self.v.id, dt(2, 14), dt(2, 6))


if __name__ == "__main__":
    unittest.main()
