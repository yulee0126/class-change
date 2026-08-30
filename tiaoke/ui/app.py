"""Flet GUI：事件清單 + 事件編輯 + 腳編輯 + 預覽 + 單鍵雙目標輸出。

視覺細節需在使用者的桌面環境實際跑 `python main.py` 檢視微調。
邏輯都在 controller.py，已有單元測試。
"""

from __future__ import annotations

import datetime

import flet as ft

from .. import roc
from ..models import CLASS_SLIP_STYLES, LEAVE_TYPES
from ..storage import AppSettings
from .controller import DEFAULT_FORM_NO, AppController

_STYLE_LABELS = {"banner": "橫幅式", "title": "標題式"}


def main(page: ft.Page) -> None:
    page.title = "調課代課通知單產生器"
    AppView(page)


class AppView:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.settings = AppSettings.load()
        self.ctl = AppController()
        if self.settings.default_master_path:
            self.ctl.project.master_path = self.settings.default_master_path

        try:
            page.window.width = self.settings.window_width
            page.window.height = self.settings.window_height
            page.window.on_close = self._on_window_close
        except Exception:
            pass

        self.status = ft.Text("", color=ft.Colors.BLUE_GREY_700, selectable=True)
        self.project_path = ft.TextField(label="專案檔（.json）", value=self.settings.last_project,
                                         dense=True, expand=True)

        self.event_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)
        self.editor = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        self._leg_form: _LegForm | None = None

        left = ft.Container(
            width=260,
            content=ft.Column([
                ft.Text("專案", weight=ft.FontWeight.BOLD),
                self.project_path,
                ft.Row([
                    ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="開啟", on_click=self._on_open_project),
                    ft.IconButton(ft.Icons.SAVE, tooltip="儲存", on_click=self._on_save_project),
                    ft.IconButton(ft.Icons.NOTE_ADD, tooltip="新專案", on_click=self._on_new_project),
                ]),
                ft.Divider(),
                ft.Row([
                    ft.Text("事件", weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.ADD, tooltip="新增", on_click=self._on_new),
                    ft.IconButton(ft.Icons.CONTENT_COPY, tooltip="複製", on_click=self._on_dup),
                    ft.IconButton(ft.Icons.DELETE, tooltip="刪除", on_click=self._on_del),
                ]),
                self.event_list,
                ft.Divider(),
                _MasterDataPanel(self.ctl, self.refresh),
            ], expand=True, scroll=ft.ScrollMode.AUTO),
        )
        page.add(
            ft.Row([left, ft.VerticalDivider(), self.editor], expand=True),
            ft.Divider(),
            self.status,
        )
        self.refresh()

    # ---- 專案 ---------------------------------------------------
    def _on_new_project(self, _e) -> None:
        self.ctl.new_project()
        self.project_path.value = ""
        self._leg_form = None
        self._set_status("已開新專案。")
        self.refresh()

    def _on_open_project(self, _e) -> None:
        path = (self.project_path.value or "").strip()
        try:
            self.ctl.load_project(path)
        except (OSError, ValueError) as exc:
            self._set_status(f"開啟失敗：{exc}")
            return
        self.settings.note_recent(path)
        self.settings.save()
        self._leg_form = None
        self._set_status(f"已開啟 {path}")
        self.refresh()

    def _on_save_project(self, _e) -> None:
        path = (self.project_path.value or "").strip()
        if not path:
            self._set_status("請先在「專案檔」欄輸入要儲存的路徑。")
            return
        try:
            saved = self.ctl.save_project(path)
        except OSError as exc:
            self._set_status(f"儲存失敗：{exc}")
            return
        self.project_path.value = saved
        self.settings.note_recent(saved)
        self.settings.save()
        self._set_status(f"已儲存 {saved}")
        self.refresh()

    def _on_window_close(self, _e) -> None:
        try:
            self.settings.window_width = int(self.page.window.width)
            self.settings.window_height = int(self.page.window.height)
            if self.ctl.project.master_path:
                self.settings.default_master_path = self.ctl.project.master_path
            self.settings.save()
        except Exception:
            pass

    # ---- 重新繪製 --------------------------------------------------
    def refresh(self) -> None:
        self._render_event_list()
        self._render_editor()
        self.page.update()

    def _render_event_list(self) -> None:
        self.event_list.controls.clear()
        titles = self.ctl.event_titles()
        if not titles:
            self.event_list.controls.append(ft.Text("（尚無事件，按「新增」）", italic=True))
        for i, t in enumerate(titles):
            selected = i == self.ctl.current_index
            self.event_list.controls.append(
                ft.Button(
                    t or f"事件 {i + 1}",
                    on_click=lambda e, idx=i: self._select(idx),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_100 if selected else None,
                    ),
                )
            )

    def _render_editor(self) -> None:
        self.editor.controls.clear()
        ev = self.ctl.current
        if ev is None:
            self.editor.controls.append(ft.Text("請先新增或選取一個事件。"))
            return

        # --- 事件欄位 ---
        f_orig = ft.TextField(label="發起教師", value=ev.originator, width=160,
                              on_change=lambda e: self._set(originator=e.control.value))
        f_leave = ft.RadioGroup(
            value=ev.leave_type,
            content=ft.Row([ft.Radio(value=x, label=x) for x in LEAVE_TYPES], wrap=True),
            on_change=lambda e: self._set(leave_type=e.control.value))
        f_form = ft.TextField(label="假單編號", value=ev.form_no or DEFAULT_FORM_NO, width=180,
                              on_change=lambda e: self._set(form_no=e.control.value))
        f_ann = ft.TextField(label="公告日期", value=roc.format_date_input(ev.announce_date),
                             width=140, hint_text="2026-08-25 或 115/8/25",
                             on_change=lambda e: self._set_date("announce", e.control.value))
        f_sheet = ft.TextField(
            label="分頁日期（可空）", width=160, hint_text="空＝取最早腳日期",
            value=roc.format_date_input(ev.sheet_date) if ev.sheet_date else "",
            on_change=lambda e: self._set_date("sheet", e.control.value))
        f_name = ft.TextField(label="分頁名稱（可空＝自動）", width=220,
                              value=ev.sheet_name_override or "",
                              hint_text=ev.sheet_name,
                              on_change=lambda e: self._set(sheet_name_override=e.control.value))
        f_style = ft.RadioGroup(
            value=ev.class_slip_style,
            content=ft.Row([ft.Radio(value=s, label=_STYLE_LABELS[s]) for s in CLASS_SLIP_STYLES]),
            on_change=lambda e: self._set(class_slip_style=e.control.value))

        self.editor.controls.append(ft.Text("事件資料", weight=ft.FontWeight.BOLD))
        self.editor.controls.append(ft.Row([f_orig, f_form, f_ann], wrap=True))
        self.editor.controls.append(ft.Row([ft.Text("假別："), f_leave], wrap=True))
        self.editor.controls.append(ft.Row([f_sheet, f_name], wrap=True))
        self.editor.controls.append(ft.Row([ft.Text("班級單樣式："), f_style]))

        # --- 說明 ---
        self.note_field = ft.TextField(
            label="說明（產生於每張通知單末端；空＝不產生）",
            value=ev.note, multiline=True, min_lines=2, max_lines=6, expand=True,
            on_change=lambda e: self._set(note=e.control.value))
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(ft.Row([
            ft.Text("說明", weight=ft.FontWeight.BOLD),
            ft.Button("產生草稿", icon=ft.Icons.AUTO_FIX_HIGH, on_click=self._on_note_draft),
        ]))
        self.editor.controls.append(self.note_field)

        # --- 腳清單 ---
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(ft.Row([
            ft.Text("調課／代課腳", weight=ft.FontWeight.BOLD),
            ft.Button("新增調課", icon=ft.Icons.SWAP_HORIZ, on_click=lambda e: self._open_leg_form("swap")),
            ft.Button("新增代課", icon=ft.Icons.PERSON_ADD, on_click=lambda e: self._open_leg_form("sub")),
        ]))
        for i, summary in enumerate(self.ctl.leg_summaries()):
            self.editor.controls.append(ft.Row([
                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="刪除",
                              on_click=lambda e, idx=i: self._remove_leg(idx)),
                ft.Text(summary, selectable=True),
            ]))
        if self._leg_form is not None:
            self.editor.controls.append(self._leg_form)

        # --- 預覽 ---
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(ft.Text("預覽", weight=ft.FontWeight.BOLD))
        pv = self.ctl.preview()
        if pv.problems:
            self.editor.controls.append(
                ft.Text("⚠ " + "；".join(pv.problems), color=ft.Colors.ORANGE_800))
        if pv.slips:
            self.editor.controls.append(ft.Text(
                f"共 {pv.teacher_count} 張教師單、{pv.class_count} 張班級單"))
            for s in pv.slips:
                self.editor.controls.append(ft.Text(f"　· {s.kind}　{s.title}（{s.row_count} 列）"))

        # --- 輸出 ---
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(ft.Text("輸出", weight=ft.FontWeight.BOLD))
        self.cb_master = ft.Checkbox(label="寫入總表（同名工作表會覆蓋）", value=bool(self.ctl.project.master_path))
        self.tf_master = ft.TextField(label="總表路徑", value=self.ctl.project.master_path,
                                      expand=True, hint_text=r"C:\...\115-1手動調代課-兼課.xlsx")
        self.cb_new = ft.Checkbox(label="另存新檔", value=True)
        self.tf_new = ft.TextField(label="另存路徑", value=self.ctl.default_new_path(), expand=True)
        self.editor.controls.append(ft.Row([self.cb_master, self.tf_master]))
        self.editor.controls.append(ft.Row([self.cb_new, self.tf_new]))
        self.editor.controls.append(
            ft.Button("產生通知單", icon=ft.Icons.DESCRIPTION,
                      on_click=self._on_generate,
                      style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)))

    # ---- 事件處理 ----------------------------------------------
    def _select(self, idx: int) -> None:
        self.ctl.select_event(idx)
        self._leg_form = None
        self.refresh()

    def _on_new(self, _e) -> None:
        self.ctl.new_event()
        self._leg_form = None
        self.refresh()

    def _on_dup(self, _e) -> None:
        self.ctl.duplicate_event()
        self.refresh()

    def _on_del(self, _e) -> None:
        self.ctl.delete_event()
        self._leg_form = None
        self.refresh()

    def _set(self, **kwargs) -> None:
        self.ctl.update_event_fields(**kwargs)
        self._render_event_list()          # 分頁名稱可能變
        self.page.update()

    def _set_date(self, which: str, text: str) -> None:
        text = (text or "").strip()
        try:
            if which == "sheet" and not text:
                self.ctl.update_event_fields(sheet_date=None)
            elif which == "sheet":
                self.ctl.update_event_fields(sheet_date=roc.parse_date(text))
            else:
                self.ctl.update_event_fields(announce_date=roc.parse_date(text))
            self._set_status("")
        except ValueError as exc:
            self._set_status(f"日期格式錯誤：{exc}")
        self._render_event_list()
        self.page.update()

    def _on_note_draft(self, _e) -> None:
        draft = self.ctl.make_note_draft()
        self.ctl.update_event_fields(note=draft)
        self.note_field.value = draft
        self.refresh()

    def _remove_leg(self, idx: int) -> None:
        self.ctl.remove_leg(idx)
        self.refresh()

    def _open_leg_form(self, kind: str) -> None:
        self._leg_form = _LegForm(kind, self._submit_leg, self._cancel_leg,
                                  self.ctl.project)
        self.refresh()

    def _cancel_leg(self) -> None:
        self._leg_form = None
        self.refresh()

    def _submit_leg(self, kind: str, data: dict) -> None:
        try:
            if kind == "swap":
                self.ctl.add_swap_leg(**data)
            else:
                self.ctl.add_sub_leg(**data)
        except (ValueError, KeyError) as exc:
            self._set_status(f"新增失敗：{exc}")
            return
        self._leg_form = None
        self._set_status("已新增一腳。")
        self.refresh()

    def _on_generate(self, _e) -> None:
        try:
            results = self.ctl.generate(
                to_master=self.cb_master.value, save_new=self.cb_new.value,
                master_path=(self.tf_master.value or "").strip(),
                dest_path=(self.tf_new.value or "").strip(),
            )
        except ValueError as exc:
            self._set_status(str(exc))
            return
        lines = []
        for r in results:
            if r.ok:
                extra = "（已覆蓋舊工作表）" if r.replaced_sheet else ""
                lines.append(f"✓ {'總表' if r.target == 'master' else '新檔'}：{r.path} {extra}")
            else:
                lines.append(f"✗ {'總表' if r.target == 'master' else '新檔'}：{r.error}")
        if self.ctl.project.master_path:
            self.settings.default_master_path = self.ctl.project.master_path
            self.settings.save()
        self._set_status("\n".join(lines))
        self.refresh()

    def _set_status(self, text: str) -> None:
        self.status.value = text
        self.page.update()


