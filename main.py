"""調課代課通知單產生器 —— 桌面 GUI 進入點。

執行：
    python main.py
"""

import flet as ft

from tiaoke.ui.app import main

if __name__ == "__main__":
    # Flet >=0.80 用 run()；舊版 fallback 到 app()
    run = getattr(ft, "run", None) or ft.app
    run(main)
