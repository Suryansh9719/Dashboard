"""Professional corporate theme for TMK Dashboard."""
from __future__ import annotations

import streamlit as st

from ui.session import get_store


BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root, [data-tmk="light"] {
  --ink: #0b1f33;
  --ink-soft: #334155;
  --muted: #64748b;
  --line: #d5dde8;
  --surface: #ffffff;
  --canvas: #e9eef4;
  --panel: #f4f7fa;
  --accent: #0f766e;
  --accent-hover: #0d9488;
  --accent-deep: #115e59;
  --navy: #0b1f33;
  --navy-mid: #123048;
  --ok: #047857;
  --radius: 8px;
  --shadow: 0 1px 2px rgba(11,31,51,.05), 0 10px 28px rgba(11,31,51,.06);
  --side-text: #1e293b;
  --side-muted: #64748b;
  --side-active-bg: rgba(15,118,110,.12);
  --side-active: #0f766e;
  --btn-secondary-bg: #ffffff;
  --btn-secondary-border: #cbd5e1;
  --btn-secondary-text: #0b1f33;
  --uploader-bg: #f8fafc;
  --uploader-border: #94a3b8;
}

[data-tmk="dark"] {
  --ink: #e8eef5;
  --ink-soft: #cbd5e1;
  --muted: #94a3b8;
  --line: #2a3b4f;
  --surface: #132337;
  --canvas: #0a1520;
  --panel: #0f1c2a;
  --accent: #14b8a6;
  --accent-hover: #2dd4bf;
  --accent-deep: #0f766e;
  --navy: #0b1f33;
  --navy-mid: #123048;
  --ok: #34d399;
  --shadow: 0 1px 2px rgba(0,0,0,.35), 0 10px 28px rgba(0,0,0,.35);
  --side-text: #e2e8f0;
  --side-muted: #94a3b8;
  --side-active-bg: rgba(20,184,166,.18);
  --side-active: #5eead4;
  --btn-secondary-bg: #1a2d42;
  --btn-secondary-border: #3d5166;
  --btn-secondary-text: #e8eef5;
  --uploader-bg: #162536;
  --uploader-border: #3d5166;
}

html, body, .stApp {
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}

/* Kill broken Material ligature text inside EVERY file uploader button.
   App font overrides the icon font → icon word "upload" + label "Upload"
   becomes "uploadupload". Hiding the icon leaves a single clean label. */
div[data-testid="stFileUploader"] [data-testid="stIconMaterial"],
div[data-testid="stFileUploader"] span[data-testid="stIconMaterial"],
div[data-testid="stFileUploader"] button [data-testid="stIconMaterial"],
section[data-testid="stFileUploaderDropzone"] [data-testid="stIconMaterial"] {
  display: none !important;
}

/* Also restore Material font globally for other icons (sidebar, etc.) */
[data-testid="stIconMaterial"],
span[data-testid="stIconMaterial"] {
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
  font-weight: 400 !important;
  font-style: normal !important;
  letter-spacing: normal !important;
  text-transform: none !important;
}

.stApp {
  background:
    radial-gradient(1100px 480px at 8% -8%, rgba(15,118,110,.08), transparent 55%),
    radial-gradient(800px 360px at 100% 0%, rgba(11,31,51,.04), transparent 50%),
    var(--canvas) !important;
  color: var(--ink) !important;
}

#MainMenu { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
footer { visibility: hidden; }
/* Keep toolbar — holds sidebar expand when collapsed; only hide Deploy actions */
div[data-testid="stToolbar"] [data-testid="stToolbarActionButton"],
div[data-testid="stToolbar"] [data-testid="stAppDeployButton"] {
  display: none !important;
}
/* Do NOT hide header buttons — Streamlit puts the "expand sidebar" control there when collapsed */

/* Always keep contract/expand controls visible */
section[data-testid="stSidebar"] button[kind="header"],
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"],
section[data-testid="stSidebar"] [data-testid="baseButton-header"],
div[data-testid="collapsedControl"],
div[data-testid="collapsedControl"] button,
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] button {
  display: flex !important;
  visibility: visible !important;
  opacity: 1 !important;
  pointer-events: auto !important;
}

