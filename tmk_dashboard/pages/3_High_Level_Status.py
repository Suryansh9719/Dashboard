"""High Level Status — Excel KPIs + OneNote Highlights/Issues (HTML parity)."""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from config import (
    ACCOUNT_NAME,
    DEFAULT_HLS_PROJECTS,
    ONENOTE_AUTO_SYNC,
    ONENOTE_NOTEBOOK_NAME,
    ONENOTE_SECTION_NAME,
    ONENOTE_USER_UPN,
)
from domain.finance import hls_stats_from_ra
from domain.periods import build_periods, detect_month_year_cols, filter_rows_by_cascade
from export.excel_export import date_suffix
from export.pdf_export import hls_pdf
from ingest.onenote import graph_configured, onenote_target_configured, sync_onenote
from ui.cascade import render_cascade
from ui.session import ensure_workbook_loaded, get_store, init_session
from ui.theme import apply_theme, render_topbar

st.set_page_config(
    page_title="High Level Status · TMK",
    layout="wide",
    page_icon="◈",
    initial_sidebar_state="expanded",
)
init_session()
apply_theme()
render_topbar()

store = get_store()
saved = store.load_hls() or {}

RAG_CYCLE = ["green", "amber", "red"]
RAG_COLORS = {"green": "#22c55e", "amber": "#f59e0b", "red": "#ef4444"}

_BILLING_HINTS = re.compile(
    r"1880|account buffer|rpa|apim|data solution|ams-sd|as-ams|ritc",
    re.I,
)


def cycle(v: str) -> str:
    v = (v or "green").lower()
    return RAG_CYCLE[(RAG_CYCLE.index(v) + 1) % len(RAG_CYCLE)] if v in RAG_CYCLE else "green"


def _default_projects() -> list[dict]:
    out = []
    for n in DEFAULT_HLS_PROJECTS:
        out.append(
            {
                "name": n,
                "del": "amber" if n == "SASR" else "green",
                "res": "green",
                "gm": "green",
            }
        )
    return out


def _default_hls() -> dict:
    return {
        "title": ACCOUNT_NAME,
        "stats": [
            "Offshore HC : —",
            "Onshore HC : —",
            "AOP : —",
            "Actual Rev : —",
            "Planned GM : —",
            "Actual GM : —",
        ],
        "overall": "green",
        "highlights": "",
        "issues": "",
        "footer": "© 2026 NTT DATA Corporation",
        "projects": _default_projects(),
        "stats_from_file": True,
    }


def _looks_like_billing_dump(projs: list) -> bool:
    if not projs:
        return False
    if len(projs) > 12:
        return True
    names = [str(p.get("name") or "") for p in projs]
    defaults = set(DEFAULT_HLS_PROJECTS)
    overlap = sum(1 for n in names if n in defaults)
    if len(projs) >= 8 and overlap <= 2:
        return True
    if any(_BILLING_HINTS.search(n) for n in names):
        return True
    return False


def _normalize(data: dict) -> dict:
    base = _default_hls()
    if not data:
        return base
    out = {**base, **data}
    if not out.get("title"):
        out["title"] = base["title"]
    if not out.get("footer"):
        out["footer"] = base["footer"]
    projs = out.get("projects") or []
    fixed: list[dict] = []
    for p in projs:
        if not isinstance(p, dict):
            continue
        if "rags" in p and "del" not in p:
            rags = p.get("rags") or []

            def _rag_from(entry, fallback="green"):
                if isinstance(entry, dict):
                    cls = str(entry.get("cls") or "")
                    if "amber" in cls:
                        return "amber"
                    if "red" in cls:
                        return "red"
                    if "green" in cls:
                        return "green"
                return fallback

            fixed.append(
                {
                    "name": p.get("name") or "Project",
                    "del": _rag_from(rags[0] if len(rags) > 0 else None),
                    "res": _rag_from(rags[1] if len(rags) > 1 else None),
                    "gm": _rag_from(rags[2] if len(rags) > 2 else None),
                }
            )
        else:
            fixed.append(
                {
                    "name": p.get("name") or "Project",
                    "del": (p.get("del") or "green").lower(),
                    "res": (p.get("res") or "green").lower(),
                    "gm": (p.get("gm") or "green").lower(),
                }
            )
    if _looks_like_billing_dump(fixed):
        out["projects"] = base["projects"]
    else:
        out["projects"] = fixed or base["projects"]
    # Drop hardcoded HTML placeholder stats so file-derived values win
    old = out.get("stats") or []
    if any("3.9 M" in str(s) or "Offshore HC : 56" in str(s) for s in old):
        out["stats"] = list(base["stats"])
        out["stats_from_file"] = True
    return out


