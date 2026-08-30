"""Flet GUI。邏輯都在 controller.py（有單元測試），這裡只做畫面。"""

from __future__ import annotations

import datetime
import os

import flet as ft

from .. import roc
from ..models import CLASS_SLIP_STYLES, LEAVE_TYPES
from ..storage import AppSettings
from .controller import DEFAULT_FORM_NO, AppController

_STYLE_LABELS = {"banner": "橫幅式（每張單抬頭一整條）", "title": "標題式（抬頭置中）"}
_HINT = ft.Colors.BLUE_GREY_600
_FIRST = datetime.date(2020, 1, 1)
_LAST = datetime.date(2035, 12, 31)


def main(page: ft.Page) -> None:
    page.title = "調課代課通知單產生器"
    page.padding = 12
    AppView(page)


def _hint(text: str) -> ft.Text:
    return ft.Text(text, size=11, color=_HINT)


def _section(text: str) -> ft.Text:
    return ft.Text(text, weight=ft.FontWeight.BOLD, size=15)


class _DateField:
    """可手打、也可按日曆選的日期欄。"""

    def __init__(self, page: ft.Page, label: str, value: datetime.date | None,
                 on_change=None, width: int = 155) -> None:
        self.page = page
        self._on_change = on_change
        self.field = ft.TextField(
            label=label, width=width, dense=True,
            value=roc.format_date_input(value) if value else "",
            hint_text="2026-08-25 或 115/8/25",
            on_change=lambda e: self._fire(),
        )
        self.control = ft.Row(
            [self.field,
             ft.IconButton(ft.Icons.CALENDAR_MONTH, tooltip="開日曆", on_click=self._open)],
            spacing=0, tight=True)

    def _open(self, _e) -> None:
        try:
            cur = self.get() or datetime.date.today()
        except ValueError:
            cur = datetime.date.today()
        dp = ft.DatePicker(value=cur, first_date=_FIRST, last_date=_LAST,
                           on_change=self._picked)
        self.page.show_dialog(dp)

    def _picked(self, e) -> None:
        v = e.control.value
        if not v:
            return
        d = v.date() if hasattr(v, "date") else v
        self.field.value = roc.format_date_input(d)
        self.field.update()
        self._fire()

    def _fire(self) -> None:
        if self._on_change:
            self._on_change()

    def get(self) -> datetime.date | None:
        txt = (self.field.value or "").strip()
        if not txt:
            return None
        return roc.parse_date(txt)


