CREATE TABLE IF NOT EXISTS project_overrides (
    project TEXT PRIMARY KEY,
    resources_json TEXT,
    fin_rows_json TEXT,
    pd_json TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS hls_data (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    payload_json TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS action_items (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    rows_json TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS fr_items (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    rows_json TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ms_project_updates (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    updates_json TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ms_highlights (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    raw_text TEXT,
    sections_json TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS changelog (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    user_name TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS commercials (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    rows_json TEXT NOT NULL,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS milestones (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    milestones_json TEXT,
    phases_json TEXT,
    updated_at TEXT
);