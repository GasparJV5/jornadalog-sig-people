"""Relay da outbox: lê `outbox_eventos` (PENDENTE) e publica no RabbitMQ.

Execução (processo separado da API):
    RABBITMQ_URL=amqp://guest:guest@localhost:5672/ python -m src.infrastructure.outbox_relay

Garantias
* At-least-once: o evento só vira PROCESSADO depois de publicado; se o processo cair entre
  publicar e gravar, ele é reenviado -> consumidores devem deduplicar por `event_id`.
* Vários relays em paralelo são seguros (FOR UPDATE SKIP LOCKED).
* Em falha, incrementa `tentativas` e grava `erro`; ao atingir o máximo vira ERRO (sai da fila).
"""
import logging
import os
import time
from typing import Optional

from src.infrastructure.publishers import log_json

SELECIONAR = ("SELECT id, tipo_evento, payload, tentativas FROM outbox_eventos "
              "WHERE status = 'PENDENTE' ORDER BY criado_em, id LIMIT %s FOR UPDATE SKIP LOCKED")
MARCAR_OK = ("UPDATE outbox_eventos SET status = 'PROCESSADO', processado_em = CURRENT_TIMESTAMP, "
             "tentativas = tentativas + 1, erro = NULL WHERE id = %s")
MARCAR_FALHA = ("UPDATE outbox_eventos SET tentativas = tentativas + 1, erro = %s, status = %s "
                "WHERE id = %s")


def processar_lote(db, publisher, tamanho: int = 50, max_tentativas: int = 5) -> int:
    """Publica até `tamanho` eventos pendentes numa transação. Retorna quantos foram publicados.
    Na primeira falha de um evento ainda dentro do limite de tentativas, interrompe o lote
    (preserva a ordem) e tenta de novo no próximo ciclo."""
    publicados = 0
    try:
        for ev in db.conn.execute(SELECIONAR, (tamanho,)).fetchall():
            try:
                publisher.publish_envelope(ev["tipo_evento"], ev["payload"])
            except Exception as e:  # noqa: BLE001 - qualquer falha de publicação é registrada
                tentativas = ev["tentativas"] + 1
                esgotou = tentativas >= max_tentativas
                db.conn.execute(MARCAR_FALHA, (str(e)[:1000], "ERRO" if esgotou else "PENDENTE", ev["id"]))
                log_json(logging.ERROR, ev["tipo_evento"], outbox_id=ev["id"], tentativas=tentativas,
                         status="ERRO" if esgotou else "PENDENTE", erro=str(e)[:200])
                if esgotou:
                    continue
                break
            db.conn.execute(MARCAR_OK, (ev["id"],))
            publicados += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return publicados


def main(intervalo: Optional[float] = None) -> None:  # pragma: no cover - laço de execução
    from src.config.settings import Settings
    from src.infrastructure.postgres import PostgresDatabase
    from src.infrastructure.publishers import RabbitMQEventPublisher

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings(persistence="postgres")
    if settings.rabbitmq_url.startswith("memory://"):
        raise SystemExit("Defina RABBITMQ_URL (ex.: amqp://guest:guest@localhost:5672/).")
    db = PostgresDatabase(settings.postgres_kwargs())
    publisher = RabbitMQEventPublisher(settings.rabbitmq_url)
    espera = intervalo if intervalo is not None else float(os.getenv("OUTBOX_INTERVALO_SEGUNDOS", "2"))
    maximo = int(os.getenv("OUTBOX_MAX_TENTATIVAS", "5"))
    while True:
        try:
            n = processar_lote(db, publisher, max_tentativas=maximo)
        except Exception:  # banco ou broker fora do ar: loga e tenta de novo
            logging.getLogger("siglog-people").exception("falha no relay da outbox")
            n = 0
        if n == 0:
            time.sleep(espera)


if __name__ == "__main__":
    main()
