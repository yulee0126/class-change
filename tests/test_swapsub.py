"""先調再代：一次產生 1 筆調課 + 1 筆代課，教師單調課列在前、代課列在後。"""

import datetime

from tiaoke.builder import ClassSlip, TeacherSlip, build
from tiaoke.models import SubLeg, SwapLeg
from tiaoke.ui.controller import AppController

D = datetime.date


def _ctl():
    c = AppController()
    c.new_event()
    c.update_event_fields(originator="劉炆明", form_no="手動", leave_type="請假")
    c.add_swap_then_sub(
        klass="二丁應", teacher_a="劉炆明", subject_a="經濟學",
        date_a=D(2026, 8, 31), period_a=1,
        teacher_b="郭惠茹", subject_b="班週會",
        date_b=D(2026, 9, 2), period_b=5,
        sub_teacher="郭惠茹",
    )
    return c


def test_creates_swap_and_sub():
    c = _ctl()
    legs = c.current.legs
    assert [type(l).__name__ for l in legs] == ["SwapLeg", "SubLeg"]
    sub = legs[1]
    assert isinstance(sub, SubLeg)
    assert sub.from_swap is True
    assert sub.orig_teacher == "劉炆明"
    assert sub.subject == "經濟學"                 # 甲的科目
    assert sub.slot == legs[0].slot_b               # 調到乙的時段那一節
    assert sub.sub_teacher == "郭惠茹"


def test_teacher_slip_orders_swap_before_sub():
    slips = build(_ctl().current)
    liu = next(s for s in slips if isinstance(s, TeacherSlip) and s.teacher == "劉炆明")
    kinds = ["調課" if (r.new and r.orig) else "代課" for r in liu.rows]
    assert kinds == sorted(kinds, key=lambda k: k == "代課")  # 調課全在前
    assert kinds[0] == "調課" and kinds[-1] == "代課"


def test_class_slip_orders_swap_before_sub():
    slips = build(_ctl().current)
    cls = next(s for s in slips if isinstance(s, ClassSlip))
    subflags = [r.is_sub for r in cls.rows]
    assert subflags == sorted(subflags)  # False(調課) 在前、True(代課) 在後
