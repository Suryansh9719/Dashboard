"""PDF export via ReportLab."""
from __future__ import annotations

import io
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleTMK", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#3730a3")))
    styles.add(ParagraphStyle(name="SubTMK", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#64748b")))
    styles.add(ParagraphStyle(name="BodyTMK", parent=styles["Normal"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="H2TMK", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#4f46e5")))
    return styles


def build_simple_pdf(
    title: str,
    sections: list[tuple[str, str | list[list]]],
    landscape_a3: bool = False,
) -> bytes:
    bio = io.BytesIO()
    pagesize = landscape(A3) if landscape_a3 else A4
    doc = SimpleDocTemplate(bio, pagesize=pagesize, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    styles = _styles()
    story = [Paragraph(title, styles["TitleTMK"]), Spacer(1, 6)]
    for heading, body in sections:
        story.append(Paragraph(heading, styles["H2TMK"]))
        story.append(Spacer(1, 4))
        if isinstance(body, list):
            if not body:
                story.append(Paragraph("(empty)", styles["BodyTMK"]))
            else:
                t = Table(body, repeatRows=1)
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4f46e5")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("FONTSIZE", (0, 0), (-1, -1), 7),
                            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                        ]
                    )
                )
                story.append(t)
        else:
            for line in str(body).split("\n"):
                story.append(Paragraph(line.replace("&", "&amp;").replace("<", "&lt;") or "&nbsp;", styles["BodyTMK"]))
        story.append(Spacer(1, 8))
    doc.build(story)
    return bio.getvalue()


def project_pdf(
    project: str,
    pd_cards: dict,
    resource_table: list[list],
    finance_table: list[list],
) -> bytes:
    sections = [
        (
            "Project Details",
            "\n".join(f"{k}: {v}" for k, v in pd_cards.items()),
        ),
        ("Resource Details", resource_table),
        ("Finance Report", finance_table),
    ]
    return build_simple_pdf(f"TMK Project Report — {project}", sections, landscape_a3=True)


def hls_pdf(title: str, rag: str, highlights: str, issues: str, projects: Iterable[dict]) -> bytes:
    proj_txt = "\n".join(
        f"{p.get('name','')}: DEL={p.get('del','')}, RES={p.get('res','')}, GM={p.get('gm','')}"
        for p in projects
    )
    return build_simple_pdf(
        title or "High Level Status",
        [
            ("Overall RAG", rag),
            ("Projects", proj_txt),
            ("Highlights", highlights or ""),
            ("Issues", issues or ""),
        ],
    )


def full_dashboard_pdf(summary_lines: list[str], tables: list[tuple[str, list[list]]]) -> bytes:
    sections: list[tuple[str, str | list[list]]] = [("Summary", "\n".join(summary_lines))]
    sections.extend(tables)
    return build_simple_pdf("TMK Full Dashboard Export", sections, landscape_a3=True)
