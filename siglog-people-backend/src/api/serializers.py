from src.domain.entities import Motorista


def _dt(d):
    return d.isoformat() if d else None


def funcionario(f) -> dict:
    out = {"id": f.id, "nome": f.nome, "cpf": f.cpf, "tipo": f.tipo.value, "ativo": f.ativo,
           "certificacoes": [{"tipo": c.tipo, "validade": c.validade.isoformat(),
                              "emitida_em": c.emitida_em.isoformat() if c.emitida_em else None}
                             for c in f.certificacoes]}
    if isinstance(f, Motorista):
        out["cnh_categoria"] = f.cnh_categoria
    return out


def veiculo(v) -> dict:
    return {"id": v.id, "placa": v.placa, "cnh_exigida": v.cnh_exigida,
            "certificacoes_exigidas": v.certificacoes_exigidas}


def disponibilidade(d) -> dict:
    return {"id": d.id, "funcionario_id": d.funcionario_id, "inicio": _dt(d.periodo.inicio),
            "fim": _dt(d.periodo.fim), "disponivel": d.disponivel}


def turno(t) -> dict:
    return {"id": t.id, "nome": t.nome, "inicio": t.inicio.strftime("%H:%M"),
            "fim": t.fim.strftime("%H:%M")}


def escala(e) -> dict:
    return {"id": e.id, "data": e.data.isoformat(), "turno_id": e.turno_id,
            "alocacoes_ids": e.alocacoes_ids}


def alocacao(a) -> dict:
    return {"id": a.id, "motorista_id": a.funcionario_id, "veiculo_id": a.veiculo_id,
            "inicio": _dt(a.periodo.inicio), "fim": _dt(a.periodo.fim),
            "escala_id": a.escala_id, "turno_id": a.turno_id, "viagem_id": a.viagem_id}


def jornada(j) -> dict:
    return {"id": j.id, "funcionario_id": j.funcionario_id,
            "inicio": _dt(j.inicio), "fim": _dt(j.fim)}


def descanso(d) -> dict:
    return {"id": d.id, "funcionario_id": d.funcionario_id,
            "inicio": _dt(d.periodo.inicio), "fim": _dt(d.periodo.fim)}
