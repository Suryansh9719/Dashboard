"""Billing Projects — Project Details, Resource, Finance, Overviews."""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from domain.helpers import get_val, norm
from domain.join import (
    build_fin_rows,
    build_resource_rows,
    calc_pd_totals,
    list_billing_projects,
    project_leadership,
    project_members,
    project_periods,
)
from domain.periods import detect_week_cols, filter_rows_by_cascade, filter_rows_by_period
from export.excel_export import date_suffix, df_to_excel_bytes
from export.pdf_export import project_pdf
from ui.cascade import matched_period_key, render_cascade
from ui.session import fmt_gbp, fmt_pct, get_store, init_session, require_data
from ui.theme import apply_theme, render_page_header, render_topbar

st.set_page_config(page_title="Billing Projects · TMK", layout="wide", page_icon="◈", initial_sidebar_state="expanded")
init_session()
apply_theme()
render_topbar()
render_page_header("Billing Projects", "Project roster, finance, and resource views")

if not require_data():
    st.stop()

store = get_store()
# Re-derive from the loaded RA workbook unless the user added/deleted projects this session.
if not st.session_state.get("_projects_customized"):
    projects, counts = list_billing_projects(st.session_state.ra or [])
    st.session_state.projects = projects
    st.session_state.proj_counts = counts
projects = list(st.session_state.projects)
counts = st.session_state.proj_counts
_src = st.session_state.get("_data_source") or ""
if _src:
    st.markdown(
        f'<p class="tmk-src-note">Data from Resource Allocation: <strong>{html.escape(_src)}</strong></p>',
        unsafe_allow_html=True,
    )

# ---- Project selector / add / delete ----
top = st.columns([3.2, 1.1, 1, 1])
with top[0]:
    labels = {"": "-- Select a Billing Project --"}
    labels.update({p: f"{p} ({counts.get(p, 0)})" for p in projects})
    opts = [""] + projects
    cur = st.session_state.selected_project if st.session_state.selected_project in opts else ""
    selected = st.selectbox(
        "Billing Project",
        opts,
        index=opts.index(cur) if cur in opts else 0,
        format_func=lambda x: labels.get(x, x),
    )
    st.session_state.selected_project = selected
with top[1]:
    st.markdown(
        f'<div class="tmk-proj-count"><span>Projects</span><b>{len(projects)}</b></div>',
        unsafe_allow_html=True,
    )
with top[2]:
    if st.button("+ New Project", use_container_width=True):
        st.session_state["_prompt_new_proj"] = True
with top[3]:
    if st.button("Delete", type="secondary", use_container_width=True) and selected:
        if selected in st.session_state.projects:
            st.session_state.projects = [p for p in st.session_state.projects if p != selected]
            st.session_state["_projects_customized"] = True
            store.delete_project_override(selected)
            store.log_change("Project Deleted", selected)
            st.session_state.selected_project = ""
            st.rerun()

if st.session_state.get("_prompt_new_proj"):
    new_name = st.text_input("New billing project name", key="_new_proj_input")
    if st.button("Create Project") and new_name.strip():
        n = new_name.strip()
        if n not in st.session_state.projects:
            st.session_state.projects = sorted(st.session_state.projects + [n], key=str.lower)
            st.session_state.proj_counts[n] = 0
            st.session_state["_projects_customized"] = True
            store.log_change("Project Added", n)
        st.session_state.selected_project = n
        st.session_state["_prompt_new_proj"] = False
        st.rerun()

if not selected:
    st.info("Select a Billing Project to view details.")
    st.stop()

ra = st.session_state.ra
tmka = st.session_state.tmka
tos_map = st.session_state.tos_map
all_members, unique_rows = project_members(ra, selected)
periods, month_col, year_col = project_periods(all_members)
week_cols = detect_week_cols(all_members)

# Period cascade (defaults to latest month in file — matches HTML)
st.markdown('<div class="tmk-period-bar"><p class="lbl">Period</p></div>', unsafe_allow_html=True)
cascade = render_cascade(f"bill_{selected}", periods, week_cols, state_key=f"cascade_{selected}")
period_key = matched_period_key(periods, cascade)
period_obj = next((p for p in periods if p["key"] == period_key), periods[0] if periods else None)
period_label = (period_obj or {}).get("label") or "All periods"

# Filter members by cascade
if cascade.get("year"):
    filt_members = filter_rows_by_cascade(
        all_members, periods, month_col, year_col,
        year=cascade.get("year", 0),
        quarter=cascade.get("quarter", 0),
        month=cascade.get("month", 0),
    )
else:
    filt_members = filter_rows_by_period(all_members, period_obj, month_col, year_col)

# Unique in filtered set
seen = set()
filt_unique = []
for row in filt_members:
    n = norm(get_val(row, "Resource Name"))
    if n and n not in seen:
        seen.add(n)
        filt_unique.append(row)

