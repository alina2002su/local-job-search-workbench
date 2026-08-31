from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

SCHEMA = """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS applications (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 job_pool_id INTEGER,
 company TEXT NOT NULL DEFAULT '', position TEXT NOT NULL DEFAULT '', business TEXT DEFAULT '', city TEXT DEFAULT '',
 external_job_id TEXT DEFAULT '', raw_title TEXT DEFAULT '', source_url TEXT DEFAULT '', jd_file_path TEXT DEFAULT '',
 jd_content TEXT DEFAULT '', jd_content_hash TEXT DEFAULT '', applied_date TEXT, current_status TEXT NOT NULL DEFAULT '已投递',
 next_action TEXT DEFAULT '', next_event_at TEXT, resume_path TEXT DEFAULT '', resume_filename TEXT DEFAULT '', notes TEXT DEFAULT '',
 interview_notes TEXT DEFAULT '', prep_content TEXT DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 last_status_changed_at TEXT NOT NULL, manual_fields TEXT NOT NULL DEFAULT '[]',
 FOREIGN KEY(job_pool_id) REFERENCES job_pool(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS job_pool (
 id INTEGER PRIMARY KEY AUTOINCREMENT, feishu_record_id TEXT NOT NULL UNIQUE,
 company TEXT DEFAULT '', position TEXT DEFAULT '', business TEXT DEFAULT '', city TEXT DEFAULT '', job_direction TEXT DEFAULT '',
 external_job_id TEXT DEFAULT '', jd_url TEXT DEFAULT '', deadline TEXT, source TEXT DEFAULT '', priority TEXT DEFAULT '',
 application_recommendation TEXT DEFAULT '', match_points TEXT DEFAULT '', risk_points TEXT DEFAULT '', career_moat TEXT DEFAULT '',
 career_moat_description TEXT DEFAULT '', ai_replacement_risk TEXT DEFAULT '', pool_status TEXT DEFAULT '', jd_text TEXT DEFAULT '',
 notes TEXT DEFAULT '', linked_application_id INTEGER, last_synced_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 local_pool_status TEXT NOT NULL DEFAULT '',
 FOREIGN KEY(linked_application_id) REFERENCES applications(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_job_pool_external ON job_pool(external_job_id);
CREATE TABLE IF NOT EXISTS job_pool_dismissals (
 feishu_record_id TEXT PRIMARY KEY, deleted_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_app_status ON applications(current_status);
CREATE INDEX IF NOT EXISTS idx_app_next ON applications(next_event_at);
CREATE TABLE IF NOT EXISTS status_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER NOT NULL, old_status TEXT, new_status TEXT NOT NULL,
 changed_at TEXT NOT NULL, FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS todos (
 id INTEGER PRIMARY KEY AUTOINCREMENT, application_id INTEGER, title TEXT NOT NULL, task_type TEXT DEFAULT 'manual',
 source_stage TEXT DEFAULT '', due_at TEXT, status TEXT NOT NULL DEFAULT 'pending', auto_generated INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT,
 FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_todo_status_due ON todos(status,due_at);
CREATE TABLE IF NOT EXISTS todo_dismissals (
 application_id INTEGER NOT NULL, task_type TEXT NOT NULL, source_stage TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
 PRIMARY KEY(application_id,task_type,source_stage),
 FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS imported_files (
 id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT NOT NULL UNIQUE, file_hash TEXT NOT NULL, last_modified REAL,
 application_id INTEGER, imported_at TEXT NOT NULL, FOREIGN KEY(application_id) REFERENCES applications(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

class Database:
    def __init__(self, path: str, timezone: str = "Asia/Shanghai"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.tz = ZoneInfo(timezone)
        self._lock = threading.RLock()
        self.initialize()

    def now(self) -> str:
        return datetime.now(self.tz).isoformat(timespec="seconds")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path), timeout=20, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        with self._lock, self.connect() as conn:
            conn.executescript(SCHEMA)
            columns={row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
            if "manual_fields" not in columns:
                conn.execute("ALTER TABLE applications ADD COLUMN manual_fields TEXT NOT NULL DEFAULT '[]'")
                # 升级已有数据时优先保护用户当前看到并可能已手动确认的业务字段。
                conn.execute("UPDATE applications SET manual_fields=?",(json.dumps(["company","position","business","city"],ensure_ascii=False),))
            if "next_action" not in columns:
                conn.execute("ALTER TABLE applications ADD COLUMN next_action TEXT NOT NULL DEFAULT ''")
            job_pool_columns={row[1] for row in conn.execute("PRAGMA table_info(job_pool)").fetchall()}
            if "local_pool_status" not in job_pool_columns:
                conn.execute("ALTER TABLE job_pool ADD COLUMN local_pool_status TEXT NOT NULL DEFAULT ''")

    def all(self, sql: str, params=()):
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params=()):
        with self.connect() as conn:
            row = conn.execute(sql, params).fetchone()
            return dict(row) if row else None

    def execute(self, sql: str, params=()):
        with self._lock, self.connect() as conn:
            cur = conn.execute(sql, params)
            return cur.lastrowid

    def set_setting(self, key: str, value):
        self.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, ensure_ascii=False)))

    def get_setting(self, key: str, default=None):
        row = self.one("SELECT value FROM settings WHERE key=?", (key,))
        if not row: return default
        try: return json.loads(row["value"])
        except Exception: return row["value"]

_db = None
def get_db() -> Database:
    if _db is None: raise RuntimeError("数据库尚未初始化")
    return _db
def configure_db(path: str, timezone: str = "Asia/Shanghai"):
    global _db
    _db = Database(path, timezone)
    return _db
