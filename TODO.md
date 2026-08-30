# TODO — 調課代課通知單產生器

狀態圖例：`[ ]` 待辦　`[~]` 進行中　`[x]` 完成

---

## P0 — 專案初始化　✅

- [x] 建立 `requirements.txt` 與 `.gitignore`
- [x] 建立套件骨架 `tiaoke/`、`tests/`（`tiaoke/ui/` 待 P2）
- [x] 範例事件改以 `tiaoke/samples.py` 的 Python 物件表示（JSON fixtures 延到 P3 storage）
- [x] 程式碼放 `class-change` repo；範例檔留在上層資料夾

## P1 — 核心邏輯（無 GUI）　✅　等 review

### models.py　✅
- [x] `Slot`（date + period；`weekday_cn` 由 date 推算）
- [x] `SwapLeg` / `SubLeg`
- [x] `Event`（originator、leave_type、form_no、announce_date、sheet_date、note、class_slip_style、legs、sheet_name_override）
- [x] `Event.sheet_name` / `effective_sheet_date` / `all_teachers` / `all_classes`
- [x] `Project`（events + 教師／班級／科目主檔 + `merge_master_data`）
- [x] `event_to_dict` / `event_from_dict` / `leg_*`（serialize，供 storage 與 fixtures）

### roc.py　✅
- [x] 民國年、星期中文、`announce_md`（補零）、`announce_line`、`slot_label`、`short_name`、`sheet_code`

### builder.py　✅
- [x] `TeacherRow` / `ClassRow` / `TeacherSlip` / `ClassSlip`
- [x] `build()`：Swap → 教師單各 +1、班級單 +2；Sub → 教師單各 +1、班級單 +1
- [x] 教師單保序；班級單排後；同師／同班多腳累積；列依時段排序
- [x] `validate()`：必填、節次 1–10、`slot_a != slot_b`、同人、重複腳

### note_draft.py　✅
- [x] 對調時段組彙整「…課務互調」；代課「{時段}由{代課老師}老師代課」
- [x] 對照 瑞文1150223 / 炆明1150831 / 代課範例 驗證措辭（見 test_note_draft）
- [ ] （P4）補「故{發起人}老師…調至…上課」等更貼近原文的敘述

### styles.py　✅
- [x] 樣式常數（欄寬、列高、字型、框線、`DATE_FMT`、頁面）
- [x] helper：`put()`、`outline_grid()`、`box()`、`set_col_widths()`

### xlsx_writer.py　✅
- [x] `_teacher_slip` / `_class_slip`（banner + title 分支）/ `_maybe_note` / `_announce_row`
- [x] `write_sheet()`：逐張輸出、張間空 1 列、欄寬／列印範圍／頁面（scale 95、A4 直向）
- [x] 被代課列 B/C/D 留空；代課者列 F/G/H 留空
- [~] 標頭多做了 `C:D`／`G:H` 合併（原檔未合併）＝刻意的視覺整理；如需完全一致再拿掉

### output.py　✅
- [x] `write_to_master`（同名工作表刪除重建）、`save_as_new`、`run(to_master, save_new 可同時)`
- [x] `TargetResult` 摘要（路徑、列數、是否覆蓋、錯誤）；Excel 開啟中 → 友善訊息

### tests　✅（24 passed）
- [x] `test_roc.py` / `test_builder.py` / `test_note_draft.py` / `test_xlsx_writer.py`
- [x] `瑞文1150223` 產出與原檔逐列比對（教師單、班級資料列完全對齊；標題式班級單完全一致）

### 里程碑　✅
- [x] CLI 煙霧測試：`python -m tiaoke.cli 瑞文1150223 -o out/x.xlsx`；肉眼比對通過 → **交付 review**

## P2 — Flet GUI　🟢　可用（持續依使用者回饋調整）

