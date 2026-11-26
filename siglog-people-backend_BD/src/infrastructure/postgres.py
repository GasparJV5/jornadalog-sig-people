"""Conexão PostgreSQL (psycopg 3) e publicação de eventos via outbox transacional."""
import logging
import threading
from contextlib import contextmanager

from src.application.ports import EventPublisher
from src.domain import events as ev
from src.domain.events import DomainEvent
from src.infrastructure.publishers import log_json


class PostgresDatabase:
    """Uma conexão por thread/requisição. A API fecha a transação no fim de cada request
    (commit em sucesso, rollback em erro); fora do Flask, use `with db.transaction():`."""

    def __init__(self, connect_kwargs: dict):
        self._kwargs = connect_kwargs
        self._local = threading.local()

    @property
    def conn(self):
        import psycopg
        from psycopg.rows import dict_row
        c = getattr(self._local, "conn", None)
        if c is None or c.closed:
            c = psycopg.connect(**self._kwargs, row_factory=dict_row)
            self._local.conn = c
        return c

    def _atual(self):
        c = getattr(self._local, "conn", None)
        return c if c is not None and not c.closed else None

    def commit(self):
        if (c := self._atual()):
            c.commit()

    def rollback(self):
        if (c := self._atual()):
            c.rollback()

    def close(self):
        if (c := self._atual()):
            c.close()
        self._local.conn = None

    @contextmanager
    def transaction(self):
        try:
            yield self
            self.commit()
        except Exception:
            self.rollback()
            raise
        finally:
            self.close()


# Campo do payload que identifica o agregado de cada evento (outbox_eventos.agregado_id é BIGINT)
_AGREGADO = {
    ev.MOTORISTA_ESCALADO: "alocacao_id",
    ev.JORNADA_INICIADA: "jornada_id",
    ev.JORNADA_FINALIZADA: "jornada_id",
    ev.DESCANSO_REGISTRADO: "descanso_id",
    ev.CERTIFICACAO_ATUALIZADA: "funcionario_id",
    ev.CONFLITO_DE_JORNADA_DETECTADO: "funcionario_id",
}


class OutboxEventPublisher(EventPublisher):
    """Grava o evento em `outbox_eventos` NA MESMA transação da operação de negócio.
    Um processo separado (relay) deve ler as linhas PENDENTE e publicar no RabbitMQ.
    A coluna `payload` guarda o envelope completo (event_id, event, occurred_at, payload)."""

    def __init__(self, db: PostgresDatabase):
        self.db = db

    def publish(self, event: DomainEvent) -> None:
        from psycopg.types.json import Jsonb
        try:
            agregado = int(event.payload.get(_AGREGADO.get(event.name, ""), 0))
        except (TypeError, ValueError):
            agregado = 0
        self.db.conn.execute(
            "INSERT INTO outbox_eventos (tipo_evento, agregado_id, payload) VALUES (%s, %s, %s)",
            (event.name, agregado, Jsonb(event.to_dict())))
        log_json(logging.INFO, event.name, event_id=event.event_id, destino="outbox")
