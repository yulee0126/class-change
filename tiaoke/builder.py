"""把 Event 展開成通知單清單（教師單、班級單）。純邏輯、無 Excel 相依。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Event, Slot, SubLeg, SwapLeg, MIN_PERIOD, MAX_PERIOD


# --------------------------------------------------------------------------
# 通知單資料結構
# --------------------------------------------------------------------------

@dataclass
class TeacherRow:
    """教師單的一列。new / orig 任一可為 None（代課情境）。"""

    klass: str
    new: Slot | None
    subject: str
    orig: Slot | None
    note: str
    highlight: bool = False


@dataclass
class ClassRow:
    """班級單的一列。"""

    slot: Slot
    subject: str
    note: str
    highlight: bool = False
    is_sub: bool = False   # True＝代課列（排在調課列之後）


@dataclass
class TeacherSlip:
    teacher: str
    rows: list[TeacherRow] = field(default_factory=list)


@dataclass
class ClassSlip:
    klass: str
    rows: list[ClassRow] = field(default_factory=list)


Slip = TeacherSlip | ClassSlip


# --------------------------------------------------------------------------
# 展開
# --------------------------------------------------------------------------

def build(event: Event) -> list[Slip]:
    """回傳：先教師單（依首次出現順序），後班級單。"""
    teacher_rows: dict[str, list[TeacherRow]] = {}
    class_rows: dict[str, list[ClassRow]] = {}

    def tr(name: str) -> list[TeacherRow]:
        return teacher_rows.setdefault(name.strip(), [])

    def cr(klass: str) -> list[ClassRow]:
        return class_rows.setdefault(klass.strip(), [])

    for leg in event.legs:
        if isinstance(leg, SwapLeg):
            tr(leg.teacher_a).append(TeacherRow(
                klass=leg.klass, new=leg.slot_b, subject=leg.subject_a, orig=leg.slot_a,
                note=f"與{_bare(leg.teacher_b)}老師調課",
            ))
            tr(leg.teacher_b).append(TeacherRow(
                klass=leg.klass, new=leg.slot_a, subject=leg.subject_b, orig=leg.slot_b,
                note=f"與{_bare(leg.teacher_a)}老師調課",
            ))
            cr(leg.klass).append(ClassRow(
                slot=leg.slot_a, subject=leg.subject_b,
                note=f"調課(原{_bare(leg.teacher_a)}老師/{leg.subject_a})",
            ))
            cr(leg.klass).append(ClassRow(
                slot=leg.slot_b, subject=leg.subject_a,
                note=f"調課(原{_bare(leg.teacher_b)}老師/{leg.subject_b})",
            ))
            # class rows above are 調課 → is_sub 預設 False
        elif isinstance(leg, SubLeg):
            hl = leg.from_swap
            tr(leg.orig_teacher).append(TeacherRow(
                klass=leg.klass, new=None, subject=leg.subject, orig=leg.slot,
                note=f"{_bare(leg.sub_teacher)}老師 代課", highlight=hl,
            ))
            tr(leg.sub_teacher).append(TeacherRow(
                klass=leg.klass, new=leg.slot, subject=leg.subject, orig=None,
                note=f"代 {_bare(leg.orig_teacher)}老師", highlight=hl,
            ))
            cr(leg.klass).append(ClassRow(
                slot=leg.slot, subject=leg.subject,
                note=f"{_bare(leg.sub_teacher)}老師 代課", highlight=hl, is_sub=True,
            ))
        else:  # pragma: no cover - 防呆
            raise TypeError(f"未知的腳型別：{type(leg)!r}")

    for rows in teacher_rows.values():
        rows.sort(key=_teacher_row_key)
    for rows in class_rows.values():
        rows.sort(key=lambda cr_: (cr_.is_sub, cr_.slot.date, cr_.slot.period))

    slips: list[Slip] = [TeacherSlip(name, rows) for name, rows in teacher_rows.items()]
    slips += [ClassSlip(klass, rows) for klass, rows in class_rows.items()]
    return slips


def _teacher_row_key(row: TeacherRow):
    """先所有調課列、再所有代課列；各自依主要時段排序。"""
    is_sub = row.new is None or row.orig is None
    primary = row.new or row.orig
    return (is_sub, primary.date, primary.period)


def _bare(name: str) -> str:
    """移除結尾的「老師」，避免重複。"""
    name = name.strip()
    return name[:-2] if name.endswith("老師") else name


# --------------------------------------------------------------------------
# 驗證
# --------------------------------------------------------------------------

def validate(event: Event) -> list[str]:
    """回傳問題訊息清單（空 = 通過）。錯誤與警告混在一起，UI 自行呈現。"""
    msgs: list[str] = []

    if not event.originator.strip():
        msgs.append("發起教師未填。")
    if not event.form_no.strip():
        msgs.append("假單編號未填。")
    if not event.legs:
        msgs.append("尚未新增任何調課／代課腳。")

    seen_keys: set[tuple] = set()
    for i, leg in enumerate(event.legs, 1):
        tag = f"第 {i} 腳"
        if isinstance(leg, SwapLeg):
            for label, t, s in (("甲", leg.teacher_a, leg.subject_a), ("乙", leg.teacher_b, leg.subject_b)):
                if not t.strip():
                    msgs.append(f"{tag}：{label}老師未填。")
                if not s.strip():
                    msgs.append(f"{tag}：{label}科目未填。")
            if not leg.klass.strip():
                msgs.append(f"{tag}：班級未填。")
            _check_period(msgs, tag, "甲", leg.slot_a.period)
            _check_period(msgs, tag, "乙", leg.slot_b.period)
            if leg.slot_a == leg.slot_b:
                msgs.append(f"{tag}：甲、乙時段相同，無法對調。")
            if _bare(leg.teacher_a) == _bare(leg.teacher_b):
                msgs.append(f"{tag}：甲、乙為同一位老師。")
            key = ("swap", leg.klass, leg.teacher_a, leg.teacher_b,
                   leg.slot_a, leg.slot_b)
        else:
            if not leg.klass.strip():
                msgs.append(f"{tag}：班級未填。")
            if not leg.orig_teacher.strip():
                msgs.append(f"{tag}：原老師未填。")
            if not leg.sub_teacher.strip():
                msgs.append(f"{tag}：代課老師未填。")
            if not leg.subject.strip():
                msgs.append(f"{tag}：科目未填。")
            _check_period(msgs, tag, "", leg.slot.period)
            if _bare(leg.orig_teacher) == _bare(leg.sub_teacher):
                msgs.append(f"{tag}：原老師與代課老師相同。")
            key = ("sub", leg.klass, leg.orig_teacher, leg.sub_teacher, leg.slot)

        if key in seen_keys:
            msgs.append(f"{tag}：與先前的腳重複。")
        seen_keys.add(key)

    return msgs


def _check_period(msgs: list[str], tag: str, label: str, period: int) -> None:
    if not (MIN_PERIOD <= period <= MAX_PERIOD):
        who = f"{label}節次" if label else "節次"
        msgs.append(f"{tag}：{who} {period} 超出範圍（{MIN_PERIOD}–{MAX_PERIOD}）。")
