"""OneNote → Highlights / Issues for High Level Status.

Supports Microsoft Graph against:
- A Team / M365 Group notebook (ONENOTE_GROUP_ID), or
- A personal OneDrive notebook (ONENOTE_USER_UPN) — e.g. links like
  https://nttdata-my.sharepoint.com/personal/.../Notebooks/Demo

Formatting is owned by OneNote — the dashboard only displays synced text.
"""
from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import requests

from config import (
    MS_GRAPH_CLIENT_ID,
    MS_GRAPH_CLIENT_SECRET,
    MS_GRAPH_TENANT_ID,
    ONENOTE_GROUP_ID,
    ONENOTE_LOCAL_HTML,
    ONENOTE_NOTEBOOK_NAME,
    ONENOTE_PAGE_TITLE,
    ONENOTE_SECTION_NAME,
    ONENOTE_USER_UPN,
)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style"):
            self._skip = True
        if t in ("br", "p", "div", "li", "h1", "h2", "h3", "h4", "tr"):
            self.parts.append("\n")
        if t == "li":
            self.parts.append("• ")

    def handle_endtag(self, tag):
        if tag.lower() in ("script", "style"):
            self._skip = False
        if tag.lower() in ("p", "div", "li", "h1", "h2", "h3", "h4"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        text = data.strip()
        if text:
            self.parts.append(text + " ")


def html_to_text(html: str) -> str:
    if not html:
        return ""
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        text = re.sub(r"(?is)<script.*?>.*?</script>", "", html)
        text = re.sub(r"(?is)<style.*?>.*?</style>", "", text)
        text = re.sub(r"(?i)<br\s*/?>", "\n", text)
        text = re.sub(r"(?i)</(p|div|li|h[1-6])>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return unescape(re.sub(r"\n{3,}", "\n\n", text)).strip()
    raw = unescape("".join(p.parts))
    raw = re.sub(r"[ \t]+\n", "\n", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw)
    raw = re.sub(r"[ \t]{2,}", " ", raw)
    return raw.strip()


def split_highlights_issues(text: str) -> dict[str, str]:
    """Split page text on Highlights / Issues headings (case-insensitive)."""
    if not text:
        return {"highlights": "", "issues": ""}

    lines = text.splitlines()
    hl_idx = iss_idx = None
    for i, ln in enumerate(lines):
        key = re.sub(r"\s+", " ", ln.strip()).lower()
        if key in ("highlights", "highlight") or key.startswith("highlights"):
            if hl_idx is None:
                hl_idx = i
        if key in ("issues", "issue", "issues / risks", "issues and risks", "risks"):
            if iss_idx is None:
                iss_idx = i

    if hl_idx is None and iss_idx is None:
        return {"highlights": text.strip(), "issues": ""}

    if hl_idx is not None and iss_idx is not None:
        if hl_idx < iss_idx:
            highlights = "\n".join(lines[hl_idx + 1 : iss_idx]).strip()
            issues = "\n".join(lines[iss_idx + 1 :]).strip()
        else:
            issues = "\n".join(lines[iss_idx + 1 : hl_idx]).strip()
            highlights = "\n".join(lines[hl_idx + 1 :]).strip()
    elif hl_idx is not None:
        highlights = "\n".join(lines[hl_idx + 1 :]).strip()
        issues = ""
    else:
        highlights = ""
        issues = "\n".join(lines[iss_idx + 1 :]).strip()

    return {"highlights": highlights, "issues": issues}


def parse_onenote_html(html: str) -> dict[str, str]:
    return split_highlights_issues(html_to_text(html))


def load_local_onenote(path: str | Path | None = None) -> dict[str, str]:
    p = Path(path or ONENOTE_LOCAL_HTML or "")
    if not p.is_file():
        raise FileNotFoundError(
            "OneNote HTML export not found. Set ONENOTE_LOCAL_HTML in config.py."
        )
    return parse_onenote_html(p.read_text(encoding="utf-8", errors="ignore"))


def graph_configured() -> bool:
    return bool(MS_GRAPH_TENANT_ID and MS_GRAPH_CLIENT_ID and MS_GRAPH_CLIENT_SECRET)


def onenote_target_configured() -> bool:
    """True when we know whose notebook to read (personal user or Team group)."""
    return bool((ONENOTE_USER_UPN or "").strip() or (ONENOTE_GROUP_ID or "").strip())


def upn_from_personal_sharepoint_url(url: str) -> str | None:
    """Extract UPN from personal OneDrive notebook links.

    Example:
      .../personal/10357769_nttdata_com/Documents/Notebooks/Demo
    → 10357769@nttdata.com
    """
    m = re.search(r"/personal/([^/]+)/", unquote(url or ""), re.I)
    if not m:
        return None
    part = m.group(1)
    # 10357769_nttdata_com → 10357769@nttdata.com
    if "_nttdata_com" in part.lower():
        user = part[: part.lower().index("_nttdata_com")]
        return f"{user}@nttdata.com"
    if "_" in part:
        # generic: first segment @ rest with last _ → .
        bits = part.split("_")
        if len(bits) >= 2:
            return f"{bits[0]}@{'.'.join(bits[1:])}"
    return None


def _graph_token() -> str:
    url = f"https://login.microsoftonline.com/{MS_GRAPH_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": MS_GRAPH_CLIENT_ID,
        "client_secret": MS_GRAPH_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }
    r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _graph_get(path: str, token: str, *, accept: str = "application/json") -> requests.Response:
    headers = {"Authorization": f"Bearer {token}", "Accept": accept}
    r = requests.get(f"https://graph.microsoft.com/v1.0{path}", headers=headers, timeout=60)
    if not r.ok:
        detail = r.text[:500]
        raise RuntimeError(f"Graph {r.status_code} on {path}: {detail}")
    return r


def _onenote_root(group_id: str = "", user_upn: str = "") -> str:
    """Graph path prefix for notebooks: /groups/{id} or /users/{upn}."""
    uid = (user_upn or ONENOTE_USER_UPN or "").strip()
    gid = (group_id or ONENOTE_GROUP_ID or "").strip()
    if uid:
        # UPN must be URL-encoded for Graph
        from urllib.parse import quote

        return f"/users/{quote(uid)}"
    if gid:
        return f"/groups/{gid}"
    raise RuntimeError(
        "This notebook is personal OneDrive (no Team Group ID). "
        "Set ONENOTE_USER_UPN in config.py (e.g. 10357769@nttdata.com from your SharePoint link)."
    )


def fetch_onenote_via_graph(
    *,
    group_id: str | None = None,
    user_upn: str | None = None,
    notebook_name: str | None = None,
    section_name: str | None = None,
    page_title: str | None = None,
) -> dict[str, str]:
    """Pull page HTML from Graph and split into highlights/issues.

    Needs Notes.Read.All (application) + admin consent.
    Use ONENOTE_USER_UPN for personal notebooks, or ONENOTE_GROUP_ID for Team notebooks.
    """
    if not graph_configured():
        raise RuntimeError(
            "Microsoft Graph is not configured. Set MS_GRAPH_TENANT_ID, "
            "MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET in config.py."
        )
    token = _graph_token()
    root = _onenote_root(group_id or "", user_upn or "")

    nb_name = (notebook_name or ONENOTE_NOTEBOOK_NAME or "").strip().lower()
    sec_name = (section_name or ONENOTE_SECTION_NAME or "").strip().lower()
    want_page = (page_title or ONENOTE_PAGE_TITLE or "").strip().lower()

    notebooks = _graph_get(f"{root}/onenote/notebooks", token).json().get("value") or []
    notebook = None
    for nb in notebooks:
        if not nb_name or (nb.get("displayName") or "").strip().lower() == nb_name:
            notebook = nb
            break
    if not notebook:
        names = ", ".join(nb.get("displayName") or "?" for nb in notebooks) or "(none)"
        raise RuntimeError(f"Notebook not found under {root}. Available: {names}")

    sections = (
        _graph_get(f"{root}/onenote/notebooks/{notebook['id']}/sections", token)
        .json()
        .get("value")
        or []
    )
    section = None
    for sec in sections:
        if not sec_name or (sec.get("displayName") or "").strip().lower() == sec_name:
            section = sec
            break
    if not section:
        names = ", ".join(s.get("displayName") or "?" for s in sections) or "(none)"
        raise RuntimeError(f"Section not found. Available: {names}")

    pages = (
        _graph_get(
            f"{root}/onenote/sections/{section['id']}/pages"
            f"?$orderby=lastModifiedDateTime desc&$top=25",
            token,
        )
        .json()
        .get("value")
        or []
    )
    page = None
    for pg in pages:
        title = (pg.get("title") or "").strip().lower()
        if want_page and title == want_page:
            page = pg
            break
        if not want_page:
            page = pg
            break
    if not page:
        raise RuntimeError("No matching OneNote page found in that section.")

    html = _graph_get(
        f"{root}/onenote/pages/{page['id']}/content",
        token,
        accept="text/html",
    ).text
    result = parse_onenote_html(html)
    result["_page_title"] = page.get("title") or ""
    result["_source"] = "graph-user" if "/users/" in root else "graph-group"
    return result


def sync_onenote(
    *,
    html_bytes: bytes | None = None,
    prefer_graph: bool = True,
) -> dict[str, str]:
    """Unified sync: optional HTML → Graph (user or group) → local path."""
    if html_bytes:
        text = html_bytes.decode("utf-8", errors="ignore")
        out = parse_onenote_html(text)
        out["_source"] = "upload"
        return out
    if prefer_graph and graph_configured() and onenote_target_configured():
        return fetch_onenote_via_graph()
    if ONENOTE_LOCAL_HTML:
        out = load_local_onenote()
        out["_source"] = "local"
        return out
    raise RuntimeError(
        "OneNote is not configured. Your notebook is personal OneDrive — set "
        "ONENOTE_USER_UPN (e.g. 10357769@nttdata.com) plus MS_GRAPH_TENANT_ID / "
        "CLIENT_ID / CLIENT_SECRET (Notes.Read.All + admin consent). "
        "ONENOTE_GROUP_ID is only for Team notebooks."
    )
