"""Risks / Action Items — parity with DASHBOARD.html tab-actions."""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from export.excel_export import date_suffix, rows_to_excel_bytes
from ui.session import ensure_workbook_loaded, get_store, init_session
from ui.theme import apply_theme, render_topbar

st.set_page_config(
    page_title="Risks / Action Items · TMK",
    layout="wide",
    page_icon="◈",
    initial_sidebar_state="expanded",
)
init_session()
apply_theme()
render_topbar()
ensure_workbook_loaded()

store = get_store()

COLS = [
    "project",
    "description",
    "category",
    "severity",
    "mitigation",
    "owner",
    "dateRaised",
    "eta",
    "completionDate",
    "status",
]
LABELS = {
    "project": "Project Name",
    "description": "Description",
    "category": "Category",
    "severity": "Severity",
    "mitigation": "Mitigation Plan",
    "owner": "Owner",
    "dateRaised": "Date Raised",
    "eta": "ETA",
    "completionDate": "Completion Date",
    "status": "Status",
}
INV = {v: k for k, v in LABELS.items()}

CATEGORIES = ["Action Item", "Risk"]
SEVERITIES = ["Low", "Medium", "High"]
# Order matches HTML UI request
STATUSES = ["Open", "Closed", "In Progress", "Rejected"]
PROJECT_PLACEHOLDER = "-- Select --"

SEV_COLOR = {"Low": "#0d9488", "Medium": "#f59e0b", "High": "#ef4444"}
STATUS_COLOR = {
    "Open": "#64748b",
    "Closed": "#10b981",
    "In Progress": "#f59e0b",
    "Rejected": "#ef4444",
}


def _blank_row() -> dict:
    return {
        "project": PROJECT_PLACEHOLDER,
        "description": "",
        "category": "Action Item",
        "severity": "Medium",
        "mitigation": "",
        "owner": "",
        "dateRaised": "",
        "eta": "",
        "completionDate": "",
        "status": "Open",
    }


def _normalize_rows(rows: list) -> list[dict]:
    out = []
    for r in rows or []:
        if not isinstance(r, dict):
            continue
        row = _blank_row()
        for k in COLS:
            v = r.get(k, row[k])
            row[k] = "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)
        if not row["project"] or row["project"] in ("", "None", "nan"):
            row["project"] = PROJECT_PLACEHOLDER
        if row["category"] not in CATEGORIES:
            row["category"] = "Action Item"
        if row["severity"] not in SEVERITIES:
            row["severity"] = "Medium"
        if row["status"] not in STATUSES:
            row["status"] = "Closed" if row["status"] in ("Done", "Complete") else "Open"
        out.append(row)
    return out or [_blank_row()]


if "ai_rows" not in st.session_state:
    st.session_state.ai_rows = _normalize_rows(store.load_action_items())

