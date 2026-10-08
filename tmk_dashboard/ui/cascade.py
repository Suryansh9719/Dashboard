"""Cascade period selector UI."""
from __future__ import annotations

import streamlit as st

from config import MONTH_NAMES
from domain.periods import (
    get_month_num_from_period,
    get_year_from_period,
    months_in_quarter,
    year_set_from_periods,
)


def render_cascade(
    key_prefix: str,
    periods: list[dict],
    week_cols: list[dict] | None = None,
    state_key: str | None = None,
) -> dict:
    """
    Render Year/Quarter/Month/(Week) selectors.
    Returns cascade dict {year, quarter, month, week}.

    Defaults match DASHBOARD.html: latest period's year + quarter + month.
    """
    from domain.periods import quarter_of_month

    week_cols = week_cols or []
    year_set = year_set_from_periods(periods)
    years = sorted(year_set.keys(), reverse=True)
    if not years:
        return {"year": 0, "quarter": 0, "month": 0, "week": ""}

    # Latest period (periods are sorted newest-first)
    latest = periods[0] if periods else None
    init_year = get_year_from_period(latest) if latest else years[0]
    init_month = get_month_num_from_period(latest) if latest else 0
    init_quarter = quarter_of_month(init_month) if init_month else 0

    sk = state_key or f"{key_prefix}_cascade"
    if sk not in st.session_state:
        st.session_state[sk] = {
            "year": init_year or years[0],
            "quarter": init_quarter,
            "month": init_month,
            "week": "",
        }
    cs = st.session_state[sk]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        year_opts = [0] + years
        year_labels = {0: "All Years", **{y: str(y) for y in years}}
        year = st.selectbox(
            "Year",
            year_opts,
            index=year_opts.index(cs.get("year") if cs.get("year") in year_opts else years[0]),
            format_func=lambda x: year_labels.get(x, str(x)),
            key=f"{key_prefix}_year",
        )
    quarter = 0
    month = 0
    week = ""
    with c2:
        if year:
            avail_qs = [
                q
                for q in (1, 2, 3, 4)
                if any(m in year_set.get(year, {}) for m in months_in_quarter(q))
            ]
            q_opts = [0] + avail_qs
            q_labels = {
                0: "All Quarters",
                1: "Q1 (Jan-Mar)",
                2: "Q2 (Apr-Jun)",
                3: "Q3 (Jul-Sep)",
                4: "Q4 (Oct-Dec)",
            }
            cur_q = cs.get("quarter") if cs.get("quarter") in q_opts else 0
            quarter = st.selectbox(
                "Quarter",
                q_opts,
                index=q_opts.index(cur_q),
                format_func=lambda x: q_labels.get(x, str(x)),
                key=f"{key_prefix}_q",
            )
        else:
            st.selectbox("Quarter", ["—"], disabled=True, key=f"{key_prefix}_q_dis")
    with c3:
        if year and quarter:
            q_months = [m for m in months_in_quarter(quarter) if m in year_set.get(year, {})]
            m_opts = [0] + q_months
            cur_m = cs.get("month") if cs.get("month") in m_opts else 0
            month = st.selectbox(
                "Month",
                m_opts,
                index=m_opts.index(cur_m),
                format_func=lambda x: "All Months" if x == 0 else MONTH_NAMES[x - 1],
                key=f"{key_prefix}_m",
            )
        else:
            st.selectbox("Month", ["—"], disabled=True, key=f"{key_prefix}_m_dis")
    with c4:
        if year and quarter and month and week_cols:
            w_opts = [""] + [w["key"] for w in week_cols]
            w_labels = {"": "All Weeks", **{w["key"]: w["label"] for w in week_cols}}
            cur_w = cs.get("week") if cs.get("week") in w_opts else ""
            week = st.selectbox(
                "Week",
                w_opts,
                index=w_opts.index(cur_w),
                format_func=lambda x: w_labels.get(x, str(x)),
                key=f"{key_prefix}_w",
            )
        else:
            st.selectbox("Week", ["—"], disabled=True, key=f"{key_prefix}_w_dis")

    # Reset children when parent changes
    if year != cs.get("year"):
        quarter = month = 0
        week = ""
    elif quarter != cs.get("quarter"):
        month = 0
        week = ""
    elif month != cs.get("month"):
        week = ""

    new_cs = {"year": year or 0, "quarter": quarter or 0, "month": month or 0, "week": week or ""}
    st.session_state[sk] = new_cs
    return new_cs


def matched_period_key(periods: list[dict], cascade: dict) -> str | None:
    """Pick a period key from cascade selection (mirrors _applyProjCascade)."""
    if not periods:
        return None
    year = cascade.get("year") or 0
    quarter = cascade.get("quarter") or 0
    month = cascade.get("month") or 0
    matched = []
    for p in periods:
        py = get_year_from_period(p)
        pm = get_month_num_from_period(p)
        if year and month:
            if py == year and pm == month:
                matched.append(p)
        elif year and quarter:
            if py == year and pm in months_in_quarter(quarter):
                matched.append(p)
        elif year:
            if py == year:
                matched.append(p)
        else:
            return periods[0]["key"]
    return matched[0]["key"] if matched else periods[0]["key"]
