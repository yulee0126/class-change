"""GUI 冒煙測試：以假的 Page 建構 AppView，確認控制項組得起來、
refresh() 不炸。視覺仍需在真實環境檢視。"""

import datetime
import os
import types

import pytest

ft = pytest.importorskip("flet")

from tiaoke import samples
from tiaoke.models import CoSwapLeg
from tiaoke.timetable import Slot, TeacherTable, Timetable
from tiaoke.ui.app import AppView, _SlipSearch, _TimetableEditor, _TimetableImport, main  # noqa: E402
from tiaoke.ui.controller import AppController  # noqa: E402
from tiaoke.xlsx_writer import write_sheet  # noqa: E402


def _write(event, path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = event.sheet_name
    write_sheet(ws, event)
    wb.save(path)


class _FakePage:
    def __init__(self):
        self.controls = []
        self.title = ""
        self.window = types.SimpleNamespace(width=0, height=0)
        self.overlay = []
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
    f_co = ft.TextField(value="陳老師")
    editor._save_slot(3, f_subj, f_klass, f_loc, f_note, f_co)

    grp = ctl.timetable_teacher_table("王小明").slot_group(2, 3)
    assert {s.klass for s in grp} == {"高一甲", "高一乙"}
    assert all(s.subject == "數學" and s.note == "(兼)" and s.co_teachers == ["陳老師"]
              for s in grp)
    assert msgs and "更新" in msgs[-1]

    # 課表校對的列會顯示協同資訊
    row = editor._row(3, grp)
    row_text = row.controls[1].value
    assert "陳老師" in row_text and "協同" in row_text

    path = str(tmp_path / "課表.json")
    editor.save_path.value = path
    editor._save(None)
    assert settings.timetable_path == path
    assert os.path.exists(path)

    editor._delete_slot(3)
    assert ctl.timetable_teacher_table("王小明").slot_group(2, 3) == []
    assert "刪除" in msgs[-1]


def test_slip_search_finds_and_loads_file(tmp_path):
    ev = samples.get("代課範例")
    path = tmp_path / f"1001-{ev.sheet_name}.xlsx"
    _write(ev, str(path))

    ctl = AppController()
    folder_field = ft.TextField(value=str(tmp_path))
    msgs = []
    search = _SlipSearch(ctl, folder_field, on_loaded=msgs.append)

    search.query.value = ev.sheet_name
    search._typed()
    assert any(b.content == path.name for b in search.results.controls)

    search._pick(str(tmp_path), path.name)
    assert ctl.current is not None
    assert ctl.current.originator == ev.originator
    assert getattr(ctl.current, "_source_path") == str(path)
    assert msgs and "讀回" in msgs[-1]


def test_slip_search_shows_error_on_unparseable_file(tmp_path):
    (tmp_path / "bad.xlsx").write_bytes(b"not a real xlsx")
    ctl = AppController()
    folder_field = ft.TextField(value=str(tmp_path))
    search = _SlipSearch(ctl, folder_field, on_loaded=lambda m: None)
    search._pick(str(tmp_path), "bad.xlsx")
    assert "失敗" in search.status.value
    assert ctl.current is None


def test_generate_confirms_before_overwriting_loaded_file(tmp_path):
    ev = samples.get("代課範例")
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))

    page = _FakePage()
    view = AppView(page)
    view.ctl.load_event_from_file(str(path))
    view.refresh()
    assert view.tf_new.value == str(path)  # 預設存回原路徑

    view._on_generate(None)
    assert view._dlg is not None
    assert "覆蓋" in view._dlg.title.value
    confirm_action = view._dlg.actions[1]
    confirm_action.on_click(None)

    assert os.path.exists(path)
    assert "已存回" in view.status.value


def test_generate_confirms_delete_old_when_renaming_loaded_file(tmp_path):
    ev = samples.get("代課範例")
    old_path = tmp_path / "old.xlsx"
    new_path = tmp_path / "new.xlsx"
    _write(ev, str(old_path))

    page = _FakePage()
    view = AppView(page)
    view.ctl.load_event_from_file(str(old_path))
    view.refresh()
    view.tf_new.value = str(new_path)

    view._on_generate(None)
    assert "另存新檔名" in view._dlg.title.value
    view._dlg.actions[1].on_click(None)

    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)


def test_generate_report_button(tmp_path):
    slips = tmp_path / "調代課單"
    slips.mkdir()
    _write(samples.get("代課範例"), str(slips / "1001-a.xlsx"))
    out = tmp_path / "record"

    page = _FakePage()
    view = AppView(page)
    view.slips_folder.value = str(slips)
    view.record_folder.value = str(out)

    view._on_generate_report(None)
    assert "個檔案" in view.status.value
    assert os.path.isdir(out)


def test_timetable_import_reads_co_teaching_and_marks_slots(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["115-1教師配課一覽表"])
    ws.append(["序號", "職稱", "教師姓名", "授課班級", "課程名稱", "課程科別",
              "學分數", "基本節數", "兼課節數", "授課總數"])
    ws.append([1, "老師", "趙瑋", "職二", "基礎雜糧加工實作", 3, "協同", 12, 3, 15])
    ws.append([2, "老師", "周蓁妍", "職二", "基礎雜糧加工實作", 3, "協同", 8, 4, 12])
    path = tmp_path / "配當表.xlsx"
    wb.save(path)

    ctl = AppController()
    ctl.timetable = Timetable()
    ctl.timetable.teachers["趙瑋"] = TeacherTable(name="趙瑋", slots=[
        Slot(2, 5, "基礎雜糧加工實作", "綜職二")])
    ctl.timetable.teachers["周蓁妍"] = TeacherTable(name="周蓁妍", slots=[
        Slot(2, 5, "基礎雜糧加工實作", "綜職二")])
    settings = types.SimpleNamespace(timetable_path="", save=lambda: None)
    msgs = []
    importer = _TimetableImport(ctl, settings, on_changed=msgs.append)

    importer.co_path.value = str(path)
    importer._read_co_teaching(None)

    assert ctl.timetable.teachers["趙瑋"].slots[0].co_teachers == ["周蓁妍"]
    assert msgs and "協同" in msgs[-1]
    assert "標記 2 個節次" in importer.status.value


