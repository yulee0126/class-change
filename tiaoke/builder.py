"""把 Event 展開成通知單清單（教師單、班級單）。純邏輯、無 Excel 相依。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import CoSwapLeg, Event, Slot, SubLeg, SwapLeg, MIN_PERIOD, MAX_PERIOD


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
    mark: str = ""          # J 欄註記：原時段若為兼課／第八節（"兼課"、"八"、或兩者用「、」相接）


@dataclass
class ClassRow:
    """班級單的一列。"""

    slot: Slot
    subject: str
    note: str
    highlight: bool = False
    is_sub: bool = False   # True＝代課列（排在調課列之後）
    mark: str = ""          # J 欄註記，同 TeacherRow.mark


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

def build(event: Event, timetable=None) -> list[Slip]:
    """回傳：先教師單（依首次出現順序），後班級單。

    timetable 有給的話，代課腳會查「原老師」在原時段的課表標記
    （P5 解析出的 `(兼)`/`(輔)`），符合的話該筆異動所有相關列
    （原老師、代課老師、班級單）J 欄都會標「兼課」／「八」。
    """
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
                note=f"與{_bare(leg.teacher_b)}老師 {leg.subject_b} 調課",
            ))
            tr(leg.teacher_b).append(TeacherRow(
                klass=leg.klass, new=leg.slot_a, subject=leg.subject_b, orig=leg.slot_b,
                note=f"與{_bare(leg.teacher_a)}老師 {leg.subject_a} 調課",
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
        elif isinstance(leg, CoSwapLeg):
            a_label = "/".join(_bare(t) for t in leg.teachers_a)
            b_label = "/".join(_bare(t) for t in leg.teachers_b)
            for t in leg.teachers_a:
                tr(t).append(TeacherRow(
                    klass=leg.klass, new=leg.slot_b, subject=leg.subject_a, orig=leg.slot_a,
                    note=f"與{b_label}老師 {leg.subject_b} 調課",
                ))
            for t in leg.teachers_b:
                tr(t).append(TeacherRow(
                    klass=leg.klass, new=leg.slot_a, subject=leg.subject_b, orig=leg.slot_b,
                    note=f"與{a_label}老師 {leg.subject_a} 調課",
                ))
            cr(leg.klass).append(ClassRow(
                slot=leg.slot_a, subject=leg.subject_b,
                note=f"調課(原{a_label}老師/{leg.subject_a})",
            ))
            cr(leg.klass).append(ClassRow(
                slot=leg.slot_b, subject=leg.subject_a,
                note=f"調課(原{b_label}老師/{leg.subject_b})",
            ))
        elif isinstance(leg, SubLeg):
            hl = leg.from_swap
            mark = _lookup_mark(timetable, leg.orig_teacher, leg.slot)
            sub_name, orig_name = _bare(leg.sub_teacher), _bare(leg.orig_teacher)
            if leg.is_co_teach:
                note_orig = f"改由{sub_name}老師獨立授課（原協同）"
                note_sub = f"獨立授課（原與{orig_name}老師協同）"
                note_class = f"{sub_name}老師獨立授課（原協同）"
            else:
                note_orig = note_class = f"{sub_name}老師 代課"
                note_sub = f"代 {orig_name}老師"
            tr(leg.orig_teacher).append(TeacherRow(
                klass=leg.klass, new=None, subject=leg.subject, orig=leg.slot,
                note=note_orig, highlight=hl, mark=mark,
            ))
            tr(leg.sub_teacher).append(TeacherRow(
                klass=leg.klass, new=leg.slot, subject=leg.subject, orig=None,
                note=note_sub, highlight=hl, mark=mark,
            ))
            cr(leg.klass).append(ClassRow(
                slot=leg.slot, subject=leg.subject,
                note=note_class, highlight=hl, is_sub=True, mark=mark,
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


def lookup_tags(timetable, teacher: str, slot: Slot) -> tuple[bool, bool]:
    """查 teacher 在 slot 當下的課表，回傳 (是否兼課, 是否第八節)。

    供 builder（J 欄註記）與 record（明細表「代課別」欄）共用，
    各自決定要顯示的文字。timetable 沒給或查不到都回傳 (False, False)。
    """
    if timetable is None or not teacher:
        return False, False
    wd = slot.date.weekday() + 1  # 1=星期一…5=星期五
    if wd > 5:
        return False, False
    for s in timetable.slots_for(teacher.strip(), wd):
        if s.period != slot.period:
            continue
        note = s.note or ""
        return "(兼)" in note, "(輔)" in note
    return False, False


def _lookup_mark(timetable, teacher: str, slot: Slot) -> str:
    """原老師在 slot 當下的課表若標了 (兼)/(輔)，回傳「兼課」／「八」（可兩者並列）。"""
    is_extra, is_period8 = lookup_tags(timetable, teacher, slot)
    tags: list[str] = []
    if is_extra:
        tags.append("兼課")
    if is_period8:
        tags.append("八")
    return "、".join(tags)


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
        elif isinstance(leg, CoSwapLeg):
            if not leg.klass.strip():
                msgs.append(f"{tag}：班級未填。")
            for label, names, subj in (("A", leg.teachers_a, leg.subject_a),
                                       ("B", leg.teachers_b, leg.subject_b)):
                if not names or all(not n.strip() for n in names):
                    msgs.append(f"{tag}：{label}側老師未填。")
                if not subj.strip():
                    msgs.append(f"{tag}：{label}側科目未填。")
            _check_period(msgs, tag, "A側", leg.slot_a.period)
            _check_period(msgs, tag, "B側", leg.slot_b.period)
            if leg.slot_a == leg.slot_b:
                msgs.append(f"{tag}：A、B側時段相同，無法對調。")
            if {_bare(t) for t in leg.teachers_a} & {_bare(t) for t in leg.teachers_b}:
                msgs.append(f"{tag}：A、B側有相同老師。")
            key = ("coswap", leg.klass, tuple(sorted(leg.teachers_a)),
                   tuple(sorted(leg.teachers_b)), leg.slot_a, leg.slot_b)
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
