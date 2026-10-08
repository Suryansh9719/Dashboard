"""Milestone Tracker logic ported from DASHBOARD.html (status, dates, Gantt, details)."""
from __future__ import annotations

import html
import re
from datetime import date, datetime, timedelta
from typing import Any

from config import MS_FIXED_PROJECTS
from domain.helpers import norm, norm_loose

STATUS_COLORS = {
    "On Track": "#f59e0b",
    "Delayed": "#ef4444",
    "Completed": "#10b981",
    "Unknown": "#64748b",
}
STATUS_BG = {
    "On Track": "#fef3c7",
    "Delayed": "#fee2e2",
    "Completed": "#dcfce7",
    "Unknown": "#f1f5f9",
}

_MONTH_ABBR = {
    "jan": 0, "feb": 1, "mar": 2, "apr": 3, "may": 4, "jun": 5,
    "jul": 6, "aug": 7, "sep": 8, "oct": 9, "nov": 10, "dec": 11,
}


def esc(s: Any) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def key_fuzzy(row: dict, patterns: list[str]) -> str | None:
    """Find a column key matching any regex pattern (HTML _msKeyFuzzy)."""
    keys = list(row.keys())
    for pat in patterns:
        rx = re.compile(pat, re.I)
        for k in keys:
            kn = re.sub(r"[\s\n\r]+", " ", str(k)).strip()
            if rx.search(kn) or rx.search(str(k)):
                return k
    return None


def _g(row: dict, key: str | None) -> str:
    if not key or key not in row or row[key] is None:
        return ""
    return str(row[key]).strip()


def date_only(d: date | datetime | None) -> date | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    return d


def date_val(v: Any) -> date | None:
    """Parse Excel / string dates like HTML _msDateVal."""
    if v is None or v == "":
        return None
    if isinstance(v, datetime):
        return None if (hasattr(v, "year") and v.year < 1900) else v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, (int, float)):
        n = float(v)
        if 25000 < n < 110000:
            return (datetime(1899, 12, 30) + timedelta(days=n)).date()
        return None

    s = str(v).strip()
    if not s or s == "-":
        return None

    if re.fullmatch(r"\d+(\.\d+)?", s):
        n = float(s)
        if 25000 < n < 110000:
            return (datetime(1899, 12, 30) + timedelta(days=n)).date()

    # ISO
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except ValueError:
            pass

    m1 = re.match(r"^(\d{1,2})[\s\-](\w{3,})[\s\-](\d{2,4})$", s)
    if m1:
        day1 = int(m1.group(1))
        mon1 = _MONTH_ABBR.get(m1.group(2).lower()[:3])
        yr1 = int(m1.group(3))
        if yr1 < 100:
            yr1 += 2000
        if mon1 is not None:
            try:
                return date(yr1, mon1 + 1, day1)
            except ValueError:
                pass

    m2 = re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$", s)
    if m2:
        day2, mon2, yr2 = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if yr2 < 100:
            yr2 += 2000
        if 1 <= mon2 <= 12 and 1 <= day2 <= 31:
            try:
                return date(yr2, mon2, day2)
            except ValueError:
                pass

    try:
        return datetime.fromisoformat(s.replace("Z", "")).date()
    except ValueError:
        return None


def fmt_date(v: Any) -> str:
    d = date_val(v) if not isinstance(v, date) else v
    if d is None:
        if v is None or v == "":
            return "-"
        return str(v) or "-"
    return d.strftime("%d %b %Y")


def to_iso(d: date | None) -> str:
    return d.isoformat() if d else ""


def parse_milestone_row(row: dict) -> dict | None:
    """Normalize one Milestones-sheet row (HTML loadMilestoneFile)."""
    if row.get("type") == "milestone" and ("project" in row or "desc" in row):
        return {
            "type": "milestone",
            "slno": str(row.get("slno") or ""),
            "project": str(row.get("project") or ""),
            "checkpoint": str(row.get("checkpoint") or "Milestone"),
            "module": str(row.get("module") or ""),
            "phase": str(row.get("phase") or ""),
            "desc": str(row.get("desc") or ""),
            "planned": to_iso(date_val(row.get("planned"))),
            "revised": to_iso(date_val(row.get("revised"))),
            "comments": str(row.get("comments") or ""),
            "impact": str(row.get("impact") or ""),
        }

    impact_key = key_fuzzy(row, [r"impact"])
    sl_key = key_fuzzy(row, [r"sl.{0,8}no", r"^#$"])
    proj_key = key_fuzzy(row, [r"^project$", r"project"])
    ckpt_key = key_fuzzy(row, [r"checkpoint"])
    mod_key = key_fuzzy(row, [r"module"])
    ph_key = key_fuzzy(row, [r"^phase$"])
    desc_key = key_fuzzy(row, [r"description"])
    plan_key = key_fuzzy(row, [r"planned.{0,8}date", r"^planned$"])
    rev_key = key_fuzzy(row, [r"revised.{0,8}date", r"^revised$"])
    comm_key = key_fuzzy(row, [r"comment"])

    project = _g(row, proj_key)
    desc = _g(row, desc_key)
    if not project and not desc:
        return None
    return {
        "type": "milestone",
        "slno": _g(row, sl_key),
        "project": project,
        "checkpoint": _g(row, ckpt_key) or "Milestone",
        "module": _g(row, mod_key),
        "phase": _g(row, ph_key),
        "desc": desc,
        "planned": to_iso(date_val(row[plan_key]) if plan_key else None),
        "revised": to_iso(date_val(row[rev_key]) if rev_key else None),
        "comments": _g(row, comm_key),
        "impact": _g(row, impact_key),
    }


