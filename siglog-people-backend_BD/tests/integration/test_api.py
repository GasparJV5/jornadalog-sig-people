"""Integração API (Flask test client) + casos de uso + repositórios + publisher."""
import unittest
from datetime import date

from src.api.app import create_app
from src.domain import events as ev
from tests.factories import CPF_OK, novo_container


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.container = novo_container()
        self.client = create_app(self.container).test_client()

    def post(self, url, body): return self.client.post(url, json=body)

    def escala(self, dia, ini="06:00", fim="14:00"):
        """Cria (ou reaproveita) turno e escala para o dia 'dia' de março/2026."""
        nome = f"T{ini}-{fim}"
        t = next((x for x in self.container.repos.turnos.list() if x.nome == nome), None)
        tid = t.id if t else self.post("/shifts", {"nome": nome, "inicio": ini, "fim": fim}).get_json()["id"]
        r = self.post("/schedules", {"data": f"2026-03-{dia:02d}", "turno_id": tid})
        return r.get_json()["id"] if r.status_code == 201 else \
            self.container.repos.escalas.get_by_data_turno(date(2026, 3, dia), tid).id

    def seed(self):
        m = self.post("/drivers", {"nome": "Ana", "cpf": CPF_OK, "cnh_categoria": "C"}).get_json()
        self.post(f"/drivers/{m['id']}/certifications", {"tipo": "MOPP", "validade": "2027-01-01"})
        self.post(f"/drivers/{m['id']}/availability",
                  {"inicio": "2026-03-01T00:00:00", "fim": "2026-03-05T23:00:00"})
        v = self.post("/vehicles", {"placa": "abc1d23", "cnh_exigida": "C",
                                    "certificacoes_exigidas": ["mopp"]}).get_json()
        return m, v


class FluxoCompletoTest(ApiTestCase):
    def test_fluxo_feliz_ate_motorista_escalado(self):
        m, v = self.seed()
        t = self.post("/shifts", {"nome": "Manhã", "inicio": "06:00", "fim": "14:00"})
        self.assertEqual(t.status_code, 201)
        esc = self.post("/schedules", {"data": "2026-03-02", "turno_id": t.get_json()["id"]}).get_json()

        payload = {"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": esc["id"]}
        val = self.post("/allocations/validate", payload)
        self.assertEqual((val.status_code, val.get_json()["permitido"]), (200, True))

        r = self.post("/allocations", {**payload, "viagem_id": "V-1"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["viagem_id"], "V-1")

        got = self.client.get(f"/schedules/{esc['id']}").get_json()
        self.assertEqual(len(got["alocacoes"]), 1)
        self.assertEqual(got["alocacoes_ids"], [r.get_json()["id"]])
        self.assertEqual(got["turno"]["inicio"], "06:00")
        self.assertEqual(self.client.get(f"/schedules/{esc['id']}/conflicts").get_json()["conflitos"], [])
        self.assertEqual(len(self.container.publisher.of(ev.MOTORISTA_ESCALADO)), 1)

    def test_listagem_e_detalhe_de_motoristas(self):
        m, _ = self.seed()
        self.assertEqual(len(self.client.get("/drivers").get_json()), 1)
        self.assertEqual(self.client.get(f"/drivers/{m['id']}").get_json()["cnh_categoria"], "C")
        av = self.client.get(f"/drivers/{m['id']}/availability").get_json()
        self.assertEqual(len(av), 1)

    def test_validate_retorna_200_com_violacoes_e_allocations_retorna_422(self):
        m, v = self.seed()
        body = {"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": self.escala(20)}
        val = self.post("/allocations/validate", body)
        self.assertEqual(val.status_code, 200)
        self.assertFalse(val.get_json()["permitido"])
        r = self.post("/allocations", body)
        self.assertEqual(r.status_code, 422)
        err = r.get_json()["error"]
        self.assertEqual(err["code"], "REGRA_DE_NEGOCIO")
        self.assertEqual(err["violacoes"][0]["codigo"], "MOTORISTA_INDISPONIVEL")

    def test_conflito_gera_evento_e_422(self):
        m, v = self.seed()
        b = {"motorista_id": m["id"], "veiculo_id": v["id"]}
        self.assertEqual(self.post("/allocations", {**b, "escala_id": self.escala(2)}).status_code, 201)
        r = self.post("/allocations", {**b, "escala_id": self.escala(2, "10:00", "16:00")})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(len(self.container.publisher.of(ev.CONFLITO_DE_JORNADA_DETECTADO)), 1)

    def test_timezone_e_normalizado_para_utc(self):
        m, v = self.seed()
        r = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"],
                                       "escala_id": self.escala(2),
                                       "inicio": "2026-03-02T08:00:00Z", "fim": "2026-03-02T12:00:00-00:00"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["inicio"], "2026-03-02T08:00:00")

    def test_jornada_e_descanso_via_api(self):
        m, v = self.seed()
        a = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": self.escala(2)}).get_json()
        j = self.post("/journeys/start", {"motorista_id": m["id"], "alocacao_id": a["id"], "inicio": "2026-03-02T06:00:00"})
        self.assertEqual(j.status_code, 201)
        self.assertEqual(j.get_json()["alocacao_id"], a["id"])
        self.assertEqual(self.post("/journeys/start", {"motorista_id": m["id"], "alocacao_id": a["id"], "inicio": "2026-03-02T07:00:00"}).status_code, 409)
        f = self.post(f"/journeys/{j.get_json()['id']}/finish", {"fim": "2026-03-02T14:00:00"})
        self.assertEqual(f.status_code, 200)
        self.assertEqual(self.post("/rest-periods", {"motorista_id": m["id"], "inicio": "2026-03-02T14:00:00", "fim": "2026-03-02T20:00:00"}).status_code, 422)
        self.assertEqual(self.post("/rest-periods", {"motorista_id": m["id"], "inicio": "2026-03-02T14:00:00", "fim": "2026-03-03T02:00:00"}).status_code, 201)
        jv = self.post("/journeys/validate", {"motorista_id": m["id"], "inicio": "2026-03-04T06:00:00", "fim": "2026-03-04T20:00:00"})
        self.assertFalse(jv.get_json()["permitido"])

    def test_jornada_exige_alocacao(self):
        m, _ = self.seed()
        r = self.post("/journeys/start", {"motorista_id": m["id"], "inicio": "2026-03-02T06:00:00"})
        self.assertEqual(r.status_code, 400)
        r = self.post("/journeys/start", {"motorista_id": m["id"], "alocacao_id": "nope", "inicio": "2026-03-02T06:00:00"})
        self.assertEqual(r.status_code, 404)

    def test_veiculo_com_campos_opcionais_e_placa_unica(self):
        r = self.post("/vehicles", {"placa": "xyz1a23", "modelo": "FH 540", "marca": "Volvo", "ano": 2022})
        self.assertEqual((r.status_code, r.get_json()["modelo"], r.get_json()["placa"]), (201, "FH 540", "XYZ1A23"))
        self.assertEqual(self.post("/vehicles", {"placa": "XYZ1A23"}).status_code, 409)


