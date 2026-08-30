"""依事件的腳自動產生「說明」草稿。使用者可於 GUI 再修改。"""

from __future__ import annotations

import datetime
from collections import OrderedDict

from .models import Event, SubLeg, SwapLeg
from .roc import weekday_cn


def draft(event: Event) -> str:
    """回傳說明本文（不含「說明:」前綴）。無腳則回空字串。"""
    swaps = [l for l in event.legs if isinstance(l, SwapLeg)]
    subs = [l for l in event.legs if isinstance(l, SubLeg)]

    segments: list[str] = []
    if swaps:
        segments.append(_swap_part(swaps))
    if subs:
        lead = "調課後需請人代課，" if swaps else ""
        segments.append(lead + _sub_part(subs))

    text = "，".join(s for s in segments if s)
    return f"{text}。" if text else ""


# --------------------------------------------------------------------------

def _fmt_periods(periods) -> str:
    return "、".join(str(p) for p in sorted(set(periods)))


def _date_periods(d: datetime.date, periods) -> str:
    return f"{d.month}/{d.day}({weekday_cn(d)})第{_fmt_periods(periods)}節"


def _bare(name: str) -> str:
    name = name.strip()
    return name[:-2] if name.endswith("老師") else name


def _swap_part(swaps: list[SwapLeg]) -> str:
    groups: "OrderedDict[tuple, list[SwapLeg]]" = OrderedDict()
    for leg in swaps:
        key = tuple(sorted({leg.slot_a.date, leg.slot_b.date}))
        groups.setdefault(key, []).append(leg)

    chunks: list[str] = []
    for dates, legs in groups.items():
        if len(dates) == 2:
            d1, d2 = dates
            p1 = [s.period for l in legs for s in (l.slot_a, l.slot_b) if s.date == d1]
            p2 = [s.period for l in legs for s in (l.slot_a, l.slot_b) if s.date == d2]
            chunks.append(f"{_date_periods(d1, p1)}課務與{_date_periods(d2, p2)}課務互調")
        else:  # 同日對調（罕見）
            for l in legs:
                chunks.append(
                    f"{l.klass}{_bare(l.teacher_a)}老師與{_bare(l.teacher_b)}老師課務對調"
                )
    return "；".join(chunks)


def _sub_part(subs: list[SubLeg]) -> str:
    groups: "OrderedDict[tuple, list[int]]" = OrderedDict()
    for leg in subs:
        groups.setdefault((leg.slot.date, _bare(leg.sub_teacher)), []).append(leg.slot.period)
    return "、".join(
        f"{_date_periods(d, periods)}由{sub}老師代課"
        for (d, sub), periods in groups.items()
    )