.block-container {
  padding-top: .85rem !important;
  padding-bottom: 2.75rem !important;
  max-width: min(1680px, 98vw) !important;
}

/* ---- Top bar (force white title — beats global h1 rules) ---- */
.tmk-topbar {
  display: flex;
  align-items: center;
  gap: 14px;
  background: linear-gradient(100deg, #0b1f33 0%, #123048 55%, #134e4a 100%);
  padding: 13px 18px;
  border-radius: var(--radius);
  margin-bottom: 18px;
  box-shadow: var(--shadow);
  border: 1px solid rgba(255,255,255,.06);
}
.tmk-topbar-brand { display: flex; align-items: center; gap: 12px; }
.tmk-mark {
  width: 34px; height: 34px; border-radius: 7px;
  background: linear-gradient(145deg, #1e40af, #0f766e);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 11px; letter-spacing: .05em;
  color: #fff !important; border: 1px solid rgba(255,255,255,.22);
}
.tmk-topbar h1,
.tmk-topbar h1 span,
div.tmk-topbar h1 {
  margin: 0 !important;
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
  font-size: 1.05rem !important;
  font-weight: 700 !important;
  letter-spacing: -.01em;
  color: #ffffff !important;
  line-height: 1.25 !important;
}
.tmk-topbar .sub {
  margin: 2px 0 0 !important;
  font-size: .7rem !important;
  color: rgba(255,255,255,.78) !important;
  font-weight: 500 !important;
}

/* ---- Landing ---- */
.tmk-landing {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 32px 24px 26px;
  box-shadow: var(--shadow);
  text-align: center;
  margin-bottom: 18px;
}
.tmk-landing .hero-mark {
  width: 48px; height: 48px; margin: 0 auto 12px; border-radius: 10px;
  background: linear-gradient(145deg, #1e40af, #0f766e);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 14px; color: #fff !important; letter-spacing: .05em;
}
.tmk-landing h2 {
  margin: 0 0 8px !important;
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
  font-size: 1.55rem !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
  letter-spacing: -.02em;
}
.tmk-landing .lead {
  margin: 0 auto !important;
  max-width: 440px;
  color: var(--muted) !important;
  font-size: .9rem !important;
  line-height: 1.5;
}

.tmk-card-label {
  display: flex; align-items: center; gap: 8px; margin-bottom: 8px;
  font-size: .7rem; font-weight: 700; letter-spacing: .07em;
  text-transform: uppercase; color: var(--muted) !important;
}
.tmk-badge {
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--navy); color: #fff !important;
  font-size: 10px; display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700;
}
[data-tmk="dark"] .tmk-badge { background: #1e40af; }
.tmk-card-hint {
  font-size: .76rem; color: var(--muted) !important; margin-top: 6px;
}

/* Uploaders — outer shell + browse button (always readable, no hover-only text) */
div[data-testid="stFileUploader"] {
  background: var(--uploader-bg) !important;
  border: 1.5px dashed var(--uploader-border) !important;
  border-radius: var(--radius);
  padding: 10px 12px;
}
div[data-testid="stFileUploader"]:hover {
  border-color: var(--accent) !important;
}
div[data-testid="stFileUploader"] section {
  padding: 4px 0 !important;
  background: transparent !important;
  border: none !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {
  background: transparent !important;
}
/* Browse/Upload button: Streamlit keeps a white surface; force dark label text */
div[data-testid="stFileUploader"] button,
div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"],
section[data-testid="stFileUploaderDropzone"] button {
  background: #ffffff !important;
  color: #0b1f33 !important;
  border: 1px solid #cbd5e1 !important;
  font-weight: 600 !important;
  opacity: 1 !important;
}
div[data-testid="stFileUploader"] button *,
div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] *,
section[data-testid="stFileUploaderDropzone"] button * {
  color: #0b1f33 !important;
  fill: #0b1f33 !important;
  opacity: 1 !important;
}
div[data-testid="stFileUploader"] button:hover,
div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]:hover,
section[data-testid="stFileUploaderDropzone"] button:hover {
  border-color: var(--accent) !important;
  color: #0f766e !important;
}
div[data-testid="stFileUploader"] button:hover *,
div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"]:hover *,
section[data-testid="stFileUploaderDropzone"] button:hover * {
  color: #0f766e !important;
  fill: #0f766e !important;
}
/* Dropzone helper (“200MB per file…”) */
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] span,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] small,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"],
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] span,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] small {
  color: var(--muted) !important;
  opacity: 1 !important;
}
/* Uploader / widget labels above controls (must stay readable in dark mode) */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
[data-testid="stWidgetLabel"] div,
label[data-testid="stWidgetLabel"],
div[data-testid="stFileUploader"] > label,
div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"],
div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"] *,
.stFileUploader label,
.stSelectbox label,
.stTextInput label,
.stMultiSelect label,
.stNumberInput label,
.stTextArea label,
.stDateInput label,
.stRadio > label,
.stCheckbox label {
  color: var(--ink) !important;
  opacity: 1 !important;
}