class ErrosTest(ApiTestCase):
    def test_health(self):
        self.assertEqual(self.client.get("/health").get_json()["status"], "ok")

    def test_400_campos_ausentes_e_formatos(self):
        self.assertEqual(self.post("/drivers", {"nome": "x"}).status_code, 400)
        self.assertEqual(self.post("/drivers", {"nome": "x", "cpf": "000"}).status_code, 400)
        self.assertEqual(self.post("/shifts", {"nome": "x", "inicio": "25:99", "fim": "10:00"}).status_code, 400)
        self.assertEqual(self.post("/schedules", {"data": "02/03/2026", "turno_id": "t"}).status_code, 400)
        r = self.client.post("/drivers", data="não é json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_404_e_405(self):
        self.assertEqual(self.client.get("/drivers/nope").status_code, 404)
        self.assertEqual(self.client.get("/schedules/nope").status_code, 404)
        self.assertEqual(self.client.get("/rota-inexistente").status_code, 404)
        self.assertEqual(self.client.delete("/drivers").status_code, 405)
        self.assertEqual(self.client.get("/rota-inexistente").get_json()["error"]["code"], "NOT_FOUND")

    def test_409_cpf_duplicado(self):
        self.post("/drivers", {"nome": "A", "cpf": CPF_OK, "cnh_categoria": "C"})
        r = self.post("/drivers", {"nome": "B", "cpf": CPF_OK, "cnh_categoria": "C"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "CONFLICT"))

    def test_409_turno_com_nome_repetido(self):
        self.post("/shifts", {"nome": "Manhã", "inicio": "06:00", "fim": "14:00"})
        self.assertEqual(self.post("/shifts", {"nome": "manhã", "inicio": "07:00", "fim": "15:00"}).status_code, 409)

    def test_alocacao_exige_escala(self):
        m, v = self.seed()
        r = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"]})
        self.assertEqual(r.status_code, 400)
        r = self.post("/allocations", {"motorista_id": m["id"], "veiculo_id": v["id"],
                                       "inicio": "2026-03-02T06:00:00", "fim": "2026-03-02T14:00:00"})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