def parse_phase_row(row: dict) -> dict | None:
    if row.get("type") == "phase" and ("project" in row or "desc" in row):
        return {
            "type": "phase",
            "slno": str(row.get("slno") or ""),
            "project": str(row.get("project") or ""),
            "checkpoint": str(row.get("checkpoint") or "Phase"),
            "module": str(row.get("module") or ""),
            "phase": str(row.get("phase") or ""),
            "desc": str(row.get("desc") or ""),
            "plannedStart": to_iso(date_val(row.get("plannedStart"))),
            "plannedEnd": to_iso(date_val(row.get("plannedEnd"))),
            "actualStart": to_iso(date_val(row.get("actualStart"))),
            "actualEnd": to_iso(date_val(row.get("actualEnd"))),
            "comments": str(row.get("comments") or ""),
            "impact": str(row.get("impact") or ""),
        }

    impact_key = key_fuzzy(row, [r"impact"])
    sl_key = key_fuzzy(row, [r"sl.{0,8}no", r"^#$"])
    proj_key = key_fuzzy(row, [r"^project$", r"project"])
    ckpt_key = key_fuzzy(row, [r"checkpoint"])
    mod_key = key_fuzzy(row, [r"module"])
    ph_key = key_fuzzy(row, [r"^phase$"])
    desc_key = key_fuzzy(row, [r"description"])
    p_start = key_fuzzy(row, [r"planned.{0,8}start"])
    p_end = key_fuzzy(row, [r"planned.{0,8}end"])
    a_start = key_fuzzy(row, [r"actual.{0,8}start"])
    a_end = key_fuzzy(row, [r"actual.{0,8}end"])
    comm_key = key_fuzzy(row, [r"comment"])

    project = _g(row, proj_key)
    desc = _g(row, desc_key)
    if not project and not desc:
        return None
    return {
        "type": "phase",
        "slno": _g(row, sl_key),
        "project": project,
        "checkpoint": _g(row, ckpt_key) or "Phase",
        "module": _g(row, mod_key),
        "phase": _g(row, ph_key),
        "desc": desc,
        "plannedStart": to_iso(date_val(row[p_start]) if p_start else None),
        "plannedEnd": to_iso(date_val(row[p_end]) if p_end else None),
        "actualStart": to_iso(date_val(row[a_start]) if a_start else None),
        "actualEnd": to_iso(date_val(row[a_end]) if a_end else None),
        "comments": _g(row, comm_key),
        "impact": _g(row, impact_key),
    }


def normalize_milestones(raw: list[dict]) -> list[dict]:
    out = []
    for row in raw or []:
        parsed = parse_milestone_row(row)
        if parsed:
            out.append(parsed)
    return out


def normalize_phases(raw: list[dict]) -> list[dict]:
    out = []
    for row in raw or []:
        parsed = parse_phase_row(row)
        if parsed:
            out.append(parsed)
    return out


def compute_display(item: dict, today: date | None = None) -> dict:
    """HTML _msComputeDisplay — status + dates/bars for Gantt & table."""
    today = today or date.today()
    impact_yes = norm(item.get("impact")) == "yes"
    out: dict[str, Any] = {
        "type": item.get("type"),
        "comments": item.get("comments") or "",
        "impact": "Yes" if impact_yes else "No",
        "status": "Unknown",
        "dates": [],
        "bars": [],
    }

    if item.get("type") == "milestone":
        rev = date_val(item.get("revised"))
        plan = date_val(item.get("planned"))
        if not impact_yes:
            out["status"] = "Completed" if (rev and rev < today) else "On Track"
            out["dates"] = [{"date": rev, "label": "Revised"}]
        else:
            if rev and rev < today:
                out["status"] = "Completed"
            else:
                same = plan and rev and plan == rev
                out["status"] = "On Track" if same else "Delayed"
            out["dates"] = [
                {"date": plan, "label": "Planned"},
                {"date": rev, "label": "Revised"},
            ]
    else:
        a_end = date_val(item.get("actualEnd"))
        a_start = date_val(item.get("actualStart"))
        p_start = date_val(item.get("plannedStart"))
        if not impact_yes:
            out["status"] = "Completed" if (a_end and a_end < today) else "On Track"
            out["bars"] = [{
                "start": date_val(item.get("actualStart")),
                "end": date_val(item.get("actualEnd")),
                "label": "Actual",
            }]
        else:
            if a_end and a_end < today:
                out["status"] = "Completed"
            else:
                late = a_start and p_start and a_start > p_start
                out["status"] = "Delayed" if late else "On Track"
            out["bars"] = [
                {
                    "start": date_val(item.get("plannedStart")),
                    "end": date_val(item.get("plannedEnd")),
                    "label": "Planned",
                },
                {
                    "start": date_val(item.get("actualStart")),
                    "end": date_val(item.get("actualEnd")),
                    "label": "Actual",
                },
            ]
    return out