class AppView:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.settings = AppSettings.load()
        self.ctl = AppController()
        if self.settings.default_master_path:
            self.ctl.project.master_path = self.settings.default_master_path
        if self.settings.timetable_path and os.path.exists(self.settings.timetable_path):
            try:
                self.ctl.load_timetable(self.settings.timetable_path)
            except Exception:
                pass

        try:
            page.window.width = self.settings.window_width
            page.window.height = self.settings.window_height
            page.window.on_close = self._on_window_close
        except Exception:
            pass

        self.status = ft.Text("", color=ft.Colors.BLUE_GREY_800, selectable=True)
        self.project_path = ft.TextField(hint_text="專案存檔路徑 .json", dense=True,
                                         value=self.settings.last_project, expand=True)
        self.event_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self.editor = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self._leg_form: _LegForm | None = None

        left = ft.Container(
            width=250,
            content=ft.Column([
                ft.Text("調代課單", weight=ft.FontWeight.BOLD, size=16),
                _hint("一張單 = Excel 裡的一個分頁。\n一次調代課（含好幾筆對調／代課）做成一張。"),
                ft.Row([
                    ft.Button("新增一張", icon=ft.Icons.ADD, on_click=self._on_new),
                    ft.IconButton(ft.Icons.CONTENT_COPY, tooltip="複製這張", on_click=self._on_dup),
                    ft.IconButton(ft.Icons.DELETE, tooltip="刪除這張", on_click=self._on_del),
                ]),
                self.event_list,
                ft.Divider(),
                ft.ExpansionTile(
                    title=ft.Text("進階：專案存檔．常用名單"),
                    tile_padding=ft.Padding(0, 0, 0, 0),
                    controls=[
                        _hint("儲存＝同時存一個 .json（可再編輯）和一個 .xlsx（所有單合在一個 Excel）。"),
                        self.project_path,
                        ft.Row([
                            ft.IconButton(ft.Icons.FOLDER_OPEN, tooltip="開啟 .json", on_click=self._on_open_project),
                            ft.IconButton(ft.Icons.SAVE, tooltip="儲存（.json + .xlsx）", on_click=self._on_save_project),
                            ft.IconButton(ft.Icons.NOTE_ADD, tooltip="全部清空重來", on_click=self._on_new_project),
                        ]),
                        ft.Button("只匯出全部成一個 Excel", icon=ft.Icons.TABLE_VIEW,
                                  on_click=self._on_export_all),
                        ft.Divider(),
                        _TimetableImport(self.ctl, self.settings, self._on_tt_changed),
                        ft.Divider(),
                        _hint("常用的老師／班級／科目，打過就記著（目前僅記錄）。"),
                        _MasterDataPanel(self.ctl, self.refresh),
                    ],
                ),
            ], scroll=ft.ScrollMode.AUTO),
        )
        page.add(
            ft.Row([left, ft.VerticalDivider(), self.editor], expand=True),
            ft.Divider(),
            self.status,
        )
        self.refresh()

    # ==================================================================
    # 繪製
    # ==================================================================
    def refresh(self) -> None:
        self._render_event_list()
        self._render_editor()
        self.page.update()

    def _render_event_list(self) -> None:
        self.event_list.controls.clear()
        titles = self.ctl.event_titles()
        if not titles:
            self.event_list.controls.append(_hint("（還沒有，按上面「新增一張」）"))
        for i, t in enumerate(titles):
            sel = i == self.ctl.current_index
            self.event_list.controls.append(ft.Button(
                t or f"第 {i + 1} 張",
                on_click=lambda e, idx=i: self._select(idx),
                style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_100 if sel else None),
            ))

    def _render_editor(self) -> None:
        self.editor.controls.clear()
        ev = self.ctl.current
        if ev is None:
            self.editor.controls.append(ft.Container(
                padding=16, content=ft.Column([
                    ft.Text("還沒有調代課單", weight=ft.FontWeight.BOLD),
                    ft.Text("點左邊「新增一張」開始。"),
                ])))
            return

        self.editor.controls.append(_guide_card())

        # ---------- 1. 基本資料 ----------
        self.editor.controls.append(_section("① 基本資料"))
        f_orig = ft.TextField(label="發起教師", value=ev.originator, width=170,
                              on_change=lambda e: self._set(originator=e.control.value))
        f_form = ft.TextField(label="假單編號", value=ev.form_no or DEFAULT_FORM_NO, width=190,
                              on_change=lambda e: self._set(form_no=e.control.value))
        self._ann_date = _DateField(self.page, "公告日期", ev.announce_date,
                                    on_change=lambda: self._pull_ann_date())
        self.editor.controls.append(ft.Row([f_orig, f_form, self._ann_date.control], wrap=True))
        self.editor.controls.append(_hint(
            "發起教師＝因為誰請假／要調課而發起這次異動（通知單抬頭會出現，也會自動帶進下面的甲老師／原老師）。\n"
            "假單編號＝請假系統的單號，自己打，例如「手動+1076」「2015+手動」。\n"
            "公告日期＝通知單「公告日期」欄要印的日期。"))

        # 假別：常用選項 + 可自訂
        custom_leave = "" if ev.leave_type in LEAVE_TYPES else ev.leave_type
        rg_leave = ft.RadioGroup(
            value=ev.leave_type if ev.leave_type in LEAVE_TYPES else None,
            content=ft.Row([ft.Radio(value=x, label=x) for x in LEAVE_TYPES], wrap=True),
            on_change=lambda e: self._set_leave(e.control.value))
        tf_leave = ft.TextField(label="或自行輸入假別", width=200, value=custom_leave, dense=True,
                                on_change=lambda e: self._set_leave(e.control.value, custom=True))
        self.editor.controls.append(ft.Row([ft.Text("假別："), rg_leave], wrap=True))
        self.editor.controls.append(ft.Row([tf_leave]))

        self._sheet_date = _DateField(self.page, "分頁日期（可空）", ev.sheet_date,
                                      on_change=self._pull_sheet_date, width=150)
        self.editor.controls.append(ft.ExpansionTile(
            title=ft.Text("進階設定（分頁名稱、班級單樣式）", size=12),
            tile_padding=ft.Padding(0, 0, 0, 0),
            controls=[
                _hint(f"不填的話分頁名稱自動＝「{ev.sheet_name}」（發起教師末兩字＋民國年月日）。"),
                ft.Row([
                    self._sheet_date.control,
                    ft.TextField(label="分頁名稱（可空＝自動）", width=230,
                                 value=ev.sheet_name_override or "", hint_text=ev.sheet_name,
                                 on_change=lambda e: self._set(sheet_name_override=e.control.value)),
                ], wrap=True),
                ft.Row([
                    ft.Text("班級單抬頭："),
                    ft.RadioGroup(value=ev.class_slip_style,
                                  content=ft.Column([ft.Radio(value=s, label=_STYLE_LABELS[s])
                                                     for s in CLASS_SLIP_STYLES]),
                                  on_change=lambda e: self._set(class_slip_style=e.control.value)),
                ]),
            ],
        ))

        # ---------- 2. 異動明細 ----------
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(_section("② 這次有哪些對調／代課"))
        self.editor.controls.append(_hint(
            "調課＝兩位老師在同一個班、各挪一節課互換。\n"
            "代課＝某位老師某一節不能上，找人代（時間不變）。\n"
            "一張單可以加很多筆；同一位老師出現多次會併在同一張通知單。"))
        self.editor.controls.append(ft.Row([
            ft.Button("＋ 新增調課", icon=ft.Icons.SWAP_HORIZ,
                      on_click=lambda e: self._open_leg_form("swap")),
            ft.Button("＋ 新增代課", icon=ft.Icons.PERSON_ADD_ALT,
                      on_click=lambda e: self._open_leg_form("sub")),
        ]))
        summaries = self.ctl.leg_summaries()
        if not summaries:
            self.editor.controls.append(_hint("（還沒加，先按上面兩顆按鈕）"))
        for i, summary in enumerate(summaries):
            editing = self._leg_form is not None and self._leg_form.edit_index == i
            self.editor.controls.append(ft.Row([
                ft.IconButton(ft.Icons.EDIT_OUTLINED, tooltip="修改這筆", icon_size=18,
                              on_click=lambda e, idx=i: self._open_leg_form(None, idx)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="刪除這筆", icon_size=18,
                              on_click=lambda e, idx=i: self._remove_leg(idx)),
                ft.Text(("✏ " if editing else "") + summary, selectable=True),
            ]))
        if self._leg_form is not None:
            self.editor.controls.append(self._leg_form)

        # ---------- 3. 說明 ----------
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(ft.Row([
            _section("③ 說明（選填）"),
            ft.Button("自動產生草稿", icon=ft.Icons.AUTO_FIX_HIGH, on_click=self._on_note_draft),
        ], wrap=True))
        self.note_field = ft.TextField(
            value=ev.note, multiline=True, min_lines=2, max_lines=6, expand=True,
            hint_text="會印在每張通知單最下面。留空就不印。",
            on_change=lambda e: self._set(note=e.control.value))
        self.editor.controls.append(self.note_field)

        # ---------- 預覽 ----------
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(_section("預覽（會產生這些通知單）"))
        pv = self.ctl.preview()
        if pv.problems:
            self.editor.controls.append(ft.Container(
                bgcolor=ft.Colors.ORANGE_50, padding=8, border_radius=6,
                content=ft.Text("要補：" + "；".join(pv.problems), color=ft.Colors.ORANGE_900)))
        if pv.slips:
            self.editor.controls.append(ft.Text(
                f"共 {pv.teacher_count} 張教師通知單、{pv.class_count} 張班級通知單"))
            self.editor.controls.append(ft.Text(
                "　" + "　".join(f"{s.title}（{s.row_count}列）" for s in pv.slips),
                size=12, color=_HINT))

        # ---------- 4. 產生 ----------
        self.editor.controls.append(ft.Divider())
        self.editor.controls.append(_section("④ 產生 Excel"))
        self.cb_new = ft.Checkbox(label="另存成一個新檔", value=True)
        self.tf_new = ft.TextField(label="新檔存到", value=self.ctl.default_new_path(),
                                   expand=True, dense=True)
        self.cb_master = ft.Checkbox(label="也寫進學期總表（同分頁會被覆蓋更新）",
                                     value=bool(self.ctl.project.master_path))
        self.tf_master = ft.TextField(label="總表檔", value=self.ctl.project.master_path,
                                      expand=True, dense=True,
                                      hint_text=r"例：C:\...\115-1手動調代課-兼課.xlsx")
        self.editor.controls.append(ft.Row([self.cb_new, self.tf_new]))
        self.editor.controls.append(ft.Row([self.cb_master, self.tf_master]))
        self.editor.controls.append(_hint("兩個可以同時勾。至少勾一個。"))
        self.editor.controls.append(ft.Button(
            "產生 Excel", icon=ft.Icons.TABLE_VIEW, height=44,
            on_click=self._on_generate,
            style=ft.ButtonStyle(bgcolor=ft.Colors.BLUE_600, color=ft.Colors.WHITE)))

    # ==================================================================
    # 事件處理
    # ==================================================================
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
        self._render_event_list()
        self.page.update()

    def _set_leave(self, value: str, custom: bool = False) -> None:
        value = (value or "").strip()
        if not value:
            return
        self.ctl.update_event_fields(leave_type=value)
        if custom:
            self.refresh()  # 讓 radio 取消選取

    def _pull_ann_date(self) -> None:
        try:
            d = self._ann_date.get()
            if d:
                self.ctl.update_event_fields(announce_date=d)
                self._set_status("")
        except ValueError as exc:
            self._set_status(f"公告日期看不懂：{exc}")
        self._render_event_list()
        self.page.update()

    def _pull_sheet_date(self) -> None:
        try:
            self.ctl.update_event_fields(sheet_date=self._sheet_date.get())
            self._set_status("")
        except ValueError as exc:
            self._set_status(f"分頁日期看不懂：{exc}")
        self._render_event_list()
        self.page.update()

    def _on_note_draft(self, _e) -> None:
        self.ctl.update_event_fields(note=self.ctl.make_note_draft())
        self.refresh()

    def _remove_leg(self, idx: int) -> None:
        if self._leg_form is not None and self._leg_form.edit_index == idx:
            self._leg_form = None
        self.ctl.remove_leg(idx)
        self.refresh()

    def _open_leg_form(self, kind: str | None, edit_index: int | None = None) -> None:
        if self.ctl.current is None:
            self.ctl.new_event()
        initial = None
        if edit_index is not None:
            initial = self.ctl.leg_form_data(edit_index)
            if initial is None:
                return
            kind = initial["kind"]
        self._leg_form = _LegForm(
            self.page, kind, self._submit_leg, self._cancel_leg,
            originator=self.ctl.current.originator, ctl=self.ctl,
            initial=initial, edit_index=edit_index)
        self.refresh()

    def _cancel_leg(self) -> None:
        self._leg_form = None
        self.refresh()

    def _submit_leg(self, kind: str, data: dict, edit_index: int | None) -> None:
        try:
            if edit_index is not None:
                self.ctl.update_leg(edit_index, kind, **data)
            elif kind == "swap":
                self.ctl.add_swap_leg(**data)
            else:
                self.ctl.add_sub_leg(**data)
        except (ValueError, KeyError) as exc:
            self._set_status(f"存不進去：{exc}")
            return
        self._leg_form = None
        self._set_status("已更新一筆。" if edit_index is not None else "已加入一筆。")
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
            tag = "總表" if r.target == "master" else "新檔"
            if r.ok:
                extra = "（已更新既有分頁）" if r.replaced_sheet else ""
                lines.append(f"✓ {tag}：{r.path} {extra}")
            else:
                lines.append(f"✗ {tag}：{r.error}")
        if self.ctl.project.master_path:
            self.settings.default_master_path = self.ctl.project.master_path
            self.settings.save()
        self._set_status("\n".join(lines))
        self.refresh()

    def _on_new_project(self, _e) -> None:
        self.ctl.new_project()
        self.project_path.value = ""
        self._leg_form = None
        self._set_status("已清空。")
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
            self._set_status("先在上面欄位打一個路徑（副檔名可省略）。")
            return
        try:
            saved = self.ctl.save_project(path)
        except OSError as exc:
            self._set_status(f"儲存失敗：{exc}")
            return
        xlsx = saved[:-5] + ".xlsx"
        r = self.ctl.export_all_xlsx(xlsx)
        self.project_path.value = saved
        self.settings.note_recent(saved)
        self.settings.save()
        msg = f"已儲存：\n{saved}"
        msg += f"\n{r.path}" if r.ok else f"\n（Excel 匯出失敗：{r.error}）"
        self._set_status(msg)
        self.refresh()

    def _on_tt_changed(self, msg: str) -> None:
        self._set_status(msg)
        self.refresh()

    def _on_export_all(self, _e) -> None:
        path = (self.project_path.value or "").strip()
        if not path:
            path = self.ctl.default_new_path()
        xlsx = (path[:-5] if path.lower().endswith(".json") else path)
        r = self.ctl.export_all_xlsx(xlsx if xlsx.lower().endswith(".xlsx") else xlsx + ".xlsx")
        self._set_status(f"✓ 已匯出 {r.path}" if r.ok else f"✗ {r.error}")
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

    def _set_status(self, text: str) -> None:
        self.status.value = text
        self.page.update()


