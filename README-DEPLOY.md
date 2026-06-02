# 台股多維度全方位觀測儀 — 部署指南

本專案提供兩種使用方式：

| 模式 | 入口 | 說明 |
|------|------|------|
| **桌面版** | `python main.py` | tkinter 視窗應用（Windows） |
| **Web 版** | `uvicorn web_app:app` | 瀏覽器使用，可部署至 Render |
| **Android APK** | `.\build-apk.ps1` | 手機 App，需連線後端 API（見 [README-APK.md](README-APK.md)） |

---

## Web 版本地測試

```bash
pip install -r requirements-web.txt
uvicorn web_app:app --reload --port 8000
```

瀏覽器開啟：http://127.0.0.1:8000

---

## 部署至 Render（GitHub 連動）

### 1. 推送到 GitHub

```bash
git init
git add .
git commit -m "Add web version for Render deployment"
git branch -M main
git remote add origin https://github.com/你的帳號/stock-observer.git
git push -u origin main
```

> 請確認 `data/stock_list.json` 已提交（供離線股號搜尋）。

### 2. 在 Render 建立 Web Service

1. 登入 [Render Dashboard](https://dashboard.render.com/)
2. **New → Blueprint**（若 repo 含 `render.yaml`）或 **New → Web Service**
3. 連接 GitHub 儲存庫
4. 設定（若手動建立）：
   - **Build Command:** `bash build.sh`
   - **Start Command:** `bash start.sh`
   - **Health Check Path:** `/api/health`
5. 選 **Free** 方案 → Deploy

部署完成後會得到網址，例如：`https://stock-observer.onrender.com`

### 3. 設定 FinMind Token（Web 版強烈建議）

Render 等雲端主機與本機共用 FinMind 免費配額（無 Token 約 **300 次/小時/IP**），容易出現籌碼、月營收、EPS 抓不到。

1. 至 [FinMind 官網](https://finmindtrade.com/) 註冊並取得 API Token  
2. Render Dashboard → 你的服務 → **Environment** → 新增：

   | Key | Value |
   |-----|-------|
   | `FINMIND_TOKEN` | 你的 Token |

3. 儲存後重新部署

有 Token 後配額提升為 **600 次/小時**，並降低被限流機率。

### 4. 其他注意事項

- **部署卡在 `No open ports detected`**：多為 Free 方案記憶體不足或啟動時載入過多套件。本專案已將分析模組改為**延遲載入**；若仍逾時，請在 Dashboard **Cancel deploy** 後重新部署，或查看 Logs 是否 `Out of memory`。
- **免費方案** 閒置 15 分鐘會休眠，首次開啟需等待約 30～60 秒喚醒
- **分析耗時** 每次約 10～30 秒（需呼叫 FinMind + Yahoo API）
- **股價非即時**：與桌面版相同，按分析時抓取一次，非盤中自動刷新
- Render 無持久化磁碟，`stock_list_cache.json` 每次重啟會重建；已內建 `data/stock_list.json`

---

## API 端點

| 方法 | 路徑 | 說明 |
|------|------|------|
| GET | `/api/health` | 健康檢查 |
| GET | `/api/stocks/search?q=` | 股號搜尋 |
| POST | `/api/analyze` | 完整分析（JSON） |
| POST | `/api/report` | 下載 HTML 報告 |

---

## 桌面版打包（Windows exe）

```powershell
.\build.ps1
```

產出：`dist\StockObserver.exe`
