"""民國紀年、星期、日期格式與姓名工具。"""

from __future__ import annotations

import datetime

# date.weekday(): 週一=0 … 週日=6
_WEEKDAYS = "一二三四五六日"


def roc_year(d: datetime.date) -> int:
    """西元 → 民國年。"""
    return d.year - 1911


def weekday_cn(d: datetime.date) -> str:
    """回傳中文星期單字：一、二 … 日。"""
    return _WEEKDAYS[d.weekday()]


def announce_md(d: datetime.date) -> str:
    """公告日期用的字串，補零：'02月23日'。"""
    return f"{d.month:02d}月{d.day:02d}日"


def announce_line(d: datetime.date) -> str:
    """公告日期整串：'公告日期：115年'（民國年不補零）。"""
    return f"公告日期：{roc_year(d)}年"


def slot_label(d: datetime.date, period: int) -> str:
    """說明草稿用的時段標記：'8/31(一)第5節'（月日不補零）。"""
    return f"{d.month}/{d.day}({weekday_cn(d)})第{period}節"


def short_name(name: str) -> str:
    """取姓名末兩字作為簡稱：'余瑞文' → '瑞文'。"""
    name = name.strip()
    return name[-2:] if len(name) >= 2 else name


def sheet_code(originator: str, d: datetime.date) -> str:
    """工作表名稱：'瑞文' + '1150223'（民國年 + 月日補零）。"""
    return f"{short_name(originator)}{roc_year(d)}{d.month:02d}{d.day:02d}"
