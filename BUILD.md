# 打包成 Windows 可攜資料夾

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller flet-cli

python build.py
```

產出 `..\調課代課產生器\`：

```
調課代課產生器\
├─ 調課代課產生器.exe          單一檔（約 75 MB，第一次開較慢）
├─ 115-1教師課表(暫行).json    教師課表（開機自動載入，姓名搜尋／課表下拉用）
├─ record\                     記錄檔資料夾（帶入現有的 {學期}調代課記錄.xlsx）
│  └─ 記錄檔規格-提案.md
└─ 使用說明.txt
```

（`build.py` 會把專案上層資料夾裡「檔名含『課表』的 .json」一起帶進交付資料夾。）

**整個資料夾複製到別台 Windows 就能用。** 程式的所有檔案（record、settings.json、
調代課資料庫.json、匯入的課表 JSON）都放在 exe 旁邊 —— 見 `tiaoke/paths.py`：
打包後 `app_dir()` = exe 所在資料夾。

## 手動打包（build.py 做的事）

```powershell
flet pack main.py `
  --name 調課代課產生器 `
  --icon assets/icon.ico `
  --product-name "調課代課通知單產生器" `
  --company-name 關西高中 `
  --add-data "assets:assets" `
  --add-data "<pdfminer>\cmap:pdfminer/cmap" `
  --hidden-import pdfplumber `
  --distpath build_out
```

`<pdfminer>` = `python -c "import pdfminer,os;print(os.path.dirname(pdfminer.__file__))"`。
`pdfminer/cmap` 是解析 PDF 中日文字型的資料，一定要帶。

## 注意

- **字型**：通知單用「標楷體」，台灣版 Windows 內建，通常不用另裝。
- PyInstaller 警告缺 `pandas / numpy / lxml / defusedxml` 等 —— 都是選用相依，
  openpyxl / pdfplumber / Pillow 沒有它們也正常運作。
- 要換 icon，替換 `assets/OIP.webp` 後重跑
  `python -c "from PIL import Image; im=Image.open('assets/OIP.webp').convert('RGBA'); im.save('assets/icon.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]); im.resize((128,128)).save('assets/icon.png'); im.resize((64,64)).save('assets/logo64.png')"`
