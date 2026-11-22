"""Garante que openapi.yaml e a API Flask não divergem.

1. Toda rota Flask está na spec (e vice-versa), com os mesmos métodos.
2. Todo $ref resolve.
3. Respostas reais da API são válidas contra os schemas declarados.
"""
import re
import unittest
from pathlib import Path

import yaml

from src.api.app import create_app
from tests.factories import CPF_OK, novo_container

SPEC = yaml.safe_load((Path(__file__).resolve().parents[2] / "openapi.yaml").read_text(encoding="utf-8"))
METODOS = {"get", "post", "put", "patch", "delete"}


def resolve(ref):
    node = SPEC
    for parte in ref.lstrip("#/").split("/"):
        node = node[parte]
    return node


def valida(valor, schema, caminho="$"):
    """Validador mínimo: type, nullable, enum, required, properties, items, allOf, $ref."""
    if "$ref" in schema:
        return valida(valor, resolve(schema["$ref"]), caminho)
    erros = []
    for sub in schema.get("allOf", []):
        erros += valida(valor, sub, caminho)
    if valor is None:
        return erros if schema.get("nullable") else erros + [f"{caminho}: null não permitido"]
    tipos = {"string": str, "boolean": bool, "array": list, "object": dict,
             "integer": int, "number": (int, float)}
    t = schema.get("type")
    if t and not isinstance(valor, tipos[t]):
        return erros + [f"{caminho}: esperado {t}, veio {type(valor).__name__}"]
    if "enum" in schema and valor not in schema["enum"]:
        erros.append(f"{caminho}: {valor!r} fora do enum")
    if t == "object":
        for r in schema.get("required", []):
            if r not in valor:
                erros.append(f"{caminho}: campo obrigatório ausente '{r}'")
        for k, v in valor.items():
            if k in schema.get("properties", {}):
                erros += valida(v, schema["properties"][k], f"{caminho}.{k}")
    if t == "array":
        for i, item in enumerate(valor):
            erros += valida(item, schema["items"], f"{caminho}[{i}]")
    return erros


