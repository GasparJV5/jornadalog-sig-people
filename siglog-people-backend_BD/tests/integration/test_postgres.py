"""Integração com o PostgreSQL REAL (repositórios SQL + outbox + transação por requisição).

NÃO roda por padrão. Para executar:
  1. Crie um banco SÓ para testes (ex.: RH_Jornada_test) e aplique migrations 000-003 e seeds nele:
       POSTGRES_DB=RH_Jornada_test python database/scripts/executar_migrations.py
       POSTGRES_DB=RH_Jornada_test python database/scripts/executar_seeds.py
  2. Defina POSTGRES_TEST_DB=RH_Jornada_test (e POSTGRES_PASSWORD etc. no ambiente ou no .env).
  3. python -m unittest tests.integration.test_postgres -v

Os dados criados ficam no banco de teste (valores únicos por execução evitam colisões).
"""
import os
import random
import unittest
import uuid

TEST_DB = os.getenv("POSTGRES_TEST_DB")


def gerar_cpf() -> str:
    n = [random.randint(0, 9) for _ in range(9)]
    for tam in (9, 10):
        soma = sum(n[j] * (tam + 1 - j) for j in range(tam))
        n.append((soma * 10 % 11) % 10)
    return "".join(map(str, n))


@unittest.skipUnless(TEST_DB, "defina POSTGRES_TEST_DB para rodar os testes com PostgreSQL")
class PostgresIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if TEST_DB == "RH_Jornada":
            raise RuntimeError("Use um banco de teste separado, nunca o RH_Jornada de desenvolvimento.")
        os.environ["POSTGRES_DB"] = TEST_DB
        from src.api.app import create_app
        from src.config.container import build_container
        from src.config.settings import Settings
        cls.make_app = staticmethod(lambda: create_app(build_container(Settings(persistence="postgres"))))
        cls.client = cls.make_app().test_client()

    def post(self, url, body):
        return self.client.post(url, json=body)

    def outbox(self, tipo):
        from psycopg import connect
        from psycopg.rows import dict_row
        from src.config.settings import Settings
        with connect(**Settings(persistence="postgres").postgres_kwargs(), row_factory=dict_row) as c:
            return c.execute("SELECT * FROM outbox_eventos WHERE tipo_evento = %s ORDER BY id", (tipo,)).fetchall()

    def cenario(self):
        sufixo = uuid.uuid4().hex[:6].upper()
        m = self.post("/drivers", {"nome": "Teste DB", "cpf": gerar_cpf(), "cnh_categoria": "C"})
        self.assertEqual(m.status_code, 201, m.get_json())
        m = m.get_json()
        self.assertEqual(self.post(f"/drivers/{m['id']}/certifications",
                                   {"tipo": "MOPP", "validade": "2099-01-01"}).status_code, 201)
        self.assertEqual(self.post(f"/drivers/{m['id']}/availability",
                                   {"inicio": "2031-03-01T00:00:00", "fim": "2031-03-05T23:00:00"}).status_code, 201)
        v = self.post("/vehicles", {"placa": f"T{sufixo}", "cnh_exigida": "C",
                                    "certificacoes_exigidas": ["MOPP"]}).get_json()
        t = self.post("/shifts", {"nome": f"Turno {sufixo}", "inicio": "06:00", "fim": "14:00"}).get_json()
        e = self.post("/schedules", {"data": "2031-03-02", "turno_id": t["id"]}).get_json()
        return m, v, t, e

    def test_fluxo_persiste_grava_outbox_e_sobrevive_a_novo_app(self):
        m, v, t, e = self.cenario()
        r = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"],
                                       "escala_id": e["id"], "viagem_id": "V-DB"})
        self.assertEqual(r.status_code, 201, r.get_json())
        aloc = r.get_json()
        self.assertEqual((aloc["inicio"], aloc["fim"]), ("2031-03-02T06:00:00", "2031-03-02T14:00:00"))

        escalados = [x for x in self.outbox("MotoristaEscalado") if x["payload"]["payload"]["alocacao_id"] == aloc["id"]]
        self.assertEqual(len(escalados), 1)
        self.assertEqual(escalados[0]["status"], "PENDENTE")
        self.assertEqual(escalados[0]["agregado_id"], int(aloc["id"]))

        # "reinício": um app novo (nova conexão) enxerga o que foi gravado
        novo = self.make_app().test_client()
        self.assertEqual(novo.get(f"/drivers/{m['id']}").get_json()["certificacoes"][0]["tipo"], "MOPP")
        esc = novo.get(f"/schedules/{e['id']}").get_json()
        self.assertEqual(esc["alocacoes_ids"], [aloc["id"]])
        disp = novo.get(f"/drivers/{m['id']}/availability").get_json()
        self.assertEqual(len(disp), 1)
        self.assertEqual((disp[0]["inicio"], disp[0]["fim"]), ("2031-03-01T00:00:00", "2031-03-05T23:00:00"))

    def test_negacao_422_nao_grava_alocacao_mas_conflito_vai_para_outbox(self):
        m, v, t, e = self.cenario()
        corpo = {"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": e["id"]}
        self.assertEqual(self.post("/allocations", corpo).status_code, 201)
        antes = len(self.outbox("ConflitoDeJornadaDetectado"))
        r = self.post("/allocations", {**corpo, "inicio": "2031-03-02T10:00:00", "fim": "2031-03-02T12:00:00"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(len(self.outbox("ConflitoDeJornadaDetectado")), antes + 1)
        esc = self.client.get(f"/schedules/{e['id']}").get_json()
        self.assertEqual(len(esc["alocacoes_ids"]), 1)

    def test_erro_de_validacao_faz_rollback(self):
        m, v, t, e = self.cenario()
        r = self.post("/vehicles", {"placa": v["placa"]})
        self.assertEqual(r.status_code, 409)

    def test_jornada_e_descanso_no_banco(self):
        m, v, t, e = self.cenario()
        a = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": e["id"]}).get_json()
        j = self.post("/journeys/start", {"motorista_id": m["id"], "alocacao_id": a["id"], "inicio": "2031-03-02T06:00:00"})
        self.assertEqual(j.status_code, 201, j.get_json())
        f = self.post(f"/journeys/{j.get_json()['id']}/finish", {"fim": "2031-03-02T14:00:00"})
        self.assertEqual(f.get_json()["fim"], "2031-03-02T14:00:00")
        d = self.post("/rest-periods", {"motorista_id": m["id"], "inicio": "2031-03-02T14:00:00", "fim": "2031-03-03T02:00:00"})
        self.assertEqual(d.status_code, 201, d.get_json())

    def test_turno_noturno_atravessa_a_meia_noite(self):
        m, v, _, _ = self.cenario()
        sufixo = uuid.uuid4().hex[:6]
        t = self.post("/shifts", {"nome": f"Noite {sufixo}", "inicio": "22:00", "fim": "06:00"}).get_json()
        e = self.post("/schedules", {"data": "2031-03-03", "turno_id": t["id"]}).get_json()
        r = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": e["id"]})
        self.assertEqual(r.status_code, 201, r.get_json())
        self.assertEqual((r.get_json()["inicio"], r.get_json()["fim"]), ("2031-03-03T22:00:00", "2031-03-04T06:00:00"))


if __name__ == "__main__":
    unittest.main()