/* Buttons — secondary / download (default text visible, not hover-only) */
.stButton > button,
.stDownloadButton > button,
div[data-testid="stDownloadButton"] > button {
  border-radius: 6px !important;
  font-weight: 600 !important;
  letter-spacing: .01em;
  transition: background .15s ease, border-color .15s ease, color .15s ease !important;
  background: var(--btn-secondary-bg) !important;
  color: var(--btn-secondary-text) !important;
  border: 1px solid var(--btn-secondary-border) !important;
  box-shadow: none !important;
  opacity: 1 !important;
}
.stButton > button *,
.stDownloadButton > button *,
div[data-testid="stDownloadButton"] > button * {
  color: inherit !important;
}
.stButton > button:hover:not(:disabled),
.stDownloadButton > button:hover:not(:disabled),
div[data-testid="stDownloadButton"] > button:hover:not(:disabled) {
  border-color: var(--accent) !important;
  color: var(--accent-deep) !important;
}
[data-tmk="dark"] .stButton > button:hover:not(:disabled),
[data-tmk="dark"] .stDownloadButton > button:hover:not(:disabled),
[data-tmk="dark"] div[data-testid="stDownloadButton"] > button:hover:not(:disabled) {
  color: var(--side-active) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
  background: var(--accent-deep) !important;
  color: #fff !important;
  border-color: var(--accent-deep) !important;
}
[data-tmk="dark"] .stButton > button[kind="primary"],
[data-tmk="dark"] .stButton > button[data-testid="baseButton-primary"],
[data-tmk="dark"] .stButton > button[data-testid="stBaseButton-primary"] {
  background: #0f766e !important;
  border-color: #0d9488 !important;
  color: #fff !important;
}
.stButton > button[kind="primary"]:hover:not(:disabled),
.stButton > button[data-testid="baseButton-primary"]:hover:not(:disabled),
.stButton > button[data-testid="stBaseButton-primary"]:hover:not(:disabled) {
  background: var(--accent-hover) !important;
  color: #fff !important;
}
.stButton > button:disabled,
.stDownloadButton > button:disabled,
div[data-testid="stDownloadButton"] > button:disabled {
  opacity: .4 !important;
}

/* Metrics */
div[data-testid="stMetric"] {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 12px 14px;
}
div[data-testid="stMetricValue"] {
  font-size: 1.3rem !important; font-weight: 700 !important; color: var(--ink) !important;
}
div[data-testid="stMetricLabel"] {
  color: var(--muted) !important; font-size: .72rem !important;
  text-transform: uppercase; letter-spacing: .04em; font-weight: 600 !important;
}

button[data-baseweb="tab"] { font-weight: 600 !important; color: var(--muted) !important; }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--ink) !important; }
div[data-baseweb="tab-highlight"] { background-color: var(--accent) !important; }

/* ========== SIDEBAR ========== */
section[data-testid="stSidebar"] {
  background: var(--panel) !important;
  border-right: 1px solid var(--line) !important;
}
section[data-testid="stSidebar"] > div { background: transparent !important; }
section[data-testid="stSidebar"] .block-container { padding-top: 1rem !important; }

