"""Repositórios em memória (testes e modo dev). Troque por SQLAlchemy/PostgreSQL
implementando as mesmas operações — a camada de aplicação não muda."""
from typing import List, Optional

from src.application.ports import Repository


class MemoryRepository(Repository):
    def __init__(self):
        self._items = {}

    def add(self, entity):
        self._items[entity.id] = entity
        return entity

    def get(self, id: str):
        return self._items.get(id)

    def list(self) -> List:
        return list(self._items.values())

    def _where(self, **attrs) -> List:
        return [e for e in self._items.values()
                if all(getattr(e, k) == v for k, v in attrs.items())]


class FuncionarioRepository(MemoryRepository):
    def get_by_cpf(self, cpf: str):
        return next((f for f in self._items.values() if f.cpf == cpf), None)

    def list_by_tipo(self, tipo) -> List:
        return self._where(tipo=tipo)


class VeiculoRepository(MemoryRepository):
    pass


class TurnoRepository(MemoryRepository):
    pass


class EscalaRepository(MemoryRepository):
    def get_by_data_turno(self, data, turno_id):
        return next(iter(self._where(data=data, turno_id=turno_id)), None)


class _PorFuncionario(MemoryRepository):
    def list_by_funcionario(self, funcionario_id: str) -> List:
        return self._where(funcionario_id=funcionario_id)


class DisponibilidadeRepository(_PorFuncionario):
    pass


class DescansoRepository(_PorFuncionario):
    pass


class JornadaRepository(_PorFuncionario):
    def get_aberta(self, funcionario_id: str):
        return next((j for j in self.list_by_funcionario(funcionario_id) if j.aberta), None)


class AlocacaoRepository(_PorFuncionario):
    def list_by_veiculo(self, veiculo_id: str) -> List:
        return self._where(veiculo_id=veiculo_id)

    def list_by_escala(self, escala_id: str) -> List:
        return self._where(escala_id=escala_id)