def test_co_swap_form_end_to_end():
    import datetime as _dt
    from tiaoke.timetable import Slot as TTSlot, TeacherTable, Timetable

    page = _FakePage()
    view = AppView(page)
    view.ctl.timetable = Timetable()
    view.ctl.timetable.teachers["趙瑋"] = TeacherTable(name="趙瑋", slots=[
        TTSlot(4, 5, "基礎雜糧加工實作", "綜職二", co_teachers=["周蓁妍"]),
    ])
    view.ctl.new_event()
    view.ctl.update_event_fields(originator="趙瑋", form_no="手動")

    view._open_leg_form("coswap")
    form = view._leg_form
    assert form.edit_index is None

    # 2026-09-03 是星期四
    form.ta.field.value = "趙瑋"
    form.date_a.field.value = "2026-09-03"
    form.period_a.value = "5"
    form._sync()
    assert form.ta_others.value == "周蓁妍"    # 自動帶出協同老師
    assert "協同" in form.co_hint_a.value

    form.klass.value = "綜職二"
    form.subject_a.value = "基礎雜糧加工實作"
    form.tb.field.value = "張宥恩"
    form.subject_b.value = "物品整理實務"
    form.date_b.field.value = "2026-09-01"
    form.period_b.value = "5"
    form._submit(None)

    assert view._leg_form is None
    legs = view.ctl.current.legs
    assert len(legs) == 1
    leg = legs[0]
    assert isinstance(leg, CoSwapLeg)
    assert leg.teachers_a == ["趙瑋", "周蓁妍"]
    assert leg.teachers_b == ["張宥恩"]
    assert "協作調課" in view.status.value


def test_sub_form_detects_co_teach_and_marks_independent_teaching():
    from tiaoke.timetable import Slot as TTSlot, TeacherTable, Timetable

    page = _FakePage()
    view = AppView(page)
    view.ctl.timetable = Timetable()
    view.ctl.timetable.teachers["趙瑋"] = TeacherTable(name="趙瑋", slots=[
        TTSlot(4, 5, "基礎雜糧加工實作", "綜職二", co_teachers=["周蓁妍"]),
    ])
    view.ctl.new_event()
    view.ctl.update_event_fields(originator="趙瑋", form_no="手動")

    view._open_leg_form("sub")
    form = view._leg_form

    # 2026-09-03 是星期四
    form.ot.field.value = "趙瑋"
    form.dd.field.value = "2026-09-03"
    form.pp.value = "5"
    form._sync()

    assert form.st.value == "周蓁妍"           # 自動帶出建議代課（協同）老師
    assert form.is_co_teach.value is True      # 自動勾選協同獨立授課
    assert "協同" in form.co_hint.value

    form.klass.value = "綜職二"
    form.subj.value = "基礎雜糧加工實作"
    form._submit(None)

    assert view._leg_form is None
    leg = view.ctl.current.legs[0]
    assert leg.is_co_teach is True
    assert leg.sub_teacher == "周蓁妍"

    slips = view.ctl.preview()
    assert slips.teacher_count == 2


def test_plain_swap_form_warns_when_picked_slot_is_co_taught():
    """使用者在普通「新增調課」選到協同課時，要提醒改用「協作調課」（不能默默漏掉另一位）。"""
    from tiaoke.timetable import Slot as TTSlot, TeacherTable, Timetable

    page = _FakePage()
    view = AppView(page)
    view.ctl.timetable = Timetable()
    view.ctl.timetable.teachers["趙瑋"] = TeacherTable(name="趙瑋", slots=[
        TTSlot(2, 5, "基礎雜糧加工實作", "綜職二", co_teachers=["周蓁妍"]),
    ])
    view.ctl.new_event()
    view.ctl.update_event_fields(originator="趙瑋", form_no="手動")

    view._open_leg_form("swap")
    form = view._leg_form
    assert form.co_warn.value == ""  # 甲老師還沒填，還不用警告

    # 2026-09-08 是星期二
    form.ta.field.value = "趙瑋"
    form.da.field.value = "2026-09-08"
    form.pa.value = "5"
    form._sync()

    assert "趙瑋" in form.co_warn.value
    assert "周蓁妍" in form.co_warn.value
    assert "協作調課" in form.co_warn.value

    # 點課表帶出的按鈕（模擬使用者點選）也會觸發同樣的警告
    form2 = view._leg_form = type(form)(
        view.page, "swap", view._submit_leg, view._cancel_leg,
        originator="趙瑋", ctl=view.ctl)
    form2.ta.field.value = "趙瑋"
    form2.da.field.value = "2026-09-08"  # 先選日期，畫面上才會列出當天的課可以點
    form2._sync()
    slot = view.ctl.timetable_slots("趙瑋", datetime.date(2026, 9, 8))[0]
    assert slot.co_teachers == ["周蓁妍"]
    form2._apply_slot("a", slot)
    assert "協作調課" in form2.co_warn.value

    # 選到不是協同課的節次就不該有警告
    form.ta.field.value = "王小明"
    form.da.field.value = "2026-09-08"
    form.pa.value = "1"
    form._sync()
    assert form.co_warn.value == ""
