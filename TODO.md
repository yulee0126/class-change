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

## P2 — Flet GUI

- [ ] `app.py` 主視窗：左＝事件清單、右＝編輯區
- [ ] 事件 CRUD（新增／複製／刪除／重新命名分頁）
- [ ] `event_form.py`：發起教師、假別下拉、假單編號（單一文字框，預設 `手動+`）、分頁日期（使用者選）、公告日期、分頁名稱、班級單樣式切換
- [ ] 說明區：按「產生草稿」帶入 `note_draft`，多行可編輯，可清空
- [ ] `leg_editors.py`：
  - [ ] 對調腳表單（班級、甲師/甲科/甲日期+節次、乙師/乙科/乙日期+節次）
  - [ ] 代課腳表單（班級、原師、科目、日期+節次、代課師）
  - [ ] **批次代課**：一位請假老師 + 多個時段 + 各指定代課老師 → 一次產生多個 `SubLeg`
  - [ ] **批次對調**：一位發起老師 + 多組（班級/科目/時段 ↔ 對方師/科目/時段）
  - [ ] 教師／班級／科目 下拉自動完成（來自主檔）
- [ ] `preview.py`：即時列出將產生的教師單／班級單與各自列數
- [ ] 輸出區：☑ 寫入總表（含總表路徑選擇）　☑ 另存新檔　＋「產生通知單」單鍵
- [ ] 執行結果對話框（摘要／開啟檔案／開啟資料夾）
- [ ] 錯誤與驗證訊息呈現（builder 的 warning）

## P3 — 收尾

- [ ] `storage.py`：專案 `.json` 存讀；最近檔案清單
- [ ] 主檔管理畫面：教師／班級／科目清單維護
- [ ] 設定：預設總表路徑、標楷體 fallback、班級單預設樣式
- [ ] 記住視窗大小／上次專案
- [ ] `flet pack` 打包 Windows exe + icon
- [ ] 使用說明（截圖）

## P4 — 複合事件

- [ ] 「先對調再代課」串接（炆明1150831）：對調後產生的新時段可再指定代課
- [ ] 反白列樣式（背景色）
- [ ] J 欄代課老師簡稱（末兩字，紅字）
- [ ] 教師單內「調課列 → 被代列 → 反白代課列」的排列順序

---

## 待釐清問題

### 已決（2026-08-30）
- [x] 分頁名稱日期 → **GUI 由使用者選**，預設帶所有腳最早日期
- [x] 公告日期 → **合併寫法** `H="公告日期：{民國年}年"`、`I="{M月D日}"`
- [x] 假單編號 `2015+手動` → **單一自由文字欄位**，不拆數字
- [x] 節次範圍 → **1–10**
- [x] 一對多（多人調課／代課）→ 以「一事件多腳」表示，builder 已支援；GUI 加批次輸入

### 待答
- [ ] 總表檔每學期一個？程式是否需要「新學期＝新總表」的引導？
- [ ] 「兼課」老師是否有任何特殊呈現，或只是普通教師姓名
- [ ] 教師單是否也可能需要「* 請…公佈」之類的結尾（目前僅班級單有）
- [ ] 假別除 公假／病假／事假／請假／其他 外是否還有其他選項
