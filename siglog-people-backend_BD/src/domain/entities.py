"""Entidades do domínio SIG-Log People."""
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import List, Optional
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


class TipoFuncionario(str, Enum):
    MOTORISTA = "MOTORISTA"
    OPERADOR = "OPERADOR"


@dataclass
class Certificacao:
    tipo: str                          # ex.: "MOPP" (produtos perigosos), "NR-11" (empilhadeira)
    validade: Optional[date]           # None = sem vencimento
    emitida_em: Optional[date] = None
    numero: Optional[str] = None       # número do certificado (opcional)
    ativa: bool = True                 # False = suspensa

    def vigente_em(self, data: date) -> bool:
        return self.ativa and (self.validade is None or self.validade >= data)


@dataclass
class Funcionario:
    nome: str
    cpf: str
    tipo: TipoFuncionario
    id: str = field(default_factory=new_id)
    ativo: bool = True
    certificacoes: List[Certificacao] = field(default_factory=list)

    def certificacao(self, tipo: str) -> Optional[Certificacao]:
        """Certificação do tipo com a validade mais longa (sem vencimento vale mais)."""
        candidatas = [c for c in self.certificacoes if c.tipo.upper() == tipo.upper()]
        if not candidatas:
            return None
        return max(candidatas, key=lambda c: (c.validade is None, c.validade or date.min))

    def registrar_certificacao(self, cert: Certificacao) -> None:
        """Insere ou atualiza (mesmo tipo e número) a certificação."""
        for atual in self.certificacoes:
            if atual.tipo.upper() == cert.tipo.upper() and atual.numero == cert.numero:
                atual.validade, atual.emitida_em, atual.ativa = cert.validade, cert.emitida_em, cert.ativa
                return
        self.certificacoes.append(cert)


@dataclass
class Motorista(Funcionario):
    cnh_categoria: str = "C"
    tipo: TipoFuncionario = TipoFuncionario.MOTORISTA


@dataclass
class Operador(Funcionario):
    tipo: TipoFuncionario = TipoFuncionario.OPERADOR


@dataclass
class Veiculo:
    placa: str
    cnh_exigida: str = "C"
    certificacoes_exigidas: List[str] = field(default_factory=list)
    id: str = field(default_factory=new_id)
    modelo: str = "NAO INFORMADO"
    marca: Optional[str] = None
    ano: Optional[int] = None


@dataclass
class Turno:
    nome: str
    inicio: time
    fim: time           # fim <= inicio indica turno que cruza a meia-noite
    id: str = field(default_factory=new_id)

    def periodo_em(self, dia: date) -> "Periodo":
        ini = datetime.combine(dia, self.inicio)
        fim = datetime.combine(dia, self.fim)
        if fim <= ini:                      # turno noturno cruza a meia-noite
            fim += timedelta(days=1)
        return Periodo(ini, fim)


@dataclass(frozen=True)
class Periodo:
    inicio: datetime
    fim: datetime

    def __post_init__(self):
        if self.fim <= self.inicio:
            raise ValueError("fim deve ser posterior ao início")

    @property
    def horas(self) -> float:
        return (self.fim - self.inicio).total_seconds() / 3600

    def sobrepoe(self, outro: "Periodo") -> bool:
        return self.inicio < outro.fim and outro.inicio < self.fim


@dataclass
class Disponibilidade:
    funcionario_id: str
    periodo: Periodo
    disponivel: bool = True
    id: str = field(default_factory=new_id)


@dataclass
class Jornada:
    funcionario_id: str
    inicio: datetime
    fim: Optional[datetime] = None
    alocacao_id: Optional[str] = None
    id: str = field(default_factory=new_id)

    @property
    def aberta(self) -> bool:
        return self.fim is None


@dataclass
class Descanso:
    funcionario_id: str
    periodo: Periodo
    id: str = field(default_factory=new_id)


@dataclass
class Alocacao:
    funcionario_id: str
    veiculo_id: str
    periodo: Periodo
    turno_id: Optional[str] = None
    escala_id: Optional[str] = None
    viagem_id: Optional[str] = None
    id: str = field(default_factory=new_id)


@dataclass
class Escala:
    data: date
    turno_id: str
    id: str = field(default_factory=new_id)
    alocacoes_ids: List[str] = field(default_factory=list)