def project_match(row_proj: str, target: str) -> bool:
    """Exact first (HTML), then loose fuzzy for sheet variants."""
    if not target or target == "__ALL__":
        return True
    a, b = (row_proj or "").strip(), target.strip()
    if a == b:
        return True
    la, lb = norm_loose(a), norm_loose(b)
    return la == lb or la.startswith(lb) or lb.startswith(la) or lb in la or la in lb


def filter_items(items: list[dict], proj: str) -> list[dict]:
    if not proj or proj == "__ALL__":
        return list(items)
    return [r for r in items if project_match(r.get("project") or "", proj)]


def status_counts(milestones: list[dict], phases: list[dict], today: date | None = None) -> dict[str, int]:
    counts = {"Total": 0, "On Track": 0, "Delayed": 0, "Completed": 0, "Unknown": 0}
    for item in list(milestones) + list(phases):
        st = compute_display(item, today)["status"]
        counts["Total"] += 1
        counts[st] = counts.get(st, 0) + 1
    return counts


def monday_of(d: date) -> date:
    # Monday of week containing d (Mon=0)
    return d - timedelta(days=d.weekday())


def next_working_day(d: date) -> date:
    """If Sat/Sun, move to next Monday; otherwise keep the date (HTML nextWorkingDay)."""
    wd = d.weekday()  # Mon=0 … Sun=6
    if wd == 5:  # Sat
        return d + timedelta(days=2)
    if wd == 6:  # Sun
        return d + timedelta(days=1)
    return d


def friday_of_week_containing(d: date) -> date:
    """Move to Friday of the week containing d (Mon–Sun week)."""
    return d + timedelta(days=(4 - d.weekday()))


def next_monday_after(d: date) -> date:
    """Strictly the next Monday after d."""
    return d + timedelta(days=(7 - d.weekday()))


def pdf_gantt_window(today: date | None = None) -> tuple[date, date, list[date]]:
    """PDF-only window: 1st of current month (or next working day) → 14th of next month.

    Week columns start at pdf_start; after a mid-week start, jump to next Monday
    (HTML _buildMsGanttUnified forPdf path).
    """
    today = today or date.today()
    pdf_start = next_working_day(date(today.year, today.month, 1))
    if today.month == 12:
        pdf_end = date(today.year + 1, 1, 14)
    else:
        pdf_end = date(today.year, today.month + 1, 14)

    weeks: list[date] = []
    c = pdf_start
    while c <= pdf_end:
        weeks.append(c)
        if c == pdf_start and c.weekday() != 0:
            c = next_monday_after(c)
        else:
            c = c + timedelta(days=7)
    return pdf_start, pdf_end, weeks


def biz_days_between(from_d: date, to_d: date) -> int:
    sign = 1
    a, b = from_d, to_d
    if b < a:
        a, b = b, a
        sign = -1
    days = 0
    cur = a
    while cur < b:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days * sign


def date_info_text(item: dict, disp: dict) -> str:
    if item.get("type") == "milestone":
        parts = []
        for d in disp.get("dates") or []:
            if d.get("date"):
                parts.append(f"{d['label']}: {fmt_date(d['date'])}")
        return " | ".join(parts)
    parts = []
    for b in disp.get("bars") or []:
        if b.get("start") or b.get("end"):
            parts.append(f"{b['label']}: {fmt_date(b.get('start'))} → {fmt_date(b.get('end'))}")
    return " | ".join(parts)


def _format_rich_inline(text: str) -> str:
    """Bold short Label: prefixes (HTML formatRich)."""
    s = (text or "").strip()
    if not s:
        return ""
    m = re.match(r"^([^:]{2,55}):\s*(.*)$", s)
    if m:
        label, rest = m.group(1), (m.group(2) or "").strip()
        if len(label.split()) <= 6 and not re.search(r"[.!?]$", label):
            return (
                f'<strong style="font-weight:800;color:#0f172a">{esc(label)}:</strong>'
                + (f" {esc(rest)}" if rest else "")
            )
    bare = re.sub(r"\s[-–—]\s*$", "", s).strip()
    if (
        len(bare) <= 40
        and len(bare.split()) <= 4
        and not re.search(r"[.!?…]", bare)
        and re.match(r"^[A-Z0-9]", bare)
        and not re.match(r"^(The|A|An|In|On|For|With|And|Or|To|As|At)\b", bare, re.I)
    ):
        return f'<strong style="font-weight:800;color:#0f172a">{esc(s)}</strong>'
    return esc(s)


