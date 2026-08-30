"""可攜路徑：打包成 exe 後，一切檔案都放在 exe 旁邊的資料夾，
整個 build 資料夾可以複製到別台電腦直接用。"""

from __future__ import annotations

import os
import sys


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_dir() -> str:
    """打包後＝exe 所在資料夾；開發時＝專案上層資料夾（調課代課程式）。"""
    if is_frozen():
        return os.path.dirname(sys.executable)
    # tiaoke/paths.py → 上三層 = 調課代課程式
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def record_dir() -> str:
    d = os.path.join(app_dir(), "record")
    os.makedirs(d, exist_ok=True)
    return d


def default_db_path() -> str:
    return os.path.join(app_dir(), "調代課資料庫.json")


def default_timetable_path() -> str:
    """exe 旁邊若有課表 JSON 就回傳它，否則空字串。"""
    for name in os.listdir(app_dir()) if os.path.isdir(app_dir()) else []:
        if name.endswith(".json") and "課表" in name:
            return os.path.join(app_dir(), name)
    return ""


def settings_path() -> str:
    """打包後放 exe 旁；開發時放 %APPDATA%\\tiaoke。"""
    if is_frozen():
        return os.path.join(app_dir(), "settings.json")
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "tiaoke")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "settings.json")
