"""Parâmetros de negócio e de infraestrutura (sobrescrevíveis por variáveis de ambiente)."""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Regras de jornada (referência: Lei 13.103/2015 - motorista profissional)
    jornada_max_horas: float = float(os.getenv("JORNADA_MAX_HORAS", "10"))
    descanso_minimo_horas: float = float(os.getenv("DESCANSO_MINIMO_HORAS", "11"))
    # Infra
    database_url: str = os.getenv("DATABASE_URL", "memory://")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "memory://")
    service_name: str = "siglog-people"
