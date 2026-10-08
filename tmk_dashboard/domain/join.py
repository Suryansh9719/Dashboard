"""Project join + finance aggregates (ported from DASHBOARD.html)."""
from __future__ import annotations

from domain.helpers import find_tmka_row, get_tos, get_val, get_val_exact, norm, parse_float
from domain.periods import build_periods, detect_month_year_cols, filter_rows_by_period


def build_tos_map(tmka: list[dict]) -> dict[str, str]:
    tos_map: dict[str, str] = {}
    if not tmka:
        return tos_map
    first = tmka[0]
    tos_key = ""
    exact = ["Type of Service", "Types of Service", "type of service", "types of service", "TypeOfService"]
    for name in exact:
        if name in first:
            tos_key = name
            break
    if not tos_key:
        for k in first:
            if "service" in norm(k):
                tos_key = k
                break
    if not tos_key:
        return tos_map
    for row in tmka:
        n = norm(get_val(row, "Resource Name") or get_val(row, "Name"))
        v = row.get(tos_key)
        if n and v is not None and str(v).strip():
            tos_map[n] = str(v).strip()
    return tos_map


def list_billing_projects(ra: list[dict]) -> tuple[list[str], dict[str, int]]:
    """Unique Billing Projects from the Resource Allocation sheet only.

    Uses the exact Billing Project column (never Planned Project Allocation
    or other fuzzy matches) so the count matches the uploaded workbook.
    """
    seen: dict[str, bool] = {}
    projs: list[str] = []
    for row in ra:
        p = get_val_exact(row, "Billing Project")
        if p and p not in seen:
            seen[p] = True
            projs.append(p)
    projs.sort(key=lambda x: x.lower())
    counts: dict[str, int] = {p: 0 for p in projs}
    names_seen: set[str] = set()
    for row in ra:
        p = get_val_exact(row, "Billing Project")
        n = norm(get_val(row, "Resource Name"))
        key = f"{p}|{n}"
        if p and n and key not in names_seen:
            names_seen.add(key)
            counts[p] = counts.get(p, 0) + 1
    return projs, counts


def project_members(ra: list[dict], proj: str) -> tuple[list[dict], list[dict]]:
    all_members = [r for r in ra if norm(get_val_exact(r, "Billing Project")) == norm(proj)]
    seen: set[str] = set()
    unique: list[dict] = []
    for row in all_members:
        n = norm(get_val(row, "Resource Name"))
        if n and n not in seen:
            seen.add(n)
            unique.append(row)
    return all_members, unique


def project_leadership(unique_rows: list[dict], tmka: list[dict]) -> dict[str, str]:
    hlm, dm, pm = "", "", ""
    for ra_row in unique_rows:
        name = get_val(ra_row, "Resource Name")
        t_row = find_tmka_row(tmka, name)
        if not hlm:
            hlm = get_val(t_row, "HLM") or get_val(t_row, "Hlm")
        if not dm:
            dm = get_val(t_row, "DM") or get_val(t_row, "Dm")
        if not pm:
            role = norm(get_val(t_row, "Role") or get_val(t_row, "Designation"))
            if "project manager" in role or role == "pm":
                pm = name
    return {"pm": pm, "hlm": hlm, "dm": dm}


def calc_pd_totals(members: list[dict]) -> dict:
    tc = tr = icr_sum = 0.0
    icr_count = 0
    margins: list[float] = []
    for row in members:
        c = parse_float(get_val(row, "Cost"))
        if c is not None and c > 0:
            tc += c
        r = parse_float(get_val(row, "Revenue"))
        if r is not None and r > 0:
            tr += r
        m = parse_float(get_val(row, "Sale Margin") or get_val(row, "Margin"))
        if m is not None and m > 0:
            margins.append(m)
        icr = parse_float(get_val(row, "ICR"))
        if icr is not None and icr > 0:
            icr_sum += icr
            icr_count += 1
    avg_m = (sum(margins) / len(margins)) if margins else None
    avg_icr = round(icr_sum / icr_count) if icr_count else None
    return {"cost": tc, "rev": tr, "margin": avg_m, "icr": avg_icr}


