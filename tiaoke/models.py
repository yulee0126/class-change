"""資料模型：Slot / SwapLeg / SubLeg / Event / Project。"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field, asdict
from typing import Iterable, Union

from . import roc

LEAVE_TYPES = ["公假", "病假", "事假", "喪假", "生理假", "請假", "其他"]
CLASS_SLIP_STYLES = ["banner", "title"]  # 橫幅式 / 標題式
MIN_PERIOD, MAX_PERIOD = 1, 10


@dataclass(frozen=True)
class Slot:
    """一節課的時間：日期 + 節次。星期由日期推算。"""

    date: datetime.date
    period: int

    @property
    def weekday_cn(self) -> str:
        return roc.weekday_cn(self.date)

    def __str__(self) -> str:
        return roc.slot_label(self.date, self.period)


@dataclass
class SwapLeg:
    """對調腳：甲、乙兩位老師在同一班各拿一節互換。"""

    klass: str
    teacher_a: str
    subject_a: str
    slot_a: Slot
    teacher_b: str
    subject_b: str
    slot_b: Slot

    kind: str = field(default="swap", init=False)

    def dates(self) -> list[datetime.date]:
        return [self.slot_a.date, self.slot_b.date]

    def teachers(self) -> list[str]:
        return [self.teacher_a, self.teacher_b]


@dataclass
class SubLeg:
    """代課腳：原老師某節請人代課，時段不動。

    from_swap=True 表示這一節原本是「調課調入」的時段（發起人先把課調進來、
    之後又請假），教師單會反白標示並在 J 欄放代課老師簡稱（對照 炆明1150831）。
    """

    klass: str
    orig_teacher: str
    subject: str
    slot: Slot
    sub_teacher: str
    from_swap: bool = False

    kind: str = field(default="sub", init=False)

    def dates(self) -> list[datetime.date]:
        return [self.slot.date]

    def teachers(self) -> list[str]:
        return [self.orig_teacher, self.sub_teacher]


Leg = Union[SwapLeg, SubLeg]


@dataclass
class Event:
    """一個調代課事件 = 一個工作表。"""

    originator: str                       # 橫幅顯示的發起教師
    leave_type: str                       # 假別
    form_no: str                          # 假單編號（單一自由文字，預設 "手動+"；印在橫幅上）
    announce_date: datetime.date          # 公告日期
    system_form_no: str = ""              # 系統假單編號：只用來組輸出檔名，不印在橫幅上
    sheet_date: datetime.date | None = None   # 分頁名稱用日期；None → 取所有腳最早日期
    note: str = ""                        # 說明本文（不含「說明:」前綴）；空則不產生說明列
    class_slip_style: str = "banner"
    legs: list[Leg] = field(default_factory=list)
    sheet_name_override: str | None = None

    # --- 衍生 ---
    @property
    def effective_sheet_date(self) -> datetime.date:
        """分頁名稱用的日期：優先取第一筆調課「甲方原本日期」，
        其次第一筆代課日期，最後才用公告日期。"""
        if self.sheet_date is not None:
            return self.sheet_date
        for leg in self.legs:
            if isinstance(leg, SwapLeg):
                return leg.slot_a.date
        for leg in self.legs:
            if isinstance(leg, SubLeg):
                return leg.slot.date
        return self.announce_date

    @property
    def sheet_name(self) -> str:
        if self.sheet_name_override:
            return self.sheet_name_override
        return roc.sheet_code(self.originator, self.effective_sheet_date)

    def all_teachers(self) -> list[str]:
        seen: list[str] = []
        for leg in self.legs:
            for t in leg.teachers():
                if t not in seen:
                    seen.append(t)
        return seen

    def all_classes(self) -> list[str]:
        seen: list[str] = []
        for leg in self.legs:
            if leg.klass not in seen:
                seen.append(leg.klass)
        return seen


@dataclass
class Project:
    """一份專案：多個事件 + 常用名稱主檔。"""

    events: list[Event] = field(default_factory=list)
    teachers: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    subjects: list[str] = field(default_factory=list)
    master_path: str = ""

    def merge_master_data(self) -> None:
        """把所有事件用到的名稱補進主檔清單。"""
        for ev in self.events:
            for t in ev.all_teachers():
                if t and t not in self.teachers:
                    self.teachers.append(t)
            for k in ev.all_classes():
                if k and k not in self.classes:
                    self.classes.append(k)
            for leg in ev.legs:
                subs = [leg.subject] if isinstance(leg, SubLeg) else [leg.subject_a, leg.subject_b]
                for s in subs:
                    if s and s not in self.subjects:
                        self.subjects.append(s)


# --------------------------------------------------------------------------
# 序列化（供 storage 使用；P1 先提供基本 dict 轉換以利測試 fixtures）
# --------------------------------------------------------------------------

def _slot_to_dict(s: Slot) -> dict:
    return {"date": s.date.isoformat(), "period": s.period}


def _slot_from_dict(d: dict) -> Slot:
    return Slot(datetime.date.fromisoformat(d["date"]), int(d["period"]))


def leg_to_dict(leg: Leg) -> dict:
    if isinstance(leg, SwapLeg):
        return {
            "kind": "swap",
            "klass": leg.klass,
            "teacher_a": leg.teacher_a, "subject_a": leg.subject_a, "slot_a": _slot_to_dict(leg.slot_a),
            "teacher_b": leg.teacher_b, "subject_b": leg.subject_b, "slot_b": _slot_to_dict(leg.slot_b),
        }
    return {
        "kind": "sub",
        "klass": leg.klass,
        "orig_teacher": leg.orig_teacher,
        "subject": leg.subject,
        "slot": _slot_to_dict(leg.slot),
        "sub_teacher": leg.sub_teacher,
        "from_swap": leg.from_swap,
    }


def leg_from_dict(d: dict) -> Leg:
    if d["kind"] == "swap":
        return SwapLeg(
            klass=d["klass"],
            teacher_a=d["teacher_a"], subject_a=d["subject_a"], slot_a=_slot_from_dict(d["slot_a"]),
            teacher_b=d["teacher_b"], subject_b=d["subject_b"], slot_b=_slot_from_dict(d["slot_b"]),
        )
    return SubLeg(
        klass=d["klass"],
        orig_teacher=d["orig_teacher"],
        subject=d["subject"],
        slot=_slot_from_dict(d["slot"]),
        sub_teacher=d["sub_teacher"],
        from_swap=d.get("from_swap", False),
    )


def event_to_dict(ev: Event) -> dict:
    return {
        "originator": ev.originator,
        "leave_type": ev.leave_type,
        "form_no": ev.form_no,
        "system_form_no": ev.system_form_no,
        "announce_date": ev.announce_date.isoformat(),
        "sheet_date": ev.sheet_date.isoformat() if ev.sheet_date else None,
        "note": ev.note,
        "class_slip_style": ev.class_slip_style,
        "sheet_name_override": ev.sheet_name_override,
        "legs": [leg_to_dict(l) for l in ev.legs],
    }


def event_from_dict(d: dict) -> Event:
    return Event(
        originator=d["originator"],
        leave_type=d["leave_type"],
        form_no=d["form_no"],
        system_form_no=d.get("system_form_no", ""),
        announce_date=datetime.date.fromisoformat(d["announce_date"]),
        sheet_date=datetime.date.fromisoformat(d["sheet_date"]) if d.get("sheet_date") else None,
        note=d.get("note", ""),
        class_slip_style=d.get("class_slip_style", "banner"),
        sheet_name_override=d.get("sheet_name_override"),
        legs=[leg_from_dict(x) for x in d.get("legs", [])],
    )
