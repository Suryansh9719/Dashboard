"""Future Resourcing — parity with DASHBOARD.html tab-fr (full-width layout)."""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from domain.helpers import get_val
from export.excel_export import date_suffix, rows_to_excel_bytes
from ui.session import ensure_workbook_loaded, get_store, init_session
from ui.theme import apply_theme, render_topbar

st.set_page_config(
    page_title="Future Resourcing · TMK",
    layout="wide",
    page_icon="◈",
    initial_sidebar_state="expanded",
)
init_session()
apply_theme()
render_topbar()
ensure_workbook_loaded()

store = get_store()

PLACEHOLDER = "-- Select --"
COLS = [
    "project",
    "band",
    "tech",
    "role",
    "rr",
    "requestType",
    "replacementOf",
    "contractType",
    "fulfilled",
    "onBoardStatus",
    "fromDate",
    "transitionStatus",
]
LABELS = {
    "project": "Project Name",
    "band": "Experience Band",
    "tech": "Tech",
    "role": "Role",
    "rr": "#RR",
    "requestType": "Request Type",
    "replacementOf": "Replacement Of",
    "contractType": "Contract Type",
    "fulfilled": "Fulfilled",
    "onBoardStatus": "On Board Status",
    "fromDate": "From Date",
    "transitionStatus": "Transition Status",
}
INV = {v: k for k, v in LABELS.items()}

REQUEST_TYPES = [PLACEHOLDER, "New", "Replacement"]
CONTRACT_TYPES = [PLACEHOLDER, "Staffing", "Managed", "Managed Staffing"]
FULFILLED = [PLACEHOLDER, "External", "Internal"]
PROGRESS = [PLACEHOLDER, "Open", "In Progress", "Done"]

DEFAULT_BANDS = ["Junior (0-2)", "Mid (2-5)", "Senior (5-8)", "Expert (8+)", "Lead (10+)"]
DEFAULT_ROLES = [
    "Software Engineer",
    "Senior Software Engineer",
    "Lead Engineer",
    "Principal Engineer",
    "Solution Architect",
    "Project Manager",
    "Scrum Master",
    "Business Analyst",
    "QA Engineer",
    "DevOps Engineer",
    "Data Engineer",
]


def _blank_row() -> dict:
    return {
        "project": PLACEHOLDER,
        "band": PLACEHOLDER,
        "tech": "",
        "role": PLACEHOLDER,
        "rr": "",
        "requestType": PLACEHOLDER,
        "replacementOf": "",
        "contractType": PLACEHOLDER,
        "fulfilled": PLACEHOLDER,
        "onBoardStatus": PLACEHOLDER,
        "fromDate": "",
        "transitionStatus": PLACEHOLDER,
    }


def _clean_sel(v: str, options: list[str], default: str = PLACEHOLDER) -> str:
    s = (v or "").strip()
    if not s or s in ("None", "nan", ""):
        return default
    return s if s in options else s


def _normalize_rows(rows: list) -> list[dict]:
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        row = _blank_row()
        for k in COLS:
            v = r.get(k, row[k])
            row[k] = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
        if not row["project"] or row["project"] in ("None", "nan"):
            row["project"] = PLACEHOLDER
        out.append(row)
    return out or [_blank_row()]


if "fr_rows" not in st.session_state:
    st.session_state.fr_rows = _normalize_rows(store.load_fr_items())

