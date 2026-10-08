"""TMK Project Commercials."""
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

from export.excel_export import date_suffix, df_to_excel_bytes
from ingest.excel_loaders import load_commercials
from ui.session import get_store, init_session
from ui.theme import apply_theme, render_page_header, render_topbar

st.set_page_config(page_title="Commercials · TMK", layout="wide", page_icon="◈", initial_sidebar_state="expanded")
init_session()
apply_theme()
render_topbar()
render_page_header("Project Commercials", "Variance tracking across commercial projects")

store = get_store()
if not st.session_state.commercials:
    st.session_state.commercials = store.load_commercials()

f = st.file_uploader("Upload TMK Project Commercials.xlsx", type=["xlsx", "xls"])
if f:
    try:
        rows = load_commercials(f.getvalue())
        st.session_state.commercials = rows
        store.save_commercials(rows)
        store.log_change("Commercials Loaded", f"{len(rows)} rows")
        st.success(f"Loaded {len(rows)} rows.")
    except Exception as e:
        st.error(str(e))

data = st.session_state.commercials
if not data:
    st.info("Upload your TMK Project Commercials.xlsx to view project financials.")
    st.stop()


def find_key(row: dict, patterns: list) -> str | None:
    for k in row.keys():
        nk = str(k).strip().lower()
        for p in patterns:
            if re.search(p, nk):
                return k
    return None


def parse_num(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        s = str(v).replace(",", "").replace("£", "").replace("%", "").strip()
        return float(s)
    except (TypeError, ValueError):
        return None


def find_variance_key(row: dict) -> str | None:
    for k in row.keys():
        if "variance" in str(k).lower():
            return k
    return None


sample = data[0]
var_key = find_variance_key(sample)
proj_key = find_key(sample, [r"^project$", r"project\s*name", r"project", r"account", r"^name$"])
desc_key = find_key(sample, [r"project\s*desc", r"^description$", r"^desc$", r"description"])

neg = pos = 0
total_var = 0.0
for row in data:
    if not var_key:
        break
    n = parse_num(row.get(var_key))
    if n is None:
        continue
    total_var += n
    if n < 0:
        neg += 1
    else:
        pos += 1

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Projects", len(data))
k2.metric("Negative Variance", neg)
k3.metric("Positive Variance", pos)
k4.metric("Net Variance", f"{'−' if total_var < 0 else ''}£{abs(round(total_var)):,}")

# KPI drill-downs
filter_mode = st.radio("KPI filter", ["all", "negative", "positive"], horizontal=True)
filtered = data
if var_key and filter_mode != "all":
    filtered = []
    for row in data:
        n = parse_num(row.get(var_key))
        if n is None:
            continue
        if filter_mode == "negative" and n < 0:
            filtered.append(row)
        if filter_mode == "positive" and n >= 0:
            filtered.append(row)

df = pd.DataFrame(filtered)
st.dataframe(df, use_container_width=True, hide_index=True)

if var_key:
    chart_rows = []
    for row in data:
        n = parse_num(row.get(var_key))
        if n is None:
            continue
        code = str(row.get(proj_key, "")).strip() if proj_key else ""
        desc = str(row.get(desc_key, "")).strip() if desc_key else ""
        label = f"{code} - {desc}" if desc else (code or "?")
        chart_rows.append({"project": label[:40], "variance": n, "color": "neg" if n < 0 else "pos"})
    if chart_rows:
        cdf = pd.DataFrame(chart_rows)
        fig = px.bar(
            cdf,
            x="project",
            y="variance",
            color="color",
            color_discrete_map={"neg": "#ef4444", "pos": "#10b981"},
            title="Variance by Project",
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

st.download_button(
    "Export Excel",
    data=df_to_excel_bytes({"Commercials": pd.DataFrame(data)}),
    file_name=f"TMK_Commercials_{date_suffix()}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
