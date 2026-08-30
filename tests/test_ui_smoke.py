"""GUI 冒煙測試：以假的 Page 建構 AppView，確認控制項組得起來、
refresh() 不炸。視覺仍需在真實環境檢視。"""

import types

import pytest

ft = pytest.importorskip("flet")

from tiaoke.ui.app import AppView, main  # noqa: E402


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
