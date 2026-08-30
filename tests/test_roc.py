import datetime

from tiaoke import roc


def test_roc_year():
    assert roc.roc_year(datetime.date(2026, 2, 23)) == 115
    assert roc.roc_year(datetime.date(2021, 11, 5)) == 110


def test_weekday_cn():
    # 2026-02-23 是週一
    assert roc.weekday_cn(datetime.date(2026, 2, 23)) == "一"
    assert roc.weekday_cn(datetime.date(2026, 2, 25)) == "三"
    assert roc.weekday_cn(datetime.date(2026, 2, 26)) == "四"


def test_announce_strings():
    d = datetime.date(2026, 2, 13)
    assert roc.announce_md(d) == "02月13日"
    assert roc.announce_line(d) == "公告日期：115年"


def test_slot_label():
    assert roc.slot_label(datetime.date(2026, 8, 31), 5) == "8/31(一)第5節"


def test_short_name_and_sheet_code():
    assert roc.short_name("余瑞文") == "瑞文"
    assert roc.short_name("王二") == "王二"
    assert roc.sheet_code("余瑞文", datetime.date(2026, 2, 23)) == "瑞文1150223"
    assert roc.sheet_code("劉炆明", datetime.date(2026, 8, 31)) == "炆明1150831"
