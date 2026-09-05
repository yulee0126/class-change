import datetime

import pytest

from tiaoke import roc
from tiaoke.models import CoSwapLeg, Project, Slot
from tiaoke.ui.controller import AppController

D = datetime.date


def test_parse_date_variants():
    assert roc.parse_date("2026-02-23") == D(2026, 2, 23)
    assert roc.parse_date("2026/2/23") == D(2026, 2, 23)
    assert roc.parse_date("115/2/23") == D(2026, 2, 23)
    assert roc.parse_date("115.02.23") == D(2026, 2, 23)
    with pytest.raises(ValueError):
        roc.parse_date("abc")


def test_new_event_defaults():
    c = AppController()
    assert c.current is None
    ev = c.new_event()
    assert c.current is ev
    assert ev.form_no == "手動+"
    assert ev.leave_type == "公假"


def test_add_swap_leg_and_preview():
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="余瑞文", form_no="手動")
    c.add_swap_leg(
        klass="高一甲", teacher_a="余瑞文", subject_a="健康與護理",
        date_a=D(2026, 2, 23), period_a=1,
        teacher_b="洪瑞霞", subject_b="班、週會",
        date_b=D(2026, 2, 25), period_b=5,
    )
    pv = c.preview()
    assert pv.teacher_count == 2
    assert pv.class_count == 1
    # 主檔學到名稱
    assert "余瑞文" in c.project.teachers
    assert "高一甲" in c.project.classes
    assert "健康與護理" in c.project.subjects


def test_co_teachers_of_looks_up_timetable():
    from tiaoke.timetable import Slot as TTSlot, TeacherTable, Timetable
    c = AppController()
    c.timetable = Timetable()
    c.timetable.teachers["趙瑋"] = TeacherTable(name="趙瑋", slots=[
        TTSlot(2, 5, "基礎雜糧加工實作", "綜職二", co_teachers=["周蓁妍"]),
        TTSlot(2, 6, "基礎雜糧加工實作", "綜職二"),  # 沒協同
    ])
    # 2026-09-01 是星期二
    assert c.co_teachers_of("趙瑋", D(2026, 9, 1), 5) == ["周蓁妍"]
    assert c.co_teachers_of("趙瑋", D(2026, 9, 1), 6) == []
    assert c.co_teachers_of("趙瑋", D(2026, 9, 2), 5) == []  # 星期三沒課
    assert c.co_teachers_of("", D(2026, 9, 1), 5) == []
    assert AppController().co_teachers_of("趙瑋", D(2026, 9, 1), 5) == []  # 沒課表


def test_add_co_swap_creates_one_symmetric_leg():
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="趙瑋", form_no="手動")
    c.add_co_swap(
        klass="綜職二",
        teachers_a=["趙瑋", "周蓁妍"], subject_a="基礎雜糧加工實作",
        date_a=D(2026, 9, 3), period_a=5,
        teachers_b=["張宥恩"], subject_b="物品整理實務",
        date_b=D(2026, 9, 1), period_b=5,
    )
    legs = c.current.legs
    assert len(legs) == 1
    leg = legs[0]
    assert isinstance(leg, CoSwapLeg)
    assert leg.teachers_a == ["趙瑋", "周蓁妍"]
    assert leg.teachers_b == ["張宥恩"]
    assert leg.slot_a == Slot(D(2026, 9, 3), 5)
    assert leg.slot_b == Slot(D(2026, 9, 1), 5)
    # 主檔學到雙側的名字
    assert "周蓁妍" in c.project.teachers and "張宥恩" in c.project.teachers


def test_add_co_swap_requires_both_sides():
    c = AppController()
    c.new_event()
    with pytest.raises(ValueError, match="B 側"):
        c.add_co_swap(
            klass="綜職二",
            teachers_a=["趙瑋", "周蓁妍"], subject_a="基礎雜糧加工實作",
            date_a=D(2026, 9, 3), period_a=5,
            teachers_b=[], subject_b="物品整理實務",
            date_b=D(2026, 9, 1), period_b=5,
        )


def test_add_co_swap_rejects_overlapping_teachers():
    c = AppController()
    c.new_event()
    with pytest.raises(ValueError, match="不能有相同老師"):
        c.add_co_swap(
            klass="綜職二",
            teachers_a=["趙瑋"], subject_a="基礎雜糧加工實作",
            date_a=D(2026, 9, 3), period_a=5,
            teachers_b=["趙瑋"], subject_b="物品整理實務",
            date_b=D(2026, 9, 1), period_b=5,
        )


def test_add_sub_batch():
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="劉炆明")
    n = c.add_sub_batch(orig_teacher="劉炆明", items=[
        dict(klass="二丁應", subject="經濟學", date=D(2026, 9, 2), period=5, sub_teacher="郭惠茹"),
        dict(klass="二丁應", subject="經濟學", date=D(2026, 9, 2), period=6, sub_teacher="郭惠茹"),
    ])
    assert n == 2
    assert len(c.current.legs) == 2


def test_generate_blocks_on_missing_fields(tmp_path):
    c = AppController()
    c.new_event()  # 沒有發起教師、沒有腳
    with pytest.raises(ValueError):
        c.generate(to_master=False, save_new=True, dest_path=str(tmp_path / "x.xlsx"))


def test_generate_writes_new_file(tmp_path):
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="余瑞文", form_no="手動",
                          announce_date=D(2026, 2, 13))
    c.add_swap_leg(
        klass="高一甲", teacher_a="余瑞文", subject_a="健康與護理",
        date_a=D(2026, 2, 23), period_a=1,
        teacher_b="洪瑞霞", subject_b="班、週會",
        date_b=D(2026, 2, 25), period_b=5,
    )
    dest = tmp_path / "余瑞文.xlsx"
    results = c.generate(to_master=False, save_new=True, dest_path=str(dest))
    assert results[0].ok
    assert dest.exists()


def test_default_new_path_uses_sheet_name():
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="余瑞文", sheet_date=D(2026, 2, 23))
    assert c.default_new_path().endswith("瑞文1150223.xlsx")


def test_default_new_path_prefixes_system_form_no():
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="余瑞文", sheet_date=D(2026, 2, 23),
                          system_form_no="1002")
    assert c.default_new_path().endswith("1002-瑞文1150223.xlsx")


def test_delete_and_select():
    c = AppController()
    a = c.new_event(); c.update_event_fields(originator="甲")
    b = c.new_event(); c.update_event_fields(originator="乙")
    assert len(c.project.events) == 2
    c.select_event(0)
    c.delete_event()
    assert len(c.project.events) == 1
    assert c.current.originator == "乙"
