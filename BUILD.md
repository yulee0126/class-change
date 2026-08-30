# 打包成 Windows 執行檔

## 前置

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install flet[all]      # 打包工具（含 flet pack / pyinstaller）
```

## 方式 A：flet pack（建議）

```powershell
flet pack main.py `
  --name 調課代課產生器 `
  --product-name "調課代課通知單產生器" `
  --company-name "學校" `
  --icon assets/icon.ico
```

產出：`dist\調課代課產生器.exe`（單一檔，可直接複製給同事）。

## 方式 B：PyInstaller 直接打

```powershell
pyinstaller --onefile --noconsole --name 調課代課產生器 `
  --collect-all flet --collect-all flet_desktop `
  --icon assets/icon.ico main.py
```

## 注意事項

- **字型**：通知單使用「標楷體」。台灣版 Windows 內建，一般不需另外安裝；
  若目標電腦沒有，Excel 會以預設字型顯示，重新指定字型即可。
- **設定檔位置**：`%APPDATA%\tiaoke\settings.json`（記住視窗大小、上次專案、預設總表路徑）。
- **總表被 Excel 開著**時無法寫入，程式會顯示提示，關閉 Excel 後再按一次「產生通知單」。
- icon 檔請自備 `assets/icon.ico`（256x256 內含多尺寸）；沒有的話拿掉 `--icon` 參數即可。
- 第一次啟動較慢（解壓縮），之後正常。
