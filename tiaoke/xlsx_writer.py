"""把通知單清單寫成 openpyxl 工作表，套用範例檔的版型與樣式。"""

from __future__ import annotations

import datetime

from openpyxl.worksheet.page import PageMargins
from openpyxl.worksheet.worksheet import Worksheet

from . import roc, styles
from .builder import ClassSlip, TeacherSlip, build
from .models import Event
from .styles import (
    BOTTOM_ONLY, CENTER, CENTER_WRAP, CLASS_ROW_H, DATE_FMT, LEFT, LEFT_WRAP,
    NOTE_ALIGN, NOTE_ROW_H, RIGHT, TEACHER_ROW_H, TITLE_ROW_H, body_font, put,
    title_font,
)

_SPACER = 2  # 每張通知單後空兩列（比照範例1）


def banner_text(event: Event) -> str:
    return (
        "教  師  調  代  課  通  知  單 "
        f"假單編號：{event.form_no}  {event.originator} {event.leave_type}"
    )


def write_sheet(ws: Worksheet, event: Event, timetable=None) -> int:
    """在 ws 上輸出整個事件。回傳最後一列的列號。

    timetable 有給的話，代課列若對應原老師課表標了 (兼)/(輔)，J 欄會加註記
    （見 builder.build 的 mark 計算）；J 欄不納入列印範圍，純 Excel 內部註記。
    """
    slips = build(event, timetable)
    styles.set_col_widths(ws)

    r = 1
    for slip in slips:
        if isinstance(slip, TeacherSlip):
            r = _teacher_slip(ws, r, slip, event)
        else:
            r = _class_slip(ws, r, slip, event)

    last = r - 1 - _SPACER
    _page_setup(ws, last)
    return last


# --------------------------------------------------------------------------
# 教師調代課通知單
# --------------------------------------------------------------------------

def _teacher_slip(ws: Worksheet, r: int, slip: TeacherSlip, event: Event) -> int:
    top = r

    # 橫幅
    ws.row_dimensions[r].height = TITLE_ROW_H
    put(ws, f"A{r}", slip.teacher, font=title_font(), align=CENTER)
    for col in "BCDEFGHI":
        put(ws, f"{col}{r}", None, border=BOTTOM_ONLY)
    put(ws, f"B{r}", banner_text(event), align=CENTER, border=BOTTOM_ONLY)
    r += 1

    hdr1, hdr2 = r, r + 1
    put(ws, f"A{hdr1}", "班級", align=CENTER)
    put(ws, f"C{hdr1}", "調課後授課時間", font=body_font(bold=True), align=CENTER)
    put(ws, f"E{hdr1}", "授課科目", align=CENTER)
    put(ws, f"G{hdr1}", "原授課時間", align=CENTER)
    put(ws, f"I{hdr1}", "備註", align=CENTER)
    for col, label in zip("BCD", ("日期", "星期", "節次")):
        put(ws, f"{col}{hdr2}", label, align=CENTER)
    for col, label in zip("FGH", ("日期", "星期", "節次")):
        put(ws, f"{col}{hdr2}", label, align=CENTER)
    r += 2

    first_data = r
    for row in slip.rows:
        ws.row_dimensions[r].height = TEACHER_ROW_H
        fill = styles.HIGHLIGHT_FILL if row.highlight else None
        put(ws, f"A{r}", row.klass, align=CENTER_WRAP, fill=fill)
        if row.new is not None:
            put(ws, f"B{r}", row.new.date, align=CENTER, fmt=DATE_FMT, fill=fill)
            put(ws, f"C{r}", row.new.weekday_cn, align=CENTER, fill=fill)
            put(ws, f"D{r}", str(row.new.period), align=CENTER, fill=fill)
        else:
            for col in "BCD":
                put(ws, f"{col}{r}", None, fill=fill)
        if row.orig is not None:
            put(ws, f"F{r}", row.orig.date, align=CENTER, fmt=DATE_FMT, fill=fill)
            put(ws, f"G{r}", row.orig.weekday_cn, align=CENTER, fill=fill)
            put(ws, f"H{r}", str(row.orig.period), align=CENTER, fill=fill)
        else:
            for col in "FGH":
                put(ws, f"{col}{r}", None, fill=fill)
        put(ws, f"E{r}", row.subject, align=CENTER, fill=fill)
        put(ws, f"I{r}", row.note, align=LEFT_WRAP, fill=fill)
        if row.mark:
            put(ws, f"J{r}", row.mark, font=styles.mark_font(), align=CENTER, fill=fill)
        r += 1
    last_data = r - 1

    styles.outline_grid(ws, f"A{hdr1}:I{last_data}")
    _merge(ws, f"B{top}:I{top}")
    _merge(ws, f"E{hdr1}:E{hdr2}")
    # 註：「調課後授課時間」C:D、「原授課時間」G:H 在範例檔並未合併，故不合併

    _announce_row(ws, r, event)
    r += 1
    r = _maybe_note(ws, r, event)
    return r + _SPACER


