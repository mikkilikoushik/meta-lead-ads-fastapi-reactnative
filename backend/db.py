import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from config import DATABASE_PATH

_lock = threading.Lock()
_conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row


def init_db() -> None:
    with _lock:
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS leads (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                meta_lead_id  TEXT NOT NULL UNIQUE,
                name          TEXT,
                email         TEXT,
                phone         TEXT,
                form_id       TEXT,
                page_id       TEXT,
                created_time  TEXT NOT NULL,
                raw           TEXT,
                received_at   TEXT NOT NULL
            )
            """
        )
        _conn.commit()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "meta_lead_id": row["meta_lead_id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "form_id": row["form_id"],
        "page_id": row["page_id"],
        "created_time": row["created_time"],
    }


def insert_lead(
    *,
    meta_lead_id: str,
    name: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    form_id: Optional[str],
    page_id: Optional[str],
    created_time: str,
    raw: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Insert a lead. Returns the stored row, or None if it already existed (Meta retries webhooks)."""
    with _lock:
        cur = _conn.execute(
            """
            INSERT OR IGNORE INTO leads
                (meta_lead_id, name, email, phone, form_id, page_id, created_time, raw, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meta_lead_id,
                name,
                email,
                phone,
                form_id,
                page_id,
                created_time,
                json.dumps(raw),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        _conn.commit()
        if cur.rowcount == 0:
            return None
        row = _conn.execute("SELECT * FROM leads WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _row_to_dict(row)


def list_leads(limit: int = 100) -> list[dict[str, Any]]:
    with _lock:
        rows = _conn.execute(
            "SELECT * FROM leads ORDER BY created_time DESC, id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
