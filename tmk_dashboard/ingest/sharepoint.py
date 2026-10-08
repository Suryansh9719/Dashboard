"""Auto-load source workbooks from SharePoint-synced local folder (Option 1)."""
from __future__ import annotations

from pathlib import Path

import requests

from config import (
    AUTO_LOAD_FROM_SHAREPOINT,
    LOCAL_ALLOCATION_SEARCH_DIRS,
    LOCAL_HIGHLIGHTS_PDF,
    LOCAL_MILESTONE_XLSX,
    LOCAL_RESOURCE_ALLOCATION,
    LOCAL_RESOURCE_INFO_TRACKER,
    SP_FILE1_URL,
    SP_FILE2_URL,
    USE_LOCAL_SYNC_PATHS,
)

# Last successfully resolved paths (for Home status messages)
_LAST_TRACKER_PATH: str | None = None
_LAST_ALLOCATION_PATH: str | None = None


def _read_local(path: str | Path) -> bytes:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {p}")
    return p.read_bytes()


def _file_stamp(path: str | Path) -> tuple[str, int, float] | None:
    p = Path(path)
    if not p.is_file():
        return None
    st = p.stat()
    return (p.name, st.st_size, st.st_mtime)


def resolve_allocation_path() -> Path | None:
    """Pick the newest Resource Allocation workbook from configured candidates.

    Scans the configured path plus LOCAL_ALLOCATION_SEARCH_DIRS for
    *Allocation*.xlsx / *allocation*.xlsx so a newer Downloads copy wins over
    a stale SharePoint-sync copy (fixes 29 vs 30 project mismatches).
    """
    candidates: dict[str, Path] = {}
    configured = Path(LOCAL_RESOURCE_ALLOCATION)
    if configured.is_file():
        candidates[str(configured.resolve())] = configured

    dirs: list[Path] = []
    if configured.parent.is_dir():
        dirs.append(configured.parent)
    for d in LOCAL_ALLOCATION_SEARCH_DIRS:
        p = Path(d)
        if p.is_dir() and p not in dirs:
            dirs.append(p)

    patterns = ("*Allocation*.xlsx", "*allocation*.xlsx", "*Allocation*.xlsm")
    for folder in dirs:
        for pat in patterns:
            for hit in folder.glob(pat):
                if hit.is_file():
                    candidates[str(hit.resolve())] = hit

    if not candidates:
        return configured if configured.is_file() else None

    return max(candidates.values(), key=lambda p: p.stat().st_mtime)


def last_loaded_paths() -> dict[str, str | None]:
    return {
        "tracker": _LAST_TRACKER_PATH,
        "allocation": _LAST_ALLOCATION_PATH,
    }


def fetch_url(url: str, timeout: int = 60) -> bytes:
    resp = requests.get(url, timeout=timeout, headers={"Cache-Control": "no-store"})
    resp.raise_for_status()
    return resp.content


def try_auto_load() -> tuple[bytes, bytes] | None:
    """Return (tracker_bytes, allocation_bytes) or None.

    Prefer OneDrive/SharePoint-synced local paths when USE_LOCAL_SYNC_PATHS is True.
    Allocation file = newest matching workbook across search dirs.
    Falls back to HTTP SharePoint URLs only if configured and reachable (usually needs auth).
    """
    global _LAST_TRACKER_PATH, _LAST_ALLOCATION_PATH

    if not AUTO_LOAD_FROM_SHAREPOINT:
        return None

    if USE_LOCAL_SYNC_PATHS:
        try:
            tracker = Path(LOCAL_RESOURCE_INFO_TRACKER)
            alloc = resolve_allocation_path()
            if not tracker.is_file() or alloc is None:
                return None
            f1 = _read_local(tracker)
            f2 = _read_local(alloc)
            _LAST_TRACKER_PATH = str(tracker)
            _LAST_ALLOCATION_PATH = str(alloc)
            return f1, f2
        except Exception:
            return None

    try:
        f1 = fetch_url(SP_FILE1_URL)
        f2 = fetch_url(SP_FILE2_URL)
        _LAST_TRACKER_PATH = SP_FILE1_URL
        _LAST_ALLOCATION_PATH = SP_FILE2_URL
        return f1, f2
    except Exception:
        return None


def try_auto_load_milestone() -> tuple[bytes, bytes] | None:
    """Return (milestone_xlsx_bytes, highlights_pdf_bytes) from sync folder, or None."""
    if not (AUTO_LOAD_FROM_SHAREPOINT and USE_LOCAL_SYNC_PATHS):
        return None
    try:
        return _read_local(LOCAL_MILESTONE_XLSX), _read_local(LOCAL_HIGHLIGHTS_PDF)
    except Exception:
        return None


def local_sync_status() -> dict:
    """Diagnostics for Home / Milestone pages."""
    p1 = Path(LOCAL_RESOURCE_INFO_TRACKER)
    p2 = resolve_allocation_path() or Path(LOCAL_RESOURCE_ALLOCATION)
    p3 = Path(LOCAL_MILESTONE_XLSX)
    p4 = Path(LOCAL_HIGHLIGHTS_PDF)
    return {
        "enabled": bool(AUTO_LOAD_FROM_SHAREPOINT and USE_LOCAL_SYNC_PATHS),
        "tracker_path": str(p1),
        "allocation_path": str(p2),
        "milestone_path": str(p3),
        "highlights_path": str(p4),
        "tracker_ok": p1.is_file(),
        "allocation_ok": p2.is_file(),
        "milestone_ok": p3.is_file(),
        "highlights_ok": p4.is_file(),
        "allocation_stamp": _file_stamp(p2),
        "milestone_stamp": _file_stamp(p3),
        "highlights_stamp": _file_stamp(p4),
    }
