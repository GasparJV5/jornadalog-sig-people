import json
import logging
from typing import List

from src.application.ports import EventPublisher
from src.domain.events import DomainEvent

logger = logging.getLogger("siglog-people")


def log_json(level: int, event: str, **extra) -> None:
    """Log estruturado conforme padrão de observabilidade do Kit."""
    from datetime import datetime, timezone
    logger.log(level, json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(),
                                  "service": "siglog-people", "event": event,
                                  "level": logging.getLevelName(level), **extra}))


class InMemoryEventPublisher(EventPublisher):
    """Guarda eventos em memória (testes) e emite log estruturado."""

    def __init__(self):
        self.published: List[DomainEvent] = []

    def publish(self, event: DomainEvent) -> None:
        self.published.append(event)
        log_json(logging.INFO, event.name, event_id=event.event_id)

    def of(self, name: str) -> List[DomainEvent]:
        return [e for e in self.published if e.name == name]


class RabbitMQEventPublisher(EventPublisher):
    """Publica em exchange topic 'siglog.events' (routing key = nome do evento).
    Requer `pika`. Não é exercitado nos testes automatizados deste pacote."""

    def __init__(self, url: str, exchange: str = "siglog.events"):
        import pika  # import tardio: dependência opcional
        self._exchange = exchange
        self._conn = pika.BlockingConnection(pika.URLParameters(url))
        self._ch = self._conn.channel()
        self._ch.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)

    def publish(self, event: DomainEvent) -> None:
        self.publish_envelope(event.name, event.to_dict())

    def publish_envelope(self, nome: str, envelope: dict) -> None:
        """Publica um envelope já pronto (usado pelo relay da outbox)."""
        import pika
        self._ch.basic_publish(
            exchange=self._exchange, routing_key=nome,
            body=json.dumps(envelope),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2))
        log_json(logging.INFO, nome, event_id=envelope.get("event_id"), destino="rabbitmq")
