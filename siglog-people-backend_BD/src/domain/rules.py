"""Motor de Regras de Alocação (A.5 do Kit).

    SE motorista indisponível      -> NÃO alocar
    SE certificação incompatível   -> NÃO alocar
    SE descanso insuficiente       -> NÃO alocar
    SE tudo válido                 -> permitir alocação

Além das três regras do Kit, o motor também aplica o limite de jornada (UC06)
e a detecção de conflitos de motorista/veículo (UC09).

Premissa de modelagem: cada Alocação equivale a uma jornada de trabalho; o
descanso mínimo é o intervalo entre o fim de uma jornada/alocação e o início da próxima.
"""
from dataclasses import dataclass, field
from datetime import timedelta
from typing import List, Optional, Protocol

from src.config.settings import Settings
from src.domain.entities import (Alocacao, Disponibilidade, Jornada, Motorista,
                                 Periodo, Veiculo)
from src.domain.validators import cnh_compativel

# Códigos de violação (estáveis: fazem parte do contrato da API)
MOTORISTA_INATIVO = "MOTORISTA_INATIVO"
MOTORISTA_INDISPONIVEL = "MOTORISTA_INDISPONIVEL"
CNH_INCOMPATIVEL = "CNH_INCOMPATIVEL"
CERTIFICACAO_AUSENTE = "CERTIFICACAO_AUSENTE"
CERTIFICACAO_VENCIDA = "CERTIFICACAO_VENCIDA"
CERTIFICACAO_SUSPENSA = "CERTIFICACAO_SUSPENSA"
DESCANSO_INSUFICIENTE = "DESCANSO_INSUFICIENTE"
JORNADA_EXCEDIDA = "JORNADA_EXCEDIDA"
CONFLITO_MOTORISTA = "CONFLITO_MOTORISTA"
CONFLITO_VEICULO = "CONFLITO_VEICULO"

CODIGOS_DE_CONFLITO = {CONFLITO_MOTORISTA, CONFLITO_VEICULO}


@dataclass(frozen=True)
class Violacao:
    codigo: str
    mensagem: str

    def to_dict(self) -> dict:
        return {"codigo": self.codigo, "mensagem": self.mensagem}


@dataclass
class ResultadoValidacao:
    violacoes: List[Violacao] = field(default_factory=list)

    @property
    def permitido(self) -> bool:
        return not self.violacoes

    @property
    def conflitos(self) -> List[Violacao]:
        return [v for v in self.violacoes if v.codigo in CODIGOS_DE_CONFLITO]

    def to_dict(self) -> dict:
        return {"permitido": self.permitido,
                "violacoes": [v.to_dict() for v in self.violacoes]}


@dataclass
class ContextoAlocacao:
    motorista: Motorista
    veiculo: Optional[Veiculo]
    periodo: Periodo
    disponibilidades: List[Disponibilidade]
    alocacoes_motorista: List[Alocacao]
    alocacoes_veiculo: List[Alocacao]
    jornadas: List[Jornada]
    config: Settings


class Regra(Protocol):
    def avaliar(self, ctx: ContextoAlocacao) -> List[Violacao]: ...


class RegraDisponibilidade:
    """Motorista ativo e com janela de disponibilidade cobrindo todo o período."""

    def avaliar(self, ctx):
        if not ctx.motorista.ativo:
            return [Violacao(MOTORISTA_INATIVO, "Motorista inativo.")]
        p = ctx.periodo
        if any(not d.disponivel and d.periodo.sobrepoe(p) for d in ctx.disponibilidades):
            return [Violacao(MOTORISTA_INDISPONIVEL,
                             "Motorista marcado como indisponível no período.")]
        cursor = p.inicio
        janelas = sorted((d for d in ctx.disponibilidades if d.disponivel),
                         key=lambda d: d.periodo.inicio)
        for d in janelas:
            if d.periodo.inicio > cursor:
                break
            cursor = max(cursor, d.periodo.fim)
            if cursor >= p.fim:
                return []
        return [Violacao(MOTORISTA_INDISPONIVEL,
                         "Nenhuma janela de disponibilidade cobre todo o período.")]