def parse_rich_text_items(t: str) -> list[dict]:
    """Tokenize highlights/updates text like HTML _msTextToHtml."""
    if not t or not str(t).strip():
        return []
    lines = str(t).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    items: list[dict] = []
    for raw in lines:
        if raw is None:
            continue
        if not str(raw).strip():
            items.append({"type": "blank"})
            continue
        s = str(raw).replace("\u00a0", " ").strip()
        if re.match(r"^[◦○º]", s) or re.match(r"^o\s+\S", s):
            items.append({"type": "li", "level": 2, "text": re.sub(r"^[o◦○º]\s*", "", s)})
            continue
        if re.match(r"^[-–—•●▪*►▸]\s*", s):
            items.append({"type": "li", "level": 1, "text": re.sub(r"^[-–—•●▪*►▸]+\s*", "", s)})
            continue
        if len(s) <= 55 and re.search(r":\s*$", s) and not re.search(r"\.\s+\S", s):
            items.append({"type": "heading", "text": re.sub(r":\s*$", "", s)})
            continue
        if len(s) <= 55 and re.search(r"\s[-–—]\s*$", s) and not re.match(r"^[-–—•]", s):
            items.append({"type": "heading", "text": re.sub(r"\s[-–—]\s*$", "", s)})
            continue
        items.append({"type": "p", "text": s})
    return items


def text_to_html(t: str) -> str:
    """Port of HTML _msTextToHtml — nested UL with hanging indents."""
    items = parse_rich_text_items(t)
    if not items:
        return ""

    html_parts: list[str] = []
    open_l1 = False
    open_l2 = False
    li_open = False

    def close_l2() -> None:
        nonlocal open_l2
        if open_l2:
            html_parts.append("</ul>")
            open_l2 = False

    def close_l1() -> None:
        nonlocal open_l1, li_open
        close_l2()
        if li_open:
            html_parts.append("</li>")
            li_open = False
        if open_l1:
            html_parts.append("</ul>")
            open_l1 = False

    def ensure_l1() -> None:
        nonlocal open_l1
        if not open_l1:
            html_parts.append(
                '<ul style="margin:3px 0 4px 0;padding-left:18px;list-style-type:disc;'
                'list-style-position:outside;">'
            )
            open_l1 = True

    for it in items:
        if it["type"] == "blank":
            continue
        if it["type"] == "heading":
            close_l1()
            html_parts.append(
                f'<div style="font-weight:800;font-size:10.5px;color:#3730a3;'
                f'margin:7px 0 3px;letter-spacing:.2px">{esc(it["text"])}</div>'
            )
            continue
        if it["type"] == "li" and it["level"] == 1:
            close_l2()
            if li_open:
                html_parts.append("</li>")
                li_open = False
            elif open_l1:
                html_parts.append("</ul>")
                open_l1 = False
            ensure_l1()
            html_parts.append(
                f'<li style="margin:3px 0;line-height:1.4;padding-left:2px;">'
                f'{_format_rich_inline(it["text"])}'
            )
            li_open = True
            continue
        if it["type"] == "li" and it["level"] == 2:
            if li_open:
                if not open_l2:
                    html_parts.append(
                        '<ul style="margin:3px 0 2px 0;padding-left:16px;'
                        'list-style-type:circle;list-style-position:outside;">'
                    )
                    open_l2 = True
                html_parts.append(
                    f'<li style="margin:2px 0;line-height:1.35;padding-left:2px;">'
                    f'{_format_rich_inline(it["text"])}</li>'
                )
                continue
            close_l2()
            if not open_l1:
                html_parts.append(
                    '<ul style="margin:3px 0 4px 0;padding-left:28px;'
                    'list-style-type:circle;list-style-position:outside;">'
                )
                open_l1 = True
            html_parts.append(
                f'<li style="margin:2px 0;line-height:1.35;padding-left:2px;">'
                f'{_format_rich_inline(it["text"])}</li>'
            )
            continue
        # paragraph / continuation
        if li_open and not open_l2:
            html_parts.append(" " + _format_rich_inline(it["text"]))
        elif open_l2:
            close_l2()
            html_parts.append(" " + _format_rich_inline(it["text"]))
        else:
            html_parts.append(
                f'<div style="margin:2px 0 2px 2px;line-height:1.4;">'
                f'{_format_rich_inline(it["text"])}</div>'
            )

    close_l1()
    return "".join(html_parts)


