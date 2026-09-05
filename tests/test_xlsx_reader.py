import datetime
import os

import openpyxl
import pytest

from tiaoke import output, samples
from tiaoke.models import SubLeg, SwapLeg
from tiaoke.ui.controller import AppController
from tiaoke.xlsx_reader import ParseError, read_event, read_events
from tiaoke.xlsx_writer import write_sheet

D = datetime.date


def _write(event, path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = event.sheet_name
    write_sheet(ws, event)
    wb.save(path)


def _leg_set(legs):
    """轉成可比較、不受順序影響的集合。"""
    out = set()
    for leg in legs:
        if isinstance(leg, SwapLeg):
            # teacher_a/teacher_b 的順序在還原時不保證跟原本一樣，兩種都收進來比對其一即可
            out.add(("swap", leg.klass, frozenset([
                (leg.teacher_a, leg.subject_a, leg.slot_a),
                (leg.teacher_b, leg.subject_b, leg.slot_b),
            ])))
        else:
            out.add(("sub", leg.klass, leg.orig_teacher, leg.subject, leg.slot,
                     leg.sub_teacher, leg.from_swap))
    return out


@pytest.mark.parametrize("name", list(samples.SAMPLES))
def test_round_trip_all_samples(name, tmp_path):
    ev = samples.get(name)
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))

    back = read_event(str(path))
    assert back.originator == ev.originator
    assert back.leave_type == ev.leave_type
    assert back.form_no == ev.form_no
    assert back.announce_date == ev.announce_date
    assert back.class_slip_style == ev.class_slip_style
    assert back.sheet_name_override == ev.sheet_name
    assert _leg_set(back.legs) == _leg_set(ev.legs)


def test_round_trip_preserves_note(tmp_path):
    ev = samples.get("若耶1150226")
    assert ev.note
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))
    back = read_event(str(path))
    assert back.note == ev.note


def test_hand_edited_note_text_does_not_break_parsing(tmp_path):
    """使用者手改教師單備註欄（附註、合併姓名）不影響結構化還原。"""
    ev = samples.get("炆明1150831")
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    edited = 0
    for row in ws.iter_rows():
        cell = row[8]  # I 欄＝備註
        if isinstance(cell.value, str) and cell.value.endswith("調課"):
            cell.value = cell.value + "\n(蓁妍同步調)"
            edited += 1
    assert edited > 0
    wb.save(path)

    back = read_event(str(path))
    assert _leg_set(back.legs) == _leg_set(ev.legs)


def test_from_swap_flag_recovered_from_highlight_fill(tmp_path):
    ev = samples.get("炆明1150831")
    hl_subs = [l for l in ev.legs if isinstance(l, SubLeg) and l.from_swap]
    assert hl_subs  # 樣本本身要有這種列，測試才有意義

    path = tmp_path / "x.xlsx"
    _write(ev, str(path))
    back = read_event(str(path))
    recovered = [l for l in back.legs if isinstance(l, SubLeg) and l.from_swap]
    assert len(recovered) == len(hl_subs)


def test_read_events_multi_sheet(tmp_path):
    events = [samples.get("瑞文1150223"), samples.get("代課範例")]
    path = tmp_path / "all.xlsx"
    output.export_all(events, str(path))

    results = read_events(str(path))
    assert len(results) == 2
    names = {name for name, ev, err in results}
    assert names == {ev.sheet_name for ev in events}
    assert all(err == "" and ev is not None for _n, ev, err in results)


def test_unmatched_swap_side_raises_parse_error(tmp_path):
    """故意弄壞一份對調單（刪掉對方那張教師單），該有配不出來的錯誤。"""
    ev = samples.get("瑞文1150223")
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))

    wb = openpyxl.load_workbook(path)
    ws = wb.active
    del wb[ws.title]
    ws2 = wb.create_sheet(ws.title)
    # 只搬「余瑞文」那張教師單（第一張），把其餘對方老師的單跟班級單都丟掉
    for row in ws.iter_rows(min_row=1, max_row=6):
        for cell in row:
            ws2.cell(cell.row, cell.column, cell.value)
            if cell.fill and cell.fill.patternType:
                ws2.cell(cell.row, cell.column).fill = cell.fill
    wb.save(path)

    with pytest.raises(ParseError, match="配不出"):
        read_event(str(path))


