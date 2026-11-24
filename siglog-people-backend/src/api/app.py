"""Camada API (Flask): controllers finos que delegam aos casos de uso."""
import logging
from typing import Optional

from flask import Flask, jsonify, request

from src.api import serializers as s
from src.api.parsing import parse_date, parse_dt, parse_time, require
from src.application.use_cases import AlocacaoNegada
from src.config.container import build_container
from src.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError


def _err(code: str, message: str, status: int, **extra):
    return jsonify({"error": {"code": code, "message": message, **extra}}), status


def create_app(container: Optional[object] = None) -> Flask:
    app = Flask(__name__)
    c = container or build_container()
    app.config["container"] = c
    body = lambda: request.get_json(silent=True) or {}

    # ------------------------------------------------------------ erros
    @app.errorhandler(ValidationError)
    def _val(e): return _err("VALIDATION_ERROR", str(e), 400)

    @app.errorhandler(NotFoundError)
    def _nf(e): return _err("NOT_FOUND", str(e), 404)

    @app.errorhandler(ConflictError)
    def _cf(e): return _err("CONFLICT", str(e), 409)

    @app.errorhandler(AlocacaoNegada)
    def _neg(e):
        return _err("REGRA_DE_NEGOCIO", str(e), 422,
                    violacoes=[v.to_dict() for v in e.resultado.violacoes])

    @app.errorhandler(DomainError)
    def _dom(e): return _err("DOMAIN_ERROR", str(e), 422)

    @app.errorhandler(404)
    def _404(e): return _err("NOT_FOUND", "Rota não encontrada.", 404)

    @app.errorhandler(405)
    def _405(e): return _err("METHOD_NOT_ALLOWED", "Método não permitido.", 405)

    @app.errorhandler(Exception)
    def _500(e):
        logging.getLogger("siglog-people").exception("erro inesperado")
        return _err("INTERNAL_ERROR", "Erro interno.", 500)

    # ------------------------------------------------------------ saúde
    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "service": c.settings.service_name})

    # ------------------------------------------------------------ drivers
    @app.post("/drivers")
    def create_driver():  # UC01 (aceita também OPERADOR via campo "tipo")
        b = body(); require(b, "nome", "cpf")
        f = c.cadastrar_funcionario.execute(b["nome"], b["cpf"], b.get("tipo", "MOTORISTA"),
                                            b.get("cnh_categoria"))
        return jsonify(s.funcionario(f)), 201

    @app.get("/drivers")
    def list_drivers():
        return jsonify([s.funcionario(m) for m in c.consultar_motoristas.execute()])

    @app.get("/drivers/<id>")
    def get_driver(id):
        return jsonify(s.funcionario(c.consultar_motoristas.por_id(id)))

    @app.post("/drivers/<id>/certifications")
    def add_certification(id):  # UC02
        b = body(); require(b, "tipo", "validade")
        f = c.registrar_certificacao.execute(
            id, b["tipo"], parse_date(b["validade"], "validade"),
            parse_date(b["emitida_em"], "emitida_em") if b.get("emitida_em") else None)
        return jsonify(s.funcionario(f)), 201

    @app.get("/drivers/<id>/availability")
    def get_availability(id):
        return jsonify([s.disponibilidade(d) for d in c.consultar_disponibilidade.execute(id)])

    @app.post("/drivers/<id>/availability")
    def add_availability(id):  # UC03
        b = body(); require(b, "inicio", "fim")
        d = c.registrar_disponibilidade.execute(
            id, parse_dt(b["inicio"], "inicio"), parse_dt(b["fim"], "fim"),
            bool(b.get("disponivel", True)))
        return jsonify(s.disponibilidade(d)), 201

    # ------------------------------------------------------------ veículos (réplica local)
    @app.post("/vehicles")
    def create_vehicle():
        b = body(); require(b, "placa")
        v = c.cadastrar_veiculo.execute(b["placa"], b.get("cnh_exigida", "C"),
                                        b.get("certificacoes_exigidas"))
        return jsonify(s.veiculo(v)), 201

    # ------------------------------------------------------------ turnos e escalas
    @app.post("/shifts")
    def create_shift():  # UC04
        b = body(); require(b, "nome", "inicio", "fim")
        t = c.criar_turno.execute(b["nome"], parse_time(b["inicio"], "inicio"),
                                  parse_time(b["fim"], "fim"))
        return jsonify(s.turno(t)), 201

    @app.post("/schedules")
    def create_schedule():  # UC05
        b = body(); require(b, "data", "turno_id")
        e = c.criar_escala.execute(parse_date(b["data"]), b["turno_id"])
        return jsonify(s.escala(e)), 201

    @app.get("/schedules/<id>")
    def get_schedule(id):  # UC10
        r = c.consultar_escala.execute(id)
        return jsonify({**s.escala(r["escala"]), "turno": s.turno(r["turno"]),
                        "alocacoes": [s.alocacao(a) for a in r["alocacoes"]]})

    @app.get("/schedules/<id>/conflicts")
    def schedule_conflicts(id):  # UC09
        return jsonify({"escala_id": id, "conflitos": c.detectar_conflitos_escala.execute(id)})

    # ------------------------------------------------------------ alocações
    def _alloc_args(b):
        require(b, "motorista_id", "veiculo_id")
        if not b.get("escala_id"):
            require(b, "inicio", "fim")
        return dict(
            funcionario_id=b["motorista_id"], veiculo_id=b["veiculo_id"],
            inicio=parse_dt(b["inicio"], "inicio") if b.get("inicio") else None,
            fim=parse_dt(b["fim"], "fim") if b.get("fim") else None,
            escala_id=b.get("escala_id"))

    @app.post("/allocations/validate")
    def validate_allocation():  # UC06/UC07/UC09 via motor de regras
        res = c.validar_alocacao.execute(**_alloc_args(body()))
        return jsonify(res.to_dict()), 200

    @app.post("/allocations")
    def create_allocation():  # UC08
        b = body()
        a = c.alocar_motorista.execute(**_alloc_args(b), viagem_id=b.get("viagem_id"))
        return jsonify(s.alocacao(a)), 201

    # ------------------------------------------------------------ jornada e descanso
    @app.post("/journeys/start")
    def start_journey():
        b = body(); require(b, "motorista_id", "inicio")
        j = c.iniciar_jornada.execute(b["motorista_id"], parse_dt(b["inicio"], "inicio"))
        return jsonify(s.jornada(j)), 201

    @app.post("/journeys/<id>/finish")
    def finish_journey(id):
        b = body(); require(b, "fim")
        return jsonify(s.jornada(c.finalizar_jornada.execute(id, parse_dt(b["fim"], "fim"))))

    @app.post("/journeys/validate")
    def validate_journey():  # UC06
        b = body(); require(b, "motorista_id", "inicio", "fim")
        res = c.validar_jornada.execute(b["motorista_id"], parse_dt(b["inicio"], "inicio"),
                                        parse_dt(b["fim"], "fim"))
        return jsonify(res.to_dict())

    @app.post("/rest-periods/validate")
    def validate_rest():  # UC07
        b = body(); require(b, "motorista_id", "inicio", "fim")
        res = c.validar_descanso.execute(b["motorista_id"], parse_dt(b["inicio"], "inicio"),
                                         parse_dt(b["fim"], "fim"))
        return jsonify(res.to_dict())

    @app.post("/rest-periods")
    def register_rest():
        b = body(); require(b, "motorista_id", "inicio", "fim")
        d = c.registrar_descanso.execute(b["motorista_id"], parse_dt(b["inicio"], "inicio"),
                                         parse_dt(b["fim"], "fim"))
        return jsonify(s.descanso(d)), 201

    return app


if __name__ == "__main__":  # execução local: python -m src.api.app
    create_app().run(host="0.0.0.0", port=5005, debug=False)
