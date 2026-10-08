"""Milestone full-report PDF — 2 sheets matching DASHBOARD.html downloadMsFullReport / DEMOO.pdf."""
from __future__ import annotations

import re
from datetime import date, timedelta
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from config import ACCOUNT_NAME, MS_FIXED_PROJECTS
from domain.milestone import (
    STATUS_COLORS,
    compute_display,
    fmt_date,
    friday_of_week_containing,
    parse_rich_text_items,
    pdf_gantt_window,
)


COLORS = {
    "purple": "#3730a3",
    "teal": "#0d9488",
    "blue": "#1e40af",
    "red": "#dc2626",
    "border": "#d1d5db",
    "text": "#1e293b",
    "muted": "#64748b",
    "lightBlue": "#eef2ff",
}


def _clip(s: str, n: int = 42) -> str:
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _rl_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_rich_rl(text: str) -> str:
    """Bold short Label: prefixes for ReportLab Paragraph XML."""
    s = (text or "").strip()
    if not s:
        return ""
    m = re.match(r"^([^:]{2,55}):\s*(.*)$", s)
    if m:
        label, rest = m.group(1), (m.group(2) or "").strip()
        if len(label.split()) <= 6 and not re.search(r"[.!?]$", label):
            return f"<b>{_rl_escape(label)}:</b>" + (f" {_rl_escape(rest)}" if rest else "")
    bare = re.sub(r"\s[-–—]\s*$", "", s).strip()
    if (
        len(bare) <= 40
        and len(bare.split()) <= 4
        and not re.search(r"[.!?…]", bare)
        and re.match(r"^[A-Z0-9]", bare)
        and not re.match(r"^(The|A|An|In|On|For|With|And|Or|To|As|At)\b", bare, re.I)
    ):
        return f"<b>{_rl_escape(s)}</b>"
    return _rl_escape(s)


