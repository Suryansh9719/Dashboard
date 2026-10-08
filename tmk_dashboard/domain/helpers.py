"""Fuzzy column helpers matching DASHBOARD.html getVal / norm."""
from __future__ import annotations

import re
from typing import Any, Mapping


def norm(s: Any) -> str:
    if s is None:
        return ""
    return str(s).strip().lower()


def norm_loose(s: Any) -> str:
    if s is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def get_val_exact(row: Mapping[str, Any], col: str) -> str:
    """Case-insensitive exact column match only (no partial / substring)."""
    n = norm(col)
    if not n:
        return ""
    for k, v in row.items():
        if norm(k) == n:
            if v is None:
                return ""
            s = str(v).strip()
            if s.lower() in {"nan", "none", "null", "undefined", "nat"}:
                return ""
            return s
    return ""


def _has_exact_col(row: Mapping[str, Any], col: str) -> bool:
    n = norm(col)
    return any(norm(k) == n for k in row)


def get_val(row: Mapping[str, Any], col: str) -> str:
    """Case-insensitive exact then partial column match.

    If an exact column exists, its value is returned even when blank — never
    fall through to a different column (e.g. Planned Project Allocation).
    """
    n = norm(col)
    if not n:
        return ""
    if _has_exact_col(row, col):
        return get_val_exact(row, col)
    for k, v in row.items():
        kn = norm(k)
        if not kn:
            continue
        if n in kn or kn in n:
            if v is None:
                return ""
            s = str(v).strip()
            if s.lower() in {"nan", "none", "null", "undefined", "nat"}:
                return ""
            return s
    return ""


def parse_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        s = str(val).replace(",", "").replace("£", "").replace("%", "").strip()
        if not s:
            return None
        return float(s)
    except (TypeError, ValueError):
        return None


def find_tmka_row(tmka: list[dict], name: str) -> dict:
    target = norm(name)
    for r in tmka:
        if norm(get_val(r, "Resource Name") or get_val(r, "Name")) == target:
            return r
    return {}


def get_tos(row: Mapping[str, Any]) -> str:
    return (
        get_val(row, "Type of Service")
        or get_val(row, "Types of Service")
        or get_val(row, "Employee Type")
        or ""
    )