# ======================================================================
# 小元件
# ======================================================================

def _labeled(label: str, control: ft.Control) -> ft.Control:
    return ft.Column([ft.Text(label, size=11, color=_HINT), control], spacing=1, tight=True)


def _period_dd(value) -> ft.Dropdown:
    v = str(value) if value not in (None, "", 0) else None
    return ft.Dropdown(
        label="節次", width=85, value=v,
        options=[ft.DropdownOption(str(i)) for i in range(1, 11)])


def _guide_card() -> ft.Control:
    return ft.Container(
        bgcolor=ft.Colors.BLUE_50, padding=12, border_radius=8,
        content=ft.Column([
            ft.Text("怎麼用", weight=ft.FontWeight.BOLD),
            ft.Text("① 填基本資料（誰發起、假別、假單編號、公告日期）"),
            ft.Text("② 按「新增調課／新增代課」，把每一筆異動加進來（可再修改）"),
            ft.Text("③ 需要的話寫幾句說明（可按「自動產生草稿」）"),
            ft.Text("④ 看預覽沒問題 → 按「產生 Excel」"),
        ], spacing=2),
    )


class _LegForm(ft.Container):
    """新增／修改一筆調課或代課的內嵌表單。填了老師＋日期後，會列出該老師課表的課供一鍵帶入。"""

    def __init__(self, page, kind: str, on_submit, on_cancel, *,
                 originator: str = "", ctl=None, initial: dict | None = None,
                 edit_index: int | None = None) -> None:
        super().__init__(bgcolor=ft.Colors.BLUE_GREY_50, padding=12, border_radius=8)
        self.kind = kind
        self.edit_index = edit_index
        self.ctl = ctl
        self._on_submit = on_submit
        self._on_cancel = on_cancel
        ini = initial or {}
        today = datetime.date.today()
        editing = edit_index is not None

        def tf(label, w=120, value="", on_change=None):
            return ft.TextField(label=label, width=w, value=str(value or ""),
                                dense=True, on_change=on_change)

        self.klass = tf("班級", 110, ini.get("klass"))
        self.pick_a = ft.Column(spacing=2, tight=True)
        self.pick_b = ft.Column(spacing=2, tight=True)

        if kind == "swap":
            self.ta = tf("甲老師", 110, ini.get("teacher_a") or originator,
                         on_change=lambda e: self._sync())
            self.sa = tf("甲的科目", 130, ini.get("subject_a"))
            self.da = _DateField(page, "甲原本日期", ini.get("date_a") or today, width=130,
                                 on_change=self._sync)
            self.pa = _period_dd(ini.get("period_a"))
            self.tb = tf("乙老師", 110, ini.get("teacher_b"),
                         on_change=lambda e: self._sync())
            self.sb = tf("乙的科目", 130, ini.get("subject_b"))
            self.db = _DateField(page, "乙原本日期", ini.get("date_b") or today, width=130,
                                 on_change=self._sync)
            self.pb = _period_dd(ini.get("period_b"))
            body = [
                ft.Text(("修改" if editing else "新增") + "調課", weight=ft.FontWeight.BOLD),
                _hint("甲、乙兩位老師在「同一個班」各挑一節課互換。\n"
                      "換完：甲改上乙的時段、乙改上甲的時段。"),
                ft.Row([self.klass], wrap=True),
                ft.Text("甲方（原時段）", size=12, color=_HINT),
                ft.Row([self.ta, self.sa, self.da.control, self.pa], wrap=True),
                self.pick_a,
                ft.Text("乙方（原時段）", size=12, color=_HINT),
                ft.Row([self.tb, self.sb, self.db.control, self.pb], wrap=True),
                self.pick_b,
            ]
        else:
            self.ot = tf("原老師", 110, ini.get("orig_teacher") or originator,
                         on_change=lambda e: self._sync())
            self.subj = tf("科目", 130, ini.get("subject"))
            self.dd = _DateField(page, "日期", ini.get("date") or today, width=130,
                                 on_change=self._sync)
            self.pp = _period_dd(ini.get("period"))
            self.st = tf("代課老師", 110, ini.get("sub_teacher"))
            self.from_swap = ft.Checkbox(
                label="這一節是前面「調課」調進來、之後又請假的（會反白標示）",
                value=bool(ini.get("from_swap")))
            body = [
                ft.Text(("修改" if editing else "新增") + "代課", weight=ft.FontWeight.BOLD),
                _hint("某位老師某一節不能上，找人代，時間不變。"),
                ft.Row([self.klass, self.ot, self.subj, self.dd.control, self.pp, self.st], wrap=True),
                self.pick_a,
                self.from_swap,
            ]

        self.err = ft.Text("", color=ft.Colors.RED_700)
        body.append(self.err)
        body.append(ft.Row([
            ft.Button("更新" if editing else "加入", icon=ft.Icons.CHECK, on_click=self._submit),
            ft.TextButton("取消", on_click=lambda e: self._on_cancel()),
        ]))
        self.content = ft.Column(body, spacing=8, tight=True)
        self._fill_picks()

    # ---- 課表帶入 ----
    def _sync(self, *_a) -> None:
        self._fill_picks()
        try:
            self.update()
        except Exception:
            pass

    def _fill_picks(self) -> None:
        if self.kind == "swap":
            self.pick_a.controls = self._pick_ctrls(self.ta.value, self.da, "a")
            self.pick_b.controls = self._pick_ctrls(self.tb.value, self.db, "b")
        else:
            self.pick_a.controls = self._pick_ctrls(self.ot.value, self.dd, "s")

    def _pick_ctrls(self, teacher, datefield, side) -> list:
        if self.ctl is None or not (teacher or "").strip():
            return []
        try:
            d = datefield.get()
        except ValueError:
            d = None
        slots = self.ctl.timetable_slots(teacher, d)
        if not slots:
            return []
        wd = "一二三四五"[d.weekday()]
        row = ft.Row(wrap=True, spacing=4, run_spacing=2)
        for s in slots:
            label = f"第{s.period}節 {s.subject}" + (f"／{s.klass}" if s.klass else "")
            row.controls.append(ft.OutlinedButton(
                label, on_click=lambda e, s=s, side=side: self._apply_slot(side, s)))
        return [ft.Text(f"{teacher} 星期{wd} 的課（點一下帶入）：", size=11, color=_HINT), row]

    def _apply_slot(self, side, s) -> None:
        if self.kind == "swap":
            if side == "a":
                self.sa.value, self.pa.value = s.subject, str(s.period)
            else:
                self.sb.value, self.pb.value = s.subject, str(s.period)
        else:
            self.subj.value, self.pp.value = s.subject, str(s.period)
        if s.klass:
            self.klass.value = s.klass
        self._sync()

    def _submit(self, _e) -> None:
        try:
            if self.kind == "swap":
                data = dict(
                    klass=self.klass.value or "",
                    teacher_a=self.ta.value or "", subject_a=self.sa.value or "",
                    date_a=self._req(self.da), period_a=self._period(self.pa, "甲節次"),
                    teacher_b=self.tb.value or "", subject_b=self.sb.value or "",
                    date_b=self._req(self.db), period_b=self._period(self.pb, "乙節次"),
                )
            else:
                data = dict(
                    klass=self.klass.value or "",
                    orig_teacher=self.ot.value or "", subject=self.subj.value or "",
                    date=self._req(self.dd), period=self._period(self.pp, "節次"),
                    sub_teacher=self.st.value or "",
                    from_swap=bool(self.from_swap.value),
                )
        except ValueError as exc:
            self.err.value = str(exc)
            self.err.update()
            return
        self._on_submit(self.kind, data, self.edit_index)

    @staticmethod
    def _req(df: "_DateField") -> datetime.date:
        d = df.get()
        if d is None:
            raise ValueError("日期沒填")
        return d

    @staticmethod
    def _period(dd: ft.Dropdown, label: str) -> int:
        s = str(dd.value or "").strip()
        if not s.isdigit():
            raise ValueError(f"請選{label}")
        return int(s)