def _styles(body_pt: float = 9.0):
    """Typography scaled by body_pt so sheet-1 can stay full-width without KeepInFrame shrink."""
    base = getSampleStyleSheet()
    b = body_pt
    styles = {
        "acct": ParagraphStyle(
            name=f"MsAcct_{b}",
            parent=base["Normal"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor(COLORS["text"]),
            fontName="Helvetica-Bold",
        ),
        "gen": ParagraphStyle(
            name=f"MsGen_{b}",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor(COLORS["muted"]),
            alignment=TA_RIGHT,
        ),
        "sheet_title": ParagraphStyle(
            name=f"MsSheetTitle_{b}",
            parent=base["Normal"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor(COLORS["purple"]),
            fontName="Helvetica-Bold",
            spaceAfter=4,
        ),
        "col_hdr": ParagraphStyle(
            name=f"MsColHdr_{b}",
            parent=base["Normal"],
            fontSize=max(9, b + 0.5),
            leading=max(11, b + 2.5),
            textColor=colors.white,
            fontName="Helvetica-Bold",
        ),
        "badge": ParagraphStyle(
            name=f"MsBadge_{b}",
            parent=base["Normal"],
            fontSize=max(8, b),
            leading=max(10, b + 2),
            textColor=colors.white,
            fontName="Helvetica-Bold",
        ),
        "proj_badge": ParagraphStyle(
            name=f"MsProjBadge_{b}",
            parent=base["Normal"],
            fontSize=max(9, b + 0.5),
            leading=max(11, b + 2.5),
            textColor=colors.HexColor(COLORS["purple"]),
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            name=f"MsBody_{b}",
            parent=base["Normal"],
            fontSize=b,
            leading=b + 2.0,
            textColor=colors.HexColor(COLORS["text"]),
        ),
        "body_l1": ParagraphStyle(
            name=f"MsBodyL1_{b}",
            parent=base["Normal"],
            fontSize=b,
            leading=b + 2.0,
            textColor=colors.HexColor(COLORS["text"]),
            leftIndent=6,
            bulletIndent=0,
        ),
        "body_l2": ParagraphStyle(
            name=f"MsBodyL2_{b}",
            parent=base["Normal"],
            fontSize=max(7.5, b - 0.5),
            leading=max(9.5, b + 1.2),
            textColor=colors.HexColor(COLORS["text"]),
            leftIndent=14,
            bulletIndent=6,
        ),
        "heading": ParagraphStyle(
            name=f"MsHdg_{b}",
            parent=base["Normal"],
            fontSize=max(8.5, b + 0.5),
            leading=max(10, b + 2.0),
            textColor=colors.HexColor(COLORS["purple"]),
            fontName="Helvetica-Bold",
            spaceBefore=2,
            spaceAfter=1,
        ),
        "muted": ParagraphStyle(
            name=f"MsMuted_{b}",
            parent=base["Normal"],
            fontSize=max(7.5, b - 0.5),
            textColor=colors.HexColor("#94a3b8"),
            fontName="Helvetica-Oblique",
        ),
        "gantt_title": ParagraphStyle(
            name=f"MsGanttTitle_{b}",
            parent=base["Normal"],
            fontSize=11,
            leading=13,
            textColor=colors.white,
            fontName="Helvetica-Bold",
        ),
        "cell": ParagraphStyle(
            name=f"MsCell_{b}",
            parent=base["Normal"],
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#0f172a"),
        ),
        "head": ParagraphStyle(
            name=f"MsHead_{b}",
            parent=base["Normal"],
            fontSize=7.5,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "mark": ParagraphStyle(
            name=f"MsMark_{b}",
            parent=base["Normal"],
            fontSize=6.5,
            leading=8.5,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#047857"),
        ),
        "legend": ParagraphStyle(
            name=f"MsLegend_{b}",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor(COLORS["muted"]),
        ),
    }
    return styles



def _rich_flowables(text: str, styles: dict) -> list:
    """Convert highlight/update text into indented ReportLab paragraphs."""
    items = parse_rich_text_items(text)
    if not items:
        return [Paragraph("No content available.", styles["muted"])]

    out: list = []
    for it in items:
        if it["type"] == "blank":
            continue
        if it["type"] == "heading":
            out.append(Paragraph(_rl_escape(it["text"]), styles["heading"]))
            continue
        if it["type"] == "li" and it["level"] == 1:
            out.append(Paragraph(f"• {_format_rich_rl(it['text'])}", styles["body_l1"]))
            continue
        if it["type"] == "li" and it["level"] == 2:
            out.append(Paragraph(f"◦ {_format_rich_rl(it['text'])}", styles["body_l2"]))
            continue
        out.append(Paragraph(_format_rich_rl(it["text"]), styles["body"]))
    return out or [Paragraph("No content available.", styles["muted"])]


def _content_block(
    label: str,
    color: str,
    text: str,
    styles: dict,
    col_w: float,
    *,
    project: bool = False,
) -> Table:
    """Full-column-width section: coloured label + body wrapping to the full width."""
    pad = 3
    # Paragraphs wrap across nearly the entire column (pad is inside col_w)
    rows: list = [[Paragraph(
        _rl_escape(label) if project else label.upper(),
        styles["proj_badge"] if project else styles["badge"],
    )]]
    for p in _rich_flowables(text, styles):
        rows.append([p])

    t = Table(rows, colWidths=[col_w])
    bg = COLORS["lightBlue"] if project else color
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(bg)),
        ("LEFTPADDING", (0, 0), (-1, -1), pad),
        ("RIGHTPADDING", (0, 0), (-1, -1), pad),
        ("TOPPADDING", (0, 0), (0, 0), 3),
        ("BOTTOMPADDING", (0, 0), (0, 0), 3),
        ("TOPPADDING", (0, 1), (0, -1), 1),
        ("BOTTOMPADDING", (0, 1), (0, -1), 1),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(COLORS["border"])),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ]))
    return t


def _header_banner(acct_name: str, styles: dict, page_w: float) -> Table:
    today_lbl = date.today().strftime("%d %B %Y")
    hdr = Table(
        [[
            Paragraph(_rl_escape(acct_name), styles["acct"]),
            Paragraph(f"Generated {today_lbl}", styles["gen"]),
        ]],
        colWidths=[page_w * 0.62, page_w * 0.38],
    )
    hdr.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 2.5, colors.HexColor(COLORS["teal"])),
    ]))
    return hdr


