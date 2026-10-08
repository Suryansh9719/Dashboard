"""Excel export helpers."""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from openpyxl import Workbook


def date_suffix() -> str:
    now = datetime.now()
    d = now.day
    months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]
    m = months[now.month - 1]
    y = str(now.year)[-2:]
    ord_ = "th"
    if d in (1, 21, 31):
        ord_ = "st"
    elif d in (2, 22):
        ord_ = "nd"
    elif d in (3, 23):
        ord_ = "rd"
    return f"{d}{ord_}{m}{y}"


def df_to_excel_bytes(sheets: dict[str, pd.DataFrame]) -> bytes:
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        for name, df in sheets.items():
            safe = name[:31]
            df.to_excel(writer, sheet_name=safe, index=False)
    return bio.getvalue()


def rows_to_excel_bytes(sheet_name: str, headers: list[str], rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    ws.append(headers)
    for r in rows:
        ws.append(r)
    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()
