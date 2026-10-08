"""Milestone Tracker — DASHBOARD.html parity (upload → KPI → Gantt → details)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from config import ACCOUNT_NAME, MS_FIXED_PROJECTS
from domain.milestone import (
    build_all_updates_html,
    build_details_table_html,
    build_gantt_html,
    build_kpi_banner_html,
    filter_items,
    normalize_milestones,
    normalize_phases,
    status_counts,
    text_to_html,
)
from export.excel_export import date_suffix, df_to_excel_bytes
from export.milestone_pdf import build_milestone_full_report_pdf
from export.pdf_export import build_simple_pdf
from ingest.excel_loaders import load_milestone
from ingest.pdf_highlights import extract_pdf_text, parse_pdf_highlights
from ingest.sharepoint import local_sync_status, try_auto_load_milestone
from ui.session import get_store, init_session
from ui.theme import apply_theme, render_page_header, render_topbar


def _apply_milestone_bytes(xlsx_bytes: bytes, pdf_bytes: bytes, *, source_label: str) -> None:
    """Parse Milestone.xlsx + Highlights.pdf into session + store."""
    milestones, phases = load_milestone(xlsx_bytes)
    st.session_state.milestones = milestones
    st.session_state.phases = phases
    store = get_store()
    store.save_milestones(milestones, phases)
    store.log_change(
        "Milestones Loaded",
        f"{len(milestones)} milestones, {len(phases)} phases ({source_label})",
    )

    raw = extract_pdf_text(pdf_bytes)
    sections, updates = parse_pdf_highlights(raw)
    st.session_state.ms_highlights = {"raw": raw, "sections": sections}
    st.session_state.ms_updates = updates
    store.save_ms_highlights(raw, sections)
    store.save_ms_updates(updates)
    store.log_change("Highlights PDF Loaded", f"{len(raw)} chars ({source_label})")

    sync = local_sync_status()
    st.session_state["_ms_file_id"] = sync.get("milestone_stamp") or ("sync", len(xlsx_bytes))
    st.session_state["_ms_file_name"] = Path(
        sync["milestone_path"]
    ).name if sync.get("milestone_path") else "Milestone.xlsx"
    st.session_state["_ms_pdf_id"] = sync.get("highlights_stamp") or ("sync", len(pdf_bytes))
    st.session_state["_ms_pdf_name"] = Path(
        sync["highlights_path"]
    ).name if sync.get("highlights_path") else "Highlights.pdf"
    st.session_state["_ms_upload_source"] = True


st.set_page_config(page_title="Milestone · TMK", layout="wide", page_icon="◈", initial_sidebar_state="expanded")
init_session()
apply_theme()
render_topbar()
render_page_header("Milestone Tracker", "Checkpoints, phases, Gantt, and highlights")

store = get_store()
dark = st.session_state.get("theme", "light") == "dark"

# Ensure stored rows are normalized (handles older raw Excel dumps)
if st.session_state.milestones and not (st.session_state.milestones[0] or {}).get("type"):
    st.session_state.milestones = normalize_milestones(st.session_state.milestones)
if st.session_state.phases and not (st.session_state.phases[0] or {}).get("type"):
    st.session_state.phases = normalize_phases(st.session_state.phases)

# ── Auto-load from SharePoint sync folder ───────────────────────────────────
_sync = local_sync_status()
if _sync["enabled"] and _sync["milestone_ok"] and _sync["highlights_ok"]:
    stamp = (_sync.get("milestone_stamp"), _sync.get("highlights_stamp"))
    need_load = (
        not st.session_state.get("_ms_file_id")
        or st.session_state.get("_ms_sync_stamp") != stamp
    )
    if need_load and not st.session_state.get("_ms_sync_skip"):
        with st.spinner("Loading Milestone + Highlights from SharePoint sync…"):
            loaded = try_auto_load_milestone()
        if loaded:
            try:
                _apply_milestone_bytes(loaded[0], loaded[1], source_label="SharePoint sync")
                st.session_state["_ms_sync_stamp"] = stamp
                st.success(
                    f"Auto-loaded from sync: {st.session_state['_ms_file_name']} + "
                    f"{st.session_state['_ms_pdf_name']}"
                )
                st.rerun()
            except Exception as e:
                st.error(f"Milestone auto-load failed: {e}. Use manual upload below.")
        else:
            st.warning("Could not read Milestone / Highlights from sync folder.")
    if st.button("Reload Milestone from SharePoint sync"):
        st.session_state.pop("_ms_sync_skip", None)
        loaded = try_auto_load_milestone()
        if loaded:
            try:
                _apply_milestone_bytes(loaded[0], loaded[1], source_label="SharePoint sync")
                st.session_state["_ms_sync_stamp"] = stamp
                st.success("Reloaded from SharePoint sync.")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        else:
            st.error("Sync files not readable.")
elif _sync["enabled"]:
    missing = []
    if not _sync["milestone_ok"]:
        missing.append("Milestone Excel")
    if not _sync["highlights_ok"]:
        missing.append("Highlights PDF")
    st.caption("Sync missing: " + ", ".join(missing) + " — upload manually below.")

# ── Uploads (manual fallback) ───────────────────────────────────────────────
st.markdown("##### Or upload manually")
u1, u2 = st.columns(2)
with u1:
    ms_file = st.file_uploader(
        "Upload Milestone.xlsx",
        type=["xlsx", "xls", "xlsm"],
        key="ms_xlsx",
        help='Expected sheets: "Milestones" and "Phase"',
    )
    if ms_file and st.session_state.get("_ms_file_id") != (ms_file.name, ms_file.size):
        try:
            milestones, phases = load_milestone(ms_file.getvalue())
            st.session_state.milestones = milestones
            st.session_state.phases = phases
            store.save_milestones(milestones, phases)
            store.log_change(
                "Milestones Loaded",
                f"{len(milestones)} milestones, {len(phases)} phases",
            )
            st.session_state["_ms_file_id"] = (ms_file.name, ms_file.size)
            st.session_state["_ms_file_name"] = ms_file.name
            st.session_state["_ms_upload_source"] = True
            st.session_state["_ms_sync_skip"] = True
            st.success(
                f"Loaded {len(milestones) + len(phases)} rows "
                f"({len(milestones)} milestones, {len(phases)} phases)."
            )
        except Exception as e:
            st.error(str(e))
    if st.session_state.get("_ms_file_name"):
        st.caption(f"✓ {st.session_state['_ms_file_name']}")

with u2:
    pdf_file = st.file_uploader(
        "Upload Highlights.pdf",
        type=["pdf"],
        key="ms_pdf",
        help="Sections: Resourcing, Knowledge Transition, Updates, Issues",
    )
    if pdf_file and st.session_state.get("_ms_pdf_id") != (pdf_file.name, pdf_file.size):
        try:
            raw = extract_pdf_text(pdf_file.getvalue())
            sections, updates = parse_pdf_highlights(raw)
            st.session_state.ms_highlights = {"raw": raw, "sections": sections}
            # HTML replaces project updates from PDF Updates section
            st.session_state.ms_updates = updates
            store.save_ms_highlights(raw, sections)
            store.save_ms_updates(updates)
            store.log_change("Highlights PDF Loaded", f"{len(raw)} chars")
            st.session_state["_ms_pdf_id"] = (pdf_file.name, pdf_file.size)
            st.session_state["_ms_pdf_name"] = pdf_file.name
            st.session_state["_ms_upload_source"] = True
            st.session_state["_ms_sync_skip"] = True
            if not any(sections.values()) and not updates:
                st.warning(
                    "PDF loaded but no recognizable sections found — "
                    "headings should match Resourcing / Knowledge Transition / Updates / Issues."
                )
            else:
                st.success("Highlights PDF loaded and parsed.")
        except Exception as e:
            st.error(str(e))
    if st.session_state.get("_ms_pdf_name"):
        st.caption(f"✓ {st.session_state['_ms_pdf_name']}")

milestones = st.session_state.milestones or []
phases = st.session_state.phases or []
sections = (st.session_state.ms_highlights or {}).get("sections") or {}
updates = st.session_state.ms_updates or {}

# Hard gate: chart/table only after Excel is loaded (upload or sync)
if not st.session_state.get("_ms_file_id"):
    milestones, phases = [], []
    st.session_state.milestones = []
    st.session_state.phases = []

clear_c, _ = st.columns([1, 4])
with clear_c:
    if st.session_state.get("_ms_upload_source") and st.button("Clear uploaded data"):
        st.session_state.milestones = []
        st.session_state.phases = []
        st.session_state.ms_updates = {}
        st.session_state.ms_highlights = {"raw": "", "sections": {}}
        st.session_state.pop("_ms_file_id", None)
        st.session_state.pop("_ms_file_name", None)
        st.session_state.pop("_ms_pdf_id", None)
        st.session_state.pop("_ms_pdf_name", None)
        st.session_state.pop("_ms_upload_source", None)
        st.session_state.pop("_ms_sync_stamp", None)
        st.session_state["_ms_sync_skip"] = True
        st.session_state["_ms_panel"] = "main"
        store.save_milestones([], [])
        store.save_ms_updates({})
        store.save_ms_highlights("", {})
        st.rerun()

if not milestones and not phases:
    st.info(
        "Milestone data not loaded yet. Enable SharePoint sync or upload Milestone.xlsx "
        '(sheets: "Milestones" and "Phase").'
    )
    st.stop()

# One-time: HTML defaults to All Projects (old Python defaulted to AMS)
if not st.session_state.get("_ms_proj_migrated"):
    st.session_state.ms_selected_project = "__ALL__"
    st.session_state["_ms_proj_migrated"] = True

# ── Project filter + actions (HTML msProjSelBar) ────────────────────────────
proj_options = ["__ALL__"] + list(MS_FIXED_PROJECTS)
proj_labels = {
    "__ALL__": "All Projects",
    **{p: p for p in MS_FIXED_PROJECTS},
}
cur = st.session_state.get("ms_selected_project") or "__ALL__"
if cur not in proj_options:
    cur = "__ALL__"
    st.session_state.ms_selected_project = "__ALL__"

sel_col, badge_col, tab_col = st.columns([2.0, 0.85, 2.6])
with sel_col:
    proj = st.selectbox(
        "PROJECT",
        proj_options,
        index=proj_options.index(cur),
        format_func=lambda x: proj_labels.get(x, x),
        key="ms_proj_select",
    )
    st.session_state.ms_selected_project = proj
with badge_col:
    st.markdown(
        f'<div class="tmk-ms-count">{len(MS_FIXED_PROJECTS)} projects</div>',
        unsafe_allow_html=True,
    )
with tab_col:
    panel_opts = ["Gantt", "Project Updates", "Highlights", "Download"]
    cur_panel = st.session_state.get("_ms_panel") or "main"
    panel_map = {
        "main": "Gantt",
        "updates": "Project Updates",
        "highlights": "Highlights",
        "download": "Download",
    }
    inv_map = {v: k for k, v in panel_map.items()}
    pick = st.radio(
        "View",
        panel_opts,
        index=panel_opts.index(panel_map.get(cur_panel, "Gantt")),
        horizontal=True,
        label_visibility="collapsed",
        key="ms_panel_radio",
    )
    st.session_state["_ms_panel"] = inv_map.get(pick, "main")

panel = st.session_state.get("_ms_panel") or "main"
if panel != "main":
    if st.button("← Back to Gantt", type="secondary"):
        st.session_state["_ms_panel"] = "main"
        st.session_state.pop("ms_panel_radio", None)
        st.rerun()

ms_f = filter_items(milestones, proj)
ph_f = filter_items(phases, proj)
is_all = proj == "__ALL__"
title_txt = "All Projects" if is_all else proj
counts = status_counts(ms_f, ph_f)

# ── Panels ──────────────────────────────────────────────────────────────────
if panel == "updates":
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#0d9488,#0f766e);color:#fff;padding:14px 18px;'
        f'border-radius:8px;margin-bottom:12px"><div style="font-size:11px;opacity:.8;font-weight:700;'
        f'text-transform:uppercase">Milestone Focus View</div>'
        f'<div style="font-size:20px;font-weight:800">{title_txt}</div></div>',
        unsafe_allow_html=True,
    )
    c_ref, _ = st.columns([1, 3])
    with c_ref:
        if st.button("Refresh from PDF"):
            raw = (st.session_state.ms_highlights or {}).get("raw") or ""
            if not raw:
                st.warning("No Highlights PDF loaded yet — upload one first.")
            else:
                sections2, updates2 = parse_pdf_highlights(raw)
                st.session_state.ms_highlights = {"raw": raw, "sections": sections2}
                st.session_state.ms_updates = updates2
                store.save_ms_highlights(raw, sections2)
                store.save_ms_updates(updates2)
                st.success("Updates refreshed from Highlights PDF.")
                st.rerun()

    st.markdown(
        '<div style="background:#0d9488;color:#fff;padding:8px 14px;font-size:12px;font-weight:800;'
        'text-transform:uppercase;border-radius:8px 8px 0 0">Update</div>',
        unsafe_allow_html=True,
    )
    if is_all:
        st.markdown(build_all_updates_html(updates, dark=dark), unsafe_allow_html=True)
    else:
        text = st.text_area(
            f"Editable updates for {proj}",
            value=updates.get(proj, ""),
            height=220,
            key=f"upd_edit_{proj}",
        )
        if st.button("Save Project Updates"):
            updates = dict(updates)
            updates[proj] = text
            st.session_state.ms_updates = updates
            store.save_ms_updates(updates)
            store.log_change("MS Updates Saved", proj)
            st.success("Saved.")
        st.markdown(text_to_html(updates.get(proj, "")), unsafe_allow_html=True)

    st.markdown(
        build_gantt_html(ms_f, ph_f, show_project_col=is_all, dark=dark),
        unsafe_allow_html=True,
    )

elif panel == "highlights":
    if not (st.session_state.ms_highlights or {}).get("raw"):
        st.warning("No Highlights PDF loaded yet — upload one first.")
    st.markdown(
        '<div style="background:linear-gradient(135deg,#7c3aed,#5b21b6);color:#fff;padding:16px 20px;'
        'border-radius:8px;margin-bottom:14px;font-size:20px;font-weight:800">Account Highlights</div>',
        unsafe_allow_html=True,
    )

    def _sec(title: str, color: str, text: str) -> str:
        body = (
            text_to_html(text)
            if (text or "").strip()
            else '<span style="color:#94a3b8;font-style:italic">No content found in the uploaded PDF.</span>'
        )
        return (
            f'<div style="background:{"#132337" if dark else "#fff"};border:1px solid '
            f'{"#2a3b4f" if dark else "#e2e8f0"};border-radius:8px;overflow:hidden;margin-bottom:16px">'
            f'<div style="background:{color};color:#fff;padding:8px 14px;font-size:12px;font-weight:800;'
            f'text-transform:uppercase">{title}</div>'
            f'<div style="padding:14px;font-size:13px;line-height:1.55">{body}</div></div>'
        )

    st.markdown(
        _sec("Resourcing", "#0d9488", sections.get("resourcing") or "")
        + _sec("Knowledge Transition", "#1e40af", sections.get("knowledgeTransition") or "")
        + _sec("Issues", "#dc2626", sections.get("issues") or ""),
        unsafe_allow_html=True,
    )
    hl_pdf = build_simple_pdf(
        "Account Highlights",
        [
            ("Resourcing", sections.get("resourcing") or ""),
            ("Knowledge Transition", sections.get("knowledgeTransition") or ""),
            ("Issues", sections.get("issues") or ""),
        ],
    )
    st.download_button(
        "Download Highlights PDF",
        data=hl_pdf,
        file_name=f"Account_Highlights_{date_suffix()}.pdf",
        mime="application/pdf",
    )

elif panel == "download":
    st.subheader("Downloads")
    sheets = {}
    if ms_f:
        sheets["Milestones"] = pd.DataFrame(ms_f)
    if ph_f:
        sheets["Phases"] = pd.DataFrame(ph_f)

    report_pdf = build_milestone_full_report_pdf(
        title=title_txt,
        milestones=ms_f,
        phases=ph_f,
        updates=updates,
        highlights=sections,
        show_project=is_all,
        account_name=ACCOUNT_NAME,
    )
    st.download_button(
        "Download Full Report PDF (Highlights + Updates + Gantt)",
        data=report_pdf,
        file_name=f"{title_txt.replace(' ', '_')}_Milestone_Report_{date_suffix()}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )
    st.caption(
        "2-sheet landscape A3 (DEMOO format): Sheet 1 = Account Highlights "
        "(Resourcing / Knowledge Transition / Issues) + Project-wise Updates; "
        "Sheet 2 = Milestone Gantt from 1st of current month (or next working day if weekend) "
        "through two weeks of next month."
    )

    d1, d2 = st.columns(2)
    with d1:
        if sheets:
            st.download_button(
                "Export Excel",
                data=df_to_excel_bytes(sheets),
                file_name=f"Milestones_{title_txt.replace(' ', '_')}_{date_suffix()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with d2:
        hl_only = build_simple_pdf(
            "Account Highlights",
            [
                ("Resourcing", sections.get("resourcing") or ""),
                ("Knowledge Transition", sections.get("knowledgeTransition") or ""),
                ("Issues", sections.get("issues") or ""),
            ],
        )
        st.download_button(
            "Highlights only PDF",
            data=hl_only,
            file_name=f"Account_Highlights_{date_suffix()}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

else:
    # ── Main tracker view (HTML _msRenderForProject) ────────────────────────
    st.markdown(build_kpi_banner_html(title_txt, counts, dark=dark), unsafe_allow_html=True)
    st.markdown(
        build_gantt_html(ms_f, ph_f, show_project_col=is_all, dark=dark),
        unsafe_allow_html=True,
    )
    st.markdown(
        build_details_table_html(ms_f, ph_f, dark=dark),
        unsafe_allow_html=True,
    )
