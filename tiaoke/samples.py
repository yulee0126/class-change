"""從範例檔重建的事件，供煙霧測試與回歸測試使用。"""

from __future__ import annotations

import datetime as _dt

from .models import Event, Slot, SubLeg, SwapLeg

_D = _dt.date


def _ev_ruiwen_1150223() -> Event:
    """瑞文1150223：余瑞文與 3 位導師分別對調（一對多對調）。"""
    return Event(
        originator="余瑞文",
        leave_type="其他",
        form_no="手動",
        announce_date=_D(2026, 2, 13),
        sheet_date=_D(2026, 2, 23),
        legs=[
            SwapLeg("高一甲", "余瑞文", "健康與護理", Slot(_D(2026, 2, 23), 1),
                    "洪瑞霞", "班、週會", Slot(_D(2026, 2, 25), 5)),
            SwapLeg("高一乙", "余瑞文", "健康與護理", Slot(_D(2026, 2, 23), 2),
                    "林志嘉", "班、週會", Slot(_D(2026, 2, 25), 6)),
            SwapLeg("加工一", "余瑞文", "健康與護理", Slot(_D(2026, 2, 23), 3),
                    "陳凱如", "班、週會", Slot(_D(2026, 2, 25), 7)),
        ],
    )


def _ev_daike_example() -> Event:
    """範例2 型：吳建勳公假，謝欣瑜代課。"""
    return Event(
        originator="吳建勳",
        leave_type="公假",
        form_no="手動+1279",
        announce_date=_D(2022, 1, 19),
        legs=[
            SubLeg("工三", "吳建勳", "食品檢驗分析", Slot(_D(2022, 1, 19), 4), "謝欣瑜"),
        ],
    )


def _ev_ruoye_1150226() -> Event:
    """若耶1150226：陳若耶與蔡文華對調，含說明。"""
    return Event(
        originator="陳若耶",
        leave_type="公假",
        form_no="2015+手動",
        announce_date=_D(2026, 2, 23),
        sheet_date=_D(2026, 2, 26),
        note=("2/25(三)第5節課務與2/26(四)第5節課務互調，"
              "故陳若耶老師上2/25(三)第5節，蔡文華老師上2/26(四)第5節。"),
        legs=[
            SwapLeg("高三甲", "陳若耶", "國語文", Slot(_D(2026, 2, 26), 5),
                    "蔡文華", "民主政治與法律", Slot(_D(2026, 2, 25), 5)),
        ],
    )


def _ev_wenming_1150831() -> Event:
    """炆明1150831（簡化）：對調 + 多人代課混合。"""
    return Event(
        originator="劉炆明",
        leave_type="請假",
        form_no="手動",
        announce_date=_D(2026, 8, 25),
        sheet_date=_D(2026, 8, 31),
        class_slip_style="banner",
        legs=[
            SwapLeg("二丁應", "劉炆明", "經濟學", Slot(_D(2026, 8, 31), 1),
                    "郭惠茹", "班週會", Slot(_D(2026, 9, 2), 5)),
            SwapLeg("二丁應", "劉炆明", "經濟學", Slot(_D(2026, 8, 31), 2),
                    "郭惠茹", "班週會", Slot(_D(2026, 9, 2), 6)),
            SwapLeg("三丁應", "劉炆明", "行銷實務", Slot(_D(2026, 8, 31), 3),
                    "黃子玟", "班週會", Slot(_D(2026, 9, 2), 7)),
            SubLeg("三丁應", "劉炆明", "經濟學補強", Slot(_D(2026, 8, 31), 4), "徐惠珠"),
            SubLeg("二丁應", "劉炆明", "經濟學", Slot(_D(2026, 9, 2), 5), "郭惠茹", from_swap=True),
            SubLeg("二丁應", "劉炆明", "經濟學", Slot(_D(2026, 9, 2), 6), "郭惠茹", from_swap=True),
            SubLeg("三丁應", "劉炆明", "行銷實務", Slot(_D(2026, 9, 2), 7), "黃子玟", from_swap=True),
        ],
    )


SAMPLES: dict[str, "callable[[], Event]"] = {
    "瑞文1150223": _ev_ruiwen_1150223,
    "代課範例": _ev_daike_example,
    "若耶1150226": _ev_ruoye_1150226,
    "炆明1150831": _ev_wenming_1150831,
}


def get(name: str) -> Event:
    return SAMPLES[name]()


def all_events() -> list[tuple[str, Event]]:
    return [(name, factory()) for name, factory in SAMPLES.items()]
