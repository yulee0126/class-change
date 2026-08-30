"""專案存讀（.json）與應用設定。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .models import Event, Project, event_from_dict, event_to_dict

PROJECT_FORMAT = 1


# --------------------------------------------------------------------------
# 專案 .json
# --------------------------------------------------------------------------

def project_to_dict(p: Project) -> dict:
    return {
        "format": PROJECT_FORMAT,
        "master_path": p.master_path,
        "teachers": p.teachers,
        "classes": p.classes,
        "subjects": p.subjects,
        "events": [event_to_dict(ev) for ev in p.events],
    }


def project_from_dict(d: dict) -> Project:
    return Project(
        events=[event_from_dict(x) for x in d.get("events", [])],
        teachers=list(d.get("teachers", [])),
        classes=list(d.get("classes", [])),
        subjects=list(d.get("subjects", [])),
        master_path=d.get("master_path", ""),
    )


def save_project(project: Project, path: str) -> None:
    path = _ensure_ext(path, ".json")
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(project_to_dict(project), fh, ensure_ascii=False, indent=2)


def load_project(path: str) -> Project:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return project_from_dict(data)


# --------------------------------------------------------------------------
# 課表 .json
# --------------------------------------------------------------------------

def save_timetable(tt, path: str) -> str:
    path = _ensure_ext(path, ".json")
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(tt.to_dict(), fh, ensure_ascii=False, indent=1)
    return path


def load_timetable(path: str):
    from .timetable import Timetable
    with open(path, "r", encoding="utf-8") as fh:
        return Timetable.from_dict(json.load(fh))


# --------------------------------------------------------------------------
# 應用設定
# --------------------------------------------------------------------------

def _config_dir() -> Path:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = Path(base) / "tiaoke"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class AppSettings:
    last_project: str = ""
    default_master_path: str = ""
    default_class_slip_style: str = "banner"
    timetable_path: str = ""
    window_width: int = 1180
    window_height: int = 820
    recent_projects: list[str] = field(default_factory=list)

    # ---- 存讀 ----
    @classmethod
    def path(cls) -> Path:
        return _config_dir() / "settings.json"

    @classmethod
    def load(cls) -> "AppSettings":
        p = cls.path()
        if not p.exists():
            return cls()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return cls()
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    def save(self) -> None:
        self.path().write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def note_recent(self, project_path: str, limit: int = 8) -> None:
        if not project_path:
            return
        project_path = os.path.abspath(project_path)
        self.recent_projects = [project_path] + [
            p for p in self.recent_projects if p != project_path
        ]
        self.recent_projects = self.recent_projects[:limit]
        self.last_project = project_path


def _ensure_ext(path: str, ext: str) -> str:
    return path if path.lower().endswith(ext) else path + ext
