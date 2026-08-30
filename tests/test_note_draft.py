from tiaoke import note_draft, samples


def test_swap_summary():
    text = note_draft.draft(samples.get("瑞文1150223"))
    assert text == "2/23(一)第1、2、3節課務與2/25(三)第5、6、7節課務互調。"


def test_swap_plus_sub():
    text = note_draft.draft(samples.get("炆明1150831"))
    assert "8/31(一)第1、2、3節課務與9/2(三)第5、6、7節課務互調" in text
    assert "8/31(一)第4節由徐惠珠老師代課" in text
    assert "9/2(三)第5、6節由郭惠茹老師代課" in text
    assert "9/2(三)第7節由黃子玟老師代課" in text
    assert text.endswith("。")


def test_sub_only():
    text = note_draft.draft(samples.get("代課範例"))
    assert text == "1/19(三)第4節由謝欣瑜老師代課。"


def test_empty_when_no_legs():
    from tiaoke.models import Event
    import datetime
    ev = Event("甲", "其他", "手動", datetime.date(2026, 1, 1))
    assert note_draft.draft(ev) == ""
