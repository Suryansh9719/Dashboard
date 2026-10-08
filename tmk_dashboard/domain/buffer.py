"""Account Buffer tree builder — Billing Project = Account Buffer, by Year/Month."""
from __future__ import annotations

from config import MONTH_NAMES
from domain.helpers import get_val, get_val_exact, norm
from domain.periods import detect_month_year_cols, parse_cell_date


def build_buffer_data(ra: list[dict]) -> dict:
    """Group Account Buffer rows by calendar year → month.

    Month cells may be Excel serials, datetime objects, or text — same as
    DASHBOARD.html / period cascade via parse_cell_date.
    """
    month_col, year_col = detect_month_year_cols(ra)
    tree: dict[int, dict[int, dict]] = {}
    total_seen: set[str] = set()

    for row in ra:
        if norm(get_val_exact(row, "Billing Project")) != "account buffer":
            continue
        name = (get_val(row, "Resource Name") or "").strip()
        if not name:
            continue

        m_raw = row.get(month_col, "") if month_col else ""
        y_raw = row.get(year_col, "") if year_col else ""

        y, m = 0, 0
        label = "(Unknown Period)"

        # Prefer Month cell as a real date (datetime / serial / ISO string)
        dt = parse_cell_date(m_raw) or parse_cell_date(y_raw)
        if dt is not None:
            y, m = dt.year, dt.month
            label = f"{MONTH_NAMES[m - 1]} {y}"
        else:
            m_str = str(m_raw or "").strip()
            y_str = str(y_raw or "").strip()
            try:
                y = int(float(y_str or m_str))
            except (TypeError, ValueError):
                y = 0
            m_lower = m_str.lower()
            found_m = 0
            for mi, mn in enumerate(MONTH_NAMES):
                if mn.lower() in m_lower:
                    found_m = mi + 1
                    break
            if not found_m:
                try:
                    m_num = int(float(m_str))
                    if 1 <= m_num <= 12:
                        found_m = m_num
                except (TypeError, ValueError):
                    pass
            m = found_m
            if m and y:
                label = f"{MONTH_NAMES[m - 1]} {y}"
            else:
                label = f"{m_str} {y_str}".strip() or "(Unknown Period)"

        tree.setdefault(y, {}).setdefault(m, {"label": label, "resources": []})
        tree[y][m]["resources"].append({"name": name, "rawRow": row})
        total_seen.add(norm(name))

    return {
        "tree": tree,
        "monthCol": month_col,
        "yearCol": year_col,
        "total": len(total_seen),
    }
