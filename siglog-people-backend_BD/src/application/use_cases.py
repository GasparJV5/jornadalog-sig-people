"""Casos de uso UC01–UC10 do SIG-Log People (+ jornada/descanso de apoio)."""
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import List, Optional

from src.application.ports import EventPublisher
from src.config.settings import Settings
from src.domain import events as ev
from src.domain.entities import (Alocacao, Certificacao, Descanso, Disponibilidade,
                                 Escala, Jornada, Motorista, Operador, Periodo,
                                 TipoFuncionario, Turno, Veiculo)
from src.domain.errors import ConflictError, DomainError, NotFoundError, ValidationError
from src.domain.rules import (ContextoAlocacao, MotorDeRegras, ResultadoValidacao,
                              Violacao, DESCANSO_INSUFICIENTE, JORNADA_EXCEDIDA,
                              RegraConflito, RegraDescanso, RegraJornada)
from src.domain.validators import CNH_CATEGORIAS, cpf_valido, normaliza_cpf


class AlocacaoNegada(DomainError):
    """Alocação rejeitada pelo motor de regras (HTTP 422 com lista de violações)."""

    def __init__(self, resultado: ResultadoValidacao):
        super().__init__("Alocação não permitida.")
        self.resultado = resultado


def _periodo(inicio: datetime, fim: datetime) -> Periodo:
    try:
        return Periodo(inicio, fim)
    except ValueError as e:
        raise ValidationError(str(e))


@dataclass
class Repos:
    funcionarios: object
    veiculos: object
    turnos: object
    escalas: object
    disponibilidades: object
    jornadas: object
    descansos: object
    alocacoes: object


class _Base:
    def __init__(self, repos: Repos, publisher: EventPublisher, settings: Settings):
        self.r, self.pub, self.cfg = repos, publisher, settings

    def _motorista(self, id: str) -> Motorista:
        m = self.r.funcionarios.get(id)
        if m is None:
            raise NotFoundError(f"Funcionário {id} não encontrado.")
        if not isinstance(m, Motorista):
            raise DomainError(f"Funcionário {id} não é motorista.")
        return m

    def _funcionario(self, id: str):
        f = self.r.funcionarios.get(id)
        if f is None:
            raise NotFoundError(f"Funcionário {id} não encontrado.")
        return f


# ---------------------------------------------------------------- UC01
class CadastrarFuncionario(_Base):
    def execute(self, nome: str, cpf: str, tipo: str, cnh_categoria: Optional[str] = None):
        if not nome or not nome.strip():
            raise ValidationError("Nome é obrigatório.")
        if not cpf_valido(cpf):
            raise ValidationError("CPF inválido.")
        try:
            t = TipoFuncionario((tipo or "").upper())
        except ValueError:
            raise ValidationError("Tipo deve ser MOTORISTA ou OPERADOR.")
        cpf_n = normaliza_cpf(cpf)
        if self.r.funcionarios.get_by_cpf(cpf_n):
            raise ConflictError("Já existe funcionário com este CPF.")
        if t is TipoFuncionario.MOTORISTA:
            cat = (cnh_categoria or "").upper()
            if cat not in CNH_CATEGORIAS:
                raise ValidationError("Motorista requer cnh_categoria entre A, B, C, D, E.")
            f = Motorista(nome=nome.strip(), cpf=cpf_n, cnh_categoria=cat)
        else:
            f = Operador(nome=nome.strip(), cpf=cpf_n)
        return self.r.funcionarios.add(f)


# ---------------------------------------------------------------- UC02
class RegistrarCertificacao(_Base):
    def execute(self, funcionario_id: str, tipo: str, validade: date,
                emitida_em: Optional[date] = None):
        f = self._funcionario(funcionario_id)
        if not tipo or not tipo.strip():
            raise ValidationError("Tipo de certificação é obrigatório.")
        if emitida_em and emitida_em > validade:
            raise ValidationError("emitida_em não pode ser posterior à validade.")
        f.registrar_certificacao(Certificacao(tipo.strip().upper(), validade, emitida_em))
        self.r.funcionarios.update(f)
        self.pub.publish(ev.DomainEvent(ev.CERTIFICACAO_ATUALIZADA, {
            "funcionario_id": f.id, "tipo": tipo.strip().upper(),
            "validade": validade.isoformat()}))
        return f


# ---------------------------------------------------------------- UC03
class RegistrarDisponibilidade(_Base):
    def execute(self, funcionario_id: str, inicio: datetime, fim: datetime,
                disponivel: bool = True):
        self._funcionario(funcionario_id)
        d = Disponibilidade(funcionario_id, _periodo(inicio, fim), disponivel)
        return self.r.disponibilidades.add(d)


