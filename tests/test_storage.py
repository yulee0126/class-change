import datetime

from tiaoke import samples, storage
from tiaoke.models import Project
from tiaoke.ui.controller import AppController

D = datetime.date


def test_project_round_trip(tmp_path):
    proj = Project(events=[samples.get("瑞文1150223"), samples.get("炆明1150831")])
    proj.merge_master_data()
    path = tmp_path / "p.json"
    storage.save_project(proj, str(path))
    assert path.exists()

    back = storage.load_project(str(path))
    assert len(back.events) == 2
    assert back.events[0].sheet_name == "瑞文1150223"
    assert back.events[1].legs[0].__class__.__name__ == "SwapLeg"
    assert set(back.teachers) >= {"余瑞文", "洪瑞霞", "劉炆明"}
    # 事件內容一致
    ev = back.events[0]
    assert ev.legs[0].slot_a == proj.events[0].legs[0].slot_a


def test_save_project_adds_extension(tmp_path):
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="余瑞文")
    rep = c.save_project(str(tmp_path / "myproj"))
    assert rep.path.endswith(".json")
    assert (tmp_path / "myproj.json").exists()


def test_save_project_merges_and_dedupes(tmp_path):
    db = str(tmp_path / "db.json")

    c1 = AppController()
    c1.project.events = [samples.get("瑞文1150223")]
    r1 = c1.save_project(db)
    assert (r1.added, r1.updated, r1.unchanged) == (1, 0, 0)

    # 同一筆再存一次 → 重複略過
    c2 = AppController()
    c2.load_project(db)
    r2 = c2.save_project(db)
    assert (r2.added, r2.updated, r2.unchanged) == (0, 0, 1)

    # 新的一筆 → 只新增，不動舊的
    c3 = AppController()
    c3.load_project(db)
    c3.new_event()
    c3.update_event_fields(originator="王大明")
    c3.add_sub_leg(klass="高一甲", orig_teacher="王大明", subject="數學",
                   date=D(2026, 9, 2), period=3, sub_teacher="李小華")
    r3 = c3.save_project(db)
    assert r3.added == 1 and r3.updated == 0
    assert len(c3.project.events) == 2

    # 改內容再存 → 更新
    ev = next(e for e in c3.project.events if e.originator == "王大明")
    ev.note = "改一下"
    r4 = c3.save_project(db)
    assert r4.updated == 1 and r4.added == 0


def test_load_project_into_controller(tmp_path):
    proj = Project(events=[samples.get("代課範例")])
    path = tmp_path / "p.json"
    storage.save_project(proj, str(path))

    c = AppController()
    c.load_project(str(path))
    assert c.current is not None
    assert c.current.originator == "吳建勳"
    assert c.current_index == 0


def test_settings_load_missing_is_default(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    s = storage.AppSettings.load()
    assert s.window_width == 1180
    s.note_recent(str(tmp_path / "a.json"))
    s.save()
    s2 = storage.AppSettings.load()
    assert s2.recent_projects and s2.last_project.endswith("a.json")


def test_master_data_edit_via_controller():
    c = AppController()
    c.add_master("teacher", "王小明")
    c.add_master("teacher", "王小明")  # 不重複
    c.add_master("class", "高一甲")
    assert c.project.teachers == ["王小明"]
    c.remove_master("teacher", "王小明")
    assert c.project.teachers == []
