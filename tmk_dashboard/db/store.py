"""SQLite persistence replacing browser localStorage."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any

from config import DB_PATH, DATA_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat(sep=" ", timespec="seconds")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat(timespec="seconds")
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            pass
    return str(obj)


def _dumps(obj: Any) -> str:
    return json.dumps(obj, default=_json_default)


class Store:
    def __init__(self, path: Path | None = None) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path or DB_PATH
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
        with self._connect() as conn:
            conn.executescript(schema)

    # ---- settings ----
    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def set_setting(self, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, _dumps(value)),
            )

    # ---- project overrides ----
    def load_overrides(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute("SELECT project, resources_json, fin_rows_json, pd_json FROM project_overrides").fetchall()
        out = {}
        for r in rows:
            out[r["project"]] = {
                "resources": json.loads(r["resources_json"] or "[]"),
                "finRows": json.loads(r["fin_rows_json"] or "[]"),
                "pd": json.loads(r["pd_json"] or "{}"),
            }
        return out

    def save_project_override(self, project: str, resources=None, fin_rows=None, pd=None) -> None:
        existing = self.load_overrides().get(project, {})
        resources = resources if resources is not None else existing.get("resources", [])
        fin_rows = fin_rows if fin_rows is not None else existing.get("finRows", [])
        pd = pd if pd is not None else existing.get("pd", {})
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO project_overrides(project, resources_json, fin_rows_json, pd_json, updated_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(project) DO UPDATE SET
                     resources_json=excluded.resources_json,
                     fin_rows_json=excluded.fin_rows_json,
                     pd_json=excluded.pd_json,
                     updated_at=excluded.updated_at""",
                (project, _dumps(resources), _dumps(fin_rows), _dumps(pd), _now()),
            )

    def delete_project_override(self, project: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM project_overrides WHERE project=?", (project,))

    # ---- HLS ----
    def load_hls(self) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT payload_json FROM hls_data WHERE id=1").fetchone()
        return json.loads(row["payload_json"]) if row else {}

    def save_hls(self, payload: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO hls_data(id, payload_json, updated_at) VALUES(1,?,?)
                   ON CONFLICT(id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at""",
                (_dumps(payload), _now()),
            )

    # ---- Action items / FR ----
    def load_action_items(self) -> list:
        with self._connect() as conn:
            row = conn.execute("SELECT rows_json FROM action_items WHERE id=1").fetchone()
        return json.loads(row["rows_json"]) if row else []

    def save_action_items(self, rows: list) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO action_items(id, rows_json, updated_at) VALUES(1,?,?)
                   ON CONFLICT(id) DO UPDATE SET rows_json=excluded.rows_json, updated_at=excluded.updated_at""",
                (_dumps(rows), _now()),
            )

    def load_fr_items(self) -> list:
        with self._connect() as conn:
            row = conn.execute("SELECT rows_json FROM fr_items WHERE id=1").fetchone()
        return json.loads(row["rows_json"]) if row else []

    def save_fr_items(self, rows: list) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO fr_items(id, rows_json, updated_at) VALUES(1,?,?)
                   ON CONFLICT(id) DO UPDATE SET rows_json=excluded.rows_json, updated_at=excluded.updated_at""",
                (_dumps(rows), _now()),
            )

    # ---- Milestone ----
    def load_ms_updates(self) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT updates_json FROM ms_project_updates WHERE id=1").fetchone()
        return json.loads(row["updates_json"]) if row else {}

    def save_ms_updates(self, updates: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO ms_project_updates(id, updates_json, updated_at) VALUES(1,?,?)
                   ON CONFLICT(id) DO UPDATE SET updates_json=excluded.updates_json, updated_at=excluded.updated_at""",
                (_dumps(updates), _now()),
            )

    def load_ms_highlights(self) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT raw_text, sections_json FROM ms_highlights WHERE id=1").fetchone()
        if not row:
            return {"raw": "", "sections": {}}
        return {"raw": row["raw_text"] or "", "sections": json.loads(row["sections_json"] or "{}")}

    def save_ms_highlights(self, raw: str, sections: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO ms_highlights(id, raw_text, sections_json, updated_at) VALUES(1,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET raw_text=excluded.raw_text, sections_json=excluded.sections_json, updated_at=excluded.updated_at""",
                (raw, _dumps(sections), _now()),
            )

    def load_milestones(self) -> dict:
        with self._connect() as conn:
            row = conn.execute("SELECT milestones_json, phases_json FROM milestones WHERE id=1").fetchone()
        if not row:
            return {"milestones": [], "phases": []}
        return {
            "milestones": json.loads(row["milestones_json"] or "[]"),
            "phases": json.loads(row["phases_json"] or "[]"),
        }

    def save_milestones(self, milestones: list, phases: list) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO milestones(id, milestones_json, phases_json, updated_at) VALUES(1,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET milestones_json=excluded.milestones_json, phases_json=excluded.phases_json, updated_at=excluded.updated_at""",
                (_dumps(milestones), _dumps(phases), _now()),
            )

    # ---- Commercials ----
    def load_commercials(self) -> list:
        with self._connect() as conn:
            row = conn.execute("SELECT rows_json FROM commercials WHERE id=1").fetchone()
        return json.loads(row["rows_json"]) if row else []

    def save_commercials(self, rows: list) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO commercials(id, rows_json, updated_at) VALUES(1,?,?)
                   ON CONFLICT(id) DO UPDATE SET rows_json=excluded.rows_json, updated_at=excluded.updated_at""",
                (_dumps(rows), _now()),
            )

    # ---- Changelog ----
    def log_change(self, action: str, detail: str = "", user_name: str = "User") -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO changelog(ts, action, detail, user_name) VALUES(?,?,?,?)",
                (_now(), action, detail, user_name),
            )
            # Keep last 200
            conn.execute(
                """DELETE FROM changelog WHERE id NOT IN (
                     SELECT id FROM changelog ORDER BY id DESC LIMIT 200
                   )"""
            )

    def load_changelog(self) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, action, detail, user_name FROM changelog ORDER BY id DESC LIMIT 200"
            ).fetchall()
        return [dict(r) for r in rows]

    def clear_changelog(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM changelog")
