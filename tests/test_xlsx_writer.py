import io

import openpyxl
import pytest

from tiaoke import output, samples
from tiaoke.xlsx_writer import write_sheet


def _render(event) -> openpyxl.worksheet.worksheet.Worksheet:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = event.sheet_name
    write_sheet(ws, event)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return openpyxl.load_workbook(buf).active


def _find(ws, text):
    return [c.coordinate for row in ws.iter_rows() for c in row
            if isinstance(c.value, str) and text in c.value]


def test_sheet_basic_shape():
    ws = _render(samples.get("瑞文1150223"))
    assert ws.title == "瑞文1150223"
    # 欄寬取自「範例1」
    assert ws.column_dimensions["I"].width == pytest.approx(17.91)
    assert ws.column_dimensions["A"].width == pytest.approx(12.27)
    assert ws.column_dimensions["E"].width == pytest.approx(13.0)
    assert ws.print_area in ("A1:I%d" % ws.max_row, "'瑞文1150223'!$A$1:$I$%d" % ws.max_row)


def test_banner_and_announce_text():
    ws = _render(samples.get("瑞文1150223"))
    assert _find(ws, "教  師  調  代  課  通  知  單 假單編號：手動  余瑞文 其他")
    assert _find(ws, "公告日期：115年")
    assert _find(ws, "02月13日")


def test_dates_stored_as_datetime_with_format():
    ws = _render(samples.get("瑞文1150223"))
    date_cells = [c for row in ws.iter_rows() for c in row
                  if c.number_format == 'm"月"d"日"']
    assert date_cells
    for c in date_cells:
        assert hasattr(c.value, "year")  # 真正的日期物件，不是字串


def test_note_row_present_only_when_note_set():
    with_note = _render(samples.get("若耶1150226"))
    assert _find(with_note, "說明:")
    without = _render(samples.get("瑞文1150223"))
    assert not _find(without, "說明:")


def test_class_slip_footer():
    ws = _render(samples.get("瑞文1150223"))
    assert _find(ws, "* 請學藝股長公佈。")


def test_merged_regions_exist():
    ws = _render(samples.get("瑞文1150223"))
    merged = {str(r) for r in ws.merged_cells.ranges}
    assert "B1:I1" in merged           # 教師單橫幅
    assert any(m.startswith("E2:E3") for m in merged)  # 授課科目


def test_write_to_master_creates_then_replaces(tmp_path):
    master = tmp_path / "master.xlsx"
    ev = samples.get("瑞文1150223")

    r1 = output.write_to_master(ev, str(master))
    assert r1.ok and not r1.replaced_sheet
    assert master.exists()

    r2 = output.write_to_master(ev, str(master))
    assert r2.ok and r2.replaced_sheet

    wb = openpyxl.load_workbook(master)
    assert wb.sheetnames.count("瑞文1150223") == 1


def test_run_requires_a_target():
    with pytest.raises(ValueError):
        output.run(samples.get("瑞文1150223"))


def test_run_both_targets(tmp_path):
    master = tmp_path / "m.xlsx"
    new = tmp_path / "n.xlsx"
    results = output.run(
        samples.get("代課範例"),
        to_master=True, master_path=str(master),
        save_new=True, dest_path=str(new),
    )
    assert len(results) == 2
    assert all(r.ok for r in results)
    assert master.exists() and new.exists()
