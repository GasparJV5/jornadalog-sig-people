"""Repositórios PostgreSQL. Esquema: migrations 001, 002 e 003 (ver proposta_infra/).

Convenções
* IDs: BIGINT no banco, texto na API/domínio. IDs não numéricos são tratados como inexistentes.
* Todas as consultas usam a conexão da requisição (`db.conn`); quem fecha a transação é a API.
* Parâmetros sempre via placeholders (%s) — nunca interpolação de strings.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional

from src.application.use_cases import Repos
from src.domain.entities import (Alocacao, Certificacao, Descanso, Disponibilidade, Escala,
                                 Jornada, Motorista, Operador, Periodo, TipoFuncionario, Turno,
                                 Veiculo)
from src.domain.errors import DomainError
from src.infrastructure import disponibilidade_semanal as ds


def _int(id) -> Optional[int]:
    try:
        return int(id)
    except (TypeError, ValueError):
        return None


def _s(v) -> Optional[str]:
    return None if v is None else str(v)


class _Sql:
    def __init__(self, db):
        self.db = db

    def _one(self, sql, params=()):
        return self.db.conn.execute(sql, params).fetchone()

    def _all(self, sql, params=()):
        return self.db.conn.execute(sql, params).fetchall()

    def _run(self, sql, params=()):
        self.db.conn.execute(sql, params)

    def _catalogo(self, nome: str) -> int:
        """Id da certificação no catálogo (case-insensitive); cria se não existir."""
        row = self._one("SELECT id FROM certificacoes WHERE UPPER(nome) = UPPER(%s)", (nome,))
        if row:
            return row["id"]
        return self._one("INSERT INTO certificacoes (nome, obrigatoria) VALUES (%s, FALSE) RETURNING id",
                         (nome.upper(),))["id"]


# ------------------------------------------------------------------ funcionários
class FuncionarioRepository(_Sql):
    _SEL = ("SELECT f.id, f.nome, f.cpf, f.status, f.cnh_categoria, c.nome AS cargo "
            "FROM funcionarios f JOIN cargos c ON c.id = f.cargo_id")

    def add(self, f):
        cargo = "Motorista" if f.tipo is TipoFuncionario.MOTORISTA else "Operador"
        row = self._one("SELECT id FROM cargos WHERE nome = %s AND ativo", (cargo,))
        if row is None:
            raise DomainError(f"Cargo '{cargo}' não encontrado no banco; execute os seeds.")
        novo = self._one(
            "INSERT INTO funcionarios (matricula, nome, cargo_id, data_admissao, status, cpf, cnh_categoria) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (f"MAT{f.cpf}", f.nome, row["id"], date.today(), "ATIVO" if f.ativo else "INATIVO",
             f.cpf, getattr(f, "cnh_categoria", None)))
        f.id = str(novo["id"])
        self._salvar_certificacoes(f)
        return f

    def update(self, f):
        """Persiste as certificações (único dado do funcionário alterado pelos casos de uso)."""
        self._salvar_certificacoes(f)
        return f

    def _salvar_certificacoes(self, f):
        fid = _int(f.id)
        for c in f.certificacoes:
            cat = self._catalogo(c.tipo)
            status = "VALIDA" if c.ativa else "SUSPENSA"
            existe = self._one(
                "SELECT id FROM funcionario_certificacoes WHERE funcionario_id = %s "
                "AND certificacao_id = %s AND numero_certificado IS NOT DISTINCT FROM %s",
                (fid, cat, c.numero))
            if existe:
                self._run("UPDATE funcionario_certificacoes SET emitida_em = %s, validade_ate = %s, "
                          "status = %s WHERE id = %s", (c.emitida_em, c.validade, status, existe["id"]))
            else:
                self._run("INSERT INTO funcionario_certificacoes "
                          "(funcionario_id, certificacao_id, numero_certificado, emitida_em, validade_ate, status) "
                          "VALUES (%s, %s, %s, %s, %s, %s)",
                          (fid, cat, c.numero, c.emitida_em, c.validade, status))

    def _montar(self, row):
        certs = [Certificacao(tipo=r["nome"], validade=r["validade_ate"], emitida_em=r["emitida_em"],
                              numero=r["numero_certificado"], ativa=r["status"] != "SUSPENSA")
                 for r in self._all(
                     "SELECT c.nome, fc.numero_certificado, fc.emitida_em, fc.validade_ate, fc.status "
                     "FROM funcionario_certificacoes fc JOIN certificacoes c ON c.id = fc.certificacao_id "
                     "WHERE fc.funcionario_id = %s ORDER BY fc.id", (row["id"],))]
        base = dict(nome=row["nome"], cpf=row["cpf"] or "", id=str(row["id"]),
                    ativo=row["status"] == "ATIVO", certificacoes=certs)
        if row["cargo"] == "Motorista":
            # CNH ausente no banco: assume a categoria mais baixa (decisão conservadora)
            return Motorista(cnh_categoria=row["cnh_categoria"] or "B", **base)
        return Operador(**base)

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE f.id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def get_by_cpf(self, cpf):
        row = self._one(self._SEL + " WHERE f.cpf = %s", (cpf,))
        return self._montar(row) if row else None

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " ORDER BY f.id")]

    def list_by_tipo(self, tipo) -> List:
        cond = "c.nome = 'Motorista'" if tipo is TipoFuncionario.MOTORISTA else "c.nome <> 'Motorista'"
        return [self._montar(r) for r in self._all(self._SEL + f" WHERE {cond} ORDER BY f.id")]


# ------------------------------------------------------------------ veículos
class VeiculoRepository(_Sql):
    _SEL = "SELECT id, placa, modelo, marca, ano, cnh_exigida FROM veiculos"

    def add(self, v):
        novo = self._one(
            "INSERT INTO veiculos (placa, modelo, marca, ano, cnh_exigida) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (v.placa, v.modelo, v.marca, v.ano, v.cnh_exigida))
        v.id = str(novo["id"])
        for tipo in v.certificacoes_exigidas:
            self._run("INSERT INTO veiculo_certificacoes_exigidas (veiculo_id, certificacao_id) "
                      "VALUES (%s, %s) ON CONFLICT DO NOTHING", (novo["id"], self._catalogo(tipo)))
        return v

    def update(self, v):
        return v

    def _montar(self, r):
        exigidas = [x["nome"] for x in self._all(
            "SELECT c.nome FROM veiculo_certificacoes_exigidas ve "
            "JOIN certificacoes c ON c.id = ve.certificacao_id WHERE ve.veiculo_id = %s ORDER BY c.nome",
            (r["id"],))]
        return Veiculo(placa=r["placa"], cnh_exigida=r["cnh_exigida"], certificacoes_exigidas=exigidas,
                       id=str(r["id"]), modelo=r["modelo"], marca=r["marca"], ano=r["ano"])

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def get_by_placa(self, placa):
        row = self._one(self._SEL + " WHERE placa = %s", (placa,))
        return self._montar(row) if row else None

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " ORDER BY id")]


# ------------------------------------------------------------------ turnos e escalas
class TurnoRepository(_Sql):
    _SEL = "SELECT id, nome, hora_inicio, hora_fim FROM turnos"

    def add(self, t):
        novo = self._one("INSERT INTO turnos (nome, hora_inicio, hora_fim) VALUES (%s, %s, %s) RETURNING id",
                         (t.nome, t.inicio, t.fim))
        t.id = str(novo["id"])
        return t

    def update(self, t):
        return t

    def _montar(self, r):
        return Turno(nome=r["nome"], inicio=r["hora_inicio"], fim=r["hora_fim"], id=str(r["id"]))

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def get_by_nome(self, nome):
        row = self._one(self._SEL + " WHERE LOWER(nome) = LOWER(%s)", (nome,))
        return self._montar(row) if row else None

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " ORDER BY id")]


class EscalaRepository(_Sql):
    _SEL = "SELECT id, data_escala, turno_id FROM escalas"

    def add(self, e):
        novo = self._one("INSERT INTO escalas (data_escala, turno_id) VALUES (%s, %s) RETURNING id",
                         (e.data, _int(e.turno_id)))
        e.id = str(novo["id"])
        return e

    def update(self, e):
        return e

    def _montar(self, r):
        ids = [str(x["id"]) for x in self._all(
            "SELECT id FROM alocacoes WHERE escala_id = %s ORDER BY id", (r["id"],))]
        return Escala(data=r["data_escala"], turno_id=str(r["turno_id"]), id=str(r["id"]), alocacoes_ids=ids)

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def get_by_data_turno(self, data, turno_id):
        t = _int(turno_id)
        row = self._one(self._SEL + " WHERE data_escala = %s AND turno_id = %s", (data, t)) if t is not None else None
        return self._montar(row) if row else None

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " ORDER BY id")]


# ------------------------------------------------------------------ disponibilidade (semanal no banco)
class DisponibilidadeRepository(_Sql):
    _SEL = ("SELECT id, funcionario_id, dia_semana, hora_inicio, hora_fim, vigencia_inicio, "
            "vigencia_fim, disponivel FROM disponibilidades")

    def add(self, d):
        fid = _int(d.funcionario_id)
        primeiro = None
        for l in ds.segmentar(d.periodo):
            novo = self._one(
                "INSERT INTO disponibilidades (funcionario_id, dia_semana, hora_inicio, hora_fim, "
                "vigencia_inicio, vigencia_fim, disponivel) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (fid, l["dia_semana"], l["hora_inicio"], l["hora_fim"], l["vigencia"], l["vigencia"], d.disponivel))
            primeiro = primeiro or novo["id"]
        d.id = str(primeiro)
        return d

    def update(self, d):
        return d

    def list_by_funcionario(self, funcionario_id):
        """Janelas pontuais (vigência de um dia), unidas quando contíguas."""
        i = _int(funcionario_id)
        if i is None:
            return []
        rows = self._all(self._SEL + " WHERE funcionario_id = %s AND vigencia_fim = vigencia_inicio "
                         "ORDER BY vigencia_inicio, hora_inicio", (i,))
        return ds.mesclar([ds.janela_de_linha_pontual(r, str(funcionario_id)) for r in rows])

    def janelas_para(self, funcionario_id, periodo):
        """Janelas concretas (pontuais e recorrentes) que tocam o período."""
        i = _int(funcionario_id)
        if i is None:
            return []
        rows = self._all(self._SEL + " WHERE funcionario_id = %s AND vigencia_inicio <= %s "
                         "AND (vigencia_fim IS NULL OR vigencia_fim >= %s)",
                         (i, periodo.fim.date(), periodo.inicio.date()))
        return ds.expandir(rows, periodo, str(funcionario_id))

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE id = %s AND vigencia_fim = vigencia_inicio", (i,)) if i is not None else None
        return ds.janela_de_linha_pontual(row, str(row["funcionario_id"])) if row else None

    def list(self) -> List:
        return [ds.janela_de_linha_pontual(r, str(r["funcionario_id"])) for r in self._all(
            self._SEL + " WHERE vigencia_fim = vigencia_inicio ORDER BY id")]


# ------------------------------------------------------------------ descansos
class DescansoRepository(_Sql):
    _SEL = "SELECT id, funcionario_id, inicio_descanso, fim_descanso FROM descansos"

    def add(self, d):
        novo = self._one("INSERT INTO descansos (funcionario_id, inicio_descanso, fim_descanso) "
                         "VALUES (%s, %s, %s) RETURNING id",
                         (_int(d.funcionario_id), d.periodo.inicio, d.periodo.fim))
        d.id = str(novo["id"])
        return d

    def update(self, d):
        return d

    def _montar(self, r):
        return Descanso(str(r["funcionario_id"]), Periodo(r["inicio_descanso"], r["fim_descanso"]), id=str(r["id"]))

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def list_by_funcionario(self, funcionario_id):
        i = _int(funcionario_id)
        return [] if i is None else [self._montar(r) for r in self._all(
            self._SEL + " WHERE funcionario_id = %s ORDER BY inicio_descanso", (i,))]

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " ORDER BY id")]


# ------------------------------------------------------------------ alocações
class AlocacaoRepository(_Sql):
    _SEL = ("SELECT a.id, a.escala_id, a.funcionario_id, a.veiculo_id, a.viagem_id, a.hora_inicio, a.hora_fim, "
            "e.data_escala, e.turno_id, t.hora_inicio AS t_ini, t.hora_fim AS t_fim "
            "FROM alocacoes a JOIN escalas e ON e.id = a.escala_id JOIN turnos t ON t.id = e.turno_id")
    _ATIVAS = " AND a.status <> 'CANCELADA'"       # alocações canceladas não bloqueiam ninguém

    def add(self, a):
        esc = self._one("SELECT data_escala FROM escalas WHERE id = %s", (_int(a.escala_id),))
        if esc is None:
            raise DomainError("Escala da alocação não encontrada.")
        if a.periodo.horas >= 24:
            raise DomainError("Alocação deve ter menos de 24h.")
        novo = self._one(
            "INSERT INTO alocacoes (escala_id, funcionario_id, veiculo_id, viagem_id, hora_inicio, hora_fim) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (_int(a.escala_id), _int(a.funcionario_id), _int(a.veiculo_id), a.viagem_id,
             a.periodo.inicio.time(), a.periodo.fim.time()))
        a.id = str(novo["id"])
        return a

    def update(self, a):
        return a

    def _montar(self, r):
        ini = datetime.combine(r["data_escala"], r["hora_inicio"] or r["t_ini"])
        fim = datetime.combine(r["data_escala"], r["hora_fim"] or r["t_fim"])
        if fim <= ini:                                  # cruza a meia-noite
            fim += timedelta(days=1)
        return Alocacao(funcionario_id=str(r["funcionario_id"]), veiculo_id=_s(r["veiculo_id"]),
                        periodo=Periodo(ini, fim), turno_id=str(r["turno_id"]),
                        escala_id=str(r["escala_id"]), viagem_id=r["viagem_id"], id=str(r["id"]))

    def _por(self, coluna, valor):
        i = _int(valor)
        if i is None:
            return []
        return [self._montar(r) for r in self._all(
            self._SEL + f" WHERE {coluna} = %s" + self._ATIVAS + " ORDER BY a.id", (i,))]

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE a.id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def list_by_funcionario(self, funcionario_id):
        return self._por("a.funcionario_id", funcionario_id)

    def list_by_veiculo(self, veiculo_id):
        return self._por("a.veiculo_id", veiculo_id)

    def list_by_escala(self, escala_id):
        return self._por("a.escala_id", escala_id)

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " WHERE TRUE" + self._ATIVAS + " ORDER BY a.id")]


# ------------------------------------------------------------------ registros de jornada
class JornadaRepository(_Sql):
    _SEL = ("SELECT rj.id, rj.alocacao_id, rj.entrada_real, rj.saida_real, a.funcionario_id "
            "FROM registros_jornada rj JOIN alocacoes a ON a.id = rj.alocacao_id")

    def add(self, j):
        novo = self._one("INSERT INTO registros_jornada (alocacao_id, entrada_real, saida_real) "
                         "VALUES (%s, %s, %s) RETURNING id", (_int(j.alocacao_id), j.inicio, j.fim))
        j.id = str(novo["id"])
        return j

    def update(self, j):
        self._run("UPDATE registros_jornada SET entrada_real = %s, saida_real = %s WHERE id = %s",
                  (j.inicio, j.fim, _int(j.id)))
        return j

    def _montar(self, r):
        return Jornada(funcionario_id=str(r["funcionario_id"]), inicio=r["entrada_real"], fim=r["saida_real"],
                       alocacao_id=str(r["alocacao_id"]), id=str(r["id"]))

    def get(self, id):
        i = _int(id)
        row = self._one(self._SEL + " WHERE rj.id = %s", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def get_by_alocacao(self, alocacao_id):
        i = _int(alocacao_id)
        row = self._one(self._SEL + " WHERE rj.alocacao_id = %s ORDER BY rj.id LIMIT 1", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def list_by_funcionario(self, funcionario_id):
        i = _int(funcionario_id)
        return [] if i is None else [self._montar(r) for r in self._all(
            self._SEL + " WHERE a.funcionario_id = %s AND rj.entrada_real IS NOT NULL ORDER BY rj.id", (i,))]

    def get_aberta(self, funcionario_id):
        i = _int(funcionario_id)
        row = self._one(self._SEL + " WHERE a.funcionario_id = %s AND rj.entrada_real IS NOT NULL "
                        "AND rj.saida_real IS NULL ORDER BY rj.id LIMIT 1", (i,)) if i is not None else None
        return self._montar(row) if row else None

    def list(self) -> List:
        return [self._montar(r) for r in self._all(self._SEL + " ORDER BY rj.id")]


def build_sql_repos(db) -> Repos:
    return Repos(funcionarios=FuncionarioRepository(db), veiculos=VeiculoRepository(db),
                 turnos=TurnoRepository(db), escalas=EscalaRepository(db),
                 disponibilidades=DisponibilidadeRepository(db), jornadas=JornadaRepository(db),
                 descansos=DescansoRepository(db), alocacoes=AlocacaoRepository(db))