- [x] `ui/controller.py`：純邏輯控制層（事件 CRUD、腳增修刪、預覽、輸出、匯出全部、名稱進主檔）＋單元測試
- [x] `ui/app.py`：左＝調代課單清單＋進階（專案存檔／常用名單），右＝① 基本資料 ② 異動明細 ③ 說明 ④ 產生，頂部「怎麼用」說明卡
- [x] 事件 CRUD（新增／複製／刪除／選取）
- [x] 大量欄位說明文字（每段 hint）
- [x] 假別：常用 RadioGroup ＋「或自行輸入」文字框
- [x] 日期：可手打，也可按日曆鈕（`_DateField` + `ft.DatePicker`）
- [x] 節次：下拉 1–10
- [x] 腳：新增／**修改（✏）**／刪除；甲老師・原老師自動帶入發起教師
- [x] 說明「自動產生草稿」
- [x] 預覽即時；輸出＝☑另存新檔 ☑寫入總表（單鍵、可同時）
- [x] 專案儲存＝同時存 `.json`（可再編）＋ `.xlsx`（全部單合成一個 Excel）；另有「只匯出全部成 Excel」鈕
- [x] 冒煙測試：假 Page + 真 Flet runtime；add→edit 流程
- [ ] 檔案「瀏覽」對話框（目前手動貼路徑；FilePicker API 待處理）
- [ ] 批次代課／批次對調 UI（`add_sub_batch` 已有）
- [ ] 老師／班級／科目 輸入自動完成
- [ ] 「開啟產生的檔案／資料夾」按鈕
- [ ] 實機視覺再微調

## P3 — 收尾　🟡

- [x] `storage.py`：專案 `.json` 存讀（`project_to/from_dict`）；`AppSettings`（`%APPDATA%\tiaoke\settings.json`）＋最近檔案清單
- [x] 主檔管理：左側 `_MasterDataPanel`（教師／班級／科目 新增刪除）＋ controller `add/remove_master`
- [x] 設定：預設總表路徑、記住視窗大小、上次專案；產生時自動記住總表路徑
- [x] 左側「開啟／儲存／新專案」；腳新增時名稱自動進主檔
- [x] `BUILD.md`：flet pack / PyInstaller 打包說明
- [x] 測試：`test_storage.py`（專案 round-trip、settings、主檔）；全 39 測試通過
- [ ] `assets/icon.ico` 待提供
- [ ] 實機打包驗證（需 Windows + flet[all]）
- [ ] 使用說明（截圖）＋ 視窗關閉事件存設定（目前 `window.on_close` 於此 flet 版本未保證觸發）

## P4 — 複合事件　🟡

- [x] 「先對調再代課」：以 `SubLeg(from_swap=True)` 標記調入後又請假的時段
- [x] 反白列樣式（`HIGHLIGHT_FILL` 淡金色）套用於教師單／班級單該列
- [x] J 欄代課老師簡稱（末兩字，紅字）於教師單原老師那張
- [x] GUI 代課表單加「此節原為調課調入」核取；序列化保留 `from_swap`
- [x] `test_p4.py`；全 43 測試通過
- [x] ~~教師單列排序完全對齊 炆明1150831~~ →（使用者：不用管這個範例）
- [x] ~~反白色對齊原檔佈景主題色~~ →（使用者：不用管這個範例）
- [ ] GUI「調課後又請假」一鍵：選一個既有調課腳 → 自動帶出對應 SubLeg（可選）

---

## 待釐清問題

### 已決（2026-08-30）
- [x] 分頁名稱日期 → **GUI 由使用者選**，預設帶所有腳最早日期
- [x] 公告日期 → **合併寫法** `H="公告日期：{民國年}年"`、`I="{M月D日}"`
- [x] 假單編號 `2015+手動` → **單一自由文字欄位**，不拆數字
- [x] 節次範圍 → **1–10**
- [x] 一對多（多人調課／代課）→ 以「一事件多腳」表示，builder 已支援；GUI 加批次輸入

### 已決（2026-08-30，第二輪）
- [x] 總表檔每學期一個／新學期精靈 → **不用**
- [x] 「兼課」老師特殊呈現 → **先不用**（當普通教師姓名）
- [x] 教師單「* 請…公佈」結尾 → **不用**（維持僅班級單有）
- [x] 假別選項（公假／病假／事假／喪假／生理假／請假／其他）→ **足夠**
- [x] P4 教師單列排序 / 反白色完全比照 炆明1150831 → **不用**