class ConsultarDisponibilidade(_Base):
    def execute(self, funcionario_id: str) -> List[Disponibilidade]:
        self._funcionario(funcionario_id)
        itens = self.r.disponibilidades.list_by_funcionario(funcionario_id)
        return sorted(itens, key=lambda d: d.periodo.inicio)


# ---------------------------------------------------------------- UC04
class CriarTurno(_Base):
    def execute(self, nome: str, inicio: time, fim: time) -> Turno:
        if not nome or not nome.strip():
            raise ValidationError("Nome do turno é obrigatório.")
        if inicio == fim:
            raise ValidationError("Início e fim do turno não podem ser iguais.")
        if self.r.turnos.get_by_nome(nome.strip()):
            raise ConflictError("Já existe turno com este nome.")
        turno = Turno(nome.strip(), inicio, fim)
        if turno.periodo_em(date(2000, 1, 1)).horas > self.cfg.jornada_max_horas:
            raise ValidationError(
                f"Turno excede a jornada máxima de {self.cfg.jornada_max_horas:g}h.")
        return self.r.turnos.add(turno)


# ---------------------------------------------------------------- UC05
class CriarEscala(_Base):
    def execute(self, data: date, turno_id: str) -> Escala:
        if self.r.turnos.get(turno_id) is None:
            raise NotFoundError(f"Turno {turno_id} não encontrado.")
        if self.r.escalas.get_by_data_turno(data, turno_id):
            raise ConflictError("Já existe escala para este turno nesta data.")
        return self.r.escalas.add(Escala(data=data, turno_id=turno_id))


# ---------------------------------------------------------------- UC06
class ValidarJornada(_Base):
    """Valida limite diário de jornada para um período (sem consultar alocações)."""

    def execute(self, funcionario_id: str, inicio: datetime, fim: datetime) -> ResultadoValidacao:
        m = self._motorista(funcionario_id)
        ctx = ContextoAlocacao(m, None, _periodo(inicio, fim), [], [], [], [], self.cfg)
        return ResultadoValidacao(RegraJornada().avaliar(ctx))


class IniciarJornada(_Base):
    """Toda jornada registrada pertence a uma alocação (registros_jornada.alocacao_id)."""

    def execute(self, funcionario_id: str, alocacao_id: str, inicio: datetime) -> Jornada:
        self._funcionario(funcionario_id)
        aloc = self.r.alocacoes.get(alocacao_id)
        if aloc is None:
            raise NotFoundError(f"Alocação {alocacao_id} não encontrada.")
        if aloc.funcionario_id != funcionario_id:
            raise ValidationError("A alocação informada pertence a outro funcionário.")
        if self.r.jornadas.get_by_alocacao(alocacao_id):
            raise ConflictError("Esta alocação já possui jornada registrada.")
        if self.r.jornadas.get_aberta(funcionario_id):
            raise ConflictError("Funcionário já possui jornada em aberto.")
        fins = [j.fim for j in self.r.jornadas.list_by_funcionario(funcionario_id)
                if j.fim and j.fim <= inicio]
        if fins:
            h = (inicio - max(fins)).total_seconds() / 3600
            if h < self.cfg.descanso_minimo_horas:
                raise AlocacaoNegada(ResultadoValidacao([Violacao(
                    DESCANSO_INSUFICIENTE,
                    f"Descanso de {h:.1f}h; mínimo {self.cfg.descanso_minimo_horas:g}h.")]))
        j = self.r.jornadas.add(Jornada(funcionario_id, inicio, alocacao_id=alocacao_id))
        self.pub.publish(ev.DomainEvent(ev.JORNADA_INICIADA, {
            "jornada_id": j.id, "funcionario_id": funcionario_id,
            "alocacao_id": alocacao_id, "inicio": inicio.isoformat()}))
        return j


class FinalizarJornada(_Base):
    def execute(self, jornada_id: str, fim: datetime) -> Jornada:
        j = self.r.jornadas.get(jornada_id)
        if j is None:
            raise NotFoundError(f"Jornada {jornada_id} não encontrada.")
        if not j.aberta:
            raise ConflictError("Jornada já finalizada.")
        p = _periodo(j.inicio, fim)
        j.fim = fim
        self.r.jornadas.update(j)
        self.pub.publish(ev.DomainEvent(ev.JORNADA_FINALIZADA, {
            "jornada_id": j.id, "funcionario_id": j.funcionario_id,
            "inicio": j.inicio.isoformat(), "fim": fim.isoformat(),
            "horas": round(p.horas, 2),
            "excedeu_limite": p.horas > self.cfg.jornada_max_horas}))
        return j


