"""Aplica as migrations de database/migrations/ em ordem, registrando-as em controle_migrations.

Uso:  python database/scripts/executar_migrations.py
Cada arquivo roda em UMA transação (DDL é transacional no PostgreSQL): se falhar, nada dele é
aplicado e o script para. Arquivos já registrados são ignorados (pode rodar quantas vezes quiser).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _conexao import RAIZ, conectar  # noqa: E402

PASTA = RAIZ / "database" / "migrations"


def arquivos():
    return sorted(PASTA.glob("*.sql"), key=lambda p: p.name)


def ja_aplicadas(conn) -> set:
    existe = conn.execute("SELECT to_regclass('public.controle_migrations')").fetchone()[0]
    if not existe:
        return set()          # banco virgem: a 000 cria a tabela de controle
    return {r[0] for r in conn.execute("SELECT versao FROM controle_migrations")}


def main() -> int:
    with conectar() as conn:
        aplicadas = ja_aplicadas(conn)
        novas = 0
        for arq in arquivos():
            versao = arq.stem
            if versao in aplicadas:
                print(f"= {arq.name} (já aplicada)")
                continue
            try:
                conn.execute(arq.read_text(encoding="utf-8"))
                conn.execute("INSERT INTO controle_migrations (versao, nome_arquivo) VALUES (%s, %s)",
                             (versao, arq.name))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"x {arq.name}: {e}", file=sys.stderr)
                return 1
            print(f"+ {arq.name}")
            novas += 1
        print(f"Concluído: {novas} migration(s) aplicada(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
