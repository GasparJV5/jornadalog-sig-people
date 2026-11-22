import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Caminho raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parents[2]

# Carrega as variáveis do arquivo .env
# Carrega as variáveis do arquivo .env
load_dotenv(RAIZ_PROJETO / ".env", override=True)


# Configurações do PostgreSQL
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "RH_Jornada"),
    "user": os.getenv("POSTGRES_USER", "rh_admin"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}


if not DB_CONFIG["password"]:
    raise ValueError("POSTGRES_PASSWORD não foi encontrada no arquivo .env")

# Pasta onde ficam os arquivos SQL das migrations
PASTA_MIGRATIONS = RAIZ_PROJETO / "database" / "migrations"


def listar_migrations():
    arquivos = sorted(PASTA_MIGRATIONS.glob("*.sql"))
    return arquivos

def obter_migrations_aplicadas(conexao):
    with conexao.cursor() as cursor:
        cursor.execute("""
            SELECT versao
            FROM controle_migrations
        """)

        resultados = cursor.fetchall()

    return {linha[0] for linha in resultados}

def executar_migration(conexao, arquivo):
    versao = arquivo.name.split("_")[0]

    with conexao.transaction():
        with conexao.cursor() as cursor:
            sql = arquivo.read_text(encoding="utf-8")
            cursor.execute(sql)

            cursor.execute(
                """
                INSERT INTO controle_migrations (versao, nome_arquivo)
                VALUES (%s, %s)
                """,
                (versao, arquivo.name)
            )

    print(f"Migration {arquivo.name} aplicada com sucesso!")

def main():
    try:
        with psycopg.connect(**DB_CONFIG) as conexao:
            print("Conectado ao PostgreSQL!")

            # Verifica se a tabela de controle já existe
            with conexao.cursor() as cursor:
                cursor.execute(
                    "SELECT to_regclass('public.controle_migrations')"
                )
                tabela_existe = cursor.fetchone()[0] is not None

            # Em um banco novo, cria a tabela de controle primeiro
            if not tabela_existe:
                migration_controle = next(
                    (
                        arquivo
                        for arquivo in listar_migrations()
                        if arquivo.name.startswith("000_")
                    ),
                    None
                )

                if migration_controle is None:
                    raise FileNotFoundError(
                        "Migration 000_controle_migrations.sql não encontrada."
                    )

                executar_migration(conexao, migration_controle)

            aplicadas = obter_migrations_aplicadas(conexao)

            for arquivo in listar_migrations():
                versao = arquivo.name.split("_")[0]

                if versao not in aplicadas:
                    executar_migration(conexao, arquivo)
                else:
                    print(f"Migration {arquivo.name} já foi aplicada.")

            print("Verificação de migrations concluída!")

    except Exception as erro:
        print(f"Erro ao executar migrations: {erro}")


if __name__ == "__main__":
    main()