st.markdown(
    """
    <style>
    .block-container {
      max-width: 100% !important;
      padding-left: 1.25rem !important;
      padding-right: 1.25rem !important;
    }
    div[data-testid="stDataEditor"] { width: 100% !important; }
    div[data-testid="stDataEditor"] > div { width: 100% !important; }
    div.st-key-fr_add button {
      background:#16a34a !important; border-color:#16a34a !important; color:#fff !important;
    }
    div.st-key-fr_save button {
      background:#4f46e5 !important; border-color:#4f46e5 !important; color:#fff !important;
    }
    div.st-key-fr_export button {
      background:#0d9488 !important; border-color:#0d9488 !important; color:#fff !important;
    }
    div.st-key-fr_view button {
      background:#0f766e !important; border-color:#0f766e !important; color:#fff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Options from TMK-A / billing projects
tmka = st.session_state.get("tmka") or []
bands = sorted(
    {get_val(r, "Experience Band") or get_val(r, "Band") for r in tmka} - {""}
)
if not bands:
    bands = list(DEFAULT_BANDS)
roles = sorted(
    {get_val(r, "Role") or get_val(r, "Designation") for r in tmka} - {""}
)
if not roles:
    roles = list(DEFAULT_ROLES)

projects = list(st.session_state.get("projects") or [])
for r in st.session_state.fr_rows:
    for key, bucket in (("project", projects), ("band", bands), ("role", roles)):
        v = (r.get(key) or "").strip()
        if v and v != PLACEHOLDER and v not in bucket:
            bucket.append(v)

project_opts = [PLACEHOLDER] + projects
band_opts = [PLACEHOLDER] + bands
role_opts = [PLACEHOLDER] + roles

# ── Toolbar ─────────────────────────────────────────────────────────────────
t1, t2, t3, t4, _ = st.columns([0.95, 0.85, 1.15, 0.85, 4.2])
with t1:
    if st.button("+ Add Row", use_container_width=True, key="fr_add"):
        st.session_state.fr_rows = list(st.session_state.fr_rows) + [_blank_row()]
        st.rerun()
with t2:
    do_save = st.button("Save", type="primary", use_container_width=True, key="fr_save")
with t4:
    if st.button("View", use_container_width=True, key="fr_view"):
        st.session_state["_fr_view"] = True


def _to_date(v):
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return None
    if hasattr(v, "date") and not isinstance(v, str):
        try:
            return pd.Timestamp(v).date()
        except Exception:
            return None
    try:
        return pd.to_datetime(str(v).strip()).date()
    except Exception:
        return None


df = pd.DataFrame(_normalize_rows(st.session_state.fr_rows))
df["project"] = df["project"].map(lambda p: _clean_sel(p, project_opts))
df["band"] = df["band"].map(lambda p: _clean_sel(p, band_opts))
df["role"] = df["role"].map(lambda p: _clean_sel(p, role_opts))
for p in df["project"].unique():
    if p and p not in project_opts:
        project_opts.append(p)
for p in df["band"].unique():
    if p and p not in band_opts:
        band_opts.append(p)
for p in df["role"].unique():
    if p and p not in role_opts:
        role_opts.append(p)
df["fromDate"] = df["fromDate"].map(_to_date)
df = df[COLS].rename(columns=LABELS)

edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    height=440,
    column_config={
        "Project Name": st.column_config.SelectboxColumn(
            options=project_opts, required=True, width="medium"
        ),
        "Experience Band": st.column_config.SelectboxColumn(
            options=band_opts, required=True, width="medium"
        ),
        "Tech": st.column_config.TextColumn(width="medium"),
        "Role": st.column_config.SelectboxColumn(
            options=role_opts, required=True, width="medium"
        ),
        "#RR": st.column_config.TextColumn(width="small"),
        "Request Type": st.column_config.SelectboxColumn(
            options=REQUEST_TYPES, required=True, width="small"
        ),
        "Replacement Of": st.column_config.TextColumn(width="medium"),
        "Contract Type": st.column_config.SelectboxColumn(
            options=CONTRACT_TYPES, required=True, width="medium"
        ),
        "Fulfilled": st.column_config.SelectboxColumn(
            options=FULFILLED, required=True, width="small"
        ),
        "On Board Status": st.column_config.SelectboxColumn(
            options=PROGRESS, required=True, width="small"
        ),
        "From Date": st.column_config.DateColumn(format="MM/DD/YYYY", width="small"),
        "Transition Status": st.column_config.SelectboxColumn(
            options=PROGRESS, required=True, width="small"
        ),
    },
    key="fr_editor",
)

st.caption(
    "Dropdowns: Project · Experience Band · Role · Request Type (New/Replacement) · "
    "Contract Type · Fulfilled · On Board / Transition Status (Open / In Progress / Done)"
)


def _cell(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return str(v).strip()


def _df_to_rows(frame: pd.DataFrame) -> list[dict]:
    back = []
    for _, row in frame.iterrows():
        item = {}
        for label in frame.columns:
            key = INV.get(label, label)
            item[key] = _cell(row[label])
        for k in (
            "project",
            "band",
            "role",
            "requestType",
            "contractType",
            "fulfilled",
            "onBoardStatus",
            "transitionStatus",
        ):
            if item.get(k) in (PLACEHOLDER, "None", "nan"):
                item[k] = ""
        if not any(
            item.get(k)
            for k in ("project", "role", "tech", "rr", "replacementOf")
        ):
            continue
        back.append(item)
    return back or [_blank_row()]


current_rows = _df_to_rows(edited)

with t3:
    xbytes = rows_to_excel_bytes(
        "Future Resourcing",
        list(LABELS.values()),
        [[r.get(k, "") for k in COLS] for r in current_rows],
    )
    st.download_button(
        "Export Excel",
        data=xbytes,
        file_name=f"Future_Resourcing_{date_suffix()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="fr_export",
    )

if do_save:
    st.session_state.fr_rows = current_rows
    store.save_fr_items(current_rows)
    store.log_change("Future Resourcing Saved", f"{len(current_rows)} rows")
    st.success("Saved.")

st.session_state.fr_rows = current_rows

# ── View dashboard ──────────────────────────────────────────────────────────
if st.session_state.get("_fr_view"):

    @st.dialog("Future Resourcing Dashboard", width="large")
    def _fr_view_dlg() -> None:
        rows = [r for r in current_rows if r.get("project") or r.get("role")]
        total = len(rows)
        # On Board Status used as pipeline status (HTML view)
        n_open = sum(1 for r in rows if r.get("onBoardStatus") == "Open")
        n_prog = sum(1 for r in rows if r.get("onBoardStatus") == "In Progress")
        n_done = sum(1 for r in rows if r.get("onBoardStatus") == "Done")

        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#1e3a5f,#1e40af);padding:14px 16px;
                 border-radius:8px;color:#fff;margin-bottom:12px">
              <div style="font-size:18px;font-weight:800">Future Resourcing Dashboard</div>
              <div style="font-size:11px;opacity:.8;margin-top:2px">
                {total} open position{"s" if total != 1 else ""}
              </div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">
                <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{total}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Total</div>
                </div>
                <div style="background:rgba(255,255,255,.12);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_open}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Open</div>
                </div>
                <div style="background:rgba(245,158,11,.35);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_prog}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">In Progress</div>
                </div>
                <div style="background:rgba(16,185,129,.35);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_done}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Done</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not rows:
            st.info("No positions yet. Add rows in the table, then Save.")
        else:
            by_proj: dict[str, list] = {}
            for r in rows:
                p = r.get("project") or "(No Project)"
                by_proj.setdefault(p, []).append(r)
            for proj, items in by_proj.items():
                st.markdown(f"**{html.escape(proj)}** · {len(items)} position(s)")
                for r in items:
                    st.markdown(
                        f'<div style="border:1px solid #334155;border-radius:8px;padding:10px 12px;'
                        f'margin-bottom:8px;background:#1e293b">'
                        f'<div style="font-size:13px;font-weight:600;color:#e2e8f0">'
                        f'{html.escape(r.get("role") or "—")} · {html.escape(r.get("band") or "—")}'
                        f"</div>"
                        f'<div style="font-size:11px;color:#94a3b8;margin-top:4px">'
                        f'Tech: {html.escape(r.get("tech") or "—")} · '
                        f'RR: {html.escape(r.get("rr") or "—")} · '
                        f'{html.escape(r.get("requestType") or "—")} · '
                        f'{html.escape(r.get("contractType") or "—")}'
                        f"</div>"
                        f'<div style="font-size:11px;color:#64748b;margin-top:4px">'
                        f'On Board: {html.escape(r.get("onBoardStatus") or "—")} · '
                        f'Transition: {html.escape(r.get("transitionStatus") or "—")} · '
                        f'From: {html.escape(r.get("fromDate") or "—")}'
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )

        if st.button("Close", use_container_width=True, key="fr_view_close"):
            st.session_state["_fr_view"] = False
            st.rerun()

    _fr_view_dlg()