class _LegForm(ft.Container):
    """新增一腳的內嵌表單。"""

    def __init__(self, kind: str, on_submit, on_cancel, project) -> None:
        super().__init__(bgcolor=ft.Colors.BLUE_GREY_50, padding=10, border_radius=6)
        self.kind = kind
        self._on_submit = on_submit
        self._on_cancel = on_cancel

        def tf(label, w=120):
            return ft.TextField(label=label, width=w, dense=True)

        self.klass = tf("班級")
        today = roc.format_date_input(datetime.date.today())

        if kind == "swap":
            self.ta = tf("甲老師"); self.sa = tf("甲科目")
            self.da = tf("甲原日期", 130); self.da.value = today
            self.pa = tf("甲節次", 70)
            self.tb = tf("乙老師"); self.sb = tf("乙科目")
            self.db = tf("乙原日期", 130); self.db.value = today
            self.pb = tf("乙節次", 70)
            rows = [
                ft.Text("新增調課（兩位老師在同一班各一節互換）", weight=ft.FontWeight.BOLD),
                ft.Row([self.klass], wrap=True),
                ft.Row([self.ta, self.sa, self.da, self.pa], wrap=True),
                ft.Row([self.tb, self.sb, self.db, self.pb], wrap=True),
            ]
        else:
            self.ot = tf("原老師"); self.subj = tf("科目")
            self.dd = tf("日期", 130); self.dd.value = today
            self.pp = tf("節次", 70)
            self.st = tf("代課老師")
            rows = [
                ft.Text("新增代課（時段不動，換人上）", weight=ft.FontWeight.BOLD),
                ft.Row([self.klass, self.ot, self.subj, self.dd, self.pp, self.st], wrap=True),
            ]

        self.err = ft.Text("", color=ft.Colors.RED_700)
        rows.append(self.err)
        rows.append(ft.Row([
            ft.Button("加入", icon=ft.Icons.CHECK, on_click=self._submit),
            ft.TextButton("取消", on_click=lambda e: self._on_cancel()),
        ]))
        self.content = ft.Column(rows, spacing=8, tight=True)

    def _submit(self, _e) -> None:
        try:
            if self.kind == "swap":
                data = dict(
                    klass=self.klass.value or "",
                    teacher_a=self.ta.value or "", subject_a=self.sa.value or "",
                    date_a=roc.parse_date(self.da.value or ""), period_a=int(self.pa.value or 0),
                    teacher_b=self.tb.value or "", subject_b=self.sb.value or "",
                    date_b=roc.parse_date(self.db.value or ""), period_b=int(self.pb.value or 0),
                )
            else:
                data = dict(
                    klass=self.klass.value or "",
                    orig_teacher=self.ot.value or "", subject=self.subj.value or "",
                    date=roc.parse_date(self.dd.value or ""), period=int(self.pp.value or 0),
                    sub_teacher=self.st.value or "",
                )
        except ValueError as exc:
            self.err.value = f"日期／節次格式錯誤：{exc}"
            self.err.update()
            return
        self._on_submit(self.kind, data)


