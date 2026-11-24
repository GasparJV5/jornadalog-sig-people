import os, sqlite3
from pathlib import Path
DB=Path(os.getenv('SQLITE_PATH','database/jornadalog.db'))
def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    schema=Path('database/schema_sqlite.sql').read_text(encoding='utf-8')
    seed=Path('database/seed.sql').read_text(encoding='utf-8')
    with connect() as c:
        c.executescript(schema)
        c.executescript(seed)
