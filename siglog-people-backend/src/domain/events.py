"""Eventos de domínio publicados pelo módulo RH (catálogo A.6 do Kit)."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

MOTORISTA_ESCALADO = "MotoristaEscalado"
JORNADA_INICIADA = "JornadaIniciada"
JORNADA_FINALIZADA = "JornadaFinalizada"
DESCANSO_REGISTRADO = "DescansoRegistrado"
CERTIFICACAO_ATUALIZADA = "CertificacaoAtualizada"
CONFLITO_DE_JORNADA_DETECTADO = "ConflitoDeJornadaDetectado"


@dataclass(frozen=True)
class DomainEvent:
    name: str
    payload: dict
    event_id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {"event_id": self.event_id, "event": self.name,
                "occurred_at": self.occurred_at, "payload": self.payload}
