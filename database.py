import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "work_helper.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_query TEXT NOT NULL,
            encrypted_query TEXT NOT NULL,
            mapping TEXT NOT NULL,
            restored_query TEXT,
            created_at TEXT NOT NULL,
            restored_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_encryption(original: str, encrypted: str, mapping: dict) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO query_history (original_query, encrypted_query, mapping, created_at) VALUES (?, ?, ?, ?)",
        (original, encrypted, json.dumps(mapping, ensure_ascii=False), datetime.now().isoformat()),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def save_restoration(history_id: int, restored_query: str):
    conn = get_conn()
    conn.execute(
        "UPDATE query_history SET restored_query = ?, restored_at = ? WHERE id = ?",
        (restored_query, datetime.now().isoformat(), history_id),
    )
    conn.commit()
    conn.close()


def get_history_list():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, substr(original_query, 1, 80) as preview, created_at, restored_at FROM query_history ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_history_detail(history_id: int):
    conn = get_conn()
    row = conn.execute("SELECT * FROM query_history WHERE id = ?", (history_id,)).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["mapping"] = json.loads(result["mapping"])
        return result
    return None
