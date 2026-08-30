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
    saved = c.save_project(str(tmp_path / "myproj"))
    assert saved.endswith(".json")
    assert (tmp_path / "myproj.json").exists()


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