pd_totals = calc_pd_totals(filt_members)
lead = project_leadership(filt_unique or unique_rows, tmka)

st.markdown(
    f"""
    <div class="tmk-proj-hero">
      <div>
        <h2>{html.escape(selected)}</h2>
        <p class="meta">Selected period · {html.escape(str(period_label))}</p>
      </div>
      <div class="tmk-team-pill">{len(filt_unique)} team members</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Overrides
ov = st.session_state.overrides.get(selected, {})
res_rows = ov.get("resources") or build_resource_rows(filt_unique or unique_rows, tmka, tos_map)
fin_rows = ov.get("finRows") or build_fin_rows(all_members, tmka, period_obj, month_col, year_col)
if not ov.get("finRows"):
    fin_rows = build_fin_rows(filt_members if filt_members else all_members, tmka, None, month_col, year_col)

tab_pd, tab_res, tab_fin, tab_ov, tab_fov = st.tabs(
    ["Project Details", "Resource Details", "Finance Report", "Resource Overview", "Project Finance Overview"]
)


def _kpi(label: str, value: str, *, accent: bool = False, ok: bool = False, num: bool = False) -> str:
    cls = "val"
    if accent:
        cls += " accent"
    if ok:
        cls += " ok"
    if num:
        cls += " num"
    return (
        f'<div class="tmk-kpi"><div class="lbl">{html.escape(label)}</div>'
        f'<div class="{cls}">{html.escape(value)}</div></div>'
    )


with tab_pd:
    st.markdown(
        '<div class="tmk-kpi-grid">'
        + _kpi("Project Manager", lead["pm"] or "-")
        + _kpi("HLM", lead["hlm"] or "-")
        + _kpi("DM", lead["dm"] or "-")
        + _kpi("Avg ICR", fmt_gbp(pd_totals["icr"]), num=True, accent=True)
        + _kpi("Total Cost", fmt_gbp(pd_totals["cost"]), num=True)
        + _kpi("Margin", fmt_pct(pd_totals["margin"]), num=True, ok=True)
        + _kpi("Revenue", fmt_gbp(pd_totals["rev"]), num=True, accent=True)
        + _kpi("Team Size", str(len(filt_unique)), num=True)
        + "</div>",
        unsafe_allow_html=True,
    )

with tab_res:
    res_df = pd.DataFrame(res_rows)
    rename = {
        "name": "Resource Name", "grade": "Grade", "portalId": "Portal ID", "oneErpId": "OneERP ID",
        "gender": "Gender", "hlm": "HLM", "dm": "DM", "location": "Base Location",
        "practice": "UK Practice", "role": "Role", "primarySkill": "Primary Skills",
        "skills": "Skills", "band": "Experience Band", "billing": "Billing Project",
        "typeOfService": "Type of Service",
    }
    res_df = res_df.rename(columns={k: v for k, v in rename.items() if k in res_df.columns})
    edited_res = st.data_editor(res_df, num_rows="dynamic", use_container_width=True, key=f"res_ed_{selected}")
    if st.button("Save Resource Details", key="save_res"):
        back = []
        inv = {v: k for k, v in rename.items()}
        for _, row in edited_res.iterrows():
            back.append({inv.get(c, c): ("" if pd.isna(row[c]) else row[c]) for c in edited_res.columns})
        st.session_state.overrides.setdefault(selected, {})["resources"] = back
        store.save_project_override(selected, resources=back, fin_rows=st.session_state.overrides[selected].get("finRows"))
        store.log_change("Resources Saved", selected)
        st.success("Saved.")

    names = edited_res["Resource Name"].tolist() if "Resource Name" in edited_res.columns else []
    if names:
        pick = st.selectbox("View resource profile", [""] + [str(n) for n in names if n], key="res_profile")
        if pick:
            row = edited_res[edited_res["Resource Name"] == pick].iloc[0].to_dict()
            st.json(row)

with tab_fin:
    fin_df = pd.DataFrame(fin_rows)
    fin_rename = {
        "name": "Resource Name", "practice": "UK Practice", "costCenter": "Cost Center",
        "typeOfService": "Type of Service", "rateId": "Rate ID / Ext Code", "icr": "ICR",
        "costRecovery": "Cost Recovery", "rateCard": "Rate Card", "rcHr": "RC/Hr",
        "cost": "Cost", "revenue": "Revenue",
    }
    fin_df = fin_df.rename(columns={k: v for k, v in fin_rename.items() if k in fin_df.columns})
    edited_fin = st.data_editor(fin_df, num_rows="dynamic", use_container_width=True, key=f"fin_ed_{selected}")
    if st.button("Save Finance Report", key="save_fin"):
        inv = {v: k for k, v in fin_rename.items()}
        back = []
        for _, row in edited_fin.iterrows():
            item = {}
            for c in edited_fin.columns:
                key = inv.get(c, c)
                val = row[c]
                if key in ("cost", "revenue"):
                    try:
                        item[key] = float(val) if val == val and val != "" else None
                    except (TypeError, ValueError):
                        item[key] = None
                else:
                    item[key] = "" if pd.isna(val) else val
            back.append(item)
        st.session_state.overrides.setdefault(selected, {})["finRows"] = back
        store.save_project_override(selected, resources=st.session_state.overrides[selected].get("resources"), fin_rows=back)
        store.log_change("Finance Saved", selected)
        st.success("Saved.")

with tab_ov:
    rdf = edited_res if isinstance(edited_res, pd.DataFrame) else res_df
    for col, title in [
        ("Role", "By Role"),
        ("Base Location", "By Location"),
        ("UK Practice", "By Practice"),
        ("Experience Band", "By Band"),
        ("Type of Service", "By Type of Service"),
        ("Grade", "By Grade"),
    ]:
        if col in rdf.columns:
            counts_s = rdf[col].fillna("(blank)").replace("", "(blank)").value_counts()
            if len(counts_s):
                fig = px.pie(names=counts_s.index, values=counts_s.values, title=title, hole=0.35)
                fig.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=320)
                st.plotly_chart(fig, use_container_width=True)

with tab_fov:
    fdf = edited_fin if isinstance(edited_fin, pd.DataFrame) else fin_df
    if "Cost" in fdf.columns and "Revenue" in fdf.columns and "Resource Name" in fdf.columns:
        melt = fdf.melt(
            id_vars=["Resource Name"],
            value_vars=["Cost", "Revenue"],
            var_name="Metric",
            value_name="Amount",
        )
        melt["Amount"] = pd.to_numeric(melt["Amount"], errors="coerce").fillna(0)
        fig = px.bar(melt, x="Resource Name", y="Amount", color="Metric", barmode="group", title="Cost vs Revenue")
        fig.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=360)
        st.plotly_chart(fig, use_container_width=True)

    if week_cols and filt_members:
        gantt_rows = []
        for row in filt_members:
            name = get_val(row, "Resource Name")
            for wc in week_cols:
                val = str(row.get(wc["key"], "") or "").strip()
                if val and val not in ("0", "0.0"):
                    gantt_rows.append({"Resource": name, "Week": wc["label"], "Value": val})
        if gantt_rows:
            gdf = pd.DataFrame(gantt_rows)
            try:
                pivot = gdf.pivot_table(index="Resource", columns="Week", values="Value", aggfunc="count", fill_value=0)
                fig = px.imshow(pivot, aspect="auto", title="Weekly Allocation Heatmap")
                fig.update_layout(margin=dict(t=40, b=20, l=20, r=20), height=320)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.dataframe(gdf, use_container_width=True)

# ---- Exports ----
st.divider()
ec1, ec2, ec3 = st.columns(3)
with ec1:
    if st.button("Save Project", use_container_width=True):
        store.save_project_override(
            selected,
            resources=st.session_state.overrides.get(selected, {}).get("resources", res_rows),
            fin_rows=st.session_state.overrides.get(selected, {}).get("finRows", fin_rows),
            pd={"lead": lead, "totals": pd_totals},
        )
        store.log_change("Project Saved", selected)
        st.success("Project saved.")
with ec2:
    xbytes = df_to_excel_bytes(
        {
            "Resource Details": edited_res if isinstance(edited_res, pd.DataFrame) else res_df,
            "Finance Report": edited_fin if isinstance(edited_fin, pd.DataFrame) else fin_df,
        }
    )
    st.download_button(
        "Export Excel",
        data=xbytes,
        file_name=f"TMK_{selected}_{date_suffix()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with ec3:
    rtable = [list((edited_res if isinstance(edited_res, pd.DataFrame) else res_df).columns)]
    for _, row in (edited_res if isinstance(edited_res, pd.DataFrame) else res_df).iterrows():
        rtable.append([str(x) if x == x else "" for x in row.tolist()])
    ftable = [list((edited_fin if isinstance(edited_fin, pd.DataFrame) else fin_df).columns)]
    for _, row in (edited_fin if isinstance(edited_fin, pd.DataFrame) else fin_df).iterrows():
        ftable.append([str(x) if x == x else "" for x in row.tolist()])
    pdf = project_pdf(
        selected,
        {
            "PM": lead["pm"],
            "HLM": lead["hlm"],
            "DM": lead["dm"],
            "Cost": fmt_gbp(pd_totals["cost"]),
            "Revenue": fmt_gbp(pd_totals["rev"]),
            "Margin": fmt_pct(pd_totals["margin"]),
            "ICR": fmt_gbp(pd_totals["icr"]),
        },
        rtable[:80],
        ftable[:80],
    )
    st.download_button(
        "Save PDF",
        data=pdf,
        file_name=f"TMK_{selected}_{date_suffix()}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