class _MasterDataPanel(ft.Column):
    """常用名單維護：教師／班級／科目。"""

    _KINDS = [("teacher", "教師"), ("class", "班級"), ("subject", "科目")]

    def __init__(self, ctl, on_change) -> None:
        super().__init__(spacing=4, tight=True)
        self.ctl = ctl
        self.on_change = on_change
        self._bodies: dict[str, ft.Column] = {}
        for kind, label in self._KINDS:
            field = ft.TextField(hint_text=f"新增{label}", dense=True, expand=True)
            body = ft.Column(spacing=0, tight=True)
            self._bodies[kind] = body
            self.controls.append(ft.Row([
                field,
                ft.IconButton(ft.Icons.ADD_CIRCLE_OUTLINE, icon_size=18,
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
                    ft.IconButton(ft.Icons.CLOSE, icon_size=13,
                                  on_click=lambda e, k=kind, n=name: self._remove(k, n)),
                    ft.Text(name, size=12),
                ], tight=True, spacing=2))

    def _add(self, kind: str, field: ft.TextField) -> None:
        self.ctl.add_master(kind, field.value or "")
        field.value = ""
        self._render()
        self.on_change()

    def _remove(self, kind: str, name: str) -> None:
        self.ctl.remove_master(kind, name)
        self._render()
        self.on_change()


class _TimetableImport(ft.Column):
    """匯入教師課表 PDF → 解析 → 問要不要存 JSON。"""

    def __init__(self, ctl, settings, on_changed) -> None:
        super().__init__(spacing=4, tight=True)
        self.ctl = ctl
        self.settings = settings
        self.on_changed = on_changed
        self.pdf_path = ft.TextField(hint_text="教師課表 PDF 路徑", dense=True, expand=True)
        self.status = ft.Text("", size=11, color=_HINT)
        self.confirm = ft.Column(spacing=4, tight=True, visible=False)
        self.controls = [
            ft.Text("匯入課表", weight=ft.FontWeight.BOLD),
            _hint("讀教師課表 PDF → 填調課／代課時，該老師的課可一鍵帶入。"),
            ft.Row([self.pdf_path,
                    ft.IconButton(ft.Icons.UPLOAD_FILE, tooltip="讀取", on_click=self._read)]),
            self.status,
            self.confirm,
        ]
        self._refresh()

    def _refresh(self) -> None:
        tt = self.ctl.timetable
        if tt:
            m = sum(len(t.slots) for t in tt.teachers.values())
            where = self.settings.timetable_path or "（未存檔，關掉就沒了）"
            self.status.value = f"目前課表：{len(tt.teachers)} 位老師、{m} 筆課\n{where}"
        else:
            self.status.value = "尚未匯入課表"

    def _read(self, _e) -> None:
        path = (self.pdf_path.value or "").strip()
        if not path:
            self.status.value = "請先填 PDF 路徑"
            self.update()
            return
        self.status.value = "讀取中…"
        self.update()
        try:
            tt = self.ctl.parse_timetable_pdf(path)
        except Exception as exc:  # noqa: BLE001
            self.status.value = f"讀取失敗：{exc}"
            self.update()
            return
        m = sum(len(t.slots) for t in tt.teachers.values())
        self._json = ft.TextField(label="存成", dense=True, expand=True,
                                  value=os.path.splitext(path)[0] + ".json")
        self.confirm.controls = [
            ft.Text(f"讀到 {len(tt.teachers)} 位老師、{m} 筆課。要存成 JSON 保存嗎？"),
            self._json,
            ft.Row([
                ft.Button("存檔並套用", icon=ft.Icons.SAVE, on_click=self._save_apply),
                ft.TextButton("只套用不存", on_click=self._apply_only),
                ft.TextButton("取消", on_click=self._cancel),
            ], wrap=True),
        ]
        self.confirm.visible = True
        self.status.value = ""
        self.update()

    def _save_apply(self, _e) -> None:
        try:
            saved = self.ctl.apply_pending_timetable(save_path=(self._json.value or "").strip())
        except OSError as exc:
            self.status.value = f"存檔失敗：{exc}"
            self.update()
            return
        self.settings.timetable_path = saved or ""
        self.settings.save()
        self._finish(f"✓ 課表已存並套用：{saved}")

    def _apply_only(self, _e) -> None:
        self.ctl.apply_pending_timetable()
        self.settings.timetable_path = ""
        self.settings.save()
        self._finish("✓ 課表已套用（未存檔）")

    def _cancel(self, _e) -> None:
        self.ctl._pending_tt = None
        self.confirm.visible = False
        self._refresh()
        self.update()

    def _finish(self, msg: str) -> None:
        self.confirm.visible = False
        self._refresh()
        self.update()
        self.on_changed(msg)
