"""GUI 與核心邏輯之間的控制層。純 Python、無 Flet 相依，可單元測試。

GUI 只負責把畫面欄位讀進來組成 dict，交給這裡的方法；
這裡負責建立/修改 Event、驗證、預覽、輸出。
"""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass, field

from .. import models, note_draft, output, record, storage
from ..builder import ClassSlip, TeacherSlip, build, validate
from ..models import (CLASS_SLIP_STYLES, LEAVE_TYPES, Event, Project, Slot,
                      SubLeg, SwapLeg)

DEFAULT_FORM_NO = "手動+"


@dataclass
class SaveReport:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    path: str = ""

    def __str__(self) -> str:
        bits = []
        if self.added:
            bits.append(f"新增 {self.added}")
        if self.updated:
            bits.append(f"更新 {self.updated}")
        if self.unchanged:
            bits.append(f"重複略過 {self.unchanged}")
        return "、".join(bits) or "無變更"


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
        self.project_path: str = ""
        self.timetable = None          # tiaoke.timetable.Timetable | None
        self._pending_tt = None
        self.record_folder: str = ""
        self.last_record: record.RecordReport | None = None
        if self.project.events:
            self.current_index = 0

    # ---- 課表 ----------------------------------------------------
    def parse_timetable_pdf(self, pdf_path: str):
        """讀 PDF，暫存解析結果（尚未套用），回傳 Timetable 供顯示摘要。"""
        from .. import timetable as _tt
        self._pending_tt = _tt.parse_pdf(pdf_path)
        return self._pending_tt

    def apply_pending_timetable(self, save_path: str | None = None) -> str | None:
        """套用剛解析的課表；save_path 有給就順便存 JSON，回傳實際存檔路徑。"""
        if self._pending_tt is None:
            return None
        self.timetable = self._pending_tt
        self._pending_tt = None
        if save_path:
            return storage.save_timetable(self.timetable, save_path)
        return None

    def load_timetable(self, path: str) -> None:
        self.timetable = storage.load_timetable(path)

    def timetable_slots(self, teacher: str, date: datetime.date | None):
        """某老師在某日期（換算星期）的課表 slot 清單。"""
        if not self.timetable or not teacher or date is None:
            return []
        wd = date.weekday() + 1
        if wd > 5:
            return []
        return self.timetable.slots_for(teacher.strip(), wd)

    def timetable_teacher_names(self) -> list[str]:
        return self.timetable.teacher_names() if self.timetable else []

    # ---- 專案存讀 --------------------------------------------------
    def new_project(self) -> None:
        self.project = Project()
        self.current_index = None
        self.project_path = ""

    def save_project(self, path: str) -> SaveReport:
        """把本次的調代課單併進資料庫 JSON（依分頁名稱去重／更新），寫回，
        並讓目前的清單同步成資料庫全部內容。"""
        path = storage._ensure_ext(path, ".json")
        existing = storage.load_project(path) if os.path.exists(path) else Project()

        merged = list(existing.events)
        idx_by_name = {ev.sheet_name: i for i, ev in enumerate(merged)}
        dicts = [models.event_to_dict(e) for e in merged]
        report = SaveReport(path=path)
        keep_name = self.current.sheet_name if self.current else None

        for ev in self.project.events:
            d = models.event_to_dict(ev)
            name = ev.sheet_name
            if name in idx_by_name:
                j = idx_by_name[name]
                if dicts[j] == d:
                    report.unchanged += 1
                else:
                    merged[j] = ev
                    dicts[j] = d
                    report.updated += 1
            elif d in dicts:
                report.unchanged += 1
            else:
                merged.append(ev)
                dicts.append(d)
                idx_by_name[name] = len(merged) - 1
                report.added += 1

        out = Project(
            events=merged,
            master_path=self.project.master_path or existing.master_path,
            teachers=list(existing.teachers), classes=list(existing.classes),
            subjects=list(existing.subjects),
        )
        out.merge_master_data()
        storage.save_project(out, path)

        self.project = out
        self.project_path = path
        self.current_index = None
        if keep_name:
            for i, ev in enumerate(out.events):
                if ev.sheet_name == keep_name:
                    self.current_index = i
                    break
        if self.current_index is None and out.events:
            self.current_index = len(out.events) - 1
        return report

    def export_all_xlsx(self, path: str) -> output.TargetResult:
        """把所有事件匯出成一個 Excel（一事件一分頁）。"""
        return output.export_all(self.project.events, path)

    def rebuild_record_stats(self) -> list[record.RecordReport]:
        """重算記錄檔資料夾裡每個「{學期}調代課記錄.xlsx」的月統計。"""
        import glob
        out = []
        if self.record_folder:
            for p in sorted(glob.glob(os.path.join(self.record_folder, "*調代課記錄.xlsx"))):
                out.append(record.rebuild_stats_file(p))
        return out

    def load_project(self, path: str) -> None:
        self.project = storage.load_project(path)
        self.project_path = path
        self.current_index = 0 if self.project.events else None

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
                            system_form_no: str | None = None,
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
        if system_form_no is not None:
            ev.system_form_no = system_form_no
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
    @staticmethod
    def _build_swap(klass, teacher_a, subject_a, date_a, period_a,
                    teacher_b, subject_b, date_b, period_b) -> SwapLeg:
        return SwapLeg(
            klass=klass.strip(),
            teacher_a=teacher_a.strip(), subject_a=subject_a.strip(),
            slot_a=Slot(date_a, int(period_a)),
            teacher_b=teacher_b.strip(), subject_b=subject_b.strip(),
            slot_b=Slot(date_b, int(period_b)),
        )

    @staticmethod
    def _build_sub(klass, orig_teacher, subject, date, period, sub_teacher,
                   from_swap=False) -> SubLeg:
        return SubLeg(
            klass=klass.strip(),
            orig_teacher=orig_teacher.strip(), subject=subject.strip(),
            slot=Slot(date, int(period)), sub_teacher=sub_teacher.strip(),
            from_swap=from_swap,
        )

    def add_swap_leg(self, **kw) -> None:
        leg = self._build_swap(**kw)
        self._require_event().legs.append(leg)
        self._learn_names(leg.klass, [leg.teacher_a, leg.teacher_b],
                          [leg.subject_a, leg.subject_b])

    def add_sub_leg(self, **kw) -> None:
        leg = self._build_sub(**kw)
        self._require_event().legs.append(leg)
        self._learn_names(leg.klass, [leg.orig_teacher, leg.sub_teacher], [leg.subject])

    def add_swap_then_sub(self, *, klass, teacher_a, subject_a, date_a, period_a,
                          teacher_b, subject_b, date_b, period_b, sub_teacher) -> None:
        """先調再代：甲把課調到乙的時段後，那節新時段再請人代（甲要請假）。
        產生 1 筆調課 + 1 筆代課（from_swap=True，代課時段＝乙原時段、科目＝甲科目）。"""
        ev = self._require_event()
        swap = self._build_swap(klass, teacher_a, subject_a, date_a, period_a,
                                teacher_b, subject_b, date_b, period_b)
        sub = self._build_sub(klass, teacher_a, subject_a, date_b, period_b,
                              sub_teacher, from_swap=True)
        ev.legs.append(swap)
        ev.legs.append(sub)
        self._learn_names(klass, [teacher_a, teacher_b, sub_teacher],
                          [subject_a, subject_b])

    def update_leg(self, index: int, kind: str, **kw) -> None:
        ev = self.current
        if not ev or not (0 <= index < len(ev.legs)):
            return
        leg = self._build_swap(**kw) if kind == "swap" else self._build_sub(**kw)
        ev.legs[index] = leg
        if kind == "swap":
            self._learn_names(leg.klass, [leg.teacher_a, leg.teacher_b],
                              [leg.subject_a, leg.subject_b])
        else:
            self._learn_names(leg.klass, [leg.orig_teacher, leg.sub_teacher], [leg.subject])

    def leg_at(self, index: int):
        ev = self.current
        if ev and 0 <= index < len(ev.legs):
            return ev.legs[index]
        return None

    def leg_form_data(self, index: int) -> dict | None:
        """把某一筆腳轉成表單可用的初始值。"""
        leg = self.leg_at(index)
        if leg is None:
            return None
        if isinstance(leg, SwapLeg):
            return dict(
                kind="swap", klass=leg.klass,
                teacher_a=leg.teacher_a, subject_a=leg.subject_a,
                date_a=leg.slot_a.date, period_a=leg.slot_a.period,
                teacher_b=leg.teacher_b, subject_b=leg.subject_b,
                date_b=leg.slot_b.date, period_b=leg.slot_b.period,
            )
        return dict(
            kind="sub", klass=leg.klass, orig_teacher=leg.orig_teacher,
            subject=leg.subject, date=leg.slot.date, period=leg.slot.period,
            sub_teacher=leg.sub_teacher, from_swap=leg.from_swap,
        )

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
        def ts(teacher: str, subject: str) -> str:
            return f"{teacher}（{subject}）" if subject else (teacher or "？")

        out = []
        for leg in ev.legs:
            if isinstance(leg, SwapLeg):
                out.append(
                    f"調課　{leg.klass or '？班'}｜"
                    f"{ts(leg.teacher_a, leg.subject_a)} {leg.slot_a} "
                    f"↔ {ts(leg.teacher_b, leg.subject_b)} {leg.slot_b}"
                )
            else:
                out.append(
                    f"代課　{leg.klass or '？班'}｜"
                    f"{ts(leg.orig_teacher, leg.subject)} {leg.slot} → {leg.sub_teacher or '？'} 代"
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
        if self.record_folder:
            folder = os.path.dirname(self.record_folder.rstrip("/\\")) or self.record_folder
        else:
            folder = os.getcwd()
        stem = f"{ev.system_form_no}-{ev.sheet_name}" if ev.system_form_no.strip() else ev.sheet_name
        return os.path.join(folder, f"{stem}.xlsx")

    def generate(self, *, to_master: bool, save_new: bool,
                 master_path: str = "", dest_path: str = "") -> list[output.TargetResult]:
        ev = self._require_event()
        problems = [p for p in validate(ev) if "未填" in p or "超出範圍" in p or "無法對調" in p]
        if problems:
            raise ValueError("請先修正：\n- " + "\n- ".join(problems))
        if to_master and master_path:
            self.project.master_path = master_path
        results = output.run(
            ev,
            to_master=to_master, master_path=master_path,
            save_new=save_new, dest_path=dest_path,
        )
        self.last_record = None
        if self.record_folder and any(r.ok for r in results):
            self.last_record = record.update_record(self.record_folder, ev, self.timetable)
        return results

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
