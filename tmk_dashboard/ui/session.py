"""Session-state helpers for Streamlit."""
from __future__ import annotations

import streamlit as st

from db.store import Store
from domain.join import build_tos_map, list_billing_projects


def get_store() -> Store:
    if "store" not in st.session_state:
        st.session_state.store = Store()
    return st.session_state.store


def init_session() -> None:
    defaults = {
        "data_loaded": False,
        "tmka": [],
        "ra": [],
        "projects": [],
        "proj_counts": {},
        "tos_map": {},
        "selected_project": "",
        "overrides": {},
        "cascade": {},  # proj -> {year, quarter, month, week}
        "tmk_cascade": {"year": 0, "quarter": 0, "month": 0},
        "tmk_selected_period": "__all__",
        "commercials": [],
        "milestones": [],
        "phases": [],
        "ms_selected_project": "__ALL__",
        "ms_updates": {},
        "ms_highlights": {"raw": "", "sections": {}},
        "theme": "light",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    store = get_store()
    if not st.session_state.overrides:
        st.session_state.overrides = store.load_overrides()
    if not st.session_state.commercials:
        st.session_state.commercials = store.load_commercials()
    # Milestone / Highlights: never auto-restore from DB — only from files the user uploads
    # (wipes any previously cached rows so charts stay empty until upload)
    if not st.session_state.get("_ms_upload_source"):
        st.session_state.milestones = []
        st.session_state.phases = []
        st.session_state.ms_updates = {}
        st.session_state.ms_highlights = {"raw": "", "sections": {}}
        st.session_state.pop("_ms_file_id", None)
        st.session_state.pop("_ms_file_name", None)
        st.session_state.pop("_ms_pdf_id", None)
        st.session_state.pop("_ms_pdf_name", None)
        if not st.session_state.get("_ms_db_cleared"):
            store.save_milestones([], [])
            store.save_ms_updates({})
            store.save_ms_highlights("", {})
            st.session_state["_ms_db_cleared"] = True
    # Clear legacy custom sidebar-hide flag (we use Streamlit's native collapse only)
    if "sidebar_hidden" in st.session_state:
        del st.session_state["sidebar_hidden"]
    try:
        if store.get_setting("sidebar_hidden", "0") == "1":
            store.set_setting("sidebar_hidden", "0")
    except Exception:
        pass
    saved_theme = store.get_setting("theme", "light")
    st.session_state.theme = saved_theme


def set_workbook_data(
    tmka: list[dict],
    ra: list[dict],
    *,
    source_label: str = "",
) -> str:
    """Populate session from loaded workbooks. Returns status message.

    Billing projects are derived only from the Resource Allocation
    Billing Project column — nothing is hardcoded.
    """
    projects, counts = list_billing_projects(ra)
    tos_map = build_tos_map(tmka)
    st.session_state.tmka = tmka
    st.session_state.ra = ra
    st.session_state.projects = projects
    st.session_state.proj_counts = counts
    st.session_state.tos_map = tos_map
    st.session_state.data_loaded = True
    st.session_state["_workbook_from_upload"] = True
    st.session_state["_data_source"] = source_label or ""
    st.session_state.pop("_projects_customized", None)
    # Reset period cascades + related widgets so they re-init to the latest month
    for k in list(st.session_state.keys()):
        if not isinstance(k, str):
            continue
        if k.startswith("cascade_") or k.endswith("_cascade"):
            del st.session_state[k]
        elif k.startswith("bill_") and any(
            k.endswith(sfx) for sfx in ("_year", "_q", "_m", "_w", "_q_dis", "_m_dis", "_w_dis")
        ):
            del st.session_state[k]
    get_store().log_change(
        "Data Loaded",
        f"{len(projects)} billing projects; TMK-A {len(tmka)} rows; RA {len(ra)} rows"
        + (f"; source={source_label}" if source_label else ""),
    )
    msg = f"Loaded! Found {len(projects)} Billing Projects. TMK-A has {len(tmka)} resource records."
    if source_label:
        msg += f" Source: {source_label}"
    return msg


def clear_workbook_data() -> None:
    """Wipe Home workbook data so modules require a fresh Load."""
    st.session_state.tmka = []
    st.session_state.ra = []
    st.session_state.projects = []
    st.session_state.proj_counts = {}
    st.session_state.tos_map = {}
    st.session_state.selected_project = ""
    st.session_state.data_loaded = False
    st.session_state.pop("_workbook_from_upload", None)
    st.session_state.pop("_data_source", None)
    st.session_state.pop("_projects_customized", None)


def require_data() -> bool:
    """Return True if data is loaded; otherwise show warning and False."""
    if not st.session_state.get("data_loaded"):
        st.warning("Load Excel files on the **Home** page first.")
        return False
    return True


def ensure_workbook_loaded() -> bool:
    """Load Resource Allocation / TMK-A if needed (same auto-load as Home).

    Call from any page that needs Excel KPIs so users don't have to visit Home first.
    """
    if st.session_state.get("data_loaded") and st.session_state.get("ra"):
        return True
    try:
        from config import AUTO_LOAD_FROM_SHAREPOINT
        from ingest.excel_loaders import load_ra, load_tmka
        from ingest.sharepoint import try_auto_load
    except Exception:
        return bool(st.session_state.get("data_loaded") and st.session_state.get("ra"))

    if not AUTO_LOAD_FROM_SHAREPOINT:
        return bool(st.session_state.get("data_loaded") and st.session_state.get("ra"))

    try:
        loaded = try_auto_load()
        if not loaded:
            return False
        tmka_bytes, ra_bytes, src = loaded
        tmka = load_tmka(tmka_bytes)
        ra = load_ra(ra_bytes)
        set_workbook_data(tmka, ra, source_label=src)
        return True
    except Exception:
        return bool(st.session_state.get("data_loaded") and st.session_state.get("ra"))


def fmt_gbp(n) -> str:
    if n is None or n == "" or n == 0:
        return "-"
    try:
        return f"£{float(n):,.0f}"
    except (TypeError, ValueError):
        return "-"


def fmt_pct(n) -> str:
    if n is None:
        return "-"
    try:
        # HTML stores margin as fraction (0.25) sometimes or already % — treat >1 as already %
        v = float(n)
        if abs(v) <= 1:
            return f"{round(v * 100)}%"
        return f"{round(v)}%"
    except (TypeError, ValueError):
        return "-"
