import datetime

import pytest

from tiaoke import samples
from tiaoke import timetable as tt_mod
from tiaoke.builder import ClassSlip, TeacherSlip, build, validate
from tiaoke.models import Event, Slot, SubLeg, SwapLeg

D = datetime.date


def _teacher(slips, name):
    return next(s for s in slips if isinstance(s, TeacherSlip) and s.teacher == name)


def _klass(slips, name):
    return next(s for s in slips if isinstance(s, ClassSlip) and s.klass == name)


def _timetable_with_note(weekday: int, period: int, note: str, teacher="余瑞文"):
    table = tt_mod.Timetable()
    table.teachers[teacher] = tt_mod.TeacherTable(name=teacher, slots=[
        tt_mod.Slot(weekday=weekday, period=period, subject="健康與護理",
                    klass="電機一", note=note),
    ])
    return table


def test_swap_expands_to_two_teacher_slips_and_one_class_slip():
    ev = Event("余瑞文", "其他", "手動", D(2026, 2, 13), legs=[
        SwapLeg("高一甲", "余瑞文", "健康與護理", Slot(D(2026, 2, 23), 1),
                "洪瑞霞", "班、週會", Slot(D(2026, 2, 25), 5)),
    ])
    slips = build(ev)
    assert [type(s).__name__ for s in slips] == ["TeacherSlip", "TeacherSlip", "ClassSlip"]

    a = _teacher(slips, "余瑞文").rows[0]
    assert a.new == Slot(D(2026, 2, 25), 5)      # 調課後 = 對方原時段
    assert a.orig == Slot(D(2026, 2, 23), 1)     # 原時段
    assert a.subject == "健康與護理"
    assert a.note == "與洪瑞霞老師 班、週會 調課"

    b = _teacher(slips, "洪瑞霞").rows[0]
    assert b.new == Slot(D(2026, 2, 23), 1)
    assert b.note == "與余瑞文老師 健康與護理 調課"

    crows = _klass(slips, "高一甲").rows
    assert len(crows) == 2
    assert crows[0].slot == Slot(D(2026, 2, 23), 1)
    assert crows[0].subject == "班、週會"
    assert crows[0].note == "調課(原余瑞文老師/健康與護理)"
    assert crows[1].note == "調課(原洪瑞霞老師/班、週會)"


def test_sub_leg_marks_extra_hours_on_all_three_slips():
    # 2026-09-07 是星期一（weekday=1）
    ev = Event("余瑞文", "病假", "手動", D(2026, 9, 3), legs=[
        SubLeg("電機一", "余瑞文", "健康與護理", Slot(D(2026, 9, 7), 1), "王小明"),
    ])
    slips = build(ev, timetable=_timetable_with_note(1, 1, "(兼)"))
    assert _teacher(slips, "余瑞文").rows[0].mark == "兼課"
    assert _teacher(slips, "王小明").rows[0].mark == "兼課"
    assert _klass(slips, "電機一").rows[0].mark == "兼課"


def test_sub_leg_marks_period8():
    ev = Event("余瑞文", "病假", "手動", D(2026, 9, 3), legs=[
        SubLeg("電機一", "余瑞文", "專業輔導", Slot(D(2026, 9, 7), 8), "王小明"),
    ])
    slips = build(ev, timetable=_timetable_with_note(1, 8, "(輔)"))
    assert _teacher(slips, "余瑞文").rows[0].mark == "八"


def test_sub_leg_marks_both_when_extra_hours_and_period8():
    ev = Event("余瑞文", "病假", "手動", D(2026, 9, 3), legs=[
        SubLeg("電機一", "余瑞文", "健康與護理", Slot(D(2026, 9, 7), 8), "王小明"),
    ])
    slips = build(ev, timetable=_timetable_with_note(1, 8, "(兼)(輔)"))
    assert _teacher(slips, "余瑞文").rows[0].mark == "兼課、八"


