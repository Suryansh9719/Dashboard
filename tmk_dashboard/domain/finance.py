"""Finance / shore / ICR helpers."""
from __future__ import annotations

from domain.helpers import get_val, get_val_exact, norm, parse_float


def classify_shore(row: dict) -> str:
    shore = norm(get_val(row, "Shore") or get_val(row, "Location Type") or "")
    if "onshore" in shore or shore in ("uk", "on"):
        return "Onshore"
    if "offshore" in shore or shore in ("off", "india"):
        return "Offshore"
    loc = norm(get_val(row, "Base Location") or get_val(row, "Location") or "")
    if any(x in loc for x in ("london", "uk", "new york", "singapore")):
        return "Onshore"
    if any(x in loc for x in ("bengaluru", "hyderabad", "mumbai", "chennai", "delhi", "pune", "india")):
        return "Offshore"
    return "Unknown"


def _fmt_millions(n: float | None) -> str:
    if n is None or n == 0:
        return "—"
    if abs(n) >= 1_000_000:
        return f"{n / 1_000_000:.1f} M"
    if abs(n) >= 1_000:
        return f"{n / 1_000:.1f} K"
    return f"{n:,.0f}"


def _normalize_margin(raw: float | None) -> float | None:
    if raw is None:
        return None
    # Sale Margin in Excel is often 24 or 0.24
    if abs(raw) > 1:
        return raw / 100.0
    return raw


def hls_stats_from_ra(ra: list[dict], tmka: list[dict] | None = None) -> list[str]:
    """Build the 6 High Level Status KPI strings from Resource Allocation rows.

    - Offshore / Onshore HC: unique resource names by shore (RA, else TMK-A)
    - Actual Rev / Actual GM: from Cost & Revenue
    - AOP: sum of AOP / Planned Revenue / Target Revenue when present; else Actual Rev
    - Planned GM: average Sale Margin (or Margin) when present
    """
    from domain.helpers import find_tmka_row

    tmka = tmka or []
    off: set[str] = set()
    on: set[str] = set()
    total_cost = total_rev = 0.0
    aop_sum = 0.0
    aop_found = False
    planned_margins: list[float] = []

    aop_keys = (
        "AOP",
        "AOP Revenue",
        "Planned Revenue",
        "Target Revenue",
        "Budget Revenue",
        "Planned Rev",
    )

    for row in ra:
        n = (get_val(row, "Resource Name") or "").strip()
        nkey = norm(n)
        shore = classify_shore(row)
        if shore == "Unknown" and nkey and tmka:
            trow = find_tmka_row(tmka, n)
            if trow:
                shore = classify_shore(trow)
        if nkey:
            if shore == "Offshore":
                off.add(nkey)
            elif shore == "Onshore":
                on.add(nkey)

        c = parse_float(get_val(row, "Cost")) or 0
        r = parse_float(get_val(row, "Revenue")) or 0
        if c > 0:
            total_cost += c
        if r > 0:
            total_rev += r

        for ak in aop_keys:
            raw = get_val_exact(row, ak) or get_val(row, ak)
            av = parse_float(raw)
            if av is not None and av > 0:
                aop_sum += av
                aop_found = True
                break

        m = parse_float(
            get_val(row, "Sale Margin") or get_val(row, "Margin") or get_val(row, "Planned GM")
        )
        nm = _normalize_margin(m)
        if nm is not None and nm > 0:
            planned_margins.append(nm)

    actual_gm = ((total_rev - total_cost) / total_rev) if total_rev else None
    planned_gm = (sum(planned_margins) / len(planned_margins)) if planned_margins else None

    def _pct(v: float | None) -> str:
        if v is None:
            return "—"
        pct = v * 100.0 if abs(v) <= 1 else float(v)
        return f"{pct:.1f}%"

    # HC always shows a number (0 if none) so users can tell data loaded
    return [
        f"Offshore HC : {len(off)}",
        f"Onshore HC : {len(on)}",
        f"AOP : {_fmt_millions(aop_sum if aop_found else (total_rev or None))}",
        f"Actual Rev : {_fmt_millions(total_rev or None)}",
        f"Planned GM : {_pct(planned_gm)}",
        f"Actual GM : {_pct(actual_gm)}",
    ]


def aggregate_account(ra: list[dict], tmka: list[dict] | None = None) -> dict:
    eng_seen: set[str] = set()
    total_cost = total_rev = 0.0
    by_project: dict[str, dict] = {}
    onshore = offshore = 0
    onshore_names: set[str] = set()
    offshore_names: set[str] = set()
    for row in ra:
        n = norm(get_val(row, "Resource Name"))
        if n:
            eng_seen.add(n)
        p = str(get_val(row, "Billing Project")).strip() or "(blank)"
        c = parse_float(get_val(row, "Cost")) or 0
        r = parse_float(get_val(row, "Revenue")) or 0
        if c > 0:
            total_cost += c
        if r > 0:
            total_rev += r
        bp = by_project.setdefault(p, {"cost": 0.0, "rev": 0.0, "eng": set()})
        if c > 0:
            bp["cost"] += c
        if r > 0:
            bp["rev"] += r
        if n:
            bp["eng"].add(n)
        shore = classify_shore(row)
        if shore == "Onshore":
            onshore += 1
            if n:
                onshore_names.add(n)
        elif shore == "Offshore":
            offshore += 1
            if n:
                offshore_names.add(n)
    projects = []
    for p, v in sorted(by_project.items()):
        projects.append(
            {
                "project": p,
                "cost": v["cost"],
                "rev": v["rev"],
                "engineers": len(v["eng"]),
                "margin": ((v["rev"] - v["cost"]) / v["rev"]) if v["rev"] else None,
            }
        )
    return {
        "total_engineers": len(eng_seen),
        "total_cost": total_cost,
        "total_rev": total_rev,
        "margin": ((total_rev - total_cost) / total_rev) if total_rev else None,
        "onshore_rows": onshore,
        "offshore_rows": offshore,
        "onshore_hc": len(onshore_names),
        "offshore_hc": len(offshore_names),
        "projects": projects,
    }
