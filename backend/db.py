import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "enrollment.db"

def get_conn() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db() -> None:
    schema_path = BASE_DIR / "schema.sql"
    with get_conn() as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))

