"""Parâmetros de negócio e de infraestrutura (sobrescrevíveis por variáveis de ambiente)."""
import os
from dataclasses import dataclass
from pathlib import Path

try:  # .env opcional (mesmo arquivo usado pelos scripts de migrations/seeds)
    from dotenv import load_dotenv
    for _pasta in Path(__file__).resolve().parents[:4]:
        if (_pasta / ".env").is_file():
            load_dotenv(_pasta / ".env", override=False)
            break
except ImportError:  # pragma: no cover
    pass


@dataclass(frozen=True)
class Settings:
    # Regras de jornada (referência: Lei 13.103/2015 - motorista profissional)
    jornada_max_horas: float = float(os.getenv("JORNADA_MAX_HORAS", "10"))
    descanso_minimo_horas: float = float(os.getenv("DESCANSO_MINIMO_HORAS", "11"))
    # Persistência: "memory" (padrão, usado nos testes) ou "postgres"
    persistence: str = os.getenv("PERSISTENCE", "memory")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "memory://")
    service_name: str = "siglog-people"

    def postgres_kwargs(self) -> dict:
        """Mesmas variáveis usadas por executar_migrations.py / executar_seeds.py."""
        senha = os.getenv("POSTGRES_PASSWORD")
        if not senha:
            raise ValueError("A variável POSTGRES_PASSWORD não foi configurada.")
        return {"host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": os.getenv("POSTGRES_PORT", "5432"),
                "dbname": os.getenv("POSTGRES_DB", "RH_Jornada"),
                "user": os.getenv("POSTGRES_USER", "rh_admin"),
                "password": senha}
