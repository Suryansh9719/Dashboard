"""Highlights PDF text extraction + section parsing (ported from DASHBOARD.html)."""
from __future__ import annotations

import io
import re

import pdfplumber

from config import MS_FIXED_PROJECTS
from domain.helpers import norm, norm_loose


def extract_pdf_text(file_bytes: bytes) -> str:
    lines: list[str] = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                line = line.strip()
                if line and "MathJax" not in line:
                    lines.append(line)
    return "\n".join(lines)


def parse_pdf_highlights(raw_text: str) -> tuple[dict, dict]:
    """Return (sections, project_updates) matching JS _msParsePdfHighlights."""
    lines = [l.strip() for l in (raw_text or "").split("\n") if l.strip() and "MathJax" not in l]
    section_names = ["Resourcing", "Knowledge Transition", "Updates", "Issues"]

    def match_heading(line: str) -> str | None:
        clean = re.sub(r"[:\-–]+$", "", line).strip()
        for name in section_names:
            if norm(clean) == norm(name):
                return name
            if norm(clean).startswith(norm(name)):
                rest = clean[len(name) :].strip()
                if len(rest) <= 2:
                    return name
        return None

    sections: dict[str, list[str]] = {}
    current = None
    for line in lines:
        heading = match_heading(line)
        if heading:
            current = heading.lower().replace(" ", "")
            sections.setdefault(current, [])
        elif current:
            sections[current].append(line)

    section_out = {
        "resourcing": "\n".join(sections.get("resourcing", [])),
        "knowledgeTransition": "\n".join(sections.get("knowledgetransition", [])),
        "issues": "\n".join(sections.get("issues", [])),
    }

    update_lines = sections.get("updates", [])
    buckets: dict[str, list[str]] = {}
    cur_proj = None
    for line in update_lines:
        cleaned = re.sub(r"[\s:\-–]+$", "", line).strip()
        matched = None
        for p in MS_FIXED_PROJECTS:
            a, b = norm_loose(cleaned), norm_loose(p)
            if a == b or (len(cleaned) < 30 and a.startswith(b) and len(a) - len(b) < 3):
                matched = p
                break
        if matched:
            cur_proj = matched
            buckets.setdefault(cur_proj, [])
        elif cur_proj:
            buckets[cur_proj].append(line)
    updates = {k: "\n".join(v) for k, v in buckets.items()}
    return section_out, updates