class _MasterDataPanel(ft.Column):
    """左側主檔維護：教師／班級／科目 清單。"""

    _KINDS = [("teacher", "教師"), ("class", "班級"), ("subject", "科目")]

    def __init__(self, ctl, on_change) -> None:
        super().__init__(spacing=4, tight=True)
        self.ctl = ctl
        self.on_change = on_change
        self.controls.append(ft.Text("主檔", weight=ft.FontWeight.BOLD))
        self._bodies: dict[str, ft.Column] = {}
        for kind, label in self._KINDS:
            field = ft.TextField(label=f"新增{label}", dense=True, expand=True)
            body = ft.Column(spacing=1, tight=True)
            self._bodies[kind] = body
            self.controls.append(ft.Row([
                field,
                ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE,
                              on_click=lambda e, k=kind, f=field: self._add(k, f)),
            ]))
            self.controls.append(body)
        self._render()

    def _lists(self, kind: str) -> list[str]:
        return {"teacher": self.ctl.project.teachers,
                "class": self.ctl.project.classes,
                "subject": self.ctl.project.subjects}[kind]

    def _render(self) -> None:
        for kind, _ in self._KINDS:
            body = self._bodies[kind]
            body.controls.clear()
            for name in self._lists(kind):
                body.controls.append(ft.Row([
                    ft.IconButton(ft.Icons.CLOSE, icon_size=14,
                                  on_click=lambda e, k=kind, n=name: self._remove(k, n)),
                    ft.Text(name, size=12),
                ], tight=True))

    def _add(self, kind: str, field: ft.TextField) -> None:
        self.ctl.add_master(kind, field.value or "")
        field.value = ""
        self._render()
        self.on_change()

    def _remove(self, kind: str, name: str) -> None:
        self.ctl.remove_master(kind, name)
        self._render()
        self.on_change()
