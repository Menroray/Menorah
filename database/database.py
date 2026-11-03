import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("FEES_TRACKER_DB_PATH", BASE_DIR / "web_demo.db")).expanduser()
RECEIPTS_DIR = BASE_DIR / "receipts"
BACKUP_DIR = BASE_DIR / "database_backups"


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def connect_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, factory=ClosingConnection)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db():
    with connect_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                class_grade TEXT NOT NULL,
                term_fees_billed REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                amount_paid REAL NOT NULL,
                date_paid TEXT NOT NULL,
                term_name TEXT NOT NULL,
                payment_method TEXT DEFAULT 'Cash',
                paid_by TEXT DEFAULT '',
                class_grade TEXT DEFAULT '',
                FOREIGN KEY(student_id) REFERENCES students(student_id) ON DELETE CASCADE
            )
            """
        )
        payment_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(payments)").fetchall()
        }
        for column_name, column_definition in {
            "payment_method": "TEXT DEFAULT 'Cash'",
            "paid_by": "TEXT DEFAULT ''",
            "class_grade": "TEXT DEFAULT ''",
        }.items():
            if column_name not in payment_columns:
                conn.execute(
                    f"ALTER TABLE payments ADD COLUMN {column_name} {column_definition}"
                )
        conn.commit()