_migrated = False
if "hls" not in st.session_state:
    raw = saved if saved else {}
    if _looks_like_billing_dump(raw.get("projects") or []):
        _migrated = True
    st.session_state.hls = _normalize(raw)
elif _looks_like_billing_dump(st.session_state.hls.get("projects") or []):
    st.session_state.hls = _normalize({**st.session_state.hls, "projects": []})
    _migrated = True

hls = _normalize(st.session_state.hls)
st.session_state.hls = hls
if _migrated:
    store.save_hls(hls)

st.markdown(
    """
    <style>
    div.st-key-hls_save button {
      background:#4f46e5 !important; border-color:#4f46e5 !important; color:#fff !important;
    }
    div.st-key-hls_pdf button {
      background:#dc2626 !important; border-color:#dc2626 !important; color:#fff !important;
    }
    div.st-key-hls_view_btn button {
      background:#0f766e !important; border-color:#0f766e !important; color:#fff !important;
    }
    div.st-key-hls_title input {
      font-size:1.25rem !important; font-weight:800 !important;
    }
    div[class*="st-key-hls_pname_"] input {
      background:#0f766e !important; color:#fff !important; font-weight:700 !important;
      font-size:12px !important; text-align:center !important;
      border:none !important; border-radius:6px 6px 0 0 !important;
    }
    /* Full DEL / RES / GM labels — never truncate to D/R/G */
    div[class*="st-key-hls_del_"] button,
    div[class*="st-key-hls_res_"] button,
    div[class*="st-key-hls_gm_"] button {
      color:#fff !important; border:none !important;
      font-size:11px !important; font-weight:700 !important;
      letter-spacing:.02em !important;
      min-height:2rem !important; padding:0.35rem 0.4rem !important;
      white-space:nowrap !important; overflow:visible !important;
    }
    div[class*="st-key-hls_del_"] button p,
    div[class*="st-key-hls_res_"] button p,
    div[class*="st-key-hls_gm_"] button p {
      font-size:11px !important; white-space:nowrap !important;
      overflow:visible !important; text-overflow:clip !important;
    }
    .hls-col-hdr {
      background:#0f766e; color:#fff !important; font-size:13px; font-weight:700;
      padding:8px 14px; text-align:center; border-radius:8px 8px 0 0;
    }
    .hls-stat-ro {
      border:1.5px solid var(--line); border-radius:6px; padding:8px 12px;
      background:var(--panel); font-size:12px; font-weight:600; color:var(--ink);
      margin-bottom:4px; min-width:120px;
    }
    .hls-footer {
      display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;
      background:var(--surface); border:1px solid var(--line); border-radius:8px;
      padding:10px 16px; margin-top:12px; font-size:11px; color:var(--muted);
    }
    .hls-legend span {
      display:inline-block; border-radius:4px; padding:4px 8px;
      font-size:11px; font-weight:700; color:#fff !important; margin-right:4px;
    }
    [data-tmk="dark"] .hls-stat-ro { background:#263348; border-color:#334155; color:#e8eef5; }
    [data-tmk="dark"] .hls-footer { background:#1e293b; border-color:#334155; }
    [data-tmk="dark"] .hls-col-hdr { background:#0f766e; color:#fff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Toolbar ─────────────────────────────────────────────────────────────────
tb1, tb2, tb3, _ = st.columns([1, 1.25, 1, 4])
with tb1:
    if st.button("Save", type="primary", use_container_width=True, key="hls_save"):
        store.save_hls(hls)
        store.log_change(
            "HLS Saved",
            f"Overall={hls.get('overall')}; projects={len(hls.get('projects', []))}",
        )
        st.success("Saved successfully")
with tb2:
    pdf = hls_pdf(
        hls.get("title") or "High Level Status",
        hls.get("overall", "green"),
        hls.get("highlights", ""),
        hls.get("issues", ""),
        hls.get("projects", []),
    )
    st.download_button(
        "Download PDF",
        data=pdf,
        file_name=f"HLS_{date_suffix()}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="hls_pdf",
    )
with tb3:
    if st.button("View", use_container_width=True, key="hls_view_btn"):
        st.session_state["_hls_view"] = True

# ── Stats from Resource Allocation (auto-load if needed) ────────────────────
ensure_workbook_loaded()

file_stats: list[str] | None = None
if st.session_state.get("data_loaded") and st.session_state.get("ra"):
    ra = st.session_state.ra
    tmka = st.session_state.get("tmka") or []
    month_col, year_col = detect_month_year_cols(ra)
    periods = build_periods(ra, month_col, year_col)
    st.caption("Period (from Resource Allocation file)")
    cascade = render_cascade("hls", periods, state_key="hls_cascade")
    if cascade.get("year"):
        filtered = filter_rows_by_cascade(
            ra,
            periods,
            month_col,
            year_col,
            year=cascade.get("year", 0),
            quarter=cascade.get("quarter", 0),
            month=cascade.get("month", 0),
        )
    else:
        filtered = ra
    # If a tight period filter yields no rows, fall back to all data so KPIs aren't blank
    if not filtered and ra:
        st.warning("No rows for the selected period — showing all periods.")
        filtered = ra
    file_stats = hls_stats_from_ra(filtered, tmka)
    hls["stats"] = file_stats
    hls["stats_from_file"] = True
    src = st.session_state.get("_data_source") or ""
    st.caption(f"KPIs from file{(': ' + src) if src else ''} · {len(filtered):,} allocation rows")
else:
    st.warning(
        "Resource Allocation is not loaded yet. Open **Home** once (or check SharePoint sync paths "
        "in config.py) so Offshore HC / AOP / GM can be calculated."
    )

stats = list(hls.get("stats") or _default_hls()["stats"])
while len(stats) < 6:
    stats.append("")

hdr_l, hdr_r = st.columns([1.3, 2.7])
with hdr_l:
    hls["title"] = st.text_input(
        "Title",
        value=hls.get("title") or ACCOUNT_NAME,
        label_visibility="collapsed",
        key="hls_title",
    )
with hdr_r:
    s1, s2, s3, s4 = st.columns([1.35, 1.35, 1.35, 0.45])
    # Read-only KPI boxes (from file) — not free-text placeholders
    boxes = [(s1, 0, 1), (s2, 2, 3), (s3, 4, 5)]
    for col, a, b in boxes:
        with col:
            st.markdown(
                f'<div class="hls-stat-ro">{html.escape(stats[a])}</div>'
                f'<div class="hls-stat-ro">{html.escape(stats[b])}</div>',
                unsafe_allow_html=True,
            )
    with s4:
        ov = (hls.get("overall") or "green").lower()
        oc = RAG_COLORS.get(ov, "#22c55e")
        st.markdown(
            f"<style>div.st-key-hls_overall button{{background:{oc}!important;color:#fff!important;"
            f"border:none!important;border-radius:50%!important;width:38px!important;height:38px!important;"
            f"min-height:38px!important;padding:0!important;box-shadow:0 0 0 3px {oc}44;"
            f"margin-top:0.6rem!important}}</style>",
            unsafe_allow_html=True,
        )
        if st.button(" ", key="hls_overall", help="Overall RAG — click to cycle"):
            hls["overall"] = cycle(ov)
            st.session_state.hls = hls
            st.rerun()

hls["stats"] = stats

# ── Project strip — wider cards so DEL/RES/GM stay full words ───────────────
projs = list(hls.get("projects") or [])


def _render_proj_card(i: int, p: dict) -> None:
    p["name"] = st.text_input(
        f"hls_pname_{i}",
        value=p.get("name", ""),
        label_visibility="collapsed",
        key=f"hls_pname_{i}",
        placeholder="Project",
    )
    css_bits = []
    for field in ("del", "res", "gm"):
        color = RAG_COLORS.get((p.get(field) or "green").lower(), "#22c55e")
        css_bits.append(
            f"div.st-key-hls_{field}_{i} button{{background:{color}!important;"
            f"color:#fff!important;border:none!important}}"
        )
    st.markdown(f"<style>{''.join(css_bits)}</style>", unsafe_allow_html=True)
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("DEL", key=f"hls_del_{i}", use_container_width=True, help="Delivery — click to cycle"):
            p["del"] = cycle(p.get("del"))
            st.session_state.hls = hls
            st.rerun()
    with b2:
        if st.button("RES", key=f"hls_res_{i}", use_container_width=True, help="Resourcing — click to cycle"):
            p["res"] = cycle(p.get("res"))
            st.session_state.hls = hls
            st.rerun()
    with b3:
        if st.button("GM", key=f"hls_gm_{i}", use_container_width=True, help="Margin — click to cycle"):
            p["gm"] = cycle(p.get("gm"))
            st.session_state.hls = hls
            st.rerun()


# 3 cards per row (+ Add) — enough width for full labels
i = 0
while i < len(projs):
    chunk = projs[i : i + 3]
    n = len(chunk)
    is_last_chunk = i + 3 >= len(projs)
    cols = st.columns(n + (1 if is_last_chunk else 0))
    for j, p in enumerate(chunk):
        with cols[j]:
            _render_proj_card(i + j, p)
    if is_last_chunk:
        with cols[n]:
            st.markdown("<div style='height:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("+ Add Project", key="hls_add", use_container_width=True):
                hls.setdefault("projects", []).append(
                    {"name": "New Project", "del": "green", "res": "green", "gm": "green"}
                )
                st.session_state.hls = hls
                st.rerun()
    i += 3

if not projs:
    if st.button("+ Add Project", key="hls_add_empty"):
        hls["projects"] = [
            {"name": "New Project", "del": "green", "res": "green", "gm": "green"}
        ]
        st.session_state.hls = hls
        st.rerun()

hls["projects"] = projs

# ── OneNote from Teams (Graph) — no manual upload ───────────────────────────
st.markdown("#### Highlights & Issues")
st.caption(
    f"Reads OneNote notebook **{ONENOTE_NOTEBOOK_NAME}** · section **{ONENOTE_SECTION_NAME}**"
    + (f" · owner **{ONENOTE_USER_UPN}**" if ONENOTE_USER_UPN else "")
    + " (newest page unless a title is set in config)."
)


def _apply_onenote(result: dict) -> None:
    hls["highlights"] = result.get("highlights") or ""
    hls["issues"] = result.get("issues") or ""
    st.session_state["hls_hl"] = hls["highlights"]
    st.session_state["hls_iss"] = hls["issues"]
    st.session_state.hls = hls
    store.save_hls(hls)
    store.log_change(
        "HLS OneNote Sync",
        f"source={result.get('_source')}; page={result.get('_page_title', '')}",
    )


# Auto-sync once per session when Graph + target are configured
if (
    ONENOTE_AUTO_SYNC
    and graph_configured()
    and onenote_target_configured()
    and not st.session_state.get("_hls_onenote_autosynced")
):
    try:
        result = sync_onenote(prefer_graph=True)
        _apply_onenote(result)
        st.session_state["_hls_onenote_autosynced"] = True
        st.session_state["_hls_onenote_last"] = result.get("_page_title") or "OK"
        st.rerun()
    except Exception as e:
        st.session_state["_hls_onenote_autosynced"] = True  # don't loop errors
        st.session_state["_hls_onenote_err"] = str(e)

oc1, oc2 = st.columns([1, 3])
with oc1:
    if st.button("Refresh from OneNote", type="primary", use_container_width=True, key="hls_sync_teams"):
        try:
            result = sync_onenote(prefer_graph=True)
            _apply_onenote(result)
            st.session_state["_hls_onenote_last"] = result.get("_page_title") or "OK"
            st.session_state.pop("_hls_onenote_err", None)
            st.success(
                "Synced from OneNote"
                + (f": {result.get('_page_title')}" if result.get("_page_title") else "")
            )
            st.rerun()
        except Exception as e:
            st.error(str(e))
with oc2:
    if not graph_configured() or not onenote_target_configured():
        st.warning(
            "Your Demo notebook is **personal OneDrive** (no Team Group ID). "
            "In config.py set `ONENOTE_USER_UPN` (already set to 10357769@nttdata.com from your link) "
            "plus `MS_GRAPH_TENANT_ID`, `MS_GRAPH_CLIENT_ID`, `MS_GRAPH_CLIENT_SECRET` "
            "(permission **Notes.Read.All** + admin consent)."
        )
    elif st.session_state.get("_hls_onenote_err"):
        st.error(st.session_state["_hls_onenote_err"])
    elif st.session_state.get("_hls_onenote_last"):
        st.caption(f"Last sync: {st.session_state['_hls_onenote_last']}")

c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="hls-col-hdr">Highlights</div>', unsafe_allow_html=True)
    hls["highlights"] = st.text_area(
        "Highlights",
        value=hls.get("highlights", ""),
        height=240,
        label_visibility="collapsed",
        key="hls_hl",
    )
with c2:
    st.markdown('<div class="hls-col-hdr">Issues</div>', unsafe_allow_html=True)
    hls["issues"] = st.text_area(
        "Issues",
        value=hls.get("issues", ""),
        height=240,
        label_visibility="collapsed",
        key="hls_iss",
    )

# ── Footer + legend ─────────────────────────────────────────────────────────
hls["footer"] = st.text_input(
    "Footer",
    value=hls.get("footer") or "© 2026 NTT DATA Corporation",
    label_visibility="collapsed",
    key="hls_footer",
)
st.markdown(
    f"""
    <div class="hls-footer">
      <span>{html.escape(hls.get("footer") or "")}</span>
      <div class="hls-legend">
        <span style="background:#22c55e">DEL – Delivery</span>
        <span style="background:#22c55e">RES – Resourcing</span>
        <span style="background:#22c55e">GM – Margin</span>
        <strong style="color:#2563eb;font-size:13px;margin-left:6px">NTT DATA</strong>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── View ────────────────────────────────────────────────────────────────────
if st.session_state.get("_hls_view"):

    @st.dialog("View — High Level Status", width="large")
    def _hls_view_dlg() -> None:
        ov = (hls.get("overall") or "green").lower()
        oc = RAG_COLORS.get(ov, "#22c55e")
        st.markdown(f"### {html.escape(hls.get('title') or ACCOUNT_NAME)}")
        st.markdown(
            '<div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:8px 0">'
            + "".join(
                f'<div style="border:1px solid #cbd5e1;border-radius:5px;padding:5px 10px;'
                f'background:#f8fafc;font-size:12px;font-weight:600;color:#1e293b">'
                f"{html.escape(s)}</div>"
                for s in (hls.get("stats") or [])
            )
            + f'<div style="width:36px;height:36px;border-radius:50%;background:{oc}"></div>'
            + "</div>",
            unsafe_allow_html=True,
        )
        strip = ['<div style="display:flex;gap:6px;flex-wrap:wrap;margin:8px 0">']
        for p in hls.get("projects") or []:
            strip.append(
                f'<div style="border:1px solid #0f766e;border-radius:5px;overflow:hidden;min-width:100px">'
                f'<div style="background:#0f766e;color:#fff;font-size:11px;font-weight:700;'
                f'padding:4px 8px;text-align:center">{html.escape(p.get("name") or "")}</div>'
                f'<div style="padding:4px;display:flex;gap:3px;justify-content:center;background:#f0fdfa">'
                f'<span style="background:{RAG_COLORS.get((p.get("del") or "green").lower())};'
                f'color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px">DEL</span>'
                f'<span style="background:{RAG_COLORS.get((p.get("res") or "green").lower())};'
                f'color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px">RES</span>'
                f'<span style="background:{RAG_COLORS.get((p.get("gm") or "green").lower())};'
                f'color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:3px">GM</span>'
                f"</div></div>"
            )
        strip.append("</div>")
        st.markdown("".join(strip), unsafe_allow_html=True)
        v1, v2 = st.columns(2)
        with v1:
            st.markdown("**Highlights**")
            st.markdown(hls.get("highlights") or "_No content synced yet._")
        with v2:
            st.markdown("**Issues**")
            st.markdown(hls.get("issues") or "_No content synced yet._")
        if st.button("Close", use_container_width=True, key="hls_view_close"):
            st.session_state["_hls_view"] = False
            st.rerun()

    _hls_view_dlg()

st.session_state.hls = hls
