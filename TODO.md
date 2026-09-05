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
- [x] 「範例1」逐項比對：合併儲存格、欄寬、總列數 完全一致（test_example1_matches_reference_layout）
- [x] 每張通知單間空 2 列（比照範例1）；教師單／班級單資料列高 34／22
- [x] 教師單、班級單：先列出調課列、再列出代課列
- [x] 「先調再代」：一顆按鈕產生 1 筆調課 + 1 筆代課（SubLeg.from_swap）
- [x] 產生 Excel 後跳結果對話框（成功/失敗、檔案路徑）

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

## P5 — 匯入教師課表（PDF）　🟢

- [x] `tiaoke/timetable.py`：解析教師課表 PDF（pdfplumber）
  - 一頁一師；抓 學校／學年期／生效日期／各節時間／教師姓名+編號+職稱
  - 每格：科目（可跨行合併）／授課班級（合班課→多列）／上課地點
  - 兩遍解析：先掃全 PDF 建班級・教室詞彙表，再據以切格
  - 領域：此 PDF 無 → 欄位保留空字串
  - 實測：90 師、1303 筆課，僅 5 筆無班級（體育／花卉利用與設計）
- [x] `Timetable` to_dict/from_dict；`storage.save_timetable/load_timetable`；`AppSettings.timetable_path`
- [x] controller：`parse_timetable_pdf` → `apply_pending_timetable(save_path?)`（先解析、問使用者再存）／`load_timetable`／`timetable_slots(teacher, date)`
- [x] GUI 左欄進階：`_TimetableImport`（PDF 路徑 → 讀取 → 「存檔並套用／只套用不存／取消」）
- [x] 啟動時若 settings 有課表路徑就自動載入
- [x] `_LegForm`：填了老師＋日期 → 列出該老師當天課表的課，點一下帶入 科目／班級／節次（例外仍可手填）
- [x] `test_timetable.py`（含實體 PDF 測試）；全 55 測試通過
- [ ] 課表「瀏覽」選檔對話框
- [ ] 蔡文華「呼嚕呼嚕…」這類超長選修課名在 PDF 被截斷（極少數）

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

## P6 — 檔案回讀／課表校對／報表整合　🟡 進行中（2026-09-05 提出；核心決定已拍板）