def build_details_table_html(milestones: list[dict], phases: list[dict], dark: bool = False) -> str:
    rows_data = []
    for item in list(milestones) + list(phases):
        disp = compute_display(item)
        rows_data.append({"item": item, "disp": disp, "dateInfo": date_info_text(item, disp)})

    txt = "#e8eef5" if dark else "#0b1f33"
    sur = "#132337" if dark else "#ffffff"
    s2 = "#0f1c2a" if dark else "#f8fafc"
    bdr = "#2a3b4f" if dark else "#e2e8f0"
    mu = "#94a3b8" if dark else "#64748b"
    th_s = "padding:9px 10px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;color:#fff;white-space:nowrap"
    td_s = f"padding:8px 10px;font-size:12px;color:{txt}"

    body_parts = []
    for i, r in enumerate(rows_data):
        it, disp = r["item"], r["disp"]
        sc = STATUS_COLORS.get(disp["status"], "#64748b")
        sb = STATUS_BG.get(disp["status"], "#f1f5f9")
        bg = s2 if i % 2 else sur
        body_parts.append(
            f'<tr style="border-bottom:1px solid {bdr};background:{bg}">'
            f'<td style="{td_s}">{esc(it.get("slno"))}</td>'
            f'<td style="{td_s};font-weight:700;color:#3730a3">{esc(it.get("project"))}</td>'
            f'<td style="{td_s}"><span style="background:#dbeafe;color:#1d4ed8;border-radius:4px;'
            f'padding:1px 7px;font-size:10px;font-weight:600">{esc(it.get("checkpoint"))}</span></td>'
            f'<td style="{td_s}">{esc(it.get("module"))}</td>'
            f'<td style="{td_s}">{esc(it.get("phase"))}</td>'
            f'<td style="{td_s}">{esc(it.get("desc"))}</td>'
            f'<td style="{td_s};font-size:11px">{esc(r["dateInfo"] or "-")}</td>'
            f'<td style="{td_s}">{esc(it.get("impact") or "-")}</td>'
            f'<td style="{td_s}"><span style="background:{sb};color:{sc};border-radius:4px;'
            f'padding:2px 8px;font-size:10px;font-weight:700">{esc(disp["status"])}</span></td>'
            f'<td style="{td_s}">{esc(it.get("comments"))}</td>'
            f"</tr>"
        )
    body = "".join(body_parts) or (
        f'<tr><td colspan="10" style="padding:16px;text-align:center;color:{mu}">No items found.</td></tr>'
    )

    return (
        f'<div style="font-size:12px;font-weight:700;color:{mu};text-transform:uppercase;'
        f'margin:16px 0 8px;border-bottom:2px solid {bdr};padding-bottom:4px">Milestone Details</div>'
        f'<div style="overflow:auto"><table style="width:max-content;min-width:100%;border-collapse:collapse;'
        f'background:{sur};border-radius:8px;overflow:hidden;font-size:12px">'
        f'<thead><tr style="background:linear-gradient(135deg,#1e3a5f,#1e40af)">'
        f'<th style="{th_s}">Sl#No</th><th style="{th_s}">Project</th><th style="{th_s}">Checkpoint</th>'
        f'<th style="{th_s}">Module</th><th style="{th_s}">Phase</th><th style="{th_s}">Description</th>'
        f'<th style="{th_s}">Dates</th><th style="{th_s}">Impact</th><th style="{th_s}">Status</th>'
        f'<th style="{th_s}">Comments</th>'
        f"</tr></thead><tbody>{body}</tbody></table></div>"
    )


