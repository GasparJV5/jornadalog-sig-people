
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv


# Caminho raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parents[2]

# Carrega o .env sem sobrescrever variáveis já definidas no ambiente
load_dotenv(RAIZ_PROJETO / ".env", override=False)


# Configurações do PostgreSQL
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
    "dbname": os.getenv("POSTGRES_DB", "RH_Jornada"),
    "user": os.getenv("POSTGRES_USER", "rh_admin"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

# Pasta onde ficam os arquivos SQL das migrations
PASTA_MIGRATIONS = RAIZ_PROJETO / "database" / "migrations"

# Padrão esperado: 001_nome_da_migration.sql
PADRAO_MIGRATION = re.compile(r"^(\d{3})_[a-zA-Z0-9_-]+\.sql$")


def listar_migrations():
    """Localiza e valida os arquivos de migration."""
    if not PASTA_MIGRATIONS.is_dir():
        raise FileNotFoundError(
            f"Pasta de migrations não encontrada: {PASTA_MIGRATIONS}"
        )

    arquivos = sorted(PASTA_MIGRATIONS.glob("*.sql"))

    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo SQL de migration encontrado.")

    versoes = []

    for arquivo in arquivos:
        correspondencia = PADRAO_MIGRATION.match(arquivo.name)

        if not correspondencia:
            raise ValueError(
                f"Nome de migration inválido: {arquivo.name}. "
                "Use o padrão NNN_nome.sql."
            )

        versoes.append(correspondencia.group(1))

    if len(versoes) != len(set(versoes)):
        raise ValueError("Existem migrations com versões duplicadas.")

    if "000" not in versoes:
        raise FileNotFoundError(
            "Migration 000_controle_migrations.sql não encontrada."
        )

    return arquivos


def obter_migrations_aplicadas(conexao):
    """Retorna as versões já registradas no banco."""
    with conexao.cursor() as cursor:
        cursor.execute("""
            SELECT versao
            FROM controle_migrations
        """)

        resultados = cursor.fetchall()

    return {linha[0] for linha in resultados}


def executar_migration(conexao, arquivo):
    """Executa uma migration e registra sua versão na mesma transação."""
    versao = arquivo.name.split("_", 1)[0]
    sql = arquivo.read_text(encoding="utf-8")

    if not sql.strip():
        raise ValueError(f"A migration {arquivo.name} está vazia.")

    with conexao.transaction():
        with conexao.cursor() as cursor:
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
        if not DB_CONFIG["password"]:
            raise ValueError(
                "A variável POSTGRES_PASSWORD não foi configurada."
            )

        migrations = listar_migrations()

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
                    arquivo
                    for arquivo in migrations
                    if arquivo.name.startswith("000_")
                )

                executar_migration(conexao, migration_controle)

            aplicadas = obter_migrations_aplicadas(conexao)

            # Não tenta recriar uma tabela de controle existente
            if "000" not in aplicadas:
                raise RuntimeError(
                    "A tabela controle_migrations existe, mas a versão "
                    "000 não está registrada. A execução foi interrompida "
                    "para evitar alterações inseguras no banco."
                )

            # Executa somente migrations ainda não aplicadas
            for arquivo in migrations:
                versao = arquivo.name.split("_", 1)[0]

                if versao in aplicadas:
                    print(f"Migration {arquivo.name} já foi aplicada.")
                    continue

                executar_migration(conexao, arquivo)
                aplicadas.add(versao)

            print("Verificação de migrations concluída!")
            return 0

    except Exception as erro:
        print(f"Erro ao executar migrations: {erro}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
