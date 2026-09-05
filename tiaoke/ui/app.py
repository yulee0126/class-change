"""Flet GUI。邏輯都在 controller.py（有單元測試），這裡只做畫面。"""

from __future__ import annotations

import base64
import datetime
import os
import re
import sys

import flet as ft

from .. import paths, roc
from ..models import CLASS_SLIP_STYLES, LEAVE_TYPES
from ..storage import AppSettings
from .controller import DEFAULT_FORM_NO, AppController

_STYLE_LABELS = {"banner": "橫幅式（每張單抬頭一整條）", "title": "標題式（抬頭置中）"}
_HINT = ft.Colors.BLUE_GREY_600
_FIRST = datetime.date(2020, 1, 1)
_LAST = datetime.date(2035, 12, 31)

def _asset(name: str) -> str:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(meipass, "assets", name)
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(root, "assets", name)


def _logo_src() -> str | None:
    try:
        with open(_asset("logo64.png"), "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except OSError:
        return None


def main(page: ft.Page) -> None:
    page.title = "調課代課通知單產生器"
    page.padding = 12
    try:
        page.window.icon = _asset("icon.ico")
    except Exception:
        pass
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
        self._dp = ft.DatePicker(
            value=datetime.datetime(cur.year, cur.month, cur.day, 12),
            first_date=datetime.datetime(_FIRST.year, _FIRST.month, _FIRST.day),
            last_date=datetime.datetime(_LAST.year, _LAST.month, _LAST.day),
            on_change=self._picked, on_dismiss=self._close)
        try:
            self.page.show_dialog(self._dp)
        except Exception:
            self.page.overlay.append(self._dp)
            self._dp.open = True
            self.page.update()

    def _close(self, *_a) -> None:
        try:
            self.page.pop_dialog()
        except Exception:
            pass

    def _picked(self, e) -> None:
        d = _event_date(e)
        self._close()
        if d is None:
            return
        self.field.value = roc.format_date_input(d)
        _safe_update(self.field)
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

        # 記錄檔資料夾：設定裡有且存在就用它，否則用 exe/專案 旁邊的 record（可攜）
        rf = self.settings.record_folder
        if not rf or not os.path.isdir(rf):
            rf = paths.record_dir()
        self.settings.record_folder = rf
        self.ctl.record_folder = rf

        # 課表：設定裡的檔在就載入，否則試 exe 旁邊 bundle 的課表 JSON
        tt_path = self.settings.timetable_path
        if not tt_path or not os.path.exists(tt_path):
            tt_path = paths.default_timetable_path()
        if tt_path and os.path.exists(tt_path):
            try:
                self.ctl.load_timetable(tt_path)
                self.settings.timetable_path = tt_path
            except Exception:
                pass

        try:
            page.window.width = self.settings.window_width
            page.window.height = self.settings.window_height
            page.window.on_close = self._on_window_close
        except Exception:
            pass

        self.status = ft.Text("", color=ft.Colors.BLUE_GREY_800, selectable=True)

        # 調代課單輸出資料夾：設定裡有且存在就用它，否則用 exe/專案 旁邊的「調代課單」（可攜）
        sf = self.settings.slips_folder
        if not sf or not os.path.isdir(sf):
            sf = paths.slips_dir()
        self.settings.slips_folder = sf

        self.slips_folder = ft.TextField(
            label="調代課單資料夾", dense=True, value=sf,
            on_change=self._on_slips_folder_change)
        self.record_folder = ft.TextField(
            label="報表存放資料夾", dense=True, value=self.settings.record_folder,
            on_change=self._on_record_folder_change)
        self.event_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self.editor = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self._leg_form: _LegForm | None = None

        _logo = _logo_src()
        _title_row = ft.Row(
            ([ft.Image(src=_logo, width=26, height=26, border_radius=4)] if _logo else []) +
            [ft.Text("調代課單", weight=ft.FontWeight.BOLD, size=16)],
            spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        left = ft.Container(
            width=250,
            content=ft.Column([
                _title_row,
                _hint("一張單 = Excel 裡的一個分頁。\n一次調代課（含好幾筆對調／代課）做成一張。"),
                ft.Row([
                    ft.Button("新增一張", icon=ft.Icons.ADD, on_click=self._on_new),
                    ft.IconButton(ft.Icons.CONTENT_COPY, tooltip="複製這張", on_click=self._on_dup),
                    ft.IconButton(ft.Icons.DELETE, tooltip="刪除這張", on_click=self._on_del),
                ]),
                self.event_list,
                ft.Divider(),
                ft.ExpansionTile(
                    title=ft.Text("進階：搜尋檔案．產製報表．課表匯入／校對"),
                    tile_padding=ft.Padding(0, 0, 0, 0),
                    controls=[
                        self.slips_folder,
                        _SlipSearch(self.ctl, self.slips_folder, self._on_file_loaded),
                        ft.Divider(),
                        _hint("掃「調代課單資料夾」內所有檔案，重新算一份記錄檔（帶時間戳記，\n"
                              "不覆蓋舊檔）。檔名前綴 ~~ 的視為作廢，會略過。"),
                        self.record_folder,
                        ft.Button("產製報表", icon=ft.Icons.SUMMARIZE,
                                  on_click=self._on_generate_report),
                        ft.Divider(),
                        _TimetableImport(self.ctl, self.settings, self._on_tt_changed),
                        ft.Divider(),
                        _TimetableEditor(self.ctl, self.settings, self._on_tt_changed),
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
        self._orig_field = _NameField(
            "發起教師", ev.originator, self._all_teacher_names(), width=170,
            on_change=lambda: self._set(originator=self._orig_field.value))
        f_form = ft.TextField(label="假單編號", value=ev.form_no or DEFAULT_FORM_NO, width=190,
                              on_change=lambda e: self._set(form_no=e.control.value))
        f_sys_form = ft.TextField(label="系統假單編號", value=ev.system_form_no, width=140,
                                  on_change=lambda e: self._set(system_form_no=e.control.value))
        self._ann_date = _DateField(self.page, "公告日期", ev.announce_date,
                                    on_change=lambda: self._pull_ann_date())
        self.editor.controls.append(ft.Row(
            [self._orig_field.control, f_form, f_sys_form, self._ann_date.control], wrap=True,
            vertical_alignment=ft.CrossAxisAlignment.START))
        self.editor.controls.append(_hint(
            "發起教師＝因為誰請假／要調課而發起這次異動（通知單抬頭會出現，也會自動帶進下面的甲老師／原老師）。\n"
            "假單編號＝請假系統的單號，自己打，例如「手動+1076」「2015+手動」；會印在通知單橫幅上。\n"
            "系統假單編號＝只用來組輸出檔名（{系統假單編號}-{分頁名稱}.xlsx），不會印在通知單上，可留空。\n"
            "公告日期＝通知單「公告日期」欄要印的日期。"))

        # 假別：常用選項 + 可自訂
        custom_leave = "" if ev.leave_type in LEAVE_TYPES else ev.leave_type
        self._rg_leave = ft.RadioGroup(
            value=ev.leave_type if ev.leave_type in LEAVE_TYPES else None,
            content=ft.Row([ft.Radio(value=x, label=x) for x in LEAVE_TYPES], wrap=True),
            on_change=self._on_leave_radio)
        self._tf_leave = ft.TextField(label="或自行輸入假別", width=200, value=custom_leave,
                                      dense=True, on_change=self._on_leave_custom)
        self.editor.controls.append(ft.Row([ft.Text("假別："), self._rg_leave], wrap=True))
        self.editor.controls.append(ft.Row([self._tf_leave]))

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
            ft.Button("＋ 先調再代", icon=ft.Icons.SYNC_PROBLEM,
                      on_click=lambda e: self._open_leg_form("swapsub")),
        ], wrap=True))
        self.editor.controls.append(_hint(
            "先調再代＝甲老師把某節課調到新時段後，那節新時段再請人代（因為甲要請假）。"
            "一次會產生「1 筆調課 + 1 筆代課」。"))
        summaries = self.ctl.leg_summaries()
        if not summaries:
            self.editor.controls.append(_hint("（還沒加，先按上面按鈕）"))
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
        src_path = getattr(ev, "_source_path", None)
        self.tf_new = ft.TextField(label="存到", value=src_path or self.ctl.default_new_path(),
                                   expand=True, dense=True)
        self.editor.controls.append(self.tf_new)
        if src_path:
            self.editor.controls.append(_hint(
                f"這張是從既有檔案讀回來的：{src_path}\n"
                "按下面按鈕存檔前會先跟你確認（存回原檔＝覆蓋；改檔名＝刪掉原檔存新檔名）。"))
        else:
            self.editor.controls.append(_hint(
                "產生這張單的 Excel。要統計代課／調課明細，用左側進階的「產製報表」\n"
                "（掃 調代課單 資料夾內所有檔案現算，不是每張單各自累加）。"))
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

    def _on_leave_radio(self, e) -> None:
        value = (e.control.value or "").strip()
        if not value:
            return
        self.ctl.update_event_fields(leave_type=value)
        # 選了常用選項就清掉自訂欄
        self._tf_leave.value = ""
        _safe_update(self._tf_leave)

    def _on_leave_custom(self, e) -> None:
        text = (e.control.value or "").strip()
        if not text:
            return
        self.ctl.update_event_fields(leave_type=text)
        # 取消常用選項的選取（不重繪整頁，避免打字時失焦）
        if self._rg_leave.value is not None:
            self._rg_leave.value = None
            _safe_update(self._rg_leave)

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
            elif kind == "swapsub":
                self.ctl.add_swap_then_sub(**data)
            else:
                self.ctl.add_sub_leg(**data)
        except (ValueError, KeyError) as exc:
            self._set_status(f"存不進去：{exc}")
            return
        self._leg_form = None
        msg = "已更新一筆。" if edit_index is not None else (
            "已加入 1 筆調課 + 1 筆代課。" if kind == "swapsub" else "已加入一筆。")
        self._set_status(msg)
        self.refresh()

    def _on_generate(self, _e) -> None:
        dest = (self.tf_new.value or "").strip()
        if not dest:
            self._set_status("請先填「存到」的路徑。")
            return
        src = getattr(self.ctl.current, "_source_path", None)
        if src:
            self._confirm_resave(src, dest)
        else:
            self._do_generate(dest)

    def _confirm_resave(self, src: str, dest: str) -> None:
        if os.path.abspath(src) == os.path.abspath(dest):
            self._show_confirm("確定覆蓋原檔？", [f"會覆蓋：{dest}"],
                               lambda: self._do_resave(dest))
        else:
            self._show_confirm("確定另存新檔名？",
                               [f"會刪除原檔：{src}", f"另存為：{dest}"],
                               lambda: self._do_resave(dest))

    def _do_resave(self, dest: str) -> None:
        try:
            result = self.ctl.resave_loaded_file(dest)
        except ValueError as exc:
            self._show_dialog("還不能存檔", [str(exc)])
            self._set_status(str(exc))
            return
        if result.ok:
            self._show_dialog("已存回", [f"✓ {result.path}"])
            self._set_status(f"✓ 已存回：{result.path}")
        else:
            self._show_dialog("存檔失敗", [f"✗ {result.error}"])
            self._set_status(f"✗ {result.error}")
        self.refresh()

    def _do_generate(self, dest: str) -> None:
        try:
            results = self.ctl.generate(
                to_master=False, save_new=True, dest_path=dest,
            )
        except ValueError as exc:
            self._show_dialog("還不能產生", [str(exc)])
            self._set_status(str(exc))
            return
        ok_lines, err_lines = [], []
        for r in results:
            if r.ok:
                ok_lines.append(f"✓ 通知單 Excel\n{r.path}")
            else:
                err_lines.append(f"✗ {r.error}")

        title = "已產生 Excel" if ok_lines and not err_lines else (
            "部分未成功" if ok_lines else "產生失敗")
        self._show_dialog(title, ok_lines + err_lines)
        self._set_status("　｜　".join(l.replace("\n", " ") for l in ok_lines + err_lines))
        self.refresh()

    # ---- 結果對話框 ----
    def _show_dialog(self, title: str, lines: list[str]) -> None:
        self._dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Column([ft.Text(l, selectable=True) for l in lines],
                              tight=True, width=560, spacing=6),
            actions=[ft.TextButton("好", on_click=lambda e: self._close_dialog())],
        )
        try:
            self.page.show_dialog(self._dlg)
        except Exception:
            self.page.overlay.append(self._dlg)
            self._dlg.open = True
            self.page.update()

    def _show_confirm(self, title: str, lines: list[str], on_confirm) -> None:
        def _yes(_e):
            self._close_dialog()
            on_confirm()

        self._dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Column([ft.Text(l, selectable=True) for l in lines],
                              tight=True, width=560, spacing=6),
            actions=[
                ft.TextButton("取消", on_click=lambda e: self._close_dialog()),
                ft.Button("確定", on_click=_yes,
                         style=ft.ButtonStyle(bgcolor=ft.Colors.RED_600, color=ft.Colors.WHITE)),
            ],
        )
        try:
            self.page.show_dialog(self._dlg)
        except Exception:
            self.page.overlay.append(self._dlg)
            self._dlg.open = True
            self.page.update()

    def _close_dialog(self) -> None:
        try:
            self.page.pop_dialog()
        except Exception:
            if getattr(self, "_dlg", None):
                self._dlg.open = False
        self.page.update()

    def _all_teacher_names(self) -> list[str]:
        names = set(self.ctl.timetable_teacher_names())
        names.update(self.ctl.project.teachers)
        return sorted(names)

    def _on_tt_changed(self, msg: str) -> None:
        self._set_status(msg)
        self.refresh()

    def _on_record_folder_change(self, e) -> None:
        folder = (e.control.value or "").strip()
        self.ctl.record_folder = folder
        self.settings.record_folder = folder
        self.settings.save()

    def _on_slips_folder_change(self, e) -> None:
        self.settings.slips_folder = (e.control.value or "").strip()
        self.settings.save()

    def _on_file_loaded(self, msg: str) -> None:
        self._leg_form = None
        self._set_status(msg)
        self.refresh()

    def _on_generate_report(self, _e) -> None:
        rep = self.ctl.generate_report(self.slips_folder.value or "",
                                       self.record_folder.value or "")
        if not rep.ok:
            self._show_dialog("產製報表失敗", [rep.error])
            self._set_status(f"✗ {rep.error}")
            return
        lines = [f"✓ {rep.files_ok} 個檔案、{rep.rows} 筆明細", f"存到：{rep.path}"]
        if rep.files_failed:
            lines.append(f"以下 {len(rep.files_failed)} 筆解析失敗，未計入：")
            lines.extend(f"　{f}" for f in rep.files_failed)
        self._show_dialog("已產製報表", lines)
        self._set_status(str(rep))

    def _on_window_close(self, _e) -> None:
        try:
            self.settings.window_width = int(self.page.window.width)
            self.settings.window_height = int(self.page.window.height)
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


class _NameField:
    """老師姓名輸入框：邊打邊從名單過濾出建議，點一下帶入；名單沒有的也能直接打。"""

    def __init__(self, label: str, value: str, names: list[str], width: int = 110,
                 on_change=None) -> None:
        self.names = names
        self._extra = on_change
        self.field = ft.TextField(label=label, width=width, value=str(value or ""),
                                  dense=True, on_change=self._typed)
        self.sug = ft.Row(wrap=True, spacing=3, run_spacing=2)
        self.control = ft.Column([self.field, self.sug], spacing=1, tight=True)

    @property
    def value(self) -> str:
        return self.field.value or ""

    def _typed(self, _e=None) -> None:
        self._rebuild()
        _safe_update(self.sug)
        if self._extra:
            self._extra()

    def _rebuild(self) -> None:
        q = (self.field.value or "").strip()
        ctrls: list = []
        if q and q not in self.names:
            for n in [x for x in self.names if q in x][:8]:
                ctrls.append(ft.TextButton(n, on_click=lambda e, n=n: self._pick(n)))
        self.sug.controls = ctrls

    def _pick(self, name: str) -> None:
        self.field.value = name
        self.sug.controls = []
        _safe_update(self.field)
        _safe_update(self.sug)
        if self._extra:
            self._extra()


def _safe_update(ctrl) -> None:
    try:
        ctrl.update()
    except Exception:
        pass


def _event_date(e) -> datetime.date | None:
    """從 DatePicker on_change 事件取出「使用者按的那一天」。

    Flet 會把選到的日期序列化成 UTC ISO 字串（帶 Z），若直接取字串前 10 碼
    會在 UTC+8 少一天。作法：連同時區資訊解析 → 轉回本地時區 → 取 date。
    """
    for cand in (getattr(e, "data", None),
                 getattr(getattr(e, "control", None), "value", None)):
        d = _coerce_local_date(cand)
        if d is not None:
            return d
    return None


def _coerce_local_date(v) -> datetime.date | None:
    if isinstance(v, datetime.datetime):
        dt = v
    elif isinstance(v, datetime.date):
        return v
    elif isinstance(v, str):
        s = v.strip().strip('"')
        if not s:
            return None
        try:
            dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
            if not m:
                return None
            try:
                return datetime.date(int(m[1]), int(m[2]), int(m[3]))
            except ValueError:
                return None
    else:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone()          # → 本地時區
    return dt.date()


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

        def tf(label, w=120, value=""):
            return ft.TextField(label=label, width=w, value=str(value or ""), dense=True)

        names = self._teacher_names()

        def nf(label, value):
            return _NameField(label, value, names, 110, on_change=self._sync)

        self.klass = tf("班級", 110, ini.get("klass"))
        self.pick_a = ft.Column(spacing=2, tight=True)
        self.pick_b = ft.Column(spacing=2, tight=True)

        if kind in ("swap", "swapsub"):
            self.ta = nf("甲老師", ini.get("teacher_a") or originator)
            self.sa = tf("甲的科目", 130, ini.get("subject_a"))
            self.da = _DateField(page, "甲原本日期", ini.get("date_a") or today, width=130,
                                 on_change=self._sync)
            self.pa = _period_dd(ini.get("period_a"))
            self.tb = nf("乙老師", ini.get("teacher_b"))
            self.sb = tf("乙的科目", 130, ini.get("subject_b"))
            self.db = _DateField(page, "乙原本日期", ini.get("date_b") or today, width=130,
                                 on_change=self._sync)
            self.pb = _period_dd(ini.get("period_b"))
            if kind == "swapsub":
                self.stx = nf("代課老師", "")
                body = [
                    ft.Text("先調再代", weight=ft.FontWeight.BOLD),
                    _hint("甲老師把「甲方」這節課調到「乙方」的時段後，那節（乙方時段）"
                          "再請代課老師代（因為甲要請假）。會產生 1 筆調課 + 1 筆代課。"),
                ]
            else:
                self.stx = None
                body = [
                    ft.Text(("修改" if editing else "新增") + "調課", weight=ft.FontWeight.BOLD),
                    _hint("甲、乙兩位老師在「同一個班」各挑一節課互換。\n"
                          "換完：甲改上乙的時段、乙改上甲的時段。"),
                ]
            body += [
                ft.Row([self.klass], wrap=True),
                ft.Text("甲方（原時段）", size=12, color=_HINT),
                ft.Row([self.ta.control, self.sa, self.da.control, self.pa], wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.START),
                self.pick_a,
                ft.Text("乙方（原時段）", size=12, color=_HINT),
                ft.Row([self.tb.control, self.sb, self.db.control, self.pb], wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.START),
                self.pick_b,
            ]
            if self.stx is not None:
                body += [
                    ft.Text("調到乙方時段後，那節由誰代", size=12, color=_HINT),
                    ft.Row([self.stx.control], wrap=True),
                ]
        else:
            self.ot = nf("原老師", ini.get("orig_teacher") or originator)
            self.subj = tf("科目", 130, ini.get("subject"))
            self.dd = _DateField(page, "日期", ini.get("date") or today, width=130,
                                 on_change=self._sync)
            self.pp = _period_dd(ini.get("period"))
            self.st = nf("代課老師", ini.get("sub_teacher"))
            self.from_swap = ft.Checkbox(
                label="這一節是前面「調課」調進來、之後又請假的（會反白標示）",
                value=bool(ini.get("from_swap")))
            body = [
                ft.Text(("修改" if editing else "新增") + "代課", weight=ft.FontWeight.BOLD),
                _hint("某位老師某一節不能上，找人代，時間不變。"),
                ft.Row([self.klass, self.ot.control, self.subj, self.dd.control, self.pp,
                        self.st.control], wrap=True,
                       vertical_alignment=ft.CrossAxisAlignment.START),
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

    def _teacher_names(self) -> list[str]:
        if self.ctl is None:
            return []
        names = set(self.ctl.timetable_teacher_names())
        names.update(self.ctl.project.teachers)
        return sorted(names)

    # ---- 課表帶入 ----
    def _sync(self, *_a) -> None:
        self._fill_picks()
        try:
            self.update()
        except Exception:
            pass

    def _fill_picks(self) -> None:
        if self.kind in ("swap", "swapsub"):
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
        # 乙方：和甲同一班的課用紅色 highlight，並排前面
        want = (self.klass.value or "").strip() if (
            self.kind in ("swap", "swapsub") and side == "b") else ""
        if want:
            slots = sorted(slots, key=lambda s: s.klass != want)
        row = ft.Row(wrap=True, spacing=4, run_spacing=2)
        for s in slots:
            label = f"第{s.period}節 {s.subject}" + (f"／{s.klass}" if s.klass else "")
            if want and s.klass == want:
                btn = ft.Button(label, on_click=lambda e, s=s, side=side: self._apply_slot(side, s),
                                style=ft.ButtonStyle(bgcolor=ft.Colors.RED_100,
                                                     color=ft.Colors.RED_900))
            else:
                btn = ft.OutlinedButton(
                    label, on_click=lambda e, s=s, side=side: self._apply_slot(side, s))
            row.controls.append(btn)
        cap = f"{teacher} 星期{wd} 的課（點一下帶入）"
        if want:
            cap += f"；🔴 = 和甲同一班（{want}）"
        return [ft.Text(cap + "：", size=11, color=_HINT), row]

    def _apply_slot(self, side, s) -> None:
        if self.kind in ("swap", "swapsub"):
            if side == "a":
                self.sa.value, self.pa.value = s.subject, str(s.period)
                # 甲定了班級 → 乙方 highlight 依此更新
                if s.klass:
                    self.klass.value = s.klass
            else:
                self.sb.value, self.pb.value = s.subject, str(s.period)
        else:
            self.subj.value, self.pp.value = s.subject, str(s.period)
            if s.klass:
                self.klass.value = s.klass
        self._sync()

    def _submit(self, _e) -> None:
        try:
            if self.kind in ("swap", "swapsub"):
                data = dict(
                    klass=self.klass.value or "",
                    teacher_a=self.ta.value or "", subject_a=self.sa.value or "",
                    date_a=self._req(self.da), period_a=self._period(self.pa, "甲節次"),
                    teacher_b=self.tb.value or "", subject_b=self.sb.value or "",
                    date_b=self._req(self.db), period_b=self._period(self.pb, "乙節次"),
                )
                if self.kind == "swapsub":
                    st = (self.stx.value or "").strip()
                    if not st:
                        raise ValueError("請填代課老師")
                    data["sub_teacher"] = st
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


class _SlipSearch(ft.Column):
    """搜尋「調代課單資料夾」內的既有檔案，邊打邊列出符合的檔名，點一下讀回來編輯。"""

    def __init__(self, ctl, folder_field: ft.TextField, on_loaded) -> None:
        super().__init__(spacing=4, tight=True)
        self.ctl = ctl
        self.folder_field = folder_field
        self.on_loaded = on_loaded
        self.query = ft.TextField(hint_text="打檔名關鍵字…", dense=True, expand=True,
                                  on_change=self._typed)
        self.results = ft.Column(spacing=1, tight=True)
        self.status = ft.Text("", size=11, color=_HINT)
        self.controls = [
            ft.Text("搜尋檔案", weight=ft.FontWeight.BOLD),
            _hint("邊打邊列出「調代課單資料夾」內符合的檔名，點一下讀回來編輯。\n"
                  "讀回後在右側修改，按「產生 Excel」存檔時會先問要覆蓋還是另存新檔名。"),
            self.query,
            self.results,
            self.status,
        ]

    def _typed(self, _e=None) -> None:
        folder = (self.folder_field.value or "").strip()
        q = (self.query.value or "").strip()
        names = self.ctl.list_slip_files(folder)
        if q:
            names = [n for n in names if q in n]
        self.results.controls = [
            ft.TextButton(n, on_click=lambda e, n=n: self._pick(folder, n))
            for n in names[:15]
        ]
        _safe_update(self.results)

    def _pick(self, folder: str, name: str) -> None:
        path = os.path.join(folder, name)
        try:
            ev = self.ctl.load_event_from_file(path)
        except Exception as exc:  # noqa: BLE001 - 讀不回來要能顯示原因，什麼錯誤都接
            self.status.value = f"讀取失敗：{exc}"
            _safe_update(self.status)
            return
        self.status.value = f"已讀回：{name}（{len(ev.legs)} 筆異動），可在右側編輯。"
        _safe_update(self.status)
        self.on_loaded(f"已讀回 {name}")


class _TimetableImport(ft.Column):
    """匯入教師課表 PDF → 解析 → 問要不要存 JSON。"""

    def __init__(self, ctl, settings, on_changed) -> None:
        super().__init__(spacing=4, tight=True)
        self.ctl = ctl
        self.settings = settings
        self.on_changed = on_changed
        self.pdf_path = ft.TextField(hint_text="教師課表 PDF 路徑", dense=True, expand=True)
        self.co_path = ft.TextField(hint_text="教師配當表路徑（協同教學）", dense=True, expand=True)
        self.status = ft.Text("", size=11, color=_HINT)
        self.confirm = ft.Column(spacing=4, tight=True, visible=False)
        self.controls = [
            ft.Text("匯入課表", weight=ft.FontWeight.BOLD),
            _hint("讀教師課表 PDF → 填調課／代課時，該老師的課可一鍵帶入。"),
            ft.Row([self.pdf_path,
                    ft.IconButton(ft.Icons.UPLOAD_FILE, tooltip="讀取", on_click=self._read)]),
            _hint("讀教師配當表（.xlsx，需先匯入課表）→ 比對出「協同」課的節次，\n"
                  "調課／代課表單會自動帶出協同老師。讀完會直接存回目前的課表 JSON。"),
            ft.Row([self.co_path,
                    ft.IconButton(ft.Icons.UPLOAD_FILE, tooltip="讀取並套用",
                                  on_click=self._read_co_teaching)]),
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
        default_name = os.path.splitext(os.path.basename(path))[0] + ".json"
        self._json = ft.TextField(label="存成", dense=True, expand=True,
                                  value=os.path.join(paths.app_dir(), default_name))
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

    def _read_co_teaching(self, _e) -> None:
        path = (self.co_path.value or "").strip()
        if not path:
            self.status.value = "請先填配當表路徑"
            _safe_update(self)
            return
        try:
            touched = self.ctl.parse_co_teaching(path)
        except Exception as exc:  # noqa: BLE001
            self.status.value = f"讀取失敗：{exc}"
            _safe_update(self)
            return
        msg = f"已標記 {touched} 個節次為協同教學"
        saved_path = self.settings.timetable_path
        if saved_path:
            try:
                self.ctl.save_timetable_to(saved_path)
                msg += f"，已存回 {saved_path}"
            except OSError as exc:
                msg += f"（存回課表檔失敗：{exc}）"
        else:
            msg += "（目前課表還沒存檔，關掉程式就沒了）"
        self.status.value = msg
        _safe_update(self)
        self.on_changed(msg)

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


_WEEKDAY_LABELS = ["一", "二", "三", "四", "五"]


class _TimetableEditor(ft.Column):
    """課表校對：選老師、選星期 → 逐節核對／修改，存回課表 JSON。"""

    def __init__(self, ctl, settings, on_changed) -> None:
        super().__init__(spacing=4, tight=True)
        self.ctl = ctl
        self.settings = settings
        self.on_changed = on_changed
        self.weekday = 1
        self._edit_period: int | None = None

        self.teacher = _NameField("老師", "", ctl.timetable_teacher_names(),
                                  width=170, on_change=self._on_teacher_change)
        self.wd_row = ft.Row(spacing=2, wrap=True)
        self.body = ft.Column(spacing=2, tight=True)
        self.save_path = ft.TextField(label="存到", dense=True, expand=True,
                                      value=settings.timetable_path)
        self.status = ft.Text("", size=11, color=_HINT)

        self.controls = [
            ft.Text("課表校對", weight=ft.FontWeight.BOLD),
            _hint("選老師、選星期 → 逐節核對／修改科目・班級・地點・備註（例如 (兼)、(輔)）。"),
            self.teacher.control,
            self.wd_row,
            self.body,
            ft.Row([self.save_path,
                    ft.IconButton(ft.Icons.SAVE, tooltip="存回課表檔", on_click=self._save)]),
            self.status,
        ]
        self._render_weekdays()
        self._render_body()

    # ---- 畫面 ----------------------------------------------------
    def _render_weekdays(self) -> None:
        self.wd_row.controls = [
            ft.TextButton(
                f"星期{lab}", on_click=lambda e, w=i + 1: self._pick_weekday(w),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_100 if self.weekday == i + 1 else None),
            )
            for i, lab in enumerate(_WEEKDAY_LABELS)
        ]

    def _render_body(self) -> None:
        self.body.controls.clear()
        name = self.teacher.value.strip()
        if not name:
            self.body.controls.append(_hint("先選一位老師。"))
            return
        table = self.ctl.timetable_teacher_table(name)
        for period in range(1, 11):
            slots = table.slot_group(self.weekday, period) if table else []
            self.body.controls.append(self._row(period, slots))
            if self._edit_period == period:
                self.body.controls.append(self._edit_form(period, slots))

    def _row(self, period: int, slots: list) -> ft.Control:
        if slots:
            klass = "、".join(s.klass for s in slots if s.klass)
            note = f" {slots[0].note}" if slots[0].note else ""
            label = f"第{period}節　{slots[0].subject}" + (f"／{klass}" if klass else "") + note
        else:
            label = f"第{period}節　（空）"
        return ft.Row([
            ft.IconButton(ft.Icons.EDIT_OUTLINED, icon_size=16, tooltip="編輯這節",
                          on_click=lambda e, p=period: self._open_edit(p)),
            ft.Text(("✏ " if self._edit_period == period else "") + label,
                    size=12, selectable=True),
        ])

    def _edit_form(self, period: int, slots: list) -> ft.Control:
        f_subj = ft.TextField(label="科目", value=slots[0].subject if slots else "",
                              dense=True, width=150)
        f_klass = ft.TextField(label="班級（合班用、分隔）",
                               value="、".join(s.klass for s in slots) if slots else "",
                               dense=True, width=190)
        f_loc = ft.TextField(label="地點", value=slots[0].location if slots else "",
                             dense=True, width=120)
        f_note = ft.TextField(label="備註（如 (兼)、(輔)）",
                              value=slots[0].note if slots else "", dense=True, width=160)
        actions = [
            ft.Button("儲存", icon=ft.Icons.SAVE,
                      on_click=lambda e: self._save_slot(period, f_subj, f_klass, f_loc, f_note)),
        ]
        if slots:
            actions.append(ft.TextButton("刪除這節", icon=ft.Icons.DELETE_OUTLINE,
                                         on_click=lambda e: self._delete_slot(period)))
        actions.append(ft.TextButton("取消", on_click=lambda e: self._cancel_edit()))
        return ft.Container(
            padding=8, bgcolor=ft.Colors.BLUE_GREY_50, border_radius=6,
            content=ft.Column([
                ft.Row([f_subj, f_klass], wrap=True),
                ft.Row([f_loc, f_note], wrap=True),
                ft.Row(actions, wrap=True),
            ], spacing=4, tight=True),
        )

    # ---- 事件 ----------------------------------------------------
    def _pick_weekday(self, wd: int) -> None:
        self.weekday = wd
        self._edit_period = None
        self._render_weekdays()
        self._render_body()
        _safe_update(self)

    def _on_teacher_change(self) -> None:
        self._edit_period = None
        self._render_body()
        _safe_update(self)

    def _open_edit(self, period: int) -> None:
        self._edit_period = period
        self._render_body()
        _safe_update(self)

    def _cancel_edit(self) -> None:
        self._edit_period = None
        self._render_body()
        _safe_update(self)

    def _save_slot(self, period: int, f_subj, f_klass, f_loc, f_note) -> None:
        name = self.teacher.value.strip()
        if not name:
            return
        klasses = [k for k in re.split(r"[、/／,，]", f_klass.value or "") if k.strip()]
        self.ctl.edit_timetable_slot(
            name, self.weekday, period,
            subject=f_subj.value or "", klasses=klasses,
            location=f_loc.value or "", note=f_note.value or "",
        )
        self._edit_period = None
        self._render_body()
        _safe_update(self)
        self.on_changed("已更新課表（記得按存檔存回課表檔）")

    def _delete_slot(self, period: int) -> None:
        name = self.teacher.value.strip()
        if name:
            self.ctl.delete_timetable_slot(name, self.weekday, period)
        self._edit_period = None
        self._render_body()
        _safe_update(self)
        self.on_changed("已刪除該節（記得按存檔存回課表檔）")

    def _save(self, _e) -> None:
        path = (self.save_path.value or "").strip()
        if not path:
            self.status.value = "請先填存檔路徑"
            _safe_update(self.status)
            return
        saved = self.ctl.save_timetable_to(path)
        if saved:
            self.settings.timetable_path = saved
            self.settings.save()
            self.status.value = f"✓ 已存回：{saved}"
        else:
            self.status.value = "沒有課表可存（請先匯入或編輯至少一節）"
        _safe_update(self.status)
        self.on_changed(self.status.value)