/* Module nav buttons — flat professional list (override global teal button styles) */
section[data-testid="stSidebar"] div[data-testid="stButton"] > button,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"],
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"],
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-secondary"],
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  border-left: 3px solid transparent !important;
  border-radius: 4px !important;
  box-shadow: none !important;
  color: var(--side-text) !important;
  justify-content: flex-start !important;
  text-align: left !important;
  font-weight: 500 !important;
  font-size: .86rem !important;
  padding: 0.55rem 0.75rem !important;
  min-height: 2.2rem !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button *,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button p,
section[data-testid="stSidebar"] div[data-testid="stButton"] > button span {
  color: inherit !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover:not(:disabled) {
  background: var(--side-active-bg) !important;
  color: var(--side-active) !important;
  border-left: 3px solid var(--accent) !important;
}
[data-tmk="dark"] section[data-testid="stSidebar"] div[data-testid="stButton"] > button,
[data-tmk="dark"] section[data-testid="stSidebar"] div[data-testid="stButton"] > button * {
  color: #e8eef5 !important;
  background: transparent !important;
  background-color: transparent !important;
  border-color: transparent !important;
}
[data-tmk="dark"] section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover:not(:disabled),
[data-tmk="dark"] section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover:not(:disabled) * {
  color: #5eead4 !important;
  background: rgba(20,184,166,.16) !important;
  border-left: 3px solid #14b8a6 !important;
}

.tmk-side-brand {
  padding: 4px 2px 14px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--line);
}
.tmk-side-brand .name {
  font-size: .82rem; font-weight: 700; color: var(--ink) !important; letter-spacing: -.01em;
}
.tmk-side-brand .meta {
  font-size: .68rem; color: var(--muted) !important; margin-top: 2px;
}
.tmk-side-title {
  font-size: .65rem; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: var(--side-muted) !important;
  margin: 10px 0 8px;
}
.tmk-side-note {
  font-size: .76rem; color: var(--side-muted) !important;
  line-height: 1.45; margin-bottom: 12px;
}

/* Captions / markdown in sidebar */
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--side-text) !important;
}
section[data-testid="stSidebar"] hr {
  border-color: var(--line) !important;
}

/* Page titles */
h1, h2, h3 {
  font-family: 'IBM Plex Sans', system-ui, sans-serif !important;
  color: var(--ink) !important;
  letter-spacing: -.015em;
}
.tmk-page-title {
  margin: 0 0 4px !important;
  font-size: 1.4rem !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
}
.tmk-page-sub {
  margin: 0 0 16px !important;
  color: var(--muted) !important;
  font-size: .86rem !important;
}