class RotasTest(unittest.TestCase):
    def test_rotas_flask_e_spec_coincidem(self):
        app = create_app(novo_container())
        flask_ops = set()
        for rule in app.url_map.iter_rules():
            if rule.endpoint == "static":
                continue
            caminho = re.sub(r"<(?:[^:>]+:)?([^>]+)>", r"{\1}", rule.rule)
            for m in rule.methods & {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                flask_ops.add((m.lower(), caminho))
        spec_ops = {(m, p) for p, item in SPEC["paths"].items() for m in item if m in METODOS}
        self.assertEqual(flask_ops - spec_ops, set(), "rotas no código sem documentação")
        self.assertEqual(spec_ops - flask_ops, set(), "rotas documentadas que não existem")

    def test_todos_os_refs_resolvem(self):
        refs = []
        def varre(n):
            if isinstance(n, dict):
                for k, v in n.items():
                    if k == "$ref": refs.append(v)
                    else: varre(v)
            elif isinstance(n, list):
                for i in n: varre(i)
        varre(SPEC)
        self.assertTrue(refs)
        for r in refs:
            resolve(r)   # KeyError se quebrado

    def test_operation_ids_unicos(self):
        ids = [op["operationId"] for item in SPEC["paths"].values()
               for m, op in item.items() if m in METODOS]
        self.assertEqual(len(ids), len(set(ids)))


class RespostasConformesTest(unittest.TestCase):
    def setUp(self):
        self.client = create_app(novo_container()).test_client()

    def checa(self, resp, caminho, metodo):
        status = str(resp.status_code)
        decl = SPEC["paths"][caminho][metodo]["responses"]
        self.assertIn(status, decl, f"{metodo.upper()} {caminho} devolveu {status} não documentado")
        r = decl[status]
        if "$ref" in r:
            r = resolve(r["$ref"])
        schema = r["content"]["application/json"]["schema"]
        erros = valida(resp.get_json(), schema)
        self.assertEqual(erros, [], f"{metodo.upper()} {caminho} {status}: {erros}")

    def test_fluxo_completo_conforme_a_spec(self):
        c = self.client
        r = c.get("/health"); self.checa(r, "/health", "get")
        r = c.post("/drivers", json={"nome": "Ana", "cpf": CPF_OK, "cnh_categoria": "C"}); self.checa(r, "/drivers", "post")
        mid = r.get_json()["id"]
        self.checa(c.get("/drivers"), "/drivers", "get")
        self.checa(c.get(f"/drivers/{mid}"), "/drivers/{id}", "get")
        self.checa(c.get("/drivers/nope"), "/drivers/{id}", "get")
        self.checa(c.post(f"/drivers/{mid}/certifications", json={"tipo": "MOPP", "validade": "2027-01-01"}),
                   "/drivers/{id}/certifications", "post")
        self.checa(c.post(f"/drivers/{mid}/availability", json={"inicio": "2026-03-01T00:00:00", "fim": "2026-03-05T23:00:00"}),
                   "/drivers/{id}/availability", "post")
        self.checa(c.get(f"/drivers/{mid}/availability"), "/drivers/{id}/availability", "get")
        r = c.post("/vehicles", json={"placa": "ABC1D23", "certificacoes_exigidas": ["MOPP"]}); self.checa(r, "/vehicles", "post")
        vid = r.get_json()["id"]
        r = c.post("/shifts", json={"nome": "Manhã", "inicio": "06:00", "fim": "14:00"}); self.checa(r, "/shifts", "post")
        r = c.post("/schedules", json={"data": "2026-03-02", "turno_id": r.get_json()["id"]}); self.checa(r, "/schedules", "post")
        eid = r.get_json()["id"]
        self.checa(c.post("/schedules", json={"data": "2026-03-02", "turno_id": "x"}), "/schedules", "post")

        corpo = {"motorista_id": mid, "veiculo_id": vid, "escala_id": eid}
        self.checa(c.post("/allocations/validate", json=corpo), "/allocations/validate", "post")
        self.checa(c.post("/allocations", json=corpo), "/allocations", "post")
        self.checa(c.post("/allocations", json=corpo), "/allocations", "post")        # 422: conflito
        self.checa(c.get(f"/schedules/{eid}"), "/schedules/{id}", "get")
        self.checa(c.get(f"/schedules/{eid}/conflicts"), "/schedules/{id}/conflicts", "get")

        r = c.post("/journeys/start", json={"motorista_id": mid, "inicio": "2026-03-04T06:00:00"}); self.checa(r, "/journeys/start", "post")
        self.checa(c.post("/journeys/start", json={"motorista_id": mid, "inicio": "2026-03-04T07:00:00"}), "/journeys/start", "post")  # 409
        self.checa(c.post(f"/journeys/{r.get_json()['id']}/finish", json={"fim": "2026-03-04T14:00:00"}), "/journeys/{id}/finish", "post")
        self.checa(c.post("/journeys/validate", json={"motorista_id": mid, "inicio": "2026-03-05T06:00:00", "fim": "2026-03-05T20:00:00"}), "/journeys/validate", "post")
        self.checa(c.post("/rest-periods/validate", json={"motorista_id": mid, "inicio": "2026-03-04T14:00:00", "fim": "2026-03-04T20:00:00"}), "/rest-periods/validate", "post")
        self.checa(c.post("/rest-periods", json={"motorista_id": mid, "inicio": "2026-03-04T14:00:00", "fim": "2026-03-04T20:00:00"}), "/rest-periods", "post")  # 422
        self.checa(c.post("/rest-periods", json={"motorista_id": mid, "inicio": "2026-03-04T14:00:00", "fim": "2026-03-05T02:00:00"}), "/rest-periods", "post")  # 201


if __name__ == "__main__":
    unittest.main()