def build_gantt_html(
    milestones: list[dict],
    phases: list[dict],
    show_project_col: bool = True,
    dark: bool = False,
) -> str:
    """Port of HTML _buildMsGanttUnified (dashboard mode, not PDF-clipped)."""
    rows = [{"item": it, "disp": compute_display(it)} for it in list(milestones) + list(phases)]

    all_dates: list[date] = []
    for r in rows:
        for d in r["disp"].get("dates") or []:
            if d.get("date"):
                all_dates.append(d["date"])
        for b in r["disp"].get("bars") or []:
            if b.get("start"):
                all_dates.append(b["start"])
            if b.get("end"):
                all_dates.append(b["end"])

    if not all_dates:
        mu = "#94a3b8" if dark else "#64748b"
        sur = "#132337" if dark else "#ffffff"
        bdr = "#2a3b4f" if dark else "#e2e8f0"
        return (
            f'<div style="padding:16px;color:{mu};font-size:12px;text-align:center;'
            f'background:{sur};border:1px solid {bdr};border-radius:8px">'
            f"No dated items for this selection.</div>"
        )

    today = date.today()
    all_dates.append(today)
    start_mon = monday_of(min(all_dates) - timedelta(days=14))
    end_mon = monday_of(max(all_dates) + timedelta(days=28))

    weeks: list[date] = []
    c = start_mon
    while c <= end_mon:
        weeks.append(c)
        c += timedelta(days=7)
    total_w = len(weeks) or 1

    def day_frac(d: date | None) -> float | None:
        if not d:
            return None
        return biz_days_between(start_mon, d) / 5.0

    months: list[dict] = []
    cur_m = None
    for i, w in enumerate(weeks):
        lbl = w.strftime("%b %y")
        if lbl != cur_m:
            months.append({"l": lbl, "s": i, "n": 1})
            cur_m = lbl
        else:
            months[-1]["n"] += 1

    cell_w, label_w, status_w, row_h = 52, 260, 100, 52
    h_bg = "#1e3a5f" if dark else "#1e40af"
    h_bg2 = "#263348" if dark else "#2563eb"
    bdr = "rgba(255,255,255,.08)" if dark else "#e2e8f0"
    mu = "#94a3b8" if dark else "#64748b"
    # Fully opaque sticky paint so scrolled markers never show through
    sticky_bg = "#0f172a" if dark else "#ffffff"
    sticky_bg2 = "#111827" if dark else "#f8fafc"
    item_fg = "#f1f5f9" if dark else "#1e293b"
    today_frac = day_frac(today) or 0
    today_w = int(round(today_frac))
    # Sticky layers must beat timeline markers (markers use z-index 1–2)
    z_item, z_status = 40, 35
    shadow = "4px 0 10px rgba(0,0,0,.45)" if dark else "4px 0 8px rgba(15,23,42,.12)"

    m_hdr = (
        f'<tr>'
        f'<th style="position:sticky;left:0;z-index:{z_item};background:{h_bg};width:{label_w}px;'
        f'min-width:{label_w}px;max-width:{label_w}px;padding:7px 10px;text-align:left;font-size:10px;'
        f'font-weight:800;color:#fff;text-transform:uppercase;border-right:2px solid rgba(255,255,255,.2);'
        f'box-shadow:{shadow}">Item</th>'
        f'<th style="position:sticky;left:{label_w}px;z-index:{z_status};background:{h_bg};width:{status_w}px;'
        f'min-width:{status_w}px;max-width:{status_w}px;padding:7px 6px;font-size:10px;font-weight:800;color:#fff;'
        f'text-align:center;border-right:2px solid rgba(255,255,255,.2);box-shadow:{shadow}">Status</th>'
        + "".join(
            f'<th colspan="{m["n"]}" style="background:{h_bg};padding:7px 4px;text-align:center;'
            f'font-size:11px;font-weight:800;color:#fff;border-right:2px solid rgba(255,255,255,.2)">{m["l"]}</th>'
            for m in months
        )
        + "</tr>"
    )

    w_cells = []
    for i, w in enumerate(weeks):
        is_t = i == today_w
        fri = w + timedelta(days=4)
        label = f"{w.day} {w.strftime('%b')} to {fri.day} {fri.strftime('%b')}"
        bg = "rgba(239,68,68,.45)" if is_t else h_bg2
        fw = 800 if is_t else 500
        col = "#fde68a" if is_t else "rgba(255,255,255,.7)"
        w_cells.append(
            f'<th style="width:{cell_w}px;min-width:{cell_w}px;background:{bg};padding:3px 2px;text-align:center;'
            f'font-size:8px;font-weight:{fw};color:{col};border-right:1px solid rgba(255,255,255,.1);'
            f'line-height:1.3;white-space:normal">{label}</th>'
        )
    w_hdr = (
        f'<tr>'
        f'<th style="position:sticky;left:0;z-index:{z_item};background:{h_bg2};width:{label_w}px;'
        f'min-width:{label_w}px;box-shadow:{shadow};border-right:2px solid rgba(255,255,255,.2)"></th>'
        f'<th style="position:sticky;left:{label_w}px;z-index:{z_status};background:{h_bg2};width:{status_w}px;'
        f'min-width:{status_w}px;box-shadow:{shadow};border-right:2px solid rgba(255,255,255,.2)"></th>'
        + "".join(w_cells)
        + "</tr>"
    )

    body_rows = []
    for ri, r in enumerate(rows):
        item, disp = r["item"], r["disp"]
        col = STATUS_COLORS.get(disp["status"], "#64748b")
        sb = STATUS_BG.get(disp["status"], "#f1f5f9")
        row_bg = ("rgba(255,255,255,.025)" if dark else "rgba(0,0,0,.015)") if ri % 2 else "transparent"
        tip = f'{esc(item.get("project"))} — {esc(item.get("desc"))}'
        if disp.get("comments"):
            tip += f' | {esc(disp["comments"])}'

        markup = ""
        if item.get("type") == "milestone":
            dates = [d for d in (disp.get("dates") or []) if d.get("date")]
            for i, dp in enumerate(dates):
                frac = day_frac(dp["date"])
                if frac is None:
                    continue
                pos = (frac / total_w) * 100
                if pos < -5 or pos > 105:
                    continue
                marker_color = "#94a3b8" if (i == 0 and len(dates) > 1) else col
                label = f'{esc(item.get("phase") or item.get("desc"))}: {esc(fmt_date(dp["date"]))}'
                border = "#1e293b" if dark else "#fff"
                markup += (
                    f'<div title="{tip} ({esc(dp["label"])}: {esc(fmt_date(dp["date"]))})" '
                    f'style="position:absolute;left:{pos}%;top:42%;transform:translate(-50%,-50%) rotate(45deg);'
                    f'width:12px;height:12px;background:{marker_color};border:2px solid {border};'
                    f'box-shadow:0 2px 8px rgba(0,0,0,.35);z-index:1"></div>'
                    f'<div style="position:absolute;left:{pos}%;top:calc(42% + 12px);transform:translateX(-50%);'
                    f'background:{marker_color};color:#fff;font-size:7px;font-weight:700;padding:1px 4px;'
                    f'border-radius:3px;white-space:nowrap;z-index:1;max-width:88px;overflow:hidden;'
                    f'text-overflow:ellipsis">{label}</div>'
                )
            if len(dates) == 2 and dates[0]["date"] and dates[1]["date"]:
                p0 = (day_frac(dates[0]["date"]) / total_w) * 100
                p1 = (day_frac(dates[1]["date"]) / total_w) * 100
                markup += (
                    f'<div style="position:absolute;left:{min(p0, p1)}%;width:{abs(p1 - p0)}%;height:2px;'
                    f'top:50%;margin-top:-1px;background:{col};opacity:.4;z-index:1"></div>'
                )
        else:
            bars = disp.get("bars") or []
            for i, b in enumerate(bars):
                if not b.get("start") or not b.get("end"):
                    continue
                lp = (day_frac(b["start"]) / total_w) * 100
                wp = max(0.8, ((day_frac(b["end"]) - day_frac(b["start"])) / total_w) * 100)
                bar_color = "#94a3b8" if (i == 0 and len(bars) > 1) else col
                y_off = (35 if i == 0 else 65) if len(bars) > 1 else 50
                bar_label = (
                    f'{esc(item.get("phase") or item.get("desc") or "")}  ·  '
                    f'{esc(fmt_date(b["start"]))} → {esc(fmt_date(b["end"]))}'
                )
                markup += (
                    f'<div style="position:absolute;left:{lp}%;width:{wp}%;height:18px;top:{y_off}%;margin-top:-9px;'
                    f'background:linear-gradient(90deg,{bar_color}f0,{bar_color}a0);border-radius:10px;'
                    f'border:1.5px solid {bar_color}cc;overflow:hidden;display:flex;align-items:center;'
                    f'padding:0 8px;z-index:1;box-shadow:0 1px 4px rgba(0,0,0,.2)">'
                    f'<span style="font-size:9px;font-weight:700;color:#fff;white-space:nowrap;overflow:hidden;'
                    f'text-overflow:ellipsis">{bar_label}</span></div>'
                )

        type_ico = (
            f'<svg width="10" height="10" viewBox="0 0 10 10" style="flex-shrink:0">'
            f'<polygon points="5,0 10,5 5,10 0,5" fill="{col}"/></svg>'
            if item.get("type") == "milestone"
            else (
                f'<span style="background:{col};color:#fff;font-size:8px;font-weight:700;'
                f'padding:1px 5px;border-radius:3px;flex-shrink:0">PH</span>'
            )
        )
        title = (f'{esc(item.get("project"))} — ' if show_project_col else "") + esc(item.get("desc"))

        grid = "".join(
            f'<div style="position:absolute;left:{(ci / total_w) * 100}%;top:0;bottom:0;width:1px;'
            f'background:{"rgba(239,68,68,.5)" if ci == today_w else bdr};z-index:0;pointer-events:none"></div>'
            for ci in range(total_w)
        )
        today_line = (
            f'<div style="position:absolute;left:{(today_frac / total_w) * 100}%;top:0;bottom:0;width:2px;'
            f'background:#ef4444;z-index:2;pointer-events:none"></div>'
        )

        row_sticky = sticky_bg2 if ri % 2 else sticky_bg
        body_rows.append(
            f'<tr style="border-bottom:1px solid {bdr};background:{row_bg}">'
            f'<td style="position:sticky;left:0;z-index:{z_item};background:{row_sticky};padding:0 10px;'
            f'height:{row_h}px;width:{label_w}px;min-width:{label_w}px;max-width:{label_w}px;'
            f'border-right:2px solid {bdr};overflow:hidden;box-shadow:{shadow}">'
            f'<div style="display:flex;align-items:center;gap:6px;overflow:hidden">{type_ico}'
            f'<div style="overflow:hidden"><div style="font-size:10px;font-weight:800;color:{item_fg};'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{title}</div></div></div></td>'
            f'<td style="position:sticky;left:{label_w}px;z-index:{z_status};background:{row_sticky};'
            f'padding:0 6px;text-align:center;width:{status_w}px;min-width:{status_w}px;max-width:{status_w}px;'
            f'border-right:2px solid {bdr};box-shadow:{shadow}">'
            f'<span style="background:{sb};color:{col};border:1px solid {col}55;border-radius:5px;'
            f'padding:2px 6px;font-size:8px;font-weight:700">{esc(disp["status"])}</span></td>'
            f'<td colspan="{total_w}" style="padding:0;position:relative;height:{row_h}px;overflow:hidden;'
            f'isolation:isolate">'
            f'{grid}{today_line}'
            f'<div style="position:absolute;inset:0;overflow:hidden;pointer-events:auto;z-index:1">{markup}</div>'
            f"</td></tr>"
        )

    table_min_w = label_w + status_w + (cell_w * total_w)
    wrap_bg = "#0f172a" if dark else "#f1f5f9"
    foot_bg = "#1e293b" if dark else "#f8fafc"

    return (
        f'<div style="background:{wrap_bg};border:1px solid {bdr};border-radius:8px;overflow:hidden;margin-bottom:16px">'
        f'<div style="padding:9px 14px;background:linear-gradient(135deg,#3730a3,#4f46e5);color:#fff;'
        f'font-size:12px;font-weight:800">Milestone Gantt Chart</div>'
        f'<div style="overflow:auto;max-height:520px">'
        f'<table style="border-collapse:collapse;width:{table_min_w}px;min-width:{table_min_w}px;'
        f'font-size:11px;table-layout:fixed"><thead>{m_hdr}{w_hdr}</thead>'
        f'<tbody>{"".join(body_rows)}</tbody></table></div>'
        f'<div style="display:flex;gap:14px;flex-wrap:wrap;padding:6px 12px;background:{foot_bg};'
        f'border-top:1px solid {bdr};font-size:9px;color:{mu}">'
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:#f59e0b;display:inline-block"></span>On Track</span>'
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:#ef4444;display:inline-block"></span>Delayed</span>'
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:#10b981;display:inline-block"></span>Completed</span>'
        f'<span style="display:flex;align-items:center;gap:4px">'
        f'<span style="width:10px;height:10px;border-radius:50%;background:#94a3b8;display:inline-block"></span>'
        f"Planned (faded, when Impact = Yes)</span>"
        f"</div></div>"
    )