class RegraCertificacao:
    """CNH compatível com o veículo e certificações exigidas vigentes até o fim do período."""

    def avaliar(self, ctx):
        if ctx.veiculo is None:
            return []
        v: List[Violacao] = []
        if not cnh_compativel(ctx.motorista.cnh_categoria, ctx.veiculo.cnh_exigida):
            v.append(Violacao(CNH_INCOMPATIVEL,
                              f"CNH {ctx.motorista.cnh_categoria} não habilita "
                              f"veículo que exige categoria {ctx.veiculo.cnh_exigida}."))
        data_fim = ctx.periodo.fim.date()
        for tipo in ctx.veiculo.certificacoes_exigidas:
            cert = ctx.motorista.certificacao(tipo)
            if cert is None:
                v.append(Violacao(CERTIFICACAO_AUSENTE, f"Certificação {tipo} ausente."))
            elif not cert.ativa:
                v.append(Violacao(CERTIFICACAO_SUSPENSA, f"Certificação {tipo} suspensa."))
            elif not cert.vigente_em(data_fim):
                v.append(Violacao(CERTIFICACAO_VENCIDA,
                                  f"Certificação {tipo} vence em {cert.validade.isoformat()}, "
                                  f"antes do fim do período."))
        return v


class RegraDescanso:
    """Intervalo mínimo entre jornadas, olhando para antes e para depois do período."""

    def avaliar(self, ctx):
        minimo = timedelta(hours=ctx.config.descanso_minimo_horas)
        p = ctx.periodo
        fins = [a.periodo.fim for a in ctx.alocacoes_motorista if a.periodo.fim <= p.inicio]
        fins += [j.fim for j in ctx.jornadas if j.fim and j.fim <= p.inicio]
        inicios = [a.periodo.inicio for a in ctx.alocacoes_motorista if a.periodo.inicio >= p.fim]
        v: List[Violacao] = []
        if fins and p.inicio - max(fins) < minimo:
            h = (p.inicio - max(fins)).total_seconds() / 3600
            v.append(Violacao(DESCANSO_INSUFICIENTE,
                              f"Descanso de {h:.1f}h desde a última jornada; "
                              f"mínimo {ctx.config.descanso_minimo_horas:g}h."))
        elif inicios and min(inicios) - p.fim < minimo:
            h = (min(inicios) - p.fim).total_seconds() / 3600
            v.append(Violacao(DESCANSO_INSUFICIENTE,
                              f"Descanso de {h:.1f}h até a próxima jornada já alocada; "
                              f"mínimo {ctx.config.descanso_minimo_horas:g}h."))
        return v


class RegraJornada:
    def avaliar(self, ctx):
        if ctx.periodo.horas > ctx.config.jornada_max_horas:
            return [Violacao(JORNADA_EXCEDIDA,
                             f"Jornada de {ctx.periodo.horas:.1f}h excede o máximo de "
                             f"{ctx.config.jornada_max_horas:g}h.")]
        return []


class RegraConflito:
    def avaliar(self, ctx):
        v: List[Violacao] = []
        if any(a.periodo.sobrepoe(ctx.periodo) for a in ctx.alocacoes_motorista):
            v.append(Violacao(CONFLITO_MOTORISTA,
                              "Motorista já alocado em período sobreposto."))
        if any(a.periodo.sobrepoe(ctx.periodo) for a in ctx.alocacoes_veiculo):
            v.append(Violacao(CONFLITO_VEICULO,
                              "Veículo já alocado em período sobreposto."))
        return v


class MotorDeRegras:
    def __init__(self, regras: Optional[List[Regra]] = None):
        self.regras = regras or [RegraDisponibilidade(), RegraCertificacao(),
                                 RegraDescanso(), RegraJornada(), RegraConflito()]

    def validar(self, ctx: ContextoAlocacao) -> ResultadoValidacao:
        res = ResultadoValidacao()
        for r in self.regras:
            res.violacoes.extend(r.avaliar(ctx))
        return res
