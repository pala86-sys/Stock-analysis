import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const mobileRoot = path.join(__dirname, "..");
const projectRoot = path.join(mobileRoot, "..");
const staticDir = path.join(projectRoot, "static");
const wwwDir = path.join(mobileRoot, "www");

const apiUrl = (process.env.STOCK_OBSERVER_API || "").trim().replace(/\/$/, "");
const files = ["index.html", "app.css", "app.js"];

if (!apiUrl) {
  console.error("ERROR: 請設定 STOCK_OBSERVER_API（Render 或自建後端網址）");
  console.error("例：set STOCK_OBSERVER_API=https://your-app.onrender.com");
  process.exit(1);
}

fs.mkdirSync(wwwDir, { recursive: true });

for (const name of files) {
  const src = path.join(staticDir, name);
  if (!fs.existsSync(src)) {
    console.error(`ERROR: 找不到 ${src}`);
    process.exit(1);
  }
  fs.copyFileSync(src, path.join(wwwDir, name));
}

const configJs = `// 由 build-apk.ps1 自動產生 — 請勿手動編輯 www/config.js\nwindow.STOCK_OBSERVER_API = ${JSON.stringify(apiUrl)};\n`;
fs.writeFileSync(path.join(wwwDir, "config.js"), configJs, "utf8");

console.log(`Synced static -> www (API: ${apiUrl})`);