def _build_highlights_column(highlights: dict, styles: dict, col_w: float) -> Table:
    rows = [[Paragraph("ACCOUNT HIGHLIGHTS", styles["col_hdr"])]]
    for label, key, color in (
        ("Resourcing", "resourcing", COLORS["teal"]),
        ("Knowledge Transition", "knowledgeTransition", COLORS["blue"]),
        ("Issues", "issues", COLORS["red"]),
    ):
        rows.append([
            _content_block(label, color, (highlights or {}).get(key) or "", styles, col_w)
        ])
    t = Table(rows, colWidths=[col_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(COLORS["purple"])),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("TOPPADDING", (0, 0), (0, 0), 5),
        ("BOTTOMPADDING", (0, 0), (0, 0), 5),
        ("LEFTPADDING", (0, 1), (0, -1), 0),
        ("RIGHTPADDING", (0, 1), (0, -1), 0),
        ("TOPPADDING", (0, 1), (0, -1), 2),
        ("BOTTOMPADDING", (0, 1), (0, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(COLORS["border"])),
    ]))
    return t


def _build_updates_column(updates: dict, styles: dict, col_w: float) -> Table:
    rows = [[Paragraph("PROJECT-WISE UPDATES", styles["col_hdr"])]]
    any_row = False
    for p in MS_FIXED_PROJECTS:
        txt = (updates or {}).get(p) or ""
        if not txt.strip():
            continue
        any_row = True
        rows.append([
            _content_block(p, COLORS["lightBlue"], txt, styles, col_w, project=True)
        ])
    if not any_row:
        rows.append([Paragraph("No project updates available.", styles["muted"])])
    t = Table(rows, colWidths=[col_w])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(COLORS["purple"])),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("RIGHTPADDING", (0, 0), (0, 0), 6),
        ("TOPPADDING", (0, 0), (0, 0), 5),
        ("BOTTOMPADDING", (0, 0), (0, 0), 5),
        ("LEFTPADDING", (0, 1), (0, -1), 0),
        ("RIGHTPADDING", (0, 1), (0, -1), 0),
        ("TOPPADDING", (0, 1), (0, -1), 2),
        ("BOTTOMPADDING", (0, 1), (0, -1), 2),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor(COLORS["border"])),
    ]))
    return t


def _sheet1_two_col(highlights: dict, updates: dict, styles: dict, page_w: float) -> Table:
    """Two columns spanning the entire frame width (32% highlights | 68% updates)."""
    left_w = page_w * 0.32
    right_w = page_w - left_w
    two_col = Table(
        [[
            _build_highlights_column(highlights or {}, styles, left_w),
            _build_updates_column(updates or {}, styles, right_w),
        ]],
        colWidths=[left_w, right_w],
    )
    two_col.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return two_col


class _Sheet1Fit(Flowable):
    """Full-width sheet 1: largest readable font that fits on one page. No canvas squeeze."""

    def __init__(self, highlights: dict, updates: dict):
        super().__init__()
        self.highlights = highlights or {}
        self.updates = updates or {}
        self._table = None
        self._pt = 9.0
        self._w = 0.0
        self._h = 0.0
        self._sy = 1.0

    def wrap(self, availWidth, availHeight):
        w = float(availWidth)
        h_max = float(availHeight) if availHeight else 800.0
        chosen = None
        chosen_h = 0.0
        for pt in (9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0):
            styles = _styles(pt)
            tbl = _sheet1_two_col(self.highlights, self.updates, styles, w)
            _tw, th = tbl.wrap(w, h_max + 4000)
            chosen, chosen_h, self._pt = tbl, th, pt
            if th <= h_max:
                break
        self._table = chosen
        self._w = w
        # Only if even 6pt overflows: tiny height-only scale (last resort)
        if chosen_h > h_max and chosen_h > 0:
            self._sy = h_max / chosen_h
            self._h = h_max
        else:
            self._sy = 1.0
            self._h = chosen_h
        return w, self._h

    def draw(self):
        if not self._table:
            return
        self.canv.saveState()
        if self._sy != 1.0:
            self.canv.scale(1.0, self._sy)
        self._table.wrapOn(self.canv, self._w, self._h / self._sy if self._sy else self._h)
        self._table.drawOn(self.canv, 0, 0)
        self.canv.restoreState()