st.markdown(
    """
    <style>
    /* Full-width layout — Risks table needs room for all columns */
    .block-container {
      max-width: 100% !important;
      padding-left: 1.25rem !important;
      padding-right: 1.25rem !important;
    }
    div[data-testid="stDataFrame"],
    div[data-testid="stDataEditor"] {
      width: 100% !important;
    }
    div[data-testid="stDataEditor"] > div {
      width: 100% !important;
    }
    /* Compact left-aligned toolbar */
    div.st-key-ai_add button {
      background:#16a34a !important; border-color:#16a34a !important; color:#fff !important;
    }
    div.st-key-ai_save button {
      background:#4f46e5 !important; border-color:#4f46e5 !important; color:#fff !important;
    }
    div.st-key-ai_export button {
      background:#0d9488 !important; border-color:#0d9488 !important; color:#fff !important;
    }
    div.st-key-ai_view button {
      background:#0f766e !important; border-color:#0f766e !important; color:#fff !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Toolbar (HTML: Add Row | Save | Export Excel | View) ────────────────────
t1, t2, t3, t4, t5 = st.columns([0.95, 0.85, 1.15, 0.85, 4.2])
with t1:
    if st.button("+ Add Row", use_container_width=True, key="ai_add"):
        st.session_state.ai_rows = list(st.session_state.ai_rows) + [_blank_row()]
        st.rerun()
with t2:
    do_save = st.button("Save", type="primary", use_container_width=True, key="ai_save")
with t3:
    pass  # export built after editor
with t4:
    if st.button("View", use_container_width=True, key="ai_view"):
        st.session_state["_ai_view"] = True

projects = list(st.session_state.get("projects") or [])
# Keep any saved project names that are not in current billing list
for r in st.session_state.ai_rows:
    p = (r.get("project") or "").strip()
    if p and p not in projects and p != PROJECT_PLACEHOLDER:
        projects.append(p)
project_options = [PROJECT_PLACEHOLDER] + projects

if len(project_options) <= 1:
    st.warning(
        "No billing projects loaded yet — open **Home** so the Project Name dropdown can fill. "
        "Severity and Status dropdowns still work."
    )

def _to_date(v):
    if v is None or v == "" or (isinstance(v, float) and pd.isna(v)):
        return None
    if hasattr(v, "date") and not isinstance(v, str):
        try:
            return pd.Timestamp(v).date()
        except Exception:
            return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return pd.to_datetime(s).date()
    except Exception:
        return None


df = pd.DataFrame(_normalize_rows(st.session_state.ai_rows))
# Project values must be in the selectbox options
df["project"] = df["project"].apply(
    lambda p: p if p in project_options else (PROJECT_PLACEHOLDER if not p else p)
)
for p in df["project"].unique():
    if p and p not in project_options:
        project_options.append(p)
for dc in ("dateRaised", "eta", "completionDate"):
    df[dc] = df[dc].map(_to_date)
df = df[COLS].rename(columns=LABELS)

edited = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    hide_index=True,
    disabled=False,
    height=420,
    column_config={
        "Project Name": st.column_config.SelectboxColumn(
            "Project Name",
            help="Select a billing project",
            options=project_options,
            required=True,
            width="medium",
        ),
        "Description": st.column_config.TextColumn("Description", width="large"),
        "Category": st.column_config.SelectboxColumn(
            "Category",
            options=CATEGORIES,
            required=True,
            width="small",
        ),
        "Severity": st.column_config.SelectboxColumn(
            "Severity",
            help="Low · Medium · High",
            options=SEVERITIES,
            required=True,
            width="small",
        ),
        "Mitigation Plan": st.column_config.TextColumn("Mitigation Plan", width="large"),
        "Owner": st.column_config.TextColumn("Owner", width="medium"),
        "Date Raised": st.column_config.DateColumn("Date Raised", format="MM/DD/YYYY", width="small"),
        "ETA": st.column_config.DateColumn("ETA", format="MM/DD/YYYY", width="small"),
        "Completion Date": st.column_config.DateColumn(
            "Completion Date", format="MM/DD/YYYY", width="small"
        ),
        "Status": st.column_config.SelectboxColumn(
            "Status",
            help="Open · Closed · In Progress · Rejected",
            options=STATUSES,
            required=True,
            width="small",
        ),
    },
    key="ai_editor",
)

st.caption(
    "Dropdowns: **Project Name** (from loaded billing projects) · "
    "**Severity** Low / Medium / High · "
    "**Status** Open / Closed / In Progress / Rejected"
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
        # Store empty project when placeholder selected (HTML -- Select --)
        if item.get("project") in (PROJECT_PLACEHOLDER, "None", "nan"):
            item["project"] = ""
        if not any(item.get(k) for k in ("project", "description", "owner", "mitigation")):
            if not item.get("project") and not item.get("description"):
                continue
        if item.get("category") not in CATEGORIES:
            item["category"] = "Action Item"
        if item.get("severity") not in SEVERITIES:
            item["severity"] = "Medium"
        if item.get("status") not in STATUSES:
            item["status"] = "Open"
        back.append(item)
    return back or [_blank_row()]


current_rows = _df_to_rows(edited)

# Export button (uses current editor state)
with t3:
    xbytes = rows_to_excel_bytes(
        "Risks Issues Action Items",
        list(LABELS.values()),
        [[r.get(k, "") for k in COLS] for r in current_rows],
    )
    st.download_button(
        "Export Excel",
        data=xbytes,
        file_name=f"Risks_Issues_ActionItems_{date_suffix()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        key="ai_export",
    )

if do_save:
    prev = _normalize_rows(st.session_state.ai_rows)
    st.session_state.ai_rows = current_rows
    store.save_action_items(current_rows)
    # Field-level changelog (HTML saveActionItems)
    prev_map = {
        f"{(p.get('project') or '')}||{(p.get('description') or '')[:30]}": p for p in prev
    }
    for r in current_rows:
        if not (r.get("project") or r.get("description")):
            continue
        key = f"{(r.get('project') or '')}||{(r.get('description') or '')[:30]}"
        old = prev_map.get(key)
        if not old:
            store.log_change(
                "Row Added",
                f"[Risks/Issues/Action Items] (NEW) Project: {r.get('project') or '-'} "
                f"| Category: {r.get('category')} | Severity: {r.get('severity')} "
                f"| Status: {r.get('status')} | {(r.get('description') or '')[:60]}",
            )
        else:
            changes = []
            for k, lab in LABELS.items():
                ov, nv = old.get(k) or "", r.get(k) or ""
                if ov != nv:
                    changes.append(f'{lab}: "{ov}" -> "{nv}"')
            if changes:
                store.log_change(
                    "Row Edited",
                    f"[Risks/Issues/Action Items] Project: {r.get('project') or '-'} | "
                    + ", ".join(changes[:8]),
                )
    store.log_change("Action Items Saved", f"{len(current_rows)} rows")
    st.success("Saved.")

# Keep session in sync with editor for View / Add Row
st.session_state.ai_rows = current_rows

# ── View modal (HTML openActionItemsView) ───────────────────────────────────
if st.session_state.get("_ai_view"):

    @st.dialog("Action Items Dashboard", width="large")
    def _ai_view_dlg() -> None:
        rows = [
            r
            for r in current_rows
            if (r.get("project") or r.get("description"))
        ]
        total = len(rows)
        n_open = sum(1 for r in rows if r.get("status") == "Open")
        n_prog = sum(1 for r in rows if r.get("status") == "In Progress")
        n_closed = sum(1 for r in rows if r.get("status") == "Closed")
        n_rej = sum(1 for r in rows if r.get("status") == "Rejected")
        done_pct = round((n_closed / total) * 100) if total else 0

        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#3730a3,#4f46e5);padding:14px 16px;
                 border-radius:8px;color:#fff;margin-bottom:12px">
              <div style="font-size:18px;font-weight:800">Action Items Dashboard</div>
              <div style="font-size:11px;opacity:.8;margin-top:2px">
                {total} total item{"s" if total != 1 else ""}
              </div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:12px">
                <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{total}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Total</div>
                </div>
                <div style="background:rgba(255,255,255,.15);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_open}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Open</div>
                </div>
                <div style="background:rgba(245,158,11,.35);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_prog}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">In Progress</div>
                </div>
                <div style="background:rgba(16,185,129,.35);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_closed}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Closed</div>
                </div>
                <div style="background:rgba(239,68,68,.35);border-radius:8px;padding:8px 14px;text-align:center;min-width:70px">
                  <div style="font-size:22px;font-weight:800">{n_rej}</div>
                  <div style="font-size:9px;opacity:.8;text-transform:uppercase">Rejected</div>
                </div>
              </div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
              <span style="font-size:11px;font-weight:700;color:#94a3b8">Completion</span>
              <div style="flex:1;background:#334155;border-radius:6px;height:12px;overflow:hidden">
                <div style="background:linear-gradient(90deg,#10b981,#0d9488);height:100%;width:{done_pct}%;border-radius:6px"></div>
              </div>
              <span style="font-size:12px;font-weight:700;color:#10b981">{done_pct}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not rows:
            st.info("No action items yet. Add rows in the table, then Save.")
        else:
            by_proj: dict[str, list] = {}
            for r in rows:
                p = r.get("project") or "(No Project)"
                by_proj.setdefault(p, []).append(r)
            for proj, items in by_proj.items():
                proj_closed = sum(1 for r in items if r.get("status") == "Closed")
                proj_pct = round((proj_closed / len(items)) * 100) if items else 0
                st.markdown(
                    f"**{html.escape(proj)}** · {len(items)} item(s) · {proj_pct}% closed"
                )
                for r in items:
                    sev = r.get("severity") or "Medium"
                    st_ = r.get("status") or "Open"
                    sc = SEV_COLOR.get(sev, "#f59e0b")
                    tc = STATUS_COLOR.get(st_, "#64748b")
                    st.markdown(
                        f'<div style="border:1px solid #334155;border-radius:8px;padding:10px 12px;'
                        f'margin-bottom:8px;background:#1e293b">'
                        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px">'
                        f'<span style="background:{sc};color:#fff;font-size:10px;font-weight:700;'
                        f'padding:2px 8px;border-radius:4px">{html.escape(sev)}</span>'
                        f'<span style="background:{tc};color:#fff;font-size:10px;font-weight:700;'
                        f'padding:2px 8px;border-radius:4px">{html.escape(st_)}</span>'
                        f'<span style="font-size:11px;color:#94a3b8">{html.escape(r.get("category") or "")}</span>'
                        f"</div>"
                        f'<div style="font-size:13px;font-weight:600;color:#e2e8f0">'
                        f'{html.escape(r.get("description") or "(no description)")}</div>'
                        f'<div style="font-size:11px;color:#94a3b8;margin-top:6px">'
                        f'Owner: {html.escape(r.get("owner") or "—")} · '
                        f'Raised: {html.escape(r.get("dateRaised") or "—")} · '
                        f'ETA: {html.escape(r.get("eta") or "—")}'
                        f"</div>"
                        f'<div style="font-size:11px;color:#64748b;margin-top:4px">'
                        f'{html.escape(r.get("mitigation") or "")}</div>'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        if st.button("Close", use_container_width=True, key="ai_view_close"):
            st.session_state["_ai_view"] = False
            st.rerun()

    _ai_view_dlg()