# --------------------------------------------------------------------------
# 班級調代課通知單
# --------------------------------------------------------------------------

def _class_slip(ws: Worksheet, r: int, slip: ClassSlip, event: Event) -> int:
    top = r
    ws.row_dimensions[r].height = TITLE_ROW_H
    put(ws, f"A{r}", slip.klass, font=title_font(), align=CENTER_WRAP)

    if event.class_slip_style == "title":
        put(ws, f"D{r}", styles.CLASS_TITLE_TEXT, align=CENTER)
        for col in "GHI":
            put(ws, f"{col}{r}", None, border=BOTTOM_ONLY)
        put(ws, f"G{r}", f"假單編號：{event.form_no}", align=CENTER, border=BOTTOM_ONLY)
        _merge(ws, f"G{top}:I{top}")
    else:  # banner
        for col in "BCDEFGHI":
            put(ws, f"{col}{r}", None, border=BOTTOM_ONLY)
        put(ws, f"B{r}", banner_text(event), align=CENTER, border=BOTTOM_ONLY)
        _merge(ws, f"B{top}:I{top}")
    r += 1

    hdr = r
    for col, label in zip("BCDE", ("日期", "星期", "節次", "授課科目")):
        put(ws, f"{col}{hdr}", label, align=CENTER)
    put(ws, f"F{hdr}", "備註", align=CENTER)
    r += 1

    first_data = r
    for row in slip.rows:
        ws.row_dimensions[r].height = CLASS_ROW_H
        fill = styles.HIGHLIGHT_FILL if getattr(row, "highlight", False) else None
        put(ws, f"B{r}", row.slot.date, align=CENTER, fmt=DATE_FMT, fill=fill)
        put(ws, f"C{r}", row.slot.weekday_cn, align=CENTER, fill=fill)
        put(ws, f"D{r}", str(row.slot.period), align=CENTER, fill=fill)
        put(ws, f"E{r}", row.subject, align=CENTER, fill=fill)
        put(ws, f"F{r}", row.note, align=LEFT_WRAP, fill=fill)
        if fill:
            for col in "GHI":
                put(ws, f"{col}{r}", None, fill=fill)
        if row.mark:
            put(ws, f"J{r}", row.mark, font=styles.mark_font(), align=CENTER, fill=fill)
        r += 1
    last_data = r - 1

    styles.outline_grid(ws, f"B{hdr}:I{last_data}")
    _merge(ws, f"F{hdr}:I{hdr}")
    for rr in range(first_data, last_data + 1):
        _merge(ws, f"F{rr}:I{rr}")

    put(ws, f"A{r}", "* 請學藝股長公佈。", font=body_font(bold=True), align=LEFT)
    _announce_row(ws, r, event)
    r += 1
    r = _maybe_note(ws, r, event)
    return r + _SPACER


# --------------------------------------------------------------------------
# 共用零件
# --------------------------------------------------------------------------

def _announce_row(ws: Worksheet, r: int, event: Event) -> None:
    put(ws, f"H{r}", roc.announce_line(event.announce_date), align=RIGHT)
    put(ws, f"I{r}", roc.announce_md(event.announce_date), align=LEFT)


def _maybe_note(ws: Worksheet, r: int, event: Event) -> int:
    if not event.note.strip():
        return r
    ws.row_dimensions[r].height = NOTE_ROW_H
    put(ws, f"A{r}", f"說明:\n{event.note.strip()}", align=NOTE_ALIGN)
    _merge(ws, f"A{r}:I{r}")
    return r + 1


def _merge(ws: Worksheet, cell_range: str) -> None:
    start = cell_range.split(":")[0]
    end = cell_range.split(":")[1]
    if start != end:
        ws.merge_cells(cell_range)


def _page_setup(ws: Worksheet, last_row: int) -> None:
    ws.print_area = f"A1:I{last_row}"
    ws.page_setup.orientation = "portrait"
    ws.page_setup.paperSize = styles.A4_PAPER
    ws.page_setup.scale = styles.PRINT_SCALE
    ws.page_margins = PageMargins(
        left=0.7, right=0.7, top=0.75, bottom=0.75, header=0.3, footer=0.3
    )
    ws.sheet_view.showGridLines = True
