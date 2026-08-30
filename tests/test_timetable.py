import datetime
import os

import pytest

from tiaoke import timetable as tt
from tiaoke.timetable import Slot, TeacherTable, Timetable, _parse_cell
from tiaoke.ui.controller import AppController

D = datetime.date

# 這台機器上的實體 PDF（若不在則跳過相關測試）
_PDF = r"C:\Users\lolola\Desktop\調課代課程式\115-1教師課表(暫行).pdf"
_HAS_PDF = os.path.exists(_PDF)

# 從真實 PDF 掃出來的班級／地點詞彙（測 _parse_cell）
_CLASSES = {"園藝一", "園藝二", "園藝三", "高一甲", "高二甲", "商經一",
            "加工一", "餐飲一", "畜保一", "電機一", "綜職二"}
_ROOMS = {"園藝視聽教室", "多媒體教室2", "果樹技術教室", "室內配線場"}


def test_parse_cell_basic():
    r = _parse_cell(["農業概論", "園藝一", "園藝視聽教室"], _CLASSES, _ROOMS)
    assert r["subject"] == "農業概論"
    assert r["classes"] == ["園藝一"]
    assert r["location"] == "園藝視聽教室"


def test_parse_cell_wrapped_subject():
    r = _parse_cell(["農業資訊管理", "實習", "園藝三", "多媒體教室"], _CLASSES | {"園藝三"}, set())
    assert r["subject"] == "農業資訊管理實習"
    assert r["classes"] == ["園藝三"]


def test_parse_cell_meeting_skipped():
    assert _parse_cell(["行政會報"], _CLASSES, _ROOMS) is None


def test_parse_cell_multi_class_slash_split_across_lines():
    r = _parse_cell(["臺灣手語", "加工一/商", "經一/餐飲一/"], _CLASSES, set())
    assert r["subject"] == "臺灣手語"
    assert r["classes"] == ["加工一", "商經一", "餐飲一"]


def test_parse_cell_class_in_middle():
    r = _parse_cell(["電工實習", "電機一", "室內配線場"], _CLASSES, set())
    assert r["subject"] == "電工實習"
    assert r["classes"] == ["電機一"]
    assert r["location"] == "室內配線場"


def test_timetable_round_trip():
    src = Timetable(school="X中", semester="115學年度第一",
                    valid_from="2026-08-31", valid_to="2026-09-04",
                    period_times={1: ["08:00", "08:50"]})
    src.teachers["余瑞文"] = TeacherTable(
        name="余瑞文", tid="01306", title="兼課教師",
        slots=[Slot(1, 1, "健康與護理", "電機一", "", ""),
               Slot(3, 5, "健康與護理", "園藝一")])
    d = src.to_dict()
    back = Timetable.from_dict(d)
    assert back.teachers["余瑞文"].tid == "01306"
    assert back.teachers["余瑞文"].title == "兼課教師"
    assert back.slots_for("余瑞文", 1)[0].subject == "健康與護理"
    assert back.slots_for("余瑞文", 3)[0].klass == "園藝一"


def test_controller_timetable_slots_weekday_mapping():
    c = AppController()
    c.timetable = Timetable()
    c.timetable.teachers["王"] = TeacherTable(name="王", slots=[
        Slot(1, 2, "國文", "高一甲"),   # 星期一
        Slot(3, 4, "國文", "高一乙"),   # 星期三
    ])
    # 2026-08-31 是星期一
    got = c.timetable_slots("王", D(2026, 8, 31))
    assert [s.period for s in got] == [2]
    # 星期六 → 無
    assert c.timetable_slots("王", D(2026, 9, 5)) == []
    # 沒課表
    assert AppController().timetable_slots("王", D(2026, 8, 31)) == []


@pytest.mark.skipif(not _HAS_PDF, reason="找不到實體課表 PDF")
def test_parse_real_pdf():
    table = tt.parse_pdf(_PDF)
    assert len(table.teachers) >= 80
    assert table.school == "國立關西高級中學"
    assert table.valid_from == "2026-08-31"
    yu = table.teachers.get("余瑞文")
    assert yu and all(s.subject == "健康與護理" for s in yu.slots)
    # 星期一應有 4 節
    assert len(yu.on(1)) == 4
    # 空班級的比例應該很低
    empties = [s for t in table.teachers.values() for s in t.slots if not s.klass]
    total = sum(len(t.slots) for t in table.teachers.values())
    assert len(empties) / total < 0.02