/* Billing Projects — toolbar + KPI cards */
.tmk-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 12px;
  padding: 12px 14px; margin: 0 0 14px;
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); box-shadow: var(--shadow);
}
.tmk-proj-count {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 8px 14px; border-radius: 6px;
  background: rgba(15,118,110,.1); border: 1px solid rgba(15,118,110,.25);
  color: var(--accent-deep); font-weight: 700; font-size: .82rem;
  white-space: nowrap;
}
.tmk-ms-count {
  margin-top: 1.75rem;
  background: var(--panel);
  color: var(--ink-soft);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 8px 12px;
  text-align: center;
  font-size: 12px;
  font-weight: 650;
}
/* Professional horizontal radio tabs — labels always readable */
div[role="radiogroup"] {
  gap: 0 !important;
  border: 1px solid var(--line) !important;
  border-radius: 6px !important;
  overflow: hidden !important;
  background: var(--panel) !important;
  display: inline-flex !important;
  flex-wrap: wrap !important;
}
div[role="radiogroup"] label {
  margin: 0 !important;
  padding: 8px 14px !important;
  border-right: 1px solid var(--line) !important;
  background: transparent !important;
  border-radius: 0 !important;
  color: var(--ink) !important;
  opacity: 1 !important;
}
div[role="radiogroup"] label p,
div[role="radiogroup"] label span,
div[role="radiogroup"] label div {
  color: var(--ink) !important;
  opacity: 1 !important;
}
div[role="radiogroup"] label:last-child { border-right: none !important; }
div[role="radiogroup"] label[data-checked="true"],
div[role="radiogroup"] label:has(input:checked) {
  background: rgba(15,118,110,.18) !important;
  color: var(--accent-deep) !important;
  font-weight: 650 !important;
}
div[role="radiogroup"] label[data-checked="true"] p,
div[role="radiogroup"] label[data-checked="true"] span,
div[role="radiogroup"] label:has(input:checked) p,
div[role="radiogroup"] label:has(input:checked) span {
  color: var(--accent-deep) !important;
}
[data-tmk="dark"] div[role="radiogroup"] {
  background: #132337 !important;
  border-color: #3d5166 !important;
}
[data-tmk="dark"] div[role="radiogroup"] label,
[data-tmk="dark"] div[role="radiogroup"] label p,
[data-tmk="dark"] div[role="radiogroup"] label span,
[data-tmk="dark"] div[role="radiogroup"] label div,
[data-tmk="dark"] .stRadio label,
[data-tmk="dark"] .stRadio label span,
[data-tmk="dark"] .stRadio label p {
  color: #e8eef5 !important;
  opacity: 1 !important;
}
[data-tmk="dark"] div[role="radiogroup"] label:has(input:checked),
[data-tmk="dark"] div[role="radiogroup"] label:has(input:checked) p,
[data-tmk="dark"] div[role="radiogroup"] label:has(input:checked) span {
  color: #5eead4 !important;
  background: rgba(20,184,166,.2) !important;
}
.tmk-proj-count b { font-size: 1.05rem; color: var(--ink); }
.tmk-proj-hero {
  display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between;
  gap: 10px; margin: 6px 0 14px; padding-bottom: 12px;
  border-bottom: 1px solid var(--line);
}
.tmk-proj-hero h2 {
  margin: 0 !important; font-size: 1.35rem !important; font-weight: 700 !important;
  color: var(--ink) !important; letter-spacing: -.02em;
}
.tmk-proj-hero .meta {
  margin: 4px 0 0; font-size: .78rem; color: var(--muted); font-weight: 500;
}
.tmk-team-pill {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 12px; border-radius: 6px;
  background: var(--panel); border: 1px solid var(--line);
  font-size: .78rem; font-weight: 600; color: var(--ink-soft);
}
.tmk-period-bar {
  padding: 10px 12px 4px; margin: 0 0 12px;
  background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius);
}
.tmk-period-bar .lbl {
  font-size: .65rem; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--muted); margin: 0 0 2px;
}
.tmk-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px; margin: 4px 0 8px;
}
@media (max-width: 900px) {
  .tmk-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.tmk-kpi {
  background: var(--surface); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 16px;
  box-shadow: var(--shadow); min-height: 78px;
}
.tmk-kpi .lbl {
  font-size: .68rem; font-weight: 700; letter-spacing: .06em;
  text-transform: uppercase; color: var(--muted); margin: 0 0 6px;
}
.tmk-kpi .val {
  font-size: 1.15rem; font-weight: 700; color: var(--ink);
  letter-spacing: -.02em; line-height: 1.25; word-break: break-word;
}
.tmk-kpi .val.accent { color: var(--accent-deep); }
.tmk-kpi .val.ok { color: var(--ok); }
.tmk-kpi .val.num { font-variant-numeric: tabular-nums; }
.tmk-src-note {
  font-size: .75rem; color: var(--muted); margin: 0 0 10px;
}

/* Module strip styles removed — navigation lives in the left sidebar only */
.tmk-nav-label { display: none !important; }

.tmk-status-ok {
  display: block; padding: 10px 14px; background: #ecfdf5; border: 1px solid #a7f3d0;
  border-radius: var(--radius); color: #047857; font-size: .86rem; font-weight: 600; margin: 10px 0;
}
.tmk-status-info {
  display: block; padding: 10px 14px; background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius); color: var(--ink-soft); font-size: .86rem; margin: 10px 0;
}
[data-tmk="dark"] .tmk-status-ok {
  background: rgba(4,120,87,.2); border-color: #047857; color: #6ee7b7;
}

