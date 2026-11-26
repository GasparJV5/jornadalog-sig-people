"""Rede de segurança SEM banco: exercita cada método dos repositórios SQL com um 'banco falso'
e confere que (1) o código Python que monta as entidades funciona e (2) o número de
placeholders %s bate com o número de parâmetros em toda consulta.
Não substitui tests/integration/test_postgres.py (que valida o SQL de verdade)."""
import unittest
from datetime import date, datetime, time

from src.domain.entities import (Alocacao, Certificacao, Descanso, Disponibilidade, Escala, Jornada,
                                 Motorista, Operador, Periodo, Turno, Veiculo)
from src.domain.entities import TipoFuncionario
from src.infrastructure import sql_repositories as sr

LINHA = {
    "id": 1, "nome": "X", "cpf": "52998224725", "status": "ATIVO", "cargo": "Motorista", "cnh_categoria": "C",
    "data_escala": date(2026, 3, 2), "hora_inicio": time(6), "hora_fim": time(14), "t_ini": time(6), "t_fim": time(14),
    "turno_id": 2, "escala_id": 3, "funcionario_id": 4, "veiculo_id": 5, "viagem_id": "V1", "alocacao_id": 6,
    "entrada_real": datetime(2026, 3, 2, 6), "saida_real": None, "placa": "ABC1D23", "modelo": "M", "marca": None,
    "ano": None, "cnh_exigida": "C", "dia_semana": 1, "vigencia_inicio": date(2026, 3, 2),
    "vigencia_fim": date(2026, 3, 2), "disponivel": True, "numero_certificado": None, "emitida_em": None,
    "validade_ate": date(2027, 1, 1), "inicio_descanso": datetime(2026, 3, 2, 14), "fim_descanso": datetime(2026, 3, 3, 2),
}


class _Cursor:
    def fetchone(self): return dict(LINHA)
    def fetchall(self): return [dict(LINHA)]


class _Conn:
    def __init__(self): self.chamadas = []
    def execute(self, sql, params=()):
        self.chamadas.append((sql, params))
        return _Cursor()


class _Db:
    def __init__(self): self.conn = _Conn()


class RepositoriosSqlComBancoFalsoTest(unittest.TestCase):
    def setUp(self):
        self.db = _Db()
        self.repos = sr.build_sql_repos(self.db)

    def tearDown(self):
        for sql, params in self.db.conn.chamadas:
            self.assertEqual(sql.count("%s"), len(params), f"placeholders x parâmetros: {sql}")

    def test_funcionarios(self):
        r = self.repos.funcionarios
        m = Motorista(nome="Ana", cpf="52998224725", cnh_categoria="C",
                      certificacoes=[Certificacao("MOPP", date(2027, 1, 1)), Certificacao("X", None, ativa=False)])
        r.add(m); r.update(m)
        self.assertEqual(m.id, "1")
        self.assertIsInstance(r.get("1"), Motorista)
        self.assertIsNone(r.get("abc"))
        self.assertTrue(r.get_by_cpf("52998224725"))
        self.assertEqual(len(r.list()), 1)
        r.list_by_tipo(TipoFuncionario.MOTORISTA); r.list_by_tipo(TipoFuncionario.OPERADOR)
        r.add(Operador(nome="Bia", cpf="11144477735"))

    def test_veiculos_e_turnos(self):
        v = Veiculo("ABC1D23", "C", ["MOPP", "NR-11"])
        self.repos.veiculos.add(v)
        self.assertEqual(self.repos.veiculos.get("1").placa, "ABC1D23")
        self.repos.veiculos.get_by_placa("ABC1D23"); self.repos.veiculos.list()
        t = Turno("Manhã", time(6), time(14)); self.repos.turnos.add(t)
        self.assertEqual(self.repos.turnos.get("1").nome, "X")
        self.repos.turnos.get_by_nome("x"); self.repos.turnos.list()

    def test_escalas(self):
        r = self.repos.escalas
        r.add(Escala(date(2026, 3, 2), "2"))
        self.assertEqual(r.get("1").alocacoes_ids, ["1"])
        r.get_by_data_turno(date(2026, 3, 2), "2"); self.assertIsNone(r.get_by_data_turno(date(2026, 3, 2), "x")); r.list()

    def test_disponibilidades(self):
        r = self.repos.disponibilidades
        d = Disponibilidade("4", Periodo(datetime(2026, 3, 1), datetime(2026, 3, 3, 12)))
        r.add(d)
        inserts = [c for c in self.db.conn.chamadas if c[0].startswith("INSERT INTO disponibilidades")]
        self.assertEqual(len(inserts), 3)                       # uma linha por dia
        r.list_by_funcionario("4"); r.janelas_para("4", Periodo(datetime(2026, 3, 2, 6), datetime(2026, 3, 2, 14)))
        self.assertEqual(r.list_by_funcionario("x"), [])
        r.get("1"); r.list()

    def test_descansos_alocacoes_jornadas(self):
        self.repos.descansos.add(Descanso("4", Periodo(datetime(2026, 3, 2, 14), datetime(2026, 3, 3, 2))))
        self.repos.descansos.list_by_funcionario("4"); self.repos.descansos.get("1"); self.repos.descansos.list()

        a = Alocacao("4", "5", Periodo(datetime(2026, 3, 2, 6), datetime(2026, 3, 2, 14)), escala_id="3")
        self.repos.alocacoes.add(a)
        got = self.repos.alocacoes.get("1")
        self.assertEqual((got.periodo.inicio, got.periodo.fim), (datetime(2026, 3, 2, 6), datetime(2026, 3, 2, 14)))
        for fn in (self.repos.alocacoes.list_by_funcionario, self.repos.alocacoes.list_by_veiculo,
                   self.repos.alocacoes.list_by_escala):
            self.assertEqual(len(fn("1")), 1); self.assertEqual(fn("x"), [])
        self.repos.alocacoes.list()

        j = Jornada("4", datetime(2026, 3, 2, 6), alocacao_id="1")
        self.repos.jornadas.add(j); j.fim = datetime(2026, 3, 2, 14); self.repos.jornadas.update(j)
        self.assertTrue(self.repos.jornadas.get("1").aberta)
        self.repos.jornadas.get_by_alocacao("1"); self.repos.jornadas.list_by_funcionario("4")
        self.repos.jornadas.get_aberta("4"); self.repos.jornadas.list()

    def test_alocacao_noturna_atravessa_meia_noite(self):
        LINHA_NOITE = dict(LINHA, hora_inicio=time(22), hora_fim=time(6))
        orig = _Cursor.fetchone
        _Cursor.fetchone = lambda self: dict(LINHA_NOITE)
        try:
            a = self.repos.alocacoes.get("1")
        finally:
            _Cursor.fetchone = orig
        self.assertEqual((a.periodo.inicio, a.periodo.fim), (datetime(2026, 3, 2, 22), datetime(2026, 3, 3, 6)))


if __name__ == "__main__":
    unittest.main()