# ---------------------------------------------------------------- UC07
class ValidarDescanso(_Base):
    """Um descanso é válido se atinge o mínimo e não sobrepõe trabalho já registrado."""

    def execute(self, funcionario_id: str, inicio: datetime, fim: datetime) -> ResultadoValidacao:
        self._funcionario(funcionario_id)
        p = _periodo(inicio, fim)
        v: List[Violacao] = []
        if p.horas < self.cfg.descanso_minimo_horas:
            v.append(Violacao(DESCANSO_INSUFICIENTE,
                              f"Descanso de {p.horas:.1f}h; mínimo {self.cfg.descanso_minimo_horas:g}h."))
        trabalho = [a.periodo for a in self.r.alocacoes.list_by_funcionario(funcionario_id)]
        trabalho += [Periodo(j.inicio, j.fim) for j in self.r.jornadas.list_by_funcionario(funcionario_id)
                     if j.fim and j.fim > j.inicio]
        if any(t.sobrepoe(p) for t in trabalho):
            v.append(Violacao("DESCANSO_SOBREPOE_TRABALHO",
                              "Período de descanso sobrepõe jornada ou alocação."))
        return ResultadoValidacao(v)


class RegistrarDescanso(_Base):
    def execute(self, funcionario_id: str, inicio: datetime, fim: datetime) -> Descanso:
        res = ValidarDescanso(self.r, self.pub, self.cfg).execute(funcionario_id, inicio, fim)
        if not res.permitido:
            raise AlocacaoNegada(res)
        d = self.r.descansos.add(Descanso(funcionario_id, Periodo(inicio, fim)))
        self.pub.publish(ev.DomainEvent(ev.DESCANSO_REGISTRADO, {
            "descanso_id": d.id, "funcionario_id": funcionario_id,
            "inicio": inicio.isoformat(), "fim": fim.isoformat(),
            "horas": round(d.periodo.horas, 2)}))
        return d


# ---------------------------------------------------------------- UC09
class DetectarConflito(_Base):
    """Conflitos de motorista e/ou veículo para um período proposto."""

    def execute(self, funcionario_id: str, veiculo_id: Optional[str], periodo: Periodo,
                ignorar_alocacao_id: Optional[str] = None) -> List[Violacao]:
        self._motorista(funcionario_id)
        am = [a for a in self.r.alocacoes.list_by_funcionario(funcionario_id)
              if a.id != ignorar_alocacao_id]
        av = [a for a in self.r.alocacoes.list_by_veiculo(veiculo_id)
              if a.id != ignorar_alocacao_id] if veiculo_id else []
        ctx = ContextoAlocacao(self._motorista(funcionario_id), None, periodo, [], am, av, [], self.cfg)
        return RegraConflito().avaliar(ctx)


class DetectarConflitosDaEscala(_Base):
    def execute(self, escala_id: str) -> List[dict]:
        escala = self.r.escalas.get(escala_id)
        if escala is None:
            raise NotFoundError(f"Escala {escala_id} não encontrada.")
        out = []
        detector = DetectarConflito(self.r, self.pub, self.cfg)
        for a in self.r.alocacoes.list_by_escala(escala_id):
            for v in detector.execute(a.funcionario_id, a.veiculo_id, a.periodo, a.id):
                out.append({"alocacao_id": a.id, **v.to_dict()})
        return out


# ---------------------------------------------------------------- UC08
class _AlocacaoBase(_Base):
    def _resolver(self, funcionario_id, veiculo_id, inicio, fim, escala_id):
        """Toda alocação pertence a uma escala (alocacoes.escala_id é obrigatório).
        O período é o do turno na data da escala; inicio/fim opcionais o substituem."""
        if not escala_id:
            raise ValidationError("escala_id é obrigatório: toda alocação pertence a uma escala.")
        escala = self.r.escalas.get(escala_id)
        if escala is None:
            raise NotFoundError(f"Escala {escala_id} não encontrada.")
        if (inicio is None) != (fim is None):
            raise ValidationError("Informe inicio e fim juntos, ou nenhum dos dois.")
        if inicio is None:
            periodo = self.r.turnos.get(escala.turno_id).periodo_em(escala.data)
        else:
            if inicio.date() != escala.data:
                raise ValidationError("inicio deve ocorrer na data da escala.")
            periodo = _periodo(inicio, fim)
        veiculo = self.r.veiculos.get(veiculo_id)
        if veiculo is None:
            raise NotFoundError(f"Veículo {veiculo_id} não encontrado.")
        return self._motorista(funcionario_id), veiculo, periodo, escala

    def _validar(self, motorista, veiculo, periodo) -> ResultadoValidacao:
        ctx = ContextoAlocacao(
            motorista=motorista, veiculo=veiculo, periodo=periodo,
            disponibilidades=self.r.disponibilidades.janelas_para(motorista.id, periodo),
            alocacoes_motorista=self.r.alocacoes.list_by_funcionario(motorista.id),
            alocacoes_veiculo=self.r.alocacoes.list_by_veiculo(veiculo.id),
            jornadas=self.r.jornadas.list_by_funcionario(motorista.id),
            config=self.cfg)
        return MotorDeRegras().validar(ctx)


