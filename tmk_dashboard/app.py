"""TMK Dashboard — Streamlit entry point (upload gate)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from config import AUTO_LOAD_FROM_SHAREPOINT
from export.excel_export import date_suffix
from export.pdf_export import full_dashboard_pdf
from ingest.excel_loaders import load_ra, load_tmka
from ingest.sharepoint import last_loaded_paths, local_sync_status, try_auto_load
from ui.session import clear_workbook_data, get_store, init_session, set_workbook_data
from ui.theme import apply_theme, render_topbar

st.set_page_config(
    page_title="Home · TMK Dashboard",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_session()
apply_theme()  # also draws left sidebar module list
render_topbar("Resource & commercial operations")

store = get_store()

with st.sidebar:
    if st.button("Change log", use_container_width=True):
        st.session_state["_show_log"] = True
    export_clicked = st.button("Export full PDF", use_container_width=True)
    if export_clicked:
        if st.session_state.get("data_loaded"):
            summary = [
                f"Projects: {len(st.session_state.projects)}",
                f"TMK-A rows: {len(st.session_state.tmka)}",
                f"RA rows: {len(st.session_state.ra)}",
            ]
            pdf = full_dashboard_pdf(
                summary,
                [
                    (
                        "Billing Projects",
                        [["Project", "Resources"]]
                        + [[p, st.session_state.proj_counts.get(p, 0)] for p in st.session_state.projects],
                    )
                ],
            )
            st.download_button(
                "Download PDF",
                data=pdf,
                file_name=f"TMK_Full_Dashboard_{date_suffix()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.warning("Load data first.")

if st.session_state.get("_show_log"):
    with st.expander("Change log", expanded=True):
        logs = store.load_changelog()
        if not logs:
            st.caption("No changes recorded yet.")
        else:
            st.dataframe(logs, use_container_width=True, hide_index=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Clear log"):
                store.clear_changelog()
                st.rerun()
        with c2:
            if st.button("Close"):
                st.session_state["_show_log"] = False
                st.rerun()

# ---- Landing ----
st.markdown(
    """
    <div class="tmk-landing">
      <div class="hero-mark">TMK</div>
      <h2>TMK Dashboard</h2>
      <p class="lead">Source workbooks auto-load from your synced SharePoint folder.
         Manual upload remains available as a fallback.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

_sync = local_sync_status()
if _sync["enabled"]:
    if _sync["tracker_ok"] and _sync["allocation_ok"]:
        stamp = _sync.get("allocation_stamp")
        stamp_txt = f" ({stamp[0]})" if stamp else ""
        st.caption(
            "SharePoint sync folder ready — "
            "Resource Info Tracker + Resource Allocation found locally"
            + stamp_txt
            + f". Using: {_sync['allocation_path']}"
        )
    else:
        missing = []
        if not _sync["tracker_ok"]:
            missing.append("Resource Info Tracker")
        if not _sync["allocation_ok"]:
            missing.append("Resource Allocation")
        st.warning(
            "Synced SharePoint files missing: "
            + ", ".join(missing)
            + ". Check OneDrive sync, or upload manually below."
        )

if AUTO_LOAD_FROM_SHAREPOINT and not st.session_state.data_loaded:
    with st.spinner("Loading workbooks from SharePoint sync folder…"):
        loaded = try_auto_load()
    if loaded:
        try:
            tmka = load_tmka(loaded[0])
            ra = load_ra(loaded[1])
            paths = last_loaded_paths()
            src = Path(paths["allocation"] or "").name or "SharePoint sync"
            msg = set_workbook_data(tmka, ra, source_label=src)
            st.success(msg + " (auto-loaded)")
            st.rerun()
        except Exception as e:
            st.error(f"Auto-load failed: {e}. Use manual upload below.")
    elif _sync["enabled"]:
        st.info("Auto-load skipped — files not readable yet. Use manual upload or fix sync paths.")

# Manual reload from sync (even if data already loaded)
if _sync["enabled"] and _sync["tracker_ok"] and _sync["allocation_ok"]:
    if st.button("Reload from SharePoint sync", use_container_width=False):
        with st.spinner("Reading synced workbooks…"):
            loaded = try_auto_load()
        if loaded:
            try:
                tmka = load_tmka(loaded[0])
                ra = load_ra(loaded[1])
                paths = last_loaded_paths()
                src = Path(paths["allocation"] or "").name or "SharePoint sync"
                msg = set_workbook_data(tmka, ra, source_label=src)
                st.success(msg + " (reloaded)")
                st.rerun()
            except Exception as e:
                st.error(f"Reload failed: {e}")
        else:
            st.error("Could not read synced files.")

st.write("")
st.markdown("##### Or upload manually")
col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown(
        '<div class="tmk-card-label"><span class="tmk-badge">1</span> Resource Info Tracker</div>',
        unsafe_allow_html=True,
    )
    f1 = st.file_uploader(
        "Resource Information Tracker",
        type=["xlsx", "xls", "xlsm"],
        key="file1",
        label_visibility="collapsed",
        help="Required sheet: TMK-A",
    )
    st.markdown('<p class="tmk-card-hint">Required sheet: <strong>TMK-A</strong></p>', unsafe_allow_html=True)

with col2:
    st.markdown(
        '<div class="tmk-card-label"><span class="tmk-badge">2</span> Resource Allocation</div>',
        unsafe_allow_html=True,
    )
    f2 = st.file_uploader(
        "Resource Allocation",
        type=["xlsx", "xls", "xlsm"],
        key="file2",
        label_visibility="collapsed",
        help="Required sheet: Resource Allocation",
    )
    st.markdown(
        '<p class="tmk-card-hint">Required sheet: <strong>Resource Allocation</strong></p>',
        unsafe_allow_html=True,
    )

st.write("")
center = st.columns([1, 2, 1])
with center[1]:
    load = st.button("Load data", type="primary", disabled=not (f1 and f2), use_container_width=True)

# Only show "Data ready" when both files are currently in the upload boxes.
# (Streamlit keeps session data after navigation, but the widgets look empty —
# that used to show a false-ready banner.)
if st.session_state.data_loaded and f1 and f2:
    st.markdown(
        f"""
        <div class="tmk-status-ok">
          Data ready — {len(st.session_state.projects)} billing projects ·
          TMK-A {len(st.session_state.tmka)} · RA {len(st.session_state.ra)}
        </div>
        <div class="tmk-status-info">
          Open a module from the left menu to continue.
        </div>
        """,
        unsafe_allow_html=True,
    )
elif st.session_state.data_loaded:
    c_msg, c_btn = st.columns([3, 1])
    with c_msg:
        st.caption(
            "Earlier Load is still in memory for other pages. "
            "Re-upload both files to refresh, or clear workspace data."
        )
    with c_btn:
        if st.button("Clear data", use_container_width=True):
            clear_workbook_data()
            st.rerun()

if load and f1 and f2:
    try:
        with st.spinner("Reading workbooks…"):
            tmka = load_tmka(f1.getvalue())
            ra = load_ra(f2.getvalue())
            src = f2.name or "uploaded Resource Allocation"
            msg = set_workbook_data(tmka, ra, source_label=src)
        st.success(msg)
        st.rerun()
    except Exception as e:
        st.error(f"Could not read files: {e}")
