"""TMK Overview — account-level KPIs and drill-downs."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import re

import pandas as pd
import plotly.express as px
import streamlit as st

from domain.finance import aggregate_account, classify_shore
from domain.helpers import find_tmka_row, get_val, norm, parse_float
from domain.periods import build_periods, detect_month_year_cols, filter_rows_by_cascade
from ui.cascade import render_cascade
from ui.session import fmt_gbp, fmt_pct, init_session, require_data
from ui.theme import apply_theme, render_page_header, render_topbar

st.set_page_config(page_title="TMK Overview · TMK", layout="wide", page_icon="◈", initial_sidebar_state="expanded")
init_session()
apply_theme()
render_topbar()
render_page_header("TMK Overview", "Account-level headcount, cost, revenue, and ICR")

if not require_data():
    st.stop()

ra = st.session_state.ra
tmka = st.session_state.tmka
month_col, year_col = detect_month_year_cols(ra)
periods = build_periods(ra, month_col, year_col)

st.caption("Period filter")
cascade = render_cascade("tmk_ov", periods, state_key="tmk_cascade")
if cascade.get("year"):
    filtered = filter_rows_by_cascade(
        ra, periods, month_col, year_col,
        year=cascade.get("year", 0),
        quarter=cascade.get("quarter", 0),
        month=cascade.get("month", 0),
    )
else:
    filtered = ra

agg = aggregate_account(filtered, tmka)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Engineers", agg["total_engineers"])
m2.metric("Total Cost", fmt_gbp(agg["total_cost"]))
m3.metric("Total Revenue", fmt_gbp(agg["total_rev"]))
m4.metric("Margin", fmt_pct(agg["margin"]))
m5.metric("Onshore / Offshore rows", f"{agg['onshore_rows']} / {agg['offshore_rows']}")

# Project table
pdf = pd.DataFrame(agg["projects"])
if not pdf.empty:
    pdf["cost"] = pdf["cost"].map(lambda x: round(x, 0))
    pdf["rev"] = pdf["rev"].map(lambda x: round(x, 0))
    st.subheader("By Billing Project")
    st.dataframe(pdf, use_container_width=True, hide_index=True)
    fig = px.bar(pdf, x="project", y=["cost", "rev"], barmode="group", title="Cost & Revenue by Project")
    st.plotly_chart(fig, use_container_width=True)

# Engineers modal-like
with st.expander("Engineers list (by project)"):
    proj_eng = {}
    seen = set()
    for row in filtered:
        p = str(get_val(row, "Billing Project")).strip()
        n = re.sub(r"\s+", " ", get_val(row, "Resource Name") or "").strip()
        if not p or not n:
            continue
        key = f"{p}||{n.lower()}"
        if key in seen:
            continue
        seen.add(key)
        t = find_tmka_row(tmka, n)
        proj_eng.setdefault(p, []).append(
            {
                "name": n,
                "role": get_val(t, "Role") or get_val(t, "Designation") or "-",
                "grade": get_val(row, "Grade") or "-",
                "practice": get_val(t, "UK Practice") or get_val(t, "Practice") or "-",
                "shore": classify_shore(row),
            }
        )
    pick = st.selectbox("Project", [""] + sorted(proj_eng.keys()))
    if pick:
        st.dataframe(pd.DataFrame(proj_eng[pick]), use_container_width=True, hide_index=True)

with st.expander("ICR by project"):
    icr_rows = []
    for row in filtered:
        p = str(get_val(row, "Billing Project")).strip()
        n = get_val(row, "Resource Name")
        icr = parse_float(get_val(row, "ICR"))
        if p and n and icr is not None and icr > 0:
            icr_rows.append({"project": p, "resource": n, "icr": icr})
    if icr_rows:
        idf = pd.DataFrame(icr_rows)
        st.dataframe(idf, use_container_width=True, hide_index=True)
        avg = idf.groupby("project", as_index=False)["icr"].mean()
        fig = px.bar(avg, x="project", y="icr", title="Average ICR by Project")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No ICR values in filtered data.")

with st.expander("Project KPI detail"):
    if not pdf.empty:
        p = st.selectbox("Select project for KPI", pdf["project"].tolist(), key="kpi_proj")
        row = pdf[pdf["project"] == p].iloc[0]
        st.write(
            {
                "Engineers": int(row["engineers"]),
                "Cost": fmt_gbp(row["cost"]),
                "Revenue": fmt_gbp(row["rev"]),
                "Margin": fmt_pct(row["margin"]),
            }
        )