def build_kpi_banner_html(
    title: str,
    counts: dict[str, int],
    dark: bool = False,
) -> str:
    total = counts.get("Total", 0)
    on_track = counts.get("On Track", 0)
    delayed = counts.get("Delayed", 0)
    completed = counts.get("Completed", 0)
    as_of = date.today().strftime("%d %b %Y")
    bg = "#0a1520" if dark else "#e9eef4"
    sur = "#132337" if dark else "#ffffff"
    bdr = "#2a3b4f" if dark else "#e2e8f0"
    mu = "#94a3b8" if dark else "#64748b"
    ink = "#e8eef5" if dark else "#0b1f33"

    def card(n: int, label: str, color: str, border: str = "") -> str:
        bl = f"border-left:4px solid {border};" if border else ""
        return (
            f'<div style="background:{sur};border:1px solid {bdr};{bl}border-radius:8px;'
            f'padding:10px 18px;text-align:center;min-width:100px">'
            f'<div style="font-size:22px;font-weight:800;color:{color}">{n}</div>'
            f'<div style="font-size:10px;font-weight:600;color:{mu};text-transform:uppercase">{label}</div></div>'
        )

    return (
        f'<div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);color:#fff;padding:14px 20px;'
        f'border-radius:8px 8px 0 0">'
        f'<div style="font-size:15px;font-weight:800">{esc(title)} — Milestone Gantt View</div>'
        f'<div style="font-size:11px;opacity:.75;margin-top:2px">{total} items • as of {as_of}</div></div>'
        f'<div style="display:flex;gap:10px;padding:14px 0;flex-wrap:wrap;background:{bg};'
        f'border-bottom:1px solid {bdr}">'
        f'{card(total, "Total", "#3730a3" if not dark else "#a5b4fc")}'
        f'{card(on_track, "On Track", "#f59e0b", "#f59e0b")}'
        f'{card(delayed, "Delayed", "#ef4444", "#ef4444")}'
        f'{card(completed, "Completed", "#10b981", "#10b981")}'
        f"</div>"
    )


def build_all_updates_html(updates: dict[str, str], dark: bool = False) -> str:
    parts = []
    pd_c = "#a5b4fc" if dark else "#1e3a5f"
    bdr = "#2a3b4f" if dark else "#e2e8f0"
    mu = "#94a3b8"
    for p in MS_FIXED_PROJECTS:
        txt = (updates or {}).get(p) or ""
        if not txt.strip():
            continue
        parts.append(
            f'<div style="margin-bottom:14px">'
            f'<div style="font-weight:800;color:{pd_c};font-size:13px;margin-bottom:4px;'
            f'border-bottom:1px solid {bdr};padding-bottom:3px">{esc(p)}</div>'
            f'<div>{text_to_html(txt)}</div></div>'
        )
    if not parts:
        return f'<span style="color:{mu};font-style:italic">No project updates available. Upload a Highlights PDF with an Updates section.</span>'
    return "".join(parts)
