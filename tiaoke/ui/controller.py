"""GUI 與核心邏輯之間的控制層。純 Python、無 Flet 相依，可單元測試。

GUI 只負責把畫面欄位讀進來組成 dict，交給這裡的方法；
這裡負責建立/修改 Event、驗證、預覽、輸出。
"""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field

from .. import note_draft, output
from ..builder import ClassSlip, TeacherSlip, build, validate
from ..models import (CLASS_SLIP_STYLES, LEAVE_TYPES, Event, Project, Slot,
                      SubLeg, SwapLeg)

DEFAULT_FORM_NO = "手動+"


@dataclass
class SlipPreview:
    kind: str          # "教師單" | "班級單"
    title: str         # 老師姓名 or 班級
    row_count: int


@dataclass
class PreviewResult:
    slips: list[SlipPreview] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def teacher_count(self) -> int:
        return sum(s.kind == "教師單" for s in self.slips)

    @property
    def class_count(self) -> int:
        return sum(s.kind == "班級單" for s in self.slips)


class AppController:
    def __init__(self, project: Project | None = None) -> None:
        self.project = project or Project()
        self.current_index: int | None = None
        if self.project.events:
            self.current_index = 0

    # ---- 事件清單 ------------------------------------------------------
    @property
    def current(self) -> Event | None:
        if self.current_index is None:
            return None
        return self.project.events[self.current_index]

    def event_titles(self) -> list[str]:
        return [ev.sheet_name for ev in self.project.events]

    def new_event(self) -> Event:
        today = datetime.date.today()
        ev = Event(
            originator="",
            leave_type=LEAVE_TYPES[0],
            form_no=DEFAULT_FORM_NO,
            announce_date=today,
            sheet_date=None,
        )
        self.project.events.append(ev)
        self.current_index = len(self.project.events) - 1
        return ev

    def duplicate_event(self) -> Event | None:
        if self.current is None:
            return None
        import copy
        ev = copy.deepcopy(self.current)
        self.project.events.append(ev)
        self.current_index = len(self.project.events) - 1
        return ev

    def delete_event(self) -> None:
        if self.current_index is None:
            return
        self.project.events.pop(self.current_index)
        if not self.project.events:
            self.current_index = None
        else:
            self.current_index = min(self.current_index, len(self.project.events) - 1)

    def select_event(self, index: int) -> None:
        if 0 <= index < len(self.project.events):
            self.current_index = index

    # ---- 事件欄位 ----------------------------------------------------
    def update_event_fields(self, *, originator: str | None = None,
                            leave_type: str | None = None, form_no: str | None = None,
                            announce_date: datetime.date | None = None,
                            sheet_date: datetime.date | None = ...,  # type: ignore[assignment]
                            note: str | None = None,
                            class_slip_style: str | None = None,
                            sheet_name_override: str | None = ...) -> None:  # type: ignore[assignment]
        ev = self.current
        if ev is None:
            return
        if originator is not None:
            ev.originator = originator
        if leave_type is not None:
            ev.leave_type = leave_type
        if form_no is not None:
            ev.form_no = form_no
        if announce_date is not None:
            ev.announce_date = announce_date
        if sheet_date is not ...:
            ev.sheet_date = sheet_date
        if note is not None:
            ev.note = note
        if class_slip_style in CLASS_SLIP_STYLES:
            ev.class_slip_style = class_slip_style
        if sheet_name_override is not ...:
            ev.sheet_name_override = sheet_name_override or None

    # ---- 腳 --------------------------------------------------------
    def add_swap_leg(self, *, klass: str, teacher_a: str, subject_a: str,
                     date_a: datetime.date, period_a: int,
                     teacher_b: str, subject_b: str,
                     date_b: datetime.date, period_b: int) -> None:
        ev = self._require_event()
        ev.legs.append(SwapLeg(
            klass=klass.strip(),
            teacher_a=teacher_a.strip(), subject_a=subject_a.strip(),
            slot_a=Slot(date_a, int(period_a)),
            teacher_b=teacher_b.strip(), subject_b=subject_b.strip(),
            slot_b=Slot(date_b, int(period_b)),
        ))
        self._learn_names(klass, [teacher_a, teacher_b], [subject_a, subject_b])

    def add_sub_leg(self, *, klass: str, orig_teacher: str, subject: str,
                    date: datetime.date, period: int, sub_teacher: str) -> None:
        ev = self._require_event()
        ev.legs.append(SubLeg(
            klass=klass.strip(),
            orig_teacher=orig_teacher.strip(), subject=subject.strip(),
            slot=Slot(date, int(period)), sub_teacher=sub_teacher.strip(),
        ))
        self._learn_names(klass, [orig_teacher, sub_teacher], [subject])

    def add_sub_batch(self, *, orig_teacher: str,
                      items: list[dict]) -> int:
        """批次代課：items = [{klass, subject, date, period, sub_teacher}, ...]。"""
        for it in items:
            self.add_sub_leg(orig_teacher=orig_teacher, **it)
        return len(items)

    def remove_leg(self, index: int) -> None:
        ev = self.current
        if ev and 0 <= index < len(ev.legs):
            ev.legs.pop(index)

    def leg_summaries(self) -> list[str]:
        ev = self.current
        if not ev:
            return []
        out = []
        for leg in ev.legs:
            if isinstance(leg, SwapLeg):
                out.append(
                    f"調課　{leg.klass}｜{leg.teacher_a}/{leg.subject_a} {leg.slot_a} "
                    f"↔ {leg.teacher_b}/{leg.subject_b} {leg.slot_b}"
                )
            else:
                out.append(
                    f"代課　{leg.klass}｜{leg.orig_teacher}/{leg.subject} {leg.slot} "
                    f"→ {leg.sub_teacher} 代"
                )
        return out

    # ---- 說明草稿 -------------------------------------------------
    def make_note_draft(self) -> str:
        ev = self.current
        return note_draft.draft(ev) if ev else ""

    # ---- 預覽 / 驗證 ---------------------------------------------
    def preview(self) -> PreviewResult:
        ev = self.current
        if ev is None:
            return PreviewResult(problems=["尚未選擇事件。"])
        res = PreviewResult(problems=validate(ev))
        if ev.legs:
            for slip in build(ev):
                if isinstance(slip, TeacherSlip):
                    res.slips.append(SlipPreview("教師單", slip.teacher, len(slip.rows)))
                elif isinstance(slip, ClassSlip):
                    res.slips.append(SlipPreview("班級單", slip.klass, len(slip.rows)))
        return res

    # ---- 輸出 ---------------------------------------------------
    def default_new_path(self) -> str:
        ev = self.current
        if ev is None:
            return ""
        folder = os.path.dirname(self.project.master_path) if self.project.master_path else os.getcwd()
        return os.path.join(folder, f"{ev.sheet_name}.xlsx")

    def generate(self, *, to_master: bool, save_new: bool,
                 master_path: str = "", dest_path: str = "") -> list[output.TargetResult]:
        ev = self._require_event()
        problems = [p for p in validate(ev) if "未填" in p or "超出範圍" in p or "無法對調" in p]
        if problems:
            raise ValueError("請先修正：\n- " + "\n- ".join(problems))
        if to_master and master_path:
            self.project.master_path = master_path
        return output.run(
            ev,
            to_master=to_master, master_path=master_path,
            save_new=save_new, dest_path=dest_path,
        )

    # ---- 內部 -------------------------------------------------
    def _require_event(self) -> Event:
        if self.current is None:
            self.new_event()
        assert self.current is not None
        return self.current

    def _learn_names(self, klass: str, teachers: list[str], subjects: list[str]) -> None:
        p = self.project
        if klass.strip() and klass.strip() not in p.classes:
            p.classes.append(klass.strip())
        for t in teachers:
            if t.strip() and t.strip() not in p.teachers:
                p.teachers.append(t.strip())
        for s in subjects:
            if s.strip() and s.strip() not in p.subjects:
                p.subjects.append(s.strip())