class ValidarAlocacao(_AlocacaoBase):
    def execute(self, funcionario_id, veiculo_id, inicio=None, fim=None,
                escala_id=None) -> ResultadoValidacao:
        m, v, p, _ = self._resolver(funcionario_id, veiculo_id, inicio, fim, escala_id)
        return self._validar(m, v, p)


class AlocarMotorista(_AlocacaoBase):
    def execute(self, funcionario_id, veiculo_id, inicio=None, fim=None,
                escala_id=None, viagem_id=None) -> Alocacao:
        m, v, p, escala = self._resolver(funcionario_id, veiculo_id, inicio, fim, escala_id)
        res = self._validar(m, v, p)
        if not res.permitido:
            if res.conflitos:
                self.pub.publish(ev.DomainEvent(ev.CONFLITO_DE_JORNADA_DETECTADO, {
                    "funcionario_id": m.id, "veiculo_id": v.id,
                    "inicio": p.inicio.isoformat(), "fim": p.fim.isoformat(),
                    "conflitos": [c.to_dict() for c in res.conflitos]}))
            raise AlocacaoNegada(res)
        if any(x.escala_id == escala.id for x in self.r.alocacoes.list_by_funcionario(m.id)):
            raise ConflictError("Motorista já está alocado nesta escala.")
        a = self.r.alocacoes.add(Alocacao(
            funcionario_id=m.id, veiculo_id=v.id, periodo=p,
            turno_id=escala.turno_id, escala_id=escala.id,
            viagem_id=str(viagem_id) if viagem_id is not None else None))
        self.pub.publish(ev.DomainEvent(ev.MOTORISTA_ESCALADO, {
            "alocacao_id": a.id, "motorista_id": m.id, "veiculo_id": v.id,
            "inicio": p.inicio.isoformat(), "fim": p.fim.isoformat(),
            "escala_id": a.escala_id, "viagem_id": a.viagem_id}))
        return a


# ---------------------------------------------------------------- UC10
class ConsultarEscala(_Base):
    def execute(self, escala_id: str) -> dict:
        escala = self.r.escalas.get(escala_id)
        if escala is None:
            raise NotFoundError(f"Escala {escala_id} não encontrada.")
        alocacoes = self.r.alocacoes.list_by_escala(escala_id)
        escala.alocacoes_ids = [a.id for a in alocacoes]
        return {"escala": escala,
                "turno": self.r.turnos.get(escala.turno_id),
                "alocacoes": alocacoes}


class ConsultarMotoristas(_Base):
    def execute(self) -> List[Motorista]:
        return self.r.funcionarios.list_by_tipo(TipoFuncionario.MOTORISTA)

    def por_id(self, id: str) -> Motorista:
        return self._motorista(id)


class CadastrarVeiculo(_Base):
    """Réplica local de veículo (a fonte da verdade é o módulo Fleet)."""

    def execute(self, placa: str, cnh_exigida: str = "C",
                certificacoes_exigidas: Optional[List[str]] = None,
                modelo: Optional[str] = None, marca: Optional[str] = None,
                ano: Optional[int] = None) -> Veiculo:
        if not placa or not placa.strip():
            raise ValidationError("Placa é obrigatória.")
        if cnh_exigida.upper() not in CNH_CATEGORIAS:
            raise ValidationError("cnh_exigida inválida.")
        if ano is not None and (not isinstance(ano, int) or isinstance(ano, bool) or ano <= 0):
            raise ValidationError("ano inválido.")
        placa_n = placa.strip().upper()
        if self.r.veiculos.get_by_placa(placa_n):
            raise ConflictError("Já existe veículo com esta placa.")
        return self.r.veiculos.add(Veiculo(
            placa_n, cnh_exigida.upper(),
            [c.strip().upper() for c in (certificacoes_exigidas or [])],
            modelo=(modelo or "NAO INFORMADO").strip(), marca=marca, ano=ano))
