"""Account Buffer — parity with DASHBOARD.html tab-buffer."""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from config import MONTH_NAMES
from domain.buffer import build_buffer_data
from ui.session import ensure_workbook_loaded, init_session
from ui.theme import apply_theme, render_topbar

st.set_page_config(
    page_title="Account Buffer · TMK",
    layout="wide",
    page_icon="◈",
    initial_sidebar_state="expanded",
)
init_session()
apply_theme()
render_topbar()
ensure_workbook_loaded()

st.markdown(
    """
    <style>
    .block-container {
      max-width: 100% !important;
      padding-left: 1.25rem !important;
      padding-right: 1.25rem !important;
    }
    .buf-banner {
      background: linear-gradient(135deg, #1e3a5f, #4f46e5);
      color: #fff; padding: 12px 18px; border-radius: 8px;
      margin-bottom: 16px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
    }
    .buf-banner .title { font-size: 15px; font-weight: 800; }
    .buf-banner .sub { font-size: 11px; opacity: .85; }
    .buf-year {
      background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
      overflow: hidden; margin-bottom: 4px; box-shadow: 0 1px 4px rgba(0,0,0,.06);
    }
    .buf-year-hdr {
      background: linear-gradient(135deg, #1e3a5f, #1e40af);
      padding: 10px 16px; display: flex; align-items: center; justify-content: space-between;
      color: #fff;
    }
    .buf-year-hdr .y { font-size: 14px; font-weight: 800; }
    .buf-year-hdr .badge {
      background: rgba(255,255,255,.2); border-radius: 12px;
      padding: 2px 10px; font-size: 11px; font-weight: 700;
    }
    /* Month card buttons — look like HTML cards */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
      background: var(--panel) !important;
      border: 1.5px solid var(--line) !important;
      border-radius: 8px !important;
      padding: 14px 10px !important;
      min-height: 96px !important;
      white-space: pre-line !important;
      line-height: 1.25 !important;
      color: var(--text) !important;
      font-weight: 600 !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
      border-color: #4f46e5 !important;
      box-shadow: 0 6px 18px rgba(79,70,229,.25) !important;
      transform: scale(1.02);
    }
    .buf-card-inner .cnt { font-size: 24px; font-weight: 800; color: #4f46e5; }
    .buf-card-inner .mon {
      font-size: 11px; font-weight: 700; color: var(--muted);
      text-transform: uppercase; letter-spacing: .4px; margin-top: 4px;
    }
    .buf-card-inner .hint { font-size: 9px; color: #6366f1; opacity: .85; margin-top: 4px; }
    .buf-res {
      background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
      overflow: hidden; margin-bottom: 14px;
    }
    .buf-res-hdr {
      background: linear-gradient(135deg, #1e3a5f, #1e40af);
      padding: 9px 16px; display: flex; align-items: center; gap: 8px; color: #fff;
    }
    .buf-res-hdr .num {
      background: rgba(255,255,255,.2); border-radius: 12px;
      padding: 1px 9px; font-size: 11px; font-weight: 700;
    }
    .buf-res-hdr .nm { font-size: 14px; font-weight: 800; }
    .buf-fields {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 1px; background: var(--line);
    }
    .buf-field { background: var(--surface); padding: 8px 12px; }
    .buf-field .k {
      font-size: 9px; font-weight: 700; text-transform: uppercase;
      letter-spacing: .4px; color: var(--muted); margin-bottom: 3px;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .buf-field .v {
      font-size: 12px; font-weight: 600; color: var(--text);
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    [data-tmk="dark"] .buf-year { background: #1e293b; border-color: #334155; }
    [data-tmk="dark"] .buf-res { background: #1e293b; border-color: #334155; }
    [data-tmk="dark"] .buf-field { background: #263348; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.get("data_loaded") or not st.session_state.get("ra"):
    st.info(
        "Load Excel files first (Home). This tab shows resources whose "
        'Billing Project is "Account Buffer", grouped by Year / Month.'
    )
    st.stop()

data = build_buffer_data(st.session_state.ra)
tree = data["tree"]
years = sorted([y for y in tree.keys() if y > 0], reverse=True)
unknown = tree.get(0)

st.markdown(
    f"""
    <div class="buf-banner">
      <span class="title">👤 Account Buffer</span>
      <span class="sub">{data["total"]} resource{"s" if data["total"] != 1 else ""}
      currently in buffer · grouped by Year / Month</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if not years and not unknown:
    st.warning(
        'No resources found with Billing Project = "Account Buffer". '
        "Check the Resource Allocation sheet."
    )
    st.stop()


def _month_abbr(y: int, m: int, m_data: dict) -> str:
    if 1 <= m <= 12:
        return MONTH_NAMES[m - 1]
    return (m_data.get("label") or str(m) or "—")[:12]


def _render_month_cards(year_key: int, months: list[int], src: dict) -> None:
    """HTML-like grid of month cards; click opens detail dialog."""
    # rows of up to 7 cards
    for start in range(0, len(months), 7):
        chunk = months[start : start + 7]
        cols = st.columns(len(chunk))
        for i, m in enumerate(chunk):
            m_data = src[m]
            cnt = len(m_data["resources"])
            label = _month_abbr(year_key, m, m_data)
            with cols[i]:
                # Visual card + View button (Streamlit can't HTML-onclick)
                st.markdown(
                    f"""
                    <div class="buf-card-inner" style="
                      background:var(--panel);border:1.5px solid var(--line);
                      border-radius:8px;padding:14px 10px;text-align:center;margin-bottom:4px">
                      <div class="cnt">{cnt}</div>
                      <div class="mon">{html.escape(label)}</div>
                      <div class="hint">👁 Click to view</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(
                    "View",
                    key=f"buf_view_{year_key}_{m}",
                    use_container_width=True,
                    type="secondary",
                ):
                    st.session_state["_buf_detail"] = (year_key, m)
                    st.rerun()


# Year → month cards
for y in years:
    months = sorted(tree[y].keys())
    year_total = sum(len(tree[y][m]["resources"]) for m in months)
    st.markdown(
        f"""
        <div class="buf-year">
          <div class="buf-year-hdr">
            <span class="y">📅 {y}</span>
            <span class="badge">{year_total} total</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_month_cards(y, months, tree[y])
    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

if unknown:
    u_months = sorted(unknown.keys())
    u_total = sum(len(unknown[m]["resources"]) for m in u_months)
    st.markdown(
        f"""
        <div class="buf-year">
          <div class="buf-year-hdr" style="background:linear-gradient(135deg,#64748b,#94a3b8)">
            <span class="y">📅 Unspecified Period</span>
            <span class="badge">{u_total} total</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_month_cards(0, u_months, unknown)

# ── Month detail dialog (HTML openBufferMonthDetail) ────────────────────────
detail = st.session_state.get("_buf_detail")
if detail:
    y, m = detail
    if y == 0 and unknown:
        m_data = unknown.get(m)
    else:
        m_data = tree.get(y, {}).get(m)

    if m_data:
        title_m = _month_abbr(y, m, m_data)
        dlg_title = f"Account Buffer — {title_m}" + (f" {y}" if y else "")

        @st.dialog(dlg_title, width="large")
        def _buf_dlg() -> None:
            resources = sorted(
                m_data["resources"], key=lambda r: (r["name"] or "").lower()
            )
            st.caption(
                f"{len(resources)} resource{'s' if len(resources) != 1 else ''}"
            )

            # Column union (Excel order) — same as HTML
            col_order: list[str] = []
            seen: set[str] = set()
            for r in resources:
                raw = r.get("rawRow") or {}
                for k in raw.keys():
                    if k not in seen:
                        seen.add(k)
                        col_order.append(k)

            for i, r in enumerate(resources, 1):
                raw = r.get("rawRow") or {}
                fields_html = []
                for k in col_order:
                    v = raw.get(k)
                    vs = "" if v is None else str(v).strip()
                    fields_html.append(
                        f'<div class="buf-field">'
                        f'<div class="k" title="{html.escape(str(k))}">{html.escape(str(k))}</div>'
                        f'<div class="v" title="{html.escape(vs)}">{html.escape(vs or "—")}</div>'
                        f"</div>"
                    )
                st.markdown(
                    f"""
                    <div class="buf-res">
                      <div class="buf-res-hdr">
                        <span class="num">{i}</span>
                        <span class="nm">{html.escape(r["name"])}</span>
                      </div>
                      <div class="buf-fields">{"".join(fields_html)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if st.button("✕ Close", use_container_width=True, key="buf_close"):
                st.session_state.pop("_buf_detail", None)
                st.rerun()

        _buf_dlg()