背景：`build_out\調代課單\` 已累積真實產出的檔案，`build_out\record\115-1調代課記錄.xlsx`
是目前的記錄檔。使用者要能回頭搜尋、編輯既有的單，並讓「產製報表」直接以資料夾內的檔案
為準重算，而不是只靠 app 內的 Session／專案 JSON。

實作順序（2026-09-05 拍板）：**A → B → D → C**
A＝6.3＋6.4 對調備註＋6.5 移除常用名單（小改）／B＝6.4 兼課／第八節 J 欄＋record 加欄（中）／
D＝6.2 課表校對 GUI（中，獨立）／C＝6.1 搜尋讀回＋`xlsx_reader.py`＋6.5 產製報表資料夾重算（最大）。
**A、B、D 已完成**（見下方打勾項目），下一步是 C（搜尋讀回既有檔案＋`xlsx_reader.py`＋
產製報表資料夾重算，最大最複雜的一塊）。

### 6.1 搜尋既有檔案並編輯
- [ ] 事件清單上方「＋新增一張」旁加「搜尋檔案」鈕
- [ ] 打字即時過濾 `調代課單/` 內檔名（下拉/彈出清單，點選開啟）
- [ ] **新模組 `xlsx_reader.py`**：把選定的 .xlsx 讀回 `Event`（含 legs）供編輯
  - 需能還原三種型態：對調 `SwapLeg`、代課 `SubLeg`、先調後代 `SubLeg(from_swap=True)`
  - 由於同一筆異動在教師單／班級單各出現一次，優先以**班級單**的列還原（格式穩定：
    `調課(原{老師}老師/{科目})`、`{代課老師}老師 代課`），教師單的「備註」欄常被使用者
    手改（如「(蓁妍同步調)」「與趙瑋/蓁妍老師調課」這類多人手改字樣），較不可靠
  - 從橫幅列 `教 師 調 代 課 通 知 單 假單編號：{form_no} {originator} {leave_type}`
    以正規表示式還原 `form_no`／`originator`／`leave_type`
  - 解析失敗或格式對不上時：不硬猜，跳出「無法自動解析，請手動修正」而不是產生錯誤資料
  - **這模組同時是 6.5「產製報表」folder-scan 的地基**，所以解析穩健度優先權很高：
    掃資料夾時，解析不了的檔案要列進報告（檔名＋原因），不能悄悄漏掉
- [ ] 存回：檔名相同 → 跳確認「要覆蓋原檔嗎？」；檔名不同 → 跳確認「會刪除原檔
      {舊檔名}，另存為 {新檔名}，確定嗎？」
- [ ] 檔名前綴 `~~`（如 `~~1007-憶平1150908.xlsx`）視為作廢／取消，6.5 folder-scan 略過

### 6.2 課表校對 GUI　✅ 完成（Phase D）
- [x] 進階區新增 `_TimetableEditor`：選老師（`_NameField` 邊打邊搜）＋選星期（一～五按鈕）
      → 該星期節次 1–10 逐列顯示（科目／班級／備註摘要），比原本規劃的「單一 5×10 大表格」
      改成「選星期後看 10 列」，同一時間畫面更窄、跟左側 250px 面板寬度相容
      （原規劃是把整週攤開成一張表；因面板夠窄、10×5=50 格會太擠，改成加一層星期切換）
- [x] 每列可點 ✏ 展開成 科目／班級（合班用「、」分隔多班）／地點／備註 的編輯表單，
      有「儲存」「刪除這節」「取消」；模型層新增 `TeacherTable.slot_group/set_slot_group/
      delete_slot_group`，一格＝一個星期＋節次（合班＝多個 `Slot` 共用同一格）
- [x] 「存到」路徑欄＋存檔鈕 → `controller.save_timetable_to()` 寫回課表 JSON
      （`storage.save_timetable`），存檔路徑記回 `settings.timetable_path`
- [x] `test_timetable.py`（`slot_group`/`set_slot_group`/`delete_slot_group`/controller 方法）、
      `test_ui_smoke.py`（`_TimetableEditor` 選老師／星期／編輯／存檔／刪除）
- [~] **尚未在真實 GUI 視覺驗證**——這台環境沒有畫面可以實際點開看，只驗證了邏輯
      （選星期、存/取/刪資料）是對的；正式使用前建議實機跑一次 `python main.py` 檢查排版

### 6.3 系統假單編號 → 檔名　✅ 完成（Phase A）
- [x] `Event` 新欄位 `system_form_no`（基本資料區新增輸入框「系統假單編號」）
- [x] 輸出檔名改為 `{system_form_no}-{sheet_name}.xlsx`（留空則沿用原本 `{sheet_name}.xlsx`；
      `sheet_name` 沿用現有 `roc.sheet_code`＝老師末兩字＋民國年月日，
      正好對齊 `調代課單/` 內目前手動命名的檔案，例如 `1002-趙瑋1150903.xlsx`）
- [x] **決定**：純粹只組檔名，跟現有「假單編號」（`form_no`，印在橫幅）欄位／內容互不影響、互不合成

### 6.4 輸出 Excel 內容調整　✅ 完成（Phase A + B）
- [x] 對調備註格式：`與{對方}老師調課` → `與{對方}老師 {對方科目} 調課`
      （`builder.py` 第 71、75 行；teacher_a 的列插 `leg.subject_b`，teacher_b 的列插 `leg.subject_a`）
- [x] 代課腳：`builder.lookup_tags(timetable, leg.orig_teacher, leg.slot)` 查原老師在該
      星期＋節次的課表 `Slot.note`（沿用 P5 的 `(兼)`/`(輔)` 解析結果）：
      - 含 `(兼)` → 「原老師」「代課老師」教師單那一列 ＋ 班級單那一列，J 欄都加藍字／標楷／
        粗體「兼課」；含 `(輔)` → 同上三處加「八」；兩者都有就寫「兼課、八」
      - `build(event, timetable=None)` 新增 `timetable` 參數（一路從 `output.run` /
        `save_as_new` / `write_to_master` / `export_all` / `xlsx_writer.write_sheet` 穿進去，
        controller 呼叫時帶 `self.timetable`）
      - J 欄先前在 P4 做過「代課老師簡稱」後來移除（見 `test_p4.py`），這次重新啟用但用途不同
      - J 欄**不**納入 `print_area`（維持 `A1:I{last}`），純 Excel 內部註記、不影響印出的紙本通知單
- [x] `record.py`：原本就存在但一直是空白的「代課別」欄（`DETAIL_HEADERS` 第 18 欄）
      現在會依上述查表結果填 `兼課`／`第八節`／`兼課、第八節`（代課列才有值，調課列固定空白）；
      `月統計` 新增「代課(兼課)堂數」「代課(第八節)堂數」兩欄（`COUNTIFS` 依「代課別」`*兼課*`／
      `*第八節*` 萬用字元比對，統計口徑＝該老師「代課」且 `實際授課教師` 是他／她的堂數）

### 6.5 進階區整理　✅ 決定
- [x]（Phase A）移除「常用名單」（`_MasterDataPanel`：教師／班級／科目維護）整塊
      （`add_master`/`remove_master` 已無其他呼叫者，一併刪除）
- [ ]（Phase C）移除「專案存檔」（開啟／儲存 .json、只匯出全部成 Excel）與現有「重算記錄檔
      月統計」按鈕，以及每次「產生 Excel」時同步寫入 `record.xlsx` 的動作（`controller` 呼叫
      `record.update_record`）——**決定**：記錄檔完全改由「產製報表」現算，不再逐次累加
      （這幾項要跟下面「產製報表」同時換上，避免中間空窗期完全沒有記錄機制）
- [ ]（Phase C）新增一顆「產製報表」按鈕：用 6.1 的 `xlsx_reader.py` 掃描 `調代課單/` 資料夾內
      所有檔案（略過 `~~` 前綴與 Excel 鎖檔 `~$` 前綴）→ 重新產生一份 record 統計表
      （同 `115-1調代課記錄.xlsx` 格式），檔名加 `-{yymmdd-hhmmss}` 時間戳
      （例：`115-1調代課記錄-260905-143012.xlsx`）
      - 完成後顯示摘要：讀了幾個檔、幾筆代課／調課、有哪些檔案解析失敗被略過

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
