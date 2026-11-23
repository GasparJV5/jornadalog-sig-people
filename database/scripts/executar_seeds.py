"""Executa os arquivos SQL de dados iniciais do banco."""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Caminho raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parents[2]

# Carrega as variáveis de ambiente
load_dotenv(RAIZ_PROJETO / ".env", override=False)


# Configurações do PostgreSQL
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "RH_Jornada"),
    "user": os.getenv("POSTGRES_USER", "rh_admin"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

# Pasta dos arquivos SQL de Seeds
PASTA_SEEDS = RAIZ_PROJETO / "database" / "seeds"


def listar_seeds():
    """Localiza os arquivos SQL de Seeds."""
    if not PASTA_SEEDS.is_dir():
        raise FileNotFoundError(
            f"Pasta de Seeds não encontrada: {PASTA_SEEDS}"
        )

    arquivos = sorted(PASTA_SEEDS.glob("*.sql"))

    if not arquivos:
        raise FileNotFoundError(
            "Nenhum arquivo SQL de Seeds encontrado."
        )

    return arquivos


def main():
    try:
        if not DB_CONFIG["password"]:
            raise ValueError(
                "A variável POSTGRES_PASSWORD não foi configurada."
            )

        seeds = listar_seeds()

        with psycopg.connect(**DB_CONFIG) as conexao:
            print("Conectado ao PostgreSQL!")

            # Executa todos os Seeds na mesma transação
            with conexao.transaction():
                with conexao.cursor() as cursor:
                    for arquivo in seeds:
                        sql = arquivo.read_text(encoding="utf-8")

                        if not sql.strip():
                            raise ValueError(
                                f"O arquivo {arquivo.name} está vazio."
                            )

                        cursor.execute(sql)
                        print(
                            f"Seed {arquivo.name} executado com sucesso!"
                        )

            print("Execução dos Seeds concluída!")
            return 0

    except Exception as erro:
        print(f"Erro ao executar Seeds: {erro}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