def _build_gantt_table(
    title: str,
    milestones: list[dict],
    phases: list[dict],
    show_project: bool,
    styles: dict,
    page_w: float,
) -> list:
    """Sheet-2 Gantt using PDF date window (current month → 2 weeks next month)."""
    items = list(milestones) + list(phases)
    rows = [{"item": it, "disp": compute_display(it)} for it in items]
    today = date.today()
    pdf_start, pdf_end, weeks = pdf_gantt_window(today)
    total_w = len(weeks) or 1

    def week_index(d: date | None) -> int | None:
        if not d:
            return None
        for i, w in enumerate(weeks):
            w_end = weeks[i + 1] if i + 1 < len(weeks) else pdf_end + timedelta(days=1)
            if w <= d < w_end:
                return i
        return None

    today_wi = week_index(today)
    if today_wi is None and weeks:
        today_wi = 0

    story: list = []
    story.append(
        Paragraph(f"Milestone Gantt Chart — {_rl_escape(_clip(title, 60))}", styles["sheet_title"])
    )

    # Banner strip
    banner = Table(
        [[Paragraph("Milestone Gantt Chart", styles["gantt_title"])]],
        colWidths=[page_w],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#4f46e5")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(banner)
    story.append(Spacer(1, 2))

    label_w = 48 * mm
    status_w = 20 * mm
    week_w = max(14 * mm, (page_w - label_w - status_w) / max(total_w, 1))

    hdr1 = [
        Paragraph("<b>ITEM</b>", styles["head"]),
        Paragraph("<b>STATUS</b>", styles["head"]),
    ] + [
        Paragraph(
            f"<b>{w.strftime('%b %y') if i == 0 or weeks[i].month != weeks[i - 1].month else ''}</b>",
            styles["head"],
        )
        for i, w in enumerate(weeks)
    ]

    hdr2 = [Paragraph("", styles["head"]), Paragraph("", styles["head"])]
    for i, w in enumerate(weeks):
        fri = friday_of_week_containing(w)
        limit_end = (
            weeks[i + 1] - timedelta(days=1) if i + 1 < len(weeks) else pdf_end
        )
        if fri > limit_end:
            fri = limit_end
        lab = f"{w.day} {w.strftime('%b')}<br/>to {fri.day} {fri.strftime('%b')}"
        hdr2.append(Paragraph(lab, styles["head"]))

    gantt_data = [hdr1, hdr2]
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 1), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#c7d2fe")),
        ("FONTSIZE", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 0), (1, -1), colors.HexColor("#1e3a5f")),
    ]
    if today_wi is not None:
        style_cmds.append(
            ("BACKGROUND", (2 + today_wi, 1), (2 + today_wi, 1), colors.HexColor("#f87171"))
        )

    for ri, r in enumerate(rows):
        item, disp = r["item"], r["disp"]
        st = disp["status"]
        sc = STATUS_COLORS.get(st, "#64748b")
        name = item.get("desc") or ""
        if show_project and item.get("project"):
            name = f"{item.get('project')} — {name}"
        cells = [
            Paragraph(_clip(name, 48), styles["cell"]),
            Paragraph(f'<font color="{sc}"><b>{st}</b></font>', styles["cell"]),
        ]
        marks = [""] * total_w
        if item.get("type") == "milestone":
            for dp in disp.get("dates") or []:
                d = dp.get("date")
                if not d or d < pdf_start or d > pdf_end:
                    continue
                wi = week_index(d)
                if wi is None:
                    continue
                phase = _clip(item.get("phase") or item.get("desc") or "MS", 10)
                dlab = fmt_date(d)
                marks[wi] = (
                    f'<font color="{sc}" size="8"><b>◆</b></font><br/>'
                    f'<font color="{sc}" size="5">{_rl_escape(phase)}<br/>{_rl_escape(dlab)}</font>'
                )
        else:
            for b in disp.get("bars") or []:
                if not b.get("start") or not b.get("end"):
                    continue
                a, b_end = b["start"], b["end"]
                if b_end < pdf_start or a > pdf_end:
                    continue
                a = max(a, pdf_start)
                b_end = min(b_end, pdf_end)
                for wi, w in enumerate(weeks):
                    w_end = weeks[wi + 1] if wi + 1 < len(weeks) else pdf_end + timedelta(days=1)
                    if b_end >= w and a < w_end:
                        marks[wi] = f'<font color="{sc}" size="7">▬</font>'
        for m in marks:
            cells.append(Paragraph(m or " ", styles["mark"]))
        gantt_data.append(cells)
        bg = colors.HexColor("#f8fafc") if ri % 2 else colors.white
        style_cmds.append(("BACKGROUND", (0, ri + 2), (-1, ri + 2), bg))
        style_cmds.append(("BACKGROUND", (0, ri + 2), (1, ri + 2), colors.HexColor("#eef2ff")))
        if today_wi is not None:
            style_cmds.append(
                ("BACKGROUND", (2 + today_wi, ri + 2), (2 + today_wi, ri + 2), colors.HexColor("#fef2f2"))
            )
            style_cmds.append(
                ("BOX", (2 + today_wi, ri + 2), (2 + today_wi, ri + 2), 1.0, colors.HexColor("#ef4444"))
            )

    if not rows:
        gantt_data.append(
            [
                Paragraph("No dated items for this selection.", styles["muted"]),
                Paragraph("", styles["cell"]),
            ]
            + [Paragraph("", styles["cell"])] * total_w
        )

    col_widths = [label_w, status_w] + [week_w] * total_w
    gt = Table(gantt_data, colWidths=col_widths, repeatRows=2)
    gt.setStyle(TableStyle(style_cmds))
    story.append(gt)
    story.append(Spacer(1, 6))
    story.append(
        Paragraph(
            "● On Track &nbsp;&nbsp; ● Delayed &nbsp;&nbsp; ● Completed &nbsp;&nbsp; "
            "● Planned (faded, when Impact = Yes) &nbsp;&nbsp; "
            "Red column = current week &nbsp;&nbsp; "
            f"Window: {pdf_start.strftime('%d %b %Y')} → {pdf_end.strftime('%d %b %Y')}",
            styles["legend"],
        )
    )
    return story