div[data-testid="stDataFrame"],
div[data-testid="stDataEditor"] {
  border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden;
}
div[data-testid="stAlert"] { border-radius: var(--radius) !important; }

/* Dark: main text widgets */
[data-tmk="dark"] .stMarkdown, [data-tmk="dark"] p, [data-tmk="dark"] label,
[data-tmk="dark"] .stTextInput label, [data-tmk="dark"] .stSelectbox label,
[data-tmk="dark"] [data-testid="stWidgetLabel"],
[data-tmk="dark"] [data-testid="stWidgetLabel"] p,
[data-tmk="dark"] [data-testid="stWidgetLabel"] span,
[data-tmk="dark"] [data-testid="stWidgetLabel"] div,
[data-tmk="dark"] .stFileUploader label,
[data-tmk="dark"] div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"],
[data-tmk="dark"] div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"] * {
  color: var(--ink) !important;
  opacity: 1 !important;
}
[data-tmk="dark"] div[data-baseweb="select"] > div,
[data-tmk="dark"] input, [data-tmk="dark"] textarea {
  background-color: #162536 !important;
  color: #e8eef5 !important;
  border-color: #3d5166 !important;
}
</style>
"""


def _theme_boot_script(mode: str) -> str:
    """Set data-tmk on html/body so CSS variables apply (incl. sidebar)."""
    return f"""
