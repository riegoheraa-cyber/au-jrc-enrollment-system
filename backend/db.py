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
        if _has_unique_lrn(conn):
            _drop_unique_lrn(conn)


def _has_unique_lrn(conn: sqlite3.Connection) -> bool:
    rows = conn.execute("PRAGMA index_list('students')").fetchall()
    for row in rows:
        if not row["unique"]:
            continue
        index_name = row["name"]
        info = conn.execute(f"PRAGMA index_info('{index_name}')").fetchall()
        if len(info) == 1 and info[0]["name"] == "lrn":
            return True
    return False


def _drop_unique_lrn(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = OFF;")
    conn.executescript(
        """
        ALTER TABLE students RENAME TO students_old;

        CREATE TABLE students (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          lrn TEXT NOT NULL,
          fullName TEXT NOT NULL,
          email TEXT,
          contact TEXT,
          address TEXT,
          dob TEXT,
          pob TEXT,
          sex TEXT,
          nationality TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        INSERT INTO students (
          id, lrn, fullName, email, contact, address,
          dob, pob, sex, nationality, created_at
        )
        SELECT
          id, lrn, fullName, email, contact, address,
          dob, pob, sex, nationality, created_at
        FROM students_old;

        DROP TABLE students_old;

        CREATE INDEX IF NOT EXISTS idx_students_lrn ON students(lrn);
        CREATE INDEX IF NOT EXISTS idx_students_fullName ON students(fullName);
        """
    )
    conn.execute("PRAGMA foreign_keys = ON;")