def build_milestone_full_report_pdf(
    title: str,
    milestones: list[dict],
    phases: list[dict],
    updates: dict | None = None,
    highlights: dict | None = None,
    show_project: bool = True,
    account_name: str | None = None,
) -> bytes:
    """2-sheet landscape A3 PDF matching DEMOO / downloadMsFullReport.

    Sheet 1 — Account Highlights (Resourcing / Knowledge Transition / Issues)
               + Project-wise Updates
    Sheet 2 — Milestone Gantt (1st of month / next working day → 14th next month)
    """
    bio = BytesIO()
    pagesize = landscape(A3)
    # Minimal margins so columns use almost the full landscape sheet
    margin = 4 * mm
    doc = SimpleDocTemplate(
        bio,
        pagesize=pagesize,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    page_w = pagesize[0] - 2 * margin
    page_h = pagesize[1] - 2 * margin
    acct = (account_name or ACCOUNT_NAME or "Account").strip()
    hdr_styles = _styles(9.0)

    story: list = []

    # ── Sheet 1 — columns span the full usable width ───────────────────────
    hdr = _header_banner(acct, hdr_styles, page_w)
    _hw, hdr_h = hdr.wrap(page_w, 80)
    story.append(hdr)
    story.append(Spacer(1, 3))
    story.append(
        _Sheet1Fit(highlights or {}, updates or {})
    )

    # ── Sheet 2 ────────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(_header_banner(acct, hdr_styles, page_w))
    story.append(Spacer(1, 4))
    gantt_parts = _build_gantt_table(
        title, milestones, phases, show_project, hdr_styles, page_w
    )
    story.extend(gantt_parts)

    doc.build(story)
    return bio.getvalue()


def build_milestone_gantt_pdf(
    title: str,
    milestones: list[dict],
    phases: list[dict],
    show_project: bool = True,
    updates_text: str = "",
    highlights: dict | None = None,
) -> bytes:
    """Backward-compatible alias: full 2-sheet report (updates_text ignored — use updates dict)."""
    # If callers only pass flattened updates_text, fold into a single bucket
    updates: dict = {}
    if updates_text and updates_text.strip():
        updates = {"Updates": updates_text}
    return build_milestone_full_report_pdf(
        title=title,
        milestones=milestones,
        phases=phases,
        updates=updates,
        highlights=highlights,
        show_project=show_project,
    )
