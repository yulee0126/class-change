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

## P6 — 檔案回讀／課表校對／報表整合　✅ 完成（2026-09-05 提出並完成，A→B→D→C 全部做完）

背景：`build_out\調代課單\` 已累積真實產出的檔案，`build_out\record\115-1調代課記錄.xlsx`
是目前的記錄檔。使用者要能回頭搜尋、編輯既有的單，並讓「產製報表」直接以資料夾內的檔案
為準重算，而不是只靠 app 內的 Session／專案 JSON。

實作順序（2026-09-05 拍板並完成）：**A → B → D → C**。
A＝6.3＋6.4 對調備註＋6.5 移除常用名單／B＝6.4 兼課／第八節 J 欄＋record 加欄／
D＝6.2 課表校對 GUI／C＝6.1 搜尋讀回＋`xlsx_reader.py`＋6.5 產製報表資料夾重算（最大最複雜）。

### 6.1 搜尋既有檔案並編輯　✅ 完成（Phase C）
- [x] 事件清單旁進階區新增 `_SlipSearch`：邊打邊過濾「調代課單資料夾」內檔名，點一下讀回編輯
- [x] **新模組 `xlsx_reader.py`**：把 .xlsx 讀回 `Event`（含 legs），**完全不解析「備註」文字**——
      每一列的「誰、班級、日期、節次、是否反白」全部是結構化資料（欄位值／儲存格底色），
      不是文字，所以使用者手改備註（如附註「(蓁妍同步調)」）不影響正確還原：
      - 只看教師調代課通知單（班級單是衍生資料，略過不讀）
      - 一列「新時段＋原時段都有值」＝對調腳一邊；只有「原時段」＝被代課；只有「新時段」＝代課者
      - 兩個對調腳一邊 `(klass, new, orig)` 與 `(klass, orig, new)` 互相對應才配成一個 `SwapLeg`；
        一個「被代課」跟一個「代課」在同一 `(klass, slot)` 才配成一個 `SubLeg`
        （`from_swap` 讀儲存格底色，不是文字）
      - 配不出的列（超出目前資料模型，例如兩位老師共同代表同一堂課的特殊多人調課）
        → 整份視為解析失敗，丟 `ParseError`，不回傳猜測、可能錯誤的資料
      - 對 `samples.py` 5 個範例事件（含對調、代課、先調後代、說明、標題式班級單）全部
        round-trip 測試通過；對真實檔案（`build_out\調代課單\` 12 份非作廢檔）測試：
        **11 份完全解析成功、1 份（`1002-趙瑋1150903.xlsx`）因為是超出資料模型的
        三人共同調課而報錯**，符合預期
- [x] 存回：`resave_loaded_file()`／GUI 用 `_show_confirm` 對話框——檔名跟原檔相同 →
      「確定覆蓋原檔？」；不同 → 「確定另存新檔名？」（文案會列出會刪除的原檔路徑），
      使用者按確定才真的執行
- [x] 檔名前綴 `~~`（如 `~~1007-憶平1150908.xlsx`）視為作廢／取消，6.5 folder-scan 略過
      （Excel 鎖檔 `~$` 前綴也一併略過）

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

### 6.5 進階區整理　✅ 完成（Phase A + C）
- [x]（Phase A）移除「常用名單」（`_MasterDataPanel`：教師／班級／科目維護）整塊
      （`add_master`/`remove_master` 已無其他呼叫者，一併刪除）
- [x]（Phase C）移除「專案存檔」（開啟／儲存 .json、只匯出全部成 Excel）與「重算記錄檔月統計」
      按鈕，以及每次「產生 Excel」時同步寫入 `record.xlsx` 的動作——記錄檔完全改由「產製報表」
      現算，不再逐次累加。`controller.generate()` 不再呼叫 `record.update_record`；
      `AppController` 不再有 `last_record`。開機也不再自動載入「調代課資料庫.json」
      （`storage.save_project`/`load_project`/`output.export_all` 底層函式保留、仍有測試，
      只是不再接到 GUI 按鈕上——這算是跟原始需求「移除進階區的專案存檔」稍有出入的地方，
      如果還是需要「整個 session 存成一份 JSON 之後接著編輯」的功能，之後可以再接回來）
- [x]（Phase C）新增「產製報表」按鈕：`controller.generate_report(slips_folder, out_folder)`
      掃 `調代課單` 資料夾所有檔案（略過 `~~`／`~$` 前綴），用 `xlsx_reader.read_events()`
      逐檔逐分頁讀回、`record.event_to_rows()` 轉成明細列、`record.build_report()` 組成
      全新的記錄檔活頁簿，檔名 `{學期}調代課記錄-{yymmdd-hhmmss}.xlsx`（不覆蓋舊檔）
      - 完成後彈窗顯示：幾個檔案成功、幾筆明細、存到哪裡、哪些檔案（連分頁名）解析失敗
      - 真實資料驗證：對 `build_out\調代課單\` 跑一次，11/12 份（扣掉 1 份作廢）成功、
        產出 57 筆明細，唯一失敗的是前述超出資料模型的三人調課檔，錯誤訊息清楚列出是哪幾列

### 尚未涵蓋 / 已知限制
- [ ] 讀回既有檔案的編輯，仍然只能靠一般的①～④表單改；沒有「差異預覽」（改了什麼、
      跟原檔差在哪）
- [ ] `xlsx_reader` 無法還原「一份課同時有兩位以上老師共同任教」這種結構（例：
      `1002-趙瑋1150903.xlsx` 的趙瑋／蓁妍協同教學一起對調）；這類檔案「產製報表」會略過
      並在摘要列出，不會讓整個報表失敗，但這幾筆資料本身不會被算進統計
- [ ] `_TimetableEditor`（P6.2）跟 `_SlipSearch`／確認覆蓋對話框（P6.1）都只在自動化測試
      （含 Flet controls 但無真實視窗）跑過，還沒有在真正的視窗畫面上實際點過一次，
      正式使用前建議跑一次 `python main.py` 走過一輪

## P7 — 協同教學（教師配當表）　🟡 進行中（2026-09-05 提出）

背景：`115-1教師配當表簽稿.xlsx` 逐老師逐課程列出授課班級／課程名稱／學分數，其中「協同」
（含「專案協同」）欄標記兩位老師一起教同一堂課。這解開了 P6 留下的謎：`1002-趙瑋1150903.xlsx`
解析失敗，就是因為趙瑋、周蓁妍協同教學「基礎雜糧加工實作」，兩人各自一列調課，內容幾乎一樣。

規劃四階段：F1（解析配當表＋比對課表）→ F2（協作調課按鈕）→ F3（代課表單的協同獨立授課）→
F4（讓 xlsx_reader 認得協同、修正 P6 那個解析失敗案例）。

### F1 匯入配當表、建立協同對照　✅ 完成
- [x] `timetable.py` 新增 `Slot.co_teachers: list[str]`（這節課協同的其他老師）
- [x] `parse_co_teaching_xlsx(path)`：讀配當表，回傳 `[(教師, 班級簡稱, 課程名稱, 標記), ...]`
      - `_find_peidang_sheet()`：配當表常常把上學期的舊表留在另一分頁、表頭一模一樣
        （只是「協同」欄位擠到不同位置），不能只憑表頭判斷，要選「協同／分組」標記
        出現次數最多的分頁，才是目前學期真的在用的那個（真實檔案裡工作表1是
        114-1 舊表、工作表2 才是 115-1 現在用的）
- [x] `apply_co_teaching(timetable, rows)`：**不是只看配當表的「協同」欄位就好**——
      改良後的規則（使用者 2026-09-05 提出修正）：
      1. 同一 (班級簡稱, 課程名稱) 有 2 位以上不同老師，且至少一邊標了「(專案)協同」
         （排除「分組」跟純代碼如 A1/B2/1-2 這類——那是不同班學生分組上課，不是協同）
      2. 再去查**已匯入的課表 PDF**：這些候選老師是否在同一班級全稱（配當表簡稱
         用「簡稱各字依序出現在全稱裡」模糊比對，例如「職二」對得上「綜職二」）、
         同星期、同節次都有課——同節次對得上才真正確認是協同，寫進雙方 `Slot.co_teachers`
      - 這兩層缺一不可：只看①會誤抓「畜二／專題初探」這種 3 位老師各自帶不同組、
        剛好都叫同課名的假陽性；只看②（不管①的協同標記）又會把「分組」誤判成協同
      - 真實資料驗證：`115-1教師配當表簽稿.xlsx` + `1151教師課表_正式公布.pdf` 比對出
        16 組協同教師、98 個節次，包含驗證趙瑋／周蓁妍那組
- [x] controller `parse_co_teaching(path)`（需要已有 `self.timetable`，否則丟錯要求先匯入 PDF）
- [x] GUI「匯入課表」區塊加第二個欄位＋按鈕：讀配當表、套用、若課表已有存檔路徑就直接存回

### F2 協作調課按鈕　✅ 完成
- [x] 獨立按鈕「＋協作調課」（`ft.Icons.GROUPS`），跟「先調再代」同一層級，不是塞進
      現有「新增調課」表單裡
- [x] 新元件 `_CoSwapForm`：班級、協同課程、甲老師＋乙老師（原時段共用同一節課）、
      目標老師＋目標科目＋目標時段；甲老師＋日期＋節次填了、剛好比對出協同節次時，
      自動帶出乙老師建議（`ctl.co_teachers_of()` 查 F1 標好的 `Slot.co_teachers`，
      使用者仍可手動改掉建議值）；點選課表帶出的節次按鈕，協同節次會多顯示「🤝協同」
- [x] `controller.add_co_swap()`：一次送出展開成兩筆獨立 `SwapLeg`（甲↔目標一筆、
      乙↔目標一筆，班級/科目/原時段/目標時段都相同，只差 teacher_a）——不改資料模型
      去支援「多人一組」；印出來會是「兩位協同老師各自一張通知單、內容很接近」，
      跟使用者過去手動做的 `1002-趙瑋1150903.xlsx` 一樣（使用者已確認接受這種呈現）
- [x] 測試涵蓋 controller（`co_teachers_of`／`add_co_swap`／缺乙老師要報錯）跟 GUI
      端到端（開表單→自動偵測協同老師→送出→驗證產生 2 筆 SwapLeg）

### F3 協同獨立授課（代課情境）　⬜ 待做
- [ ] 情境：協同課其中一位老師請假，另一位協同老師直接單獨上課，不找外部代課
- [ ] 使用者決定：**仍然產生一張通知單**，但備註措辭改成「獨立授課」（不寫「XX老師代課」）
- [ ] `SubLeg` 新增 `is_co_teach: bool`（同 `from_swap` 的做法），`builder.py` 據此改寫
      原老師列／代課老師列／班級列的備註文字（正式措辭實作時再讓使用者過目微調）
- [ ] 「＋新增代課」表單：原老師＋班級＋科目符合已知協同組時，自動建議代課老師＝協同老師，
      並提供「標記為協同獨立授課」核取方塊

### F4 xlsx_reader 認得協同　⬜ 待做（依賴 F1）
- [ ] 目前 `_pair_entries` 遇到「兩個一模一樣的 swap-side entry 搶同一個對方」會直接放進
      unmatched 報錯（`1002-趙瑋1150903.xlsx` 就是這樣）。有了協同對照表後，可以在配對失敗時
      額外檢查：這幾個 unmatched entries 是否互為已知協同教師、且 (klass, new, orig) 完全一樣
      →是的話视為「同一次調課的兩個化身」，允許還原成兩個 SwapLeg 而不報錯
      - 這步驟需要 `xlsx_reader` 拿得到 `timetable`（目前 `read_event`/`read_events` 都沒收這個
        參數，`generate_report` 呼叫時要一併傳進去）

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
