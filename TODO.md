# TODO — 調課代課通知單產生器

狀態圖例：`[ ]` 待辦　`[~]` 進行中　`[x]` 完成

---

## P0 — 專案初始化

- [ ] 建立 `requirements.txt`（flet、openpyxl）與 `.gitignore`（`.venv/`、`__pycache__/`、`~$*.xlsx`、`build/`、`dist/`）
- [ ] 建立套件骨架 `tiaoke/`、`tiaoke/ui/`、`tests/`
- [ ] 把範例檔的 8 個事件人工轉成測試 fixtures（`tests/fixtures/*.json`），作為 P1 回歸基準
- [ ] 決定程式碼放這個 repo（`class-change`）；範例檔仍留在上層資料夾

## P1 — 核心邏輯（無 GUI，先給 review）

### models.py
- [ ] `Slot`（date + period；`weekday_cn` 由 date 推算）
- [ ] `SwapLeg` / `SubLeg`
- [ ] `Event`（originator、leave_type、form_no、announce_date、sheet_date、note、class_slip_style、legs）
  - `form_no`：單一自由文字（預設 `手動+`）
  - `sheet_date`：分頁名稱用；GUI 由使用者選，預設＝所有腳最早日期
- [ ] `Event.sheet_name` 屬性（`{末兩字}{民國YYYMMDD}`）
- [ ] `Project`（events + 教師／班級／科目主檔）
- [ ] `to_dict` / `from_dict`（給 storage 用）

### roc.py
- [ ] 西元 date → 民國年（int）
- [ ] date → 星期中文（一…日）
- [ ] date → `M月D日` 字串
- [ ] 姓名 → 末兩字
- [ ] 時段格式化：`8/31(一)第5節`、多節合併 `第5、6、7節`

### builder.py
- [ ] `TeacherRow` / `ClassRow` / `TeacherSlip` / `ClassSlip` 結構
- [ ] `build(event) -> list[Slip]`：
  - [ ] SwapLeg → 甲/乙教師單各 +1、班級單 +2
  - [ ] SubLeg → 原/代教師單各 +1、班級單 +1
  - [ ] 教師依首次出現順序保序；班級單排在教師單之後
  - [ ] 同師／同班多腳累積列
- [ ] 驗證：`slot_a != slot_b`、姓名去「老師」後綴、班級／科目非空、節次 1–10、重複腳偵測（warning）

### note_draft.py
- [ ] 對調腳依互換時段組彙整成「…課務互調」
- [ ] 「故{發起人}老師{原時段}調至{新時段}上課」
- [ ] 代課腳「{時段}由{代課老師}老師代課」
- [ ] 對照 炆明1150831 / 若耶1150226 / 炆明1150223 三個範例調整措辭

### styles.py
- [ ] 從範例檔擷取的樣式常數：欄寬、列高、字型、框線、number_format、頁面設定
- [ ] helper：`set_cell(ws, coord, value, *, font, align, border, fmt)`、`box_range(...)`、`merge_and_set(...)`

### xlsx_writer.py
- [ ] `write_teacher_slip(ws, cursor, slip, event) -> new_cursor`
- [ ] `write_class_slip(ws, cursor, slip, event) -> new_cursor`（橫幅式；標題式為分支）
- [ ] `write_note_row(ws, cursor, text) -> new_cursor`
- [ ] `write_announce_row(...)`：公告日期／`* 請學藝股長公佈。`
- [ ] `write_sheet(wb, event)`：逐張輸出、張間空 1 列、設定欄寬／列印範圍／頁面
- [ ] 被代課列 B/C/D 留空；代課者列 F/G/H 留空

### output.py
- [ ] `write_to_master(master_path, event)`：開啟 → 同名工作表存在則刪除 → 重建 → 存回
- [ ] `save_as_new(dest_path, event)`：新活頁簿只放一張工作表
- [ ] `run(event, *, to_master: bool, master_path, save_new: bool, dest_path) -> ResultSummary`
  - [ ] 兩目標可同時；至少一個
  - [ ] 回傳摘要：路徑、列數、是否覆蓋舊表、錯誤

### tests
- [ ] `test_roc.py`：民國年、星期、時段格式
- [ ] `test_builder.py`：8 事件 → 通知單結構與備註文字比對
- [ ] `test_xlsx_writer.py`：產表後與原檔逐格比對（值 + number_format + 合併儲存格 + 欄寬）
  - [ ] 容許差異清單（範例本身不一致處，例如空白數、假單編號寫法）

### 里程碑
- [ ] **CLI 煙霧測試**：`python -m tiaoke.cli fixtures/瑞文1150223.json` → 產出 `.xlsx`，肉眼與範例比對 → 交付 review

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
