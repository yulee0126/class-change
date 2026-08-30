"""一鍵打包成可攜資料夾。

用法（在 class-change 下）：
    pip install pyinstaller flet-cli
    python build.py

產出：../調課代課產生器/  （exe + record/ + 使用說明.txt），整包可複製到別台電腦。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)                       # 調課代課程式
DIST = os.path.join(PROJECT, "調課代課產生器")         # 交付資料夾
NAME = "調課代課產生器"


def _cmap_dir() -> str:
    import pdfminer
    return os.path.join(os.path.dirname(pdfminer.__file__), "cmap")


def main() -> int:
    print("== 跑測試 ==")
    if subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=HERE) != 0:
        print("測試沒過，停止。")
        return 1

    for d in ("build", "build_out"):
        shutil.rmtree(os.path.join(HERE, d), ignore_errors=True)
    for f in os.listdir(HERE):
        if f.endswith(".spec"):
            os.remove(os.path.join(HERE, f))

    print("== flet pack ==")
    cmd = [
        "flet", "pack", "main.py",
        "--name", NAME,
        "--icon", "assets/icon.ico",
        "--product-name", "調課代課通知單產生器",
        "--company-name", "關西高中",
        "--add-data", "assets:assets",
        "--add-data", f"{_cmap_dir()}:pdfminer/cmap",
        "--hidden-import", "pdfplumber",
        "--distpath", "build_out",
        "-y",
    ]
    if subprocess.call(cmd, cwd=HERE) != 0:
        return 2

    exe = os.path.join(HERE, "build_out", f"{NAME}.exe")
    if not os.path.exists(exe):
        print("找不到產出的 exe")
        return 3

    print(f"== 組裝交付資料夾 {DIST} ==")
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(os.path.join(DIST, "record"), exist_ok=True)
    shutil.copy2(exe, DIST)

    src_record = os.path.join(PROJECT, "record")
    if os.path.isdir(src_record):
        for f in os.listdir(src_record):
            if f.endswith((".xlsx", ".md")) and not f.startswith("~$"):
                shutil.copy2(os.path.join(src_record, f), os.path.join(DIST, "record"))

    readme = os.path.join(DIST, "使用說明.txt")
    if not os.path.exists(readme):
        shutil.copy2(os.path.join(PROJECT, "調課代課產生器", "使用說明.txt"), readme) \
            if os.path.exists(os.path.join(PROJECT, "調課代課產生器", "使用說明.txt")) else None

    print(f"\n完成 → {DIST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
