"""GUI 冒煙測試：以假的 Page 建構 AppView，確認控制項組得起來、
refresh() 不炸。視覺仍需在真實環境檢視。"""

import os
import types

import pytest

ft = pytest.importorskip("flet")

from tiaoke.ui.app import AppView, _TimetableEditor, main  # noqa: E402
from tiaoke.ui.controller import AppController  # noqa: E402


class _FakePage:
    def __init__(self):
        self.controls = []
        self.title = ""
        self.window = types.SimpleNamespace(width=0, height=0)
        self.updated = 0

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        self.updated += 1


def test_appview_constructs_and_refreshes():
    page = _FakePage()
    view = AppView(page)
    assert page.controls  # 有畫東西
    assert page.updated >= 1

    # 新增事件 → 填欄位 → 加一腳 → 預覽有內容
    view.ctl.new_event()
    view.ctl.update_event_fields(originator="余瑞文", form_no="手動")
    view.ctl.add_swap_leg(
        klass="高一甲", teacher_a="余瑞文", subject_a="健康與護理",
        date_a=__import__("datetime").date(2026, 2, 23), period_a=1,
        teacher_b="洪瑞霞", subject_b="班、週會",
        date_b=__import__("datetime").date(2026, 2, 25), period_b=5,
    )
    view.refresh()
    pv = view.ctl.preview()
    assert pv.teacher_count == 2

    # 開啟兩種腳表單不炸
    view._open_leg_form("swap")
    view._open_leg_form("sub")
    view._cancel_leg()


def test_main_callable():
    assert callable(main)


def test_timetable_editor_edit_delete_and_save(tmp_path):
    ctl = AppController()
    settings = types.SimpleNamespace(timetable_path="", save=lambda: None)
    msgs = []
    editor = _TimetableEditor(ctl, settings, on_changed=msgs.append)

    editor.teacher.field.value = "王小明"
    editor._on_teacher_change()
    editor._pick_weekday(2)
    assert editor.weekday == 2

    f_subj = ft.TextField(value="數學")
    f_klass = ft.TextField(value="高一甲、高一乙")
    f_loc = ft.TextField(value="")
    f_note = ft.TextField(value="(兼)")
    editor._save_slot(3, f_subj, f_klass, f_loc, f_note)

    grp = ctl.timetable_teacher_table("王小明").slot_group(2, 3)
    assert {s.klass for s in grp} == {"高一甲", "高一乙"}
    assert all(s.subject == "數學" and s.note == "(兼)" for s in grp)
    assert msgs and "更新" in msgs[-1]

    path = str(tmp_path / "課表.json")
    editor.save_path.value = path
    editor._save(None)
    assert settings.timetable_path == path
    assert os.path.exists(path)

    editor._delete_slot(3)
    assert ctl.timetable_teacher_table("王小明").slot_group(2, 3) == []
    assert "刪除" in msgs[-1]
