"""Conexão compartilhada pelos scripts de banco (mesmas variáveis do backend)."""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
    if (RAIZ / ".env").is_file():
        load_dotenv(RAIZ / ".env", override=False)
except ImportError:  # python-dotenv é opcional
    pass


def conectar():
    import psycopg
    senha = os.getenv("POSTGRES_PASSWORD")
    if not senha:
        raise SystemExit("A variável POSTGRES_PASSWORD não foi configurada.")
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "RH_Jornada"),
        user=os.getenv("POSTGRES_USER", "rh_admin"),
        password=senha,
    )
