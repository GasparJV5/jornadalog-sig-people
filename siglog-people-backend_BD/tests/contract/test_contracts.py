"""Testes de contrato.

1. Evento MotoristaEscalado (produtor RH → consumidor Fleet): campos obrigatórios e tipos.
2. Respostas da API: formato estável dos principais endpoints e do envelope de erro.
Se o Fleet publicar um contrato diferente, ajuste CONTRATO_MOTORISTA_ESCALADO e alinhe as equipes.
"""
import unittest
from datetime import datetime

from src.api.app import create_app
from src.domain import events as ev
from tests.factories import CPF_OK, novo_container

CONTRATO_MOTORISTA_ESCALADO = {
    "alocacao_id": str, "motorista_id": str, "veiculo_id": str,
    "inicio": str, "fim": str, "escala_id": (str, type(None)), "viagem_id": (str, type(None)),
}
CONTRATO_ENVELOPE = {"event_id": str, "event": str, "occurred_at": str, "payload": dict}


def conforme(test, obj: dict, contrato: dict):
    test.assertEqual(set(obj), set(contrato), "conjunto de campos difere do contrato")
    for campo, tipo in contrato.items():
        test.assertIsInstance(obj[campo], tipo, f"campo {campo} com tipo inesperado")


class EventoMotoristaEscaladoTest(unittest.TestCase):
    def test_payload_respeita_contrato_com_fleet(self):
        c = novo_container(); client = create_app(c).test_client()
        m = client.post("/drivers", json={"nome": "Ana", "cpf": CPF_OK, "cnh_categoria": "C"}).get_json()
        client.post(f"/drivers/{m['id']}/availability", json={"inicio": "2026-03-01T00:00:00", "fim": "2026-03-05T00:00:00"})
        v = client.post("/vehicles", json={"placa": "ABC1D23"}).get_json()
        t = client.post("/shifts", json={"nome": "Manhã", "inicio": "06:00", "fim": "14:00"}).get_json()
        esc = client.post("/schedules", json={"data": "2026-03-02", "turno_id": t["id"]}).get_json()
        client.post("/allocations", json={"motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": esc["id"]})
        e = c.publisher.of(ev.MOTORISTA_ESCALADO)[0]
        conforme(self, e.to_dict(), CONTRATO_ENVELOPE)
        conforme(self, e.payload, CONTRATO_MOTORISTA_ESCALADO)
        datetime.fromisoformat(e.payload["inicio"]); datetime.fromisoformat(e.payload["fim"])

    def test_nomes_do_catalogo_de_eventos(self):
        self.assertEqual(
            {ev.MOTORISTA_ESCALADO, ev.JORNADA_INICIADA, ev.JORNADA_FINALIZADA,
             ev.DESCANSO_REGISTRADO, ev.CERTIFICACAO_ATUALIZADA, ev.CONFLITO_DE_JORNADA_DETECTADO},
            {"MotoristaEscalado", "JornadaIniciada", "JornadaFinalizada",
             "DescansoRegistrado", "CertificacaoAtualizada", "ConflitoDeJornadaDetectado"})


class ContratoApiTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app(novo_container()).test_client()

    def test_resposta_de_motorista(self):
        r = self.client.post("/drivers", json={"nome": "Ana", "cpf": CPF_OK, "cnh_categoria": "C"})
        conforme(self, r.get_json(), {"id": str, "nome": str, "cpf": str, "tipo": str, "ativo": bool,
                                      "certificacoes": list, "cnh_categoria": str})

    def test_resposta_de_validacao(self):
        m = self.client.post("/drivers", json={"nome": "Ana", "cpf": CPF_OK, "cnh_categoria": "C"}).get_json()
        v = self.client.post("/vehicles", json={"placa": "ABC1D23"}).get_json()
        t = self.client.post("/shifts", json={"nome": "Manhã", "inicio": "06:00", "fim": "14:00"}).get_json()
        esc = self.client.post("/schedules", json={"data": "2026-03-02", "turno_id": t["id"]}).get_json()
        r = self.client.post("/allocations/validate", json={
            "motorista_id": m["id"], "veiculo_id": v["id"], "escala_id": esc["id"]}).get_json()
        conforme(self, r, {"permitido": bool, "violacoes": list})
        conforme(self, r["violacoes"][0], {"codigo": str, "mensagem": str})

    def test_envelope_de_erro(self):
        err = self.client.get("/drivers/x").get_json()
        self.assertEqual(set(err), {"error"})
        conforme(self, err["error"], {"code": str, "message": str})


if __name__ == "__main__":
    unittest.main()
