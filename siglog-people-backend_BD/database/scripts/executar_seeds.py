"""Aplica os seeds de database/seeds/ (idempotentes: usam ON CONFLICT DO NOTHING).

Uso:  python database/scripts/executar_seeds.py   (depois das migrations)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _conexao import RAIZ, conectar  # noqa: E402

PASTA = RAIZ / "database" / "seeds"


def main() -> int:
    with conectar() as conn:
        for arq in sorted(PASTA.glob("*.sql"), key=lambda p: p.name):
            try:
                conn.execute(arq.read_text(encoding="utf-8"))
                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"x {arq.name}: {e}", file=sys.stderr)
                return 1
            print(f"+ {arq.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
