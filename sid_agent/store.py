"""SQLite store for SidAgent: tasks, internship applications, memories.

Zero external dependencies (stdlib sqlite3). One file DB; pass ":memory:"
for tests.
"""
import sqlite3
from datetime import datetime, timezone

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    due TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'applied',
    applied_on TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path=":memory:"):
        # check_same_thread=False: the FastAPI layer serves requests from a
        # worker thread; the store is single-process dev-scale, so sharing
        # one connection is fine.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self):
        self._conn.close()

    # -- tasks ------------------------------------------------------------
    def create_task(self, title, due=None):
        cur = self._conn.execute(
            "INSERT INTO tasks (title, due, created_at) VALUES (?, ?, ?)",
            (title, due, _now()),
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "title": title, "due": due, "status": "open"}

    def list_tasks(self, status="open"):
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY COALESCE(due, '9999'), id",
            (status,),
        ).fetchall()
        return [dict(r) for r in rows]

    def complete_task(self, task_id):
        cur = self._conn.execute(
            "UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,)
        )
        self._conn.commit()
        return {"id": task_id, "updated": cur.rowcount > 0}

    # -- applications -----------------------------------------------------
    def log_application(self, company, role, status="applied", notes=None):
        cur = self._conn.execute(
            "INSERT INTO applications (company, role, status, applied_on, notes, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (company, role, status, _now()[:10], notes, _now()),
        )
        self._conn.commit()
        return {"id": cur.lastrowid, "company": company, "role": role, "status": status}

    def list_applications(self):
        rows = self._conn.execute(
            "SELECT * FROM applications ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_application(self, company, status):
        cur = self._conn.execute(
            "UPDATE applications SET status = ? WHERE lower(company) = lower(?)",
            (status, company),
        )
        self._conn.commit()
        return {"company": company, "status": status, "updated": cur.rowcount}

    # -- memories ---------------------------------------------------------
    def add_memory(self, key, value):
        self._conn.execute(
            "INSERT INTO memories (key, value, created_at) VALUES (?, ?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value, _now()),
        )
        self._conn.commit()
        return {"key": key, "value": value}

    def recall_memory(self, key):
        row = self._conn.execute(
            "SELECT value FROM memories WHERE key = ?", (key,)
        ).fetchone()
        return {"key": key, "value": row["value"] if row else None}