<script>
(function() {{
  const mode = {mode!r};
  const root = window.parent.document.documentElement;
  const body = window.parent.document.body;
  root.setAttribute('data-tmk', mode);
  if (body) body.setAttribute('data-tmk', mode);
  // Also tag the sidebar iframe's parent app
  try {{
    const app = window.parent.document.querySelector('.stApp');
    if (app) app.setAttribute('data-tmk', mode);
  }} catch (e) {{}}
}})();
</script>
"""


def apply_theme() -> None:
    mode = st.session_state.get("theme", "light")
    if mode not in ("light", "dark"):
        mode = "light"
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    # Inline attribute on a wrapper Streamlit can keep in the main doc
    st.markdown(
        f'<div id="tmk-theme-anchor" data-tmk="{mode}" style="display:none"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(_theme_boot_script(mode), unsafe_allow_html=True)
    _style_native_sidebar_collapse()
    # Left sidebar with all module tabs on every page
    render_sidebar_chrome()
    # Fallback without JS: inject a style block scoped by repeating dark rules
    # when mode is dark (in case parent script is blocked)
    if mode == "dark":
        st.markdown(
            """
            <style>
            .stApp, section[data-testid="stSidebar"] {
              --ink: #e8eef5; --muted: #94a3b8; --line: #2a3b4f; --surface: #132337;
              --canvas: #0a1520; --panel: #0f1c2a; --side-text: #e2e8f0; --side-muted: #94a3b8;
              --side-active-bg: rgba(20,184,166,.18); --side-active: #5eead4;
              --btn-secondary-bg: #1a2d42; --btn-secondary-border: #3d5166;
              --btn-secondary-text: #e8eef5; --uploader-bg: #162536; --uploader-border: #3d5166;
            }
            section[data-testid="stSidebar"] {
              background: #0f1c2a !important;
              border-right-color: #2a3b4f !important;
            }
            section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
            section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"],
            section[data-testid="stSidebar"] [data-testid="stSidebarNav"] span,
            section[data-testid="stSidebar"] nav a,
            section[data-testid="stSidebar"] nav span {
              color: #e2e8f0 !important;
              opacity: 1 !important;
            }
            section[data-testid="stSidebar"] [data-testid="stSidebarNav"] a[aria-selected="true"],
            section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"][aria-current="page"] {
              background: rgba(20,184,166,.18) !important;
              color: #5eead4 !important;
            }
            .stApp { background: #0a1520 !important; }
            .tmk-landing { background: #132337 !important; border-color: #2a3b4f !important; }
            .tmk-landing h2 { color: #e8eef5 !important; }
            .tmk-landing .lead, .tmk-card-hint, .tmk-card-label { color: #94a3b8 !important; }
            .tmk-page-title, h1, h2, h3 { color: #e8eef5 !important; }
            .tmk-side-brand .name { color: #e8eef5 !important; }
            .tmk-side-brand .meta, .tmk-side-title, .tmk-side-note { color: #94a3b8 !important; }
            .stButton > button,
            .stDownloadButton > button,
            div[data-testid="stDownloadButton"] > button {
              background: #1a2d42 !important; color: #e8eef5 !important;
              border: 1px solid #3d5166 !important;
            }
            .stButton > button *,
            .stDownloadButton > button *,
            div[data-testid="stDownloadButton"] > button * {
              color: inherit !important;
            }
            .stButton > button[kind="primary"],
            .stButton > button[data-testid="baseButton-primary"],
            .stButton > button[data-testid="stBaseButton-primary"] {
              background: #0f766e !important; color: #fff !important; border-color: #0d9488 !important;
            }
            .stButton > button[kind="primary"] *,
            .stButton > button[data-testid="baseButton-primary"] *,
            .stButton > button[data-testid="stBaseButton-primary"] * {
              color: #fff !important;
            }
            /* Sidebar module list must stay flat (override rules above) */
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button,
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"],
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
              background: transparent !important;
              background-color: transparent !important;
              color: #e8eef5 !important;
              border: none !important;
              border-left: 3px solid transparent !important;
              box-shadow: none !important;
              justify-content: flex-start !important;
              text-align: left !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button *,
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] * {
              color: #e8eef5 !important;
              background: transparent !important;
            }
            section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover:not(:disabled) {
              background: rgba(20,184,166,.16) !important;
              color: #5eead4 !important;
              border-left: 3px solid #14b8a6 !important;
            }
            /* Radio / segment labels readable in dark mode */
            div[role="radiogroup"] label,
            div[role="radiogroup"] label p,
            div[role="radiogroup"] label span,
            .stRadio label,
            .stRadio label span,
            .stRadio label p {
              color: #e8eef5 !important;
              opacity: 1 !important;
            }
            div[data-testid="stFileUploader"] {
              background: #162536 !important; border-color: #3d5166 !important;
            }
            div[data-testid="stFileUploader"] button,
            div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"],
            section[data-testid="stFileUploaderDropzone"] button {
              background: #ffffff !important;
              color: #0b1f33 !important;
              border: 1px solid #cbd5e1 !important;
            }
            div[data-testid="stFileUploader"] button *,
            div[data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] *,
            section[data-testid="stFileUploaderDropzone"] button * {
              color: #0b1f33 !important;
            }
            div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] span,
            div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] span,
            div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] small {
              color: #94a3b8 !important;
            }
            /* Widget labels: Milestone.xlsx…, Highlights PDF, Project, etc. */
            .stApp [data-testid="stWidgetLabel"],
            .stApp [data-testid="stWidgetLabel"] p,
            .stApp [data-testid="stWidgetLabel"] span,
            .stApp [data-testid="stWidgetLabel"] div,
            .stApp label[data-testid="stWidgetLabel"],
            .stApp .stFileUploader label,
            .stApp .stSelectbox label,
            .stApp .stTextInput label,
            .stApp .stMultiSelect label,
            .stApp .stNumberInput label,
            .stApp .stTextArea label,
            .stApp div[data-testid="stFileUploader"] > label,
            .stApp div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"],
            .stApp div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"] * {
              color: #e8eef5 !important;
              opacity: 1 !important;
            }
            .stApp div[data-baseweb="select"] > div,
            .stApp input, .stApp textarea {
              background-color: #162536 !important;
              color: #e8eef5 !important;
              border-color: #3d5166 !important;
            }
            div[data-testid="stMetric"] {
              background: #132337 !important; border-color: #2a3b4f !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


def _style_native_sidebar_collapse() -> None:
    """High-contrast collapse/expand controls for light and dark mode."""
    if st.session_state.pop("sidebar_hidden", None) is not None:
        try:
            get_store().set_setting("sidebar_hidden", "0")
        except Exception:
            pass

    st.markdown(
        """
        <style>
        /* Collapse + expand: white face, dark icon — readable on any background */
        [data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarCollapseButton"] button,
        section[data-testid="stSidebar"] button[kind="header"],
        section[data-testid="stSidebar"] [data-testid="stBaseButton-header"],
        div[data-testid="collapsedControl"],
        div[data-testid="collapsedControl"] button,
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stSidebarCollapsedControl"] button,
        [data-testid="stExpandSidebarButton"],
        [data-testid="stExpandSidebarButton"] button,
        header[data-testid="stHeader"] button[kind="header"],
        header[data-testid="stHeader"] button[data-testid="baseButton-headerNoPadding"],
        header[data-testid="stHeader"] [data-testid="stBaseButton-headerNoPadding"] {
          display: flex !important;
          visibility: visible !important;
          opacity: 1 !important;
          pointer-events: auto !important;
          z-index: 2147483000 !important;
          background: #ffffff !important;
          color: #0b1f33 !important;
          border: 2px solid #14b8a6 !important;
          border-radius: 6px !important;
          box-shadow: 0 2px 14px rgba(0,0,0,.45) !important;
          width: 2.75rem !important;
          min-width: 2.75rem !important;
          height: 2.75rem !important;
        }
        [data-testid="stSidebarCollapseButton"] svg,
        section[data-testid="stSidebar"] button[kind="header"] svg,
        div[data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stExpandSidebarButton"] svg,
        header[data-testid="stHeader"] button svg {
          fill: #0b1f33 !important;
          color: #0b1f33 !important;
          stroke: #0b1f33 !important;
        }
        #tmk-expand-fab { display: none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_topbar(subtitle: str = "NTT DATA · Tokio Marine Kiln") -> None:
    st.markdown(
        f"""
        <div class="tmk-topbar">
          <div class="tmk-topbar-brand">
            <div class="tmk-mark">TMK</div>
            <div>
              <h1><span>TMK Dashboard</span></h1>
              <p class="sub">{subtitle}</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str = "") -> None:
    sub = f'<p class="tmk-page-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<p class="tmk-page-title">{title}</p>{sub}', unsafe_allow_html=True)


def render_sidebar_chrome() -> None:
    st.sidebar.markdown(
        """
        <div class="tmk-side-brand">
          <div class="name">TMK Workspace</div>
          <div class="meta">Tokio Marine Kiln · NTT DATA</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="tmk-side-title">Modules</div>', unsafe_allow_html=True)

    modules = (
        ("app.py", "Home"),
        ("pages/1_Billing_Projects.py", "Billing Projects"),
        ("pages/2_TMK_Overview.py", "TMK Overview"),
        ("pages/3_High_Level_Status.py", "High Level Status"),
        ("pages/4_Risks_Action_Items.py", "Risks / Action Items"),
        ("pages/5_Future_Resourcing.py", "Future Resourcing"),
        ("pages/6_Milestone.py", "Milestone"),
        ("pages/7_Account_Buffer.py", "Account Buffer"),
        ("pages/8_Commercials.py", "Commercials"),
    )
    for path, label in modules:
        if st.sidebar.button(label, key=f"tmk_nav_{label}", use_container_width=True):
            try:
                st.switch_page(path)
            except Exception as e:
                st.sidebar.error(str(e))

    st.sidebar.divider()
    st.sidebar.markdown('<div class="tmk-side-title">Controls</div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="tmk-side-note">Load workbooks on Home, then open a module below. '
        "Use the white chevron to collapse or expand this panel.</div>",
        unsafe_allow_html=True,
    )
    theme_toggle()
    st.sidebar.divider()


def theme_toggle() -> None:
    store = get_store()
    cur = st.session_state.get("theme", "light")
    label = "Switch to dark" if cur == "light" else "Switch to light"
    if st.sidebar.button(label, use_container_width=True, key="tmk_theme_btn"):
        st.session_state.theme = "dark" if cur == "light" else "light"
        store.set_setting("theme", st.session_state.theme)
        st.rerun()
