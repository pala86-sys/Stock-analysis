# 台股多維度全方位觀測儀 — Android APK 打包指南

APK 是 **Android 原生殼 + 內建前端介面**，分析仍由 **後端 API** 執行（Python / FastAPI）。  
因此需要先有一個可從手機連線的後端網址（建議部署 [Render](README-DEPLOY.md)）。

```
┌─────────────┐      HTTPS       ┌──────────────────┐
│  Android    │  ──────────────► │  FastAPI 後端     │
│  APK 前端   │                  │  (Render / 自建)  │
└─────────────┘                  └──────────────────┘
```

> **說明**：分析邏輯、FinMind / Yahoo 資料抓取都在後端，APK 本身不含 Python 引擎，  
> 安裝包小、維護簡單。需 **網路連線** 才能分析（與 Web 版相同）。

---

## 前置需求（Windows）

| 項目 | 說明 |
|------|------|
| **Node.js 18+** | https://nodejs.org/ |
| **Android Studio** | 含 Android SDK、Build-Tools |
| **JDK 17** | Android Studio 通常已內建 |
| **已部署後端** | 例如 `https://stock-observer.onrender.com` |

安裝 Android Studio 後，確認環境變數（擇一即可）：

- `ANDROID_HOME` = `C:\Users\你的帳號\AppData\Local\Android\Sdk`
- 或 `ANDROID_SDK_ROOT` 指向相同路徑

---

## 快速打包

### 1. 設定 API 網址

```powershell
copy mobile\api-url.example.txt mobile\api-url.txt
# 編輯 api-url.txt，改成你的 Render 網址（不要結尾斜線）
```

或執行時指定：

```powershell
.\build-apk.ps1 -ApiUrl "https://your-app.onrender.com"
```

### 2. 執行打包

```powershell
.\build-apk.ps1
```

首次執行會：

1. 安裝 `mobile/` 的 npm 依賴  
2. 複製 `static/` 前端到 `mobile/www/`  
3. 寫入 `config.js`（指向你的 API）  
4. 建立 Capacitor Android 專案  
5. 編譯 Debug APK  

成功後產出：

```
mobile\android\app\build\outputs\apk\debug\app-debug.apk
```

### 3. 安裝到手機

- 用 USB 傳到手機，或  
- `adb install mobile\android\app\build\outputs\apk\debug\app-debug.apk`  
- 需在手機開啟「允許安裝未知來源」

---

## 發佈用正式版 APK（可選）

Debug 版適合自用。若要給他人安裝或上架 Google Play：

1. 用 Android Studio 開啟專案：

   ```powershell
   cd mobile
   npx cap open android
   ```

2. **Build → Generate Signed Bundle / APK**  
3. 建立 keystore 並選 **release** 建置  

或使用命令列（需先設定 signing）：

```powershell
cd mobile\android
.\gradlew.bat assembleRelease
```

---

## 常見問題

### 開啟 App 顯示「無法連線分析伺服器」

- 確認 `api-url.txt` 網址正確、手機有網路  
- Render 免費方案休眠時，首次請求需等 30～60 秒  
- 後端需已部署含 CORS 的最新版 `web_app.py`

### 分析很慢

- 與 Web 版相同，每次約 10～30 秒（呼叫外部資料源）

### 能否完全離線、不連雲端？

- 目前 APK 方案 **不行**（需後端 API）  
- 若要在手機本機跑 Python 分析，需另做 Chaquopy 等嵌入方案，APK 會很大且建置複雜

### 修改 UI 後如何重打包？

改完 `static/` 後重新執行：

```powershell
.\build-apk.ps1
```

---

## 目錄結構

```
mobile/
  package.json          # Capacitor 依賴
  capacitor.config.json # App ID、名稱
  api-url.txt           # 你的 API 網址（自行建立，勿提交 git）
  www/                  # 打包用前端（自動產生）
  android/              # Android 專案（首次 build 產生）
build-apk.ps1           # 一鍵打包腳本
```

---

## 與其他版本對照

| 版本 | 入口 | 後端 |
|------|------|------|
| 桌面版 | `dist\StockObserver.exe` | 本機 Python |
| Web 版 | 瀏覽器 | Render / 本機 uvicorn |
| **Android APK** | 安裝 App | Render / 自建 API |
