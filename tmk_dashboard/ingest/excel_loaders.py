"""Excel / PDF ingest utilities."""
from __future__ import annotations

import io
import json
import warnings
from datetime import date, datetime, time
from typing import Any, BinaryIO

import pandas as pd

from domain.helpers import norm

# Excel files from SharePoint often include data-validation rules openpyxl cannot load.
warnings.filterwarnings(
    "ignore",
    message="Data Validation extension is not supported",
    module="openpyxl",
)


def _cell_to_jsonable(v: Any) -> Any:
    """Convert Excel cell values to JSON-safe types (fixes datetime serialization)."""
    if v is None:
        return ""
    if isinstance(v, (str, int, bool)):
        return v
    if isinstance(v, float):
        if pd.isna(v):
            return ""
        return v
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass

    # Pandas / numpy datetimes first
    if isinstance(v, pd.Timestamp):
        return "" if pd.isna(v) else v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, time):
        return v.strftime("%H:%M:%S")

    # numpy.datetime64.item() returns a Python datetime — recurse so it becomes a string
    type_name = type(v).__name__
    if "datetime64" in type_name or type_name == "Timestamp":
        try:
            return _cell_to_jsonable(pd.Timestamp(v))
        except Exception:
            return str(v)

    if hasattr(v, "item") and not isinstance(v, (bytes, bytearray)):
        try:
            return _cell_to_jsonable(v.item())
        except Exception:
            pass

    # Final safety net — never return a non-JSON value
    try:
        json.dumps(v)
        return v
    except TypeError:
        return str(v)


def _records_from_df(df: pd.DataFrame) -> list[dict]:
    df = df.where(pd.notnull(df), None)
    out = []
    for row in df.to_dict(orient="records"):
        cleaned = {str(k): _cell_to_jsonable(v) for k, v in row.items()}
        out.append(cleaned)
    return out


def sheet_to_records(file_bytes: bytes | BinaryIO, sheet_name: str) -> list[dict]:
    """Read a named sheet (case-insensitive) into list of dicts."""
    bio = io.BytesIO(file_bytes) if isinstance(file_bytes, (bytes, bytearray)) else file_bytes
    xl = pd.ExcelFile(bio)
    target = None
    for name in xl.sheet_names:
        if norm(name) == norm(sheet_name):
            target = name
            break
    if target is None:
        raise ValueError(
            f'"{sheet_name}" sheet not found. Available: {", ".join(xl.sheet_names)}'
        )
    df = pd.read_excel(xl, sheet_name=target, dtype=object)
    return _records_from_df(df)


def first_sheet_records(file_bytes: bytes | BinaryIO) -> list[dict]:
    bio = io.BytesIO(file_bytes) if isinstance(file_bytes, (bytes, bytearray)) else file_bytes
    df = pd.read_excel(bio, sheet_name=0, dtype=object)
    return _records_from_df(df)


def load_tmka(file_bytes: bytes) -> list[dict]:
    return sheet_to_records(file_bytes, "TMK-A")


def load_ra(file_bytes: bytes) -> list[dict]:
    return sheet_to_records(file_bytes, "Resource Allocation")


def load_milestone(file_bytes: bytes) -> tuple[list[dict], list[dict]]:
    """Load & normalize Milestones + Phase sheets (DASHBOARD.html parity)."""
    from domain.milestone import normalize_milestones, normalize_phases

    bio = io.BytesIO(file_bytes)
    xl = pd.ExcelFile(bio)
    names = xl.sheet_names

    def find_sheet(*needles: str) -> str | None:
        for n in names:
            nn = norm(n)
            if nn in needles:
                return n
        for n in names:
            nn = norm(n)
            if any(nd in nn for nd in needles):
                return n
        return None

    ms_name = find_sheet("milestones", "milestone")
    ph_name = find_sheet("phase", "phases")
    if not ms_name and not ph_name:
        raise ValueError(
            f'Could not find "Milestones" or "Phase" sheet. Found: {", ".join(names)}'
        )

    ms_raw = _records_from_df(pd.read_excel(xl, sheet_name=ms_name, dtype=object)) if ms_name else []
    ph_raw = _records_from_df(pd.read_excel(xl, sheet_name=ph_name, dtype=object)) if ph_name else []
    return normalize_milestones(ms_raw), normalize_phases(ph_raw)


def load_commercials(file_bytes: bytes) -> list[dict]:
    return first_sheet_records(file_bytes)