def build_resource_rows(
    unique_rows: list[dict],
    tmka: list[dict],
    tos_map: dict[str, str],
) -> list[dict]:
    rows = []
    for ra_row in unique_rows:
        name = get_val(ra_row, "Resource Name") or ""
        t_row = find_tmka_row(tmka, name)
        rows.append(
            {
                "name": name,
                "grade": get_val(ra_row, "Grade"),
                "portalId": get_val(ra_row, "Portal ID") or get_val(ra_row, "Portal Id"),
                "oneErpId": get_val(ra_row, "OneERP ID") or get_val(ra_row, "One ERP ID"),
                "gender": get_val(t_row, "Gender"),
                "hlm": get_val(t_row, "HLM") or get_val(t_row, "Hlm"),
                "dm": get_val(t_row, "DM") or get_val(t_row, "Dm"),
                "location": get_val(t_row, "Base Location") or get_val(t_row, "Location"),
                "practice": get_val(t_row, "UK Practice") or get_val(t_row, "Practice"),
                "role": get_val(t_row, "Role") or get_val(t_row, "Designation"),
                "primarySkill": get_val(t_row, "Primary Skills") or get_val(t_row, "Primary Skill"),
                "skills": get_val(t_row, "Skills") or get_val(t_row, "Skill"),
                "band": get_val(t_row, "Experience Band") or get_val(t_row, "Band"),
                "billing": get_val(ra_row, "Billing Project"),
                "typeOfService": tos_map.get(norm(name)) or get_tos(t_row) or get_tos(ra_row),
            }
        )
    return rows


def build_fin_rows(
    all_members: list[dict],
    tmka: list[dict],
    period: dict | None,
    month_col: str,
    year_col: str,
) -> list[dict]:
    filtered = filter_rows_by_period(all_members, period, month_col, year_col)
    seen: set[str] = set()
    filt_uniq: list[dict] = []
    for row in filtered:
        n = norm(get_val(row, "Resource Name"))
        if n and n not in seen:
            seen.add(n)
            filt_uniq.append(row)
    out = []
    for ra_row in filt_uniq:
        name = get_val(ra_row, "Resource Name") or ""
        t_row = find_tmka_row(tmka, name)
        filt_row = next(
            (r for r in filtered if norm(get_val(r, "Resource Name")) == norm(name)),
            ra_row,
        )
        cost = parse_float(get_val(filt_row, "Cost"))
        rev = parse_float(get_val(filt_row, "Revenue"))
        out.append(
            {
                "name": name,
                "practice": get_val(t_row, "UK Practice") or get_val(t_row, "Practice"),
                "costCenter": get_val(t_row, "Cost Center") or get_val(ra_row, "Cost Center"),
                "typeOfService": (
                    get_val(t_row, "Types of Service")
                    or get_val(ra_row, "Type of Service")
                    or get_val(ra_row, "Employee Type")
                ),
                "rateId": get_val(ra_row, "Ext Code") or get_val(t_row, "Rate ID"),
                "icr": get_val(ra_row, "ICR"),
                "costRecovery": get_val(t_row, "Cost Recovery") or get_val(ra_row, "Cost Recovery"),
                "rateCard": get_val(t_row, "Rate Card") or get_val(ra_row, "Rate Card"),
                "rcHr": get_val(t_row, "RC/Hr") or get_val(t_row, "Rate Card/Hr"),
                "cost": cost if cost is not None and cost > 0 else None,
                "revenue": rev if rev is not None and rev > 0 else None,
            }
        )
    return out


def count_by(rows: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for r in rows:
        v = (r.get(key) or "").strip() or "(blank)"
        counts[v] = counts.get(v, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: (-x[1], x[0])))


def project_periods(all_members: list[dict]) -> tuple[list[dict], str, str]:
    month_col, year_col = detect_month_year_cols(all_members)
    periods = build_periods(all_members, month_col, year_col)
    return periods, month_col, year_col