def test_missing_banner_raises_parse_error(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws["A1"] = "不是通知單"
    path = tmp_path / "x.xlsx"
    wb.save(path)
    with pytest.raises(ParseError):
        read_event(str(path))


# ==========================================================================
# controller：搜尋既有檔案 / 讀回編輯 / 存回 / 產製報表
# ==========================================================================

def test_list_slip_files_sorted_newest_first_and_skips_lock_files(tmp_path):
    c = AppController()
    _write(samples.get("代課範例"), str(tmp_path / "a.xlsx"))
    os.utime(tmp_path / "a.xlsx", (1000, 1000))
    _write(samples.get("瑞文1150223"), str(tmp_path / "b.xlsx"))
    os.utime(tmp_path / "b.xlsx", (2000, 2000))
    (tmp_path / "~$a.xlsx").write_text("lock")
    (tmp_path / "notes.txt").write_text("x")

    names = c.list_slip_files(str(tmp_path))
    assert names == ["b.xlsx", "a.xlsx"]
    assert c.list_slip_files(str(tmp_path / "不存在")) == []
    assert c.list_slip_files("") == []


def test_load_event_from_file_adds_and_selects_event(tmp_path):
    ev = samples.get("代課範例")
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))

    c = AppController()
    c.new_event()  # 原本已經有一張在編輯
    loaded = c.load_event_from_file(str(path))
    assert c.current is loaded
    assert loaded.originator == ev.originator
    assert getattr(loaded, "_source_path") == str(path)


def test_resave_loaded_file_same_path_overwrites(tmp_path):
    ev = samples.get("代課範例")
    path = tmp_path / "x.xlsx"
    _write(ev, str(path))

    c = AppController()
    c.load_event_from_file(str(path))
    result = c.resave_loaded_file(str(path))
    assert result.ok
    assert os.path.exists(path)
    assert getattr(c.current, "_source_path") == str(path)


def test_resave_loaded_file_new_name_deletes_old(tmp_path):
    ev = samples.get("代課範例")
    old_path = tmp_path / "old.xlsx"
    new_path = tmp_path / "new.xlsx"
    _write(ev, str(old_path))

    c = AppController()
    c.load_event_from_file(str(old_path))
    result = c.resave_loaded_file(str(new_path))
    assert result.ok
    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)
    assert getattr(c.current, "_source_path") == str(new_path)


def test_generate_report_scans_folder_and_skips_marked_files(tmp_path):
    folder = tmp_path / "調代課單"
    folder.mkdir()
    _write(samples.get("代課範例"), str(folder / "1001-x.xlsx"))
    _write(samples.get("瑞文1150223"), str(folder / "1002-y.xlsx"))
    # 作廢檔（~~ 前綴）跟 Excel 鎖檔（~$ 前綴）都該略過
    _write(samples.get("炆明1150831"), str(folder / "~~1003-作廢.xlsx"))
    (folder / "~$1001-x.xlsx").write_text("lock")
    (folder / "說明.txt").write_text("not excel")

    out_folder = tmp_path / "record"
    c = AppController()
    rep = c.generate_report(str(folder), str(out_folder))

    assert rep.ok
    assert rep.files_ok == 2          # 只有 1001、1002 被算進去
    assert not rep.files_failed
    assert os.path.exists(rep.path)
    assert os.path.dirname(rep.path) == str(out_folder)
    assert "調代課記錄-" in os.path.basename(rep.path)

    wb = openpyxl.load_workbook(rep.path)
    detail = [r for r in wb["調代課明細"].iter_rows(min_row=2, values_only=True) if r[0]]
    assert len(detail) == rep.rows
    assert rep.rows == 1 + 6  # 代課範例 1 列（代課）+ 瑞文1150223 三筆對調各 2 列 = 6 列


def test_generate_report_reports_unparseable_files_without_crashing(tmp_path):
    folder = tmp_path / "調代課單"
    folder.mkdir()
    _write(samples.get("代課範例"), str(folder / "good.xlsx"))
    (folder / "bad.xlsx").write_bytes(b"not a real xlsx file")

    c = AppController()
    rep = c.generate_report(str(folder), str(tmp_path / "record"))
    assert rep.ok
    assert rep.files_ok == 1
    assert any("bad.xlsx" in f for f in rep.files_failed)


def test_generate_report_no_folder():
    c = AppController()
    rep = c.generate_report("", "")
    assert not rep.ok
    assert "資料夾" in rep.error