def test_sub_leg_no_mark_without_timetable_or_match():
    ev = Event("余瑞文", "病假", "手動", D(2026, 9, 3), legs=[
        SubLeg("電機一", "余瑞文", "健康與護理", Slot(D(2026, 9, 7), 1), "王小明"),
    ])
    assert _teacher(build(ev), "余瑞文").rows[0].mark == ""
    # 有課表但那個時段沒有標記
    assert _teacher(build(ev, timetable=_timetable_with_note(1, 1, "")),
                    "余瑞文").rows[0].mark == ""
    # 課表裡是別的節次
    assert _teacher(build(ev, timetable=_timetable_with_note(1, 2, "(兼)")),
                    "余瑞文").rows[0].mark == ""


def test_swap_leg_is_never_marked():
    ev = Event("余瑞文", "其他", "手動", D(2026, 2, 13), legs=[
        SwapLeg("高一甲", "余瑞文", "健康與護理", Slot(D(2026, 2, 23), 1),
                "洪瑞霞", "班、週會", Slot(D(2026, 2, 25), 5)),
    ])
    slips = build(ev, timetable=_timetable_with_note(3, 1, "(兼)"))
    assert _teacher(slips, "余瑞文").rows[0].mark == ""


def test_sub_expands_correctly():
    ev = Event("吳建勳", "公假", "手動+1279", D(2022, 1, 19), legs=[
        SubLeg("工三", "吳建勳", "食品檢驗分析", Slot(D(2022, 1, 19), 4), "謝欣瑜"),
    ])
    slips = build(ev)
    orig = _teacher(slips, "吳建勳").rows[0]
    assert orig.new is None and orig.orig == Slot(D(2022, 1, 19), 4)
    assert orig.note == "謝欣瑜老師 代課"

    sub = _teacher(slips, "謝欣瑜").rows[0]
    assert sub.orig is None and sub.new == Slot(D(2022, 1, 19), 4)
    assert sub.note == "代 吳建勳老師"

    crow = _klass(slips, "工三").rows[0]
    assert crow.note == "謝欣瑜老師 代課"


def test_one_to_many_accumulates_rows():
    slips = build(samples.get("瑞文1150223"))
    assert len(_teacher(slips, "余瑞文").rows) == 3           # 一師多腳
    assert {type(s).__name__ for s in slips} == {"TeacherSlip", "ClassSlip"}
    assert sum(isinstance(s, ClassSlip) for s in slips) == 3


def test_class_rows_sorted_chronologically():
    slips = build(samples.get("若耶1150226"))
    rows = _klass(slips, "高三甲").rows
    assert [r.slot.date for r in rows] == [D(2026, 2, 25), D(2026, 2, 26)]


def test_validate_flags_bad_period_and_same_slot():
    ev = Event("甲", "其他", "手動", D(2026, 2, 13), legs=[
        SwapLeg("X", "甲", "s1", Slot(D(2026, 2, 23), 11),
                "乙", "s2", Slot(D(2026, 2, 23), 11)),
    ])
    msgs = " ".join(validate(ev))
    assert "超出範圍" in msgs
    assert "無法對調" in msgs


def test_validate_clean_event_has_no_messages():
    assert validate(samples.get("瑞文1150223")) == []


def test_sheet_date_defaults_to_swap_teacher_a_date():
    ev = Event("陳若耶", "公假", "手動", D(2026, 2, 20), legs=[
        SwapLeg("高三甲", "陳若耶", "國語文", Slot(D(2026, 2, 26), 5),
                "蔡文華", "公民", Slot(D(2026, 2, 25), 5)),
    ])
    # 取甲方原本日期 2/26，不是最早的 2/25
    assert ev.effective_sheet_date == D(2026, 2, 26)
    assert ev.sheet_name == "若耶1150226"


def test_sheet_date_falls_back_to_sub_date():
    ev = Event("吳建勳", "公假", "手動", D(2022, 1, 10), legs=[
        SubLeg("工三", "吳建勳", "食品", Slot(D(2022, 1, 19), 4), "謝欣瑜"),
    ])
    assert ev.effective_sheet_date == D(2022, 1, 19)
