"""Year → Quarter → Month → Week period cascade (ported from DASHBOARD.html)."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from config import MONTH_NAMES
from domain.helpers import norm


def is_excel_serial(v: Any) -> bool:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return False
    s = str(v).strip()
    return n > 25000 and n < 70000 and "/" not in s and "-" not in s and " " not in s


def serial_to_date(s: Any) -> datetime:
    return datetime(1899, 12, 30) + timedelta(days=float(s))


def serial_label(s: Any) -> str:
    d = serial_to_date(s)
    return f"{MONTH_NAMES[d.month - 1]} {d.year}"


def serial_sort_key(s: Any) -> int:
    d = serial_to_date(s)
    return d.year * 100 + d.month


def parse_cell_date(v: Any) -> datetime | None:
    """Parse Month/Year cell: Excel serial, datetime, or ISO/date string."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if is_excel_serial(v):
        return serial_to_date(v)
    s = str(v).strip()
    if not s:
        return None
    # pandas often stores Month as "2026-07-01 00:00:00"
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%b %Y",
        "%B %Y",
    ):
        try:
            return datetime.strptime(s[:19] if fmt.startswith("%Y-%m-%d %H") else s, fmt)
        except ValueError:
            continue
    # "Jul 2026" already covered; try loose year-month from ISO prefix
    m = re.match(r"^(\d{4})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1)
    return None


def detect_month_year_cols(rows: list[dict]) -> tuple[str, str]:
    if not rows:
        return "", ""
    month_col, year_col = "", ""
    for k in rows[0].keys():
        kn = norm(k)
        if not month_col and (kn in ("month", "mnth", "mon") or "month" in kn):
            month_col = k
        if not year_col and (kn in ("year", "yr", "fy") or "year" in kn):
            year_col = k
    return month_col, year_col


def detect_week_cols(rows: list[dict]) -> list[dict]:
    if not rows:
        return []
    week_cols = []
    for wk in rows[0].keys():
        wkn = wk.strip().upper()
        if re.match(r"^W[1-5]$", wkn) or re.match(r"^WEEK\s*[1-5]$", wk.strip(), re.I):
            week_cols.append({"key": wk, "label": wkn})
    week_cols.sort(key=lambda x: x["label"])
    return week_cols


def build_periods(rows: list[dict], month_col: str = "", year_col: str = "") -> list[dict]:
    if not month_col and not year_col:
        month_col, year_col = detect_month_year_cols(rows)
    periods_map: dict[str, dict] = {}
    for row in rows:
        m = str(row.get(month_col, "") or "").strip() if month_col else ""
        y = str(row.get(year_col, "") or "").strip() if year_col else ""
        if not (m or y):
            continue
        label, sort_key = "", 0
        dt = parse_cell_date(m) or parse_cell_date(y)
        if dt:
            label = f"{MONTH_NAMES[dt.month - 1]} {dt.year}"
            sort_key = dt.year * 100 + dt.month
        elif m and is_excel_serial(m):
            label, sort_key = serial_label(m), serial_sort_key(m)
        elif y and is_excel_serial(y):
            label, sort_key = serial_label(y), serial_sort_key(y)
        else:
            label = f"{m} {y}".strip() if (m and y) else (m or y)
            try:
                y_num = int(float(y or m))
                sort_key = y_num * 100
            except (TypeError, ValueError):
                sort_key = 0
        key = f"{y}||{m}" if (y and m) else (y or m)
        if key not in periods_map:
            periods_map[key] = {
                "key": key,
                "month": m,
                "year": y,
                "label": label,
                "sortKey": sort_key,
            }
    periods = list(periods_map.values())
    periods.sort(key=lambda p: p.get("sortKey") or 0, reverse=True)
    return periods


def get_year_from_period(p: dict) -> int | None:
    sk = p.get("sortKey")
    if sk:
        y = int(sk) // 100
        if y > 1900:
            return y
    dt = parse_cell_date(p.get("month")) or parse_cell_date(p.get("year")) or parse_cell_date(p.get("label"))
    if dt:
        return dt.year
    m = re.search(r"\d{4}", p.get("label") or "")
    return int(m.group(0)) if m else None


def get_month_num_from_period(p: dict) -> int:
    sk = p.get("sortKey")
    if sk:
        mn = int(sk) % 100
        if 1 <= mn <= 12:
            return mn
    dt = parse_cell_date(p.get("month")) or parse_cell_date(p.get("label"))
    if dt:
        return dt.month
    lab = (p.get("label") or "").lower()
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    for i, name in enumerate(months):
        if name in lab:
            return i + 1
    return 0


def quarter_of_month(m: int) -> int:
    if m <= 3:
        return 1
    if m <= 6:
        return 2
    if m <= 9:
        return 3
    return 4


def months_in_quarter(q: int) -> list[int]:
    return {1: [1, 2, 3], 2: [4, 5, 6], 3: [7, 8, 9], 4: [10, 11, 12]}.get(q, [])


def filter_rows_by_period(
    rows: list[dict],
    period: dict | None,
    month_col: str,
    year_col: str,
) -> list[dict]:
    if not period:
        return rows
    out = []
    for row in rows:
        m = str(row.get(month_col, "") or "").strip() if month_col else ""
        y = str(row.get(year_col, "") or "").strip() if year_col else ""
        match_m = (not period.get("month")) or (m == period["month"])
        match_y = (not period.get("year")) or (y == period["year"])
        if match_m and match_y:
            out.append(row)
    return out


def filter_rows_by_cascade(
    rows: list[dict],
    periods: list[dict],
    month_col: str,
    year_col: str,
    year: int = 0,
    quarter: int = 0,
    month: int = 0,
) -> list[dict]:
    """Filter RA rows by cascade selection (year / quarter / month)."""
    if not year:
        return rows
    matched_periods = []
    for p in periods:
        py = get_year_from_period(p)
        pm = get_month_num_from_period(p)
        if py != year:
            continue
        if month and pm != month:
            continue
        if quarter and not month and pm not in months_in_quarter(quarter):
            continue
        matched_periods.append(p)
    if not matched_periods:
        return []
    keys = {(p.get("month"), p.get("year")) for p in matched_periods}
    out = []
    for row in rows:
        m = str(row.get(month_col, "") or "").strip() if month_col else ""
        y = str(row.get(year_col, "") or "").strip() if year_col else ""
        if (m, y) in keys or (None, y) in keys:
            out.append(row)
        else:
            for pm, py in keys:
                if (not pm or m == pm) and (not py or y == py):
                    out.append(row)
                    break
    seen = set()
    unique = []
    for r in out:
        rid = id(r)
        if rid not in seen:
            seen.add(rid)
            unique.append(r)
    return unique


def year_set_from_periods(periods: list[dict]) -> dict[int, dict[int, dict]]:
    year_set: dict[int, dict[int, dict]] = {}
    for p in periods:
        y = get_year_from_period(p)
        mn = get_month_num_from_period(p)
        if not y or not mn:
            continue
        year_set.setdefault(y, {})[mn] = p
    return year_set


def today_period_info() -> dict:
    now = datetime.now()
    y, m = now.year, now.month
    return {
        "key": f"{y}||{m}",
        "year": str(y),
        "month": str(m),
        "label": f"{MONTH_NAMES[m - 1]} {y}",
        "sortKey": y * 100 + m,
    }
