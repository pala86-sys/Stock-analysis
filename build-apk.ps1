# Android APK 打包 — 台股多維度全方位觀測儀
param(
    [string]$ApiUrl = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Require-Command($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "找不到 $name，請先安裝（見 README-APK.md）"
    }
}

function Read-ApiUrl {
    param([string]$Override)
    if ($Override) {
        return $Override.Trim().TrimEnd("/")
    }
    if ($env:STOCK_OBSERVER_API) {
        return $env:STOCK_OBSERVER_API.Trim().TrimEnd("/")
    }
    $urlFile = Join-Path $PSScriptRoot "mobile\api-url.txt"
    if (Test-Path $urlFile) {
        $line = Get-Content $urlFile | Where-Object { $_ -and -not $_.Trim().StartsWith("#") } | Select-Object -First 1
        if ($line) {
            return $line.Trim().TrimEnd("/")
        }
    }
    throw @"
請設定後端 API 網址（Render 部署網址）：
  1. copy mobile\api-url.example.txt mobile\api-url.txt 並填入網址
  2. 或：.\build-apk.ps1 -ApiUrl `"https://your-app.onrender.com`"
  3. 或：set STOCK_OBSERVER_API=https://your-app.onrender.com
"@
}

Require-Command node
Require-Command npm

$resolvedApi = Read-ApiUrl -Override $ApiUrl
if ($resolvedApi -notmatch "^https?://") {
    throw "API 網址格式錯誤：$resolvedApi"
}

Write-Host "==> API 後端：$resolvedApi"

$mobileDir = Join-Path $PSScriptRoot "mobile"
Set-Location $mobileDir

Write-Host "==> 安裝 npm 依賴..."
npm install

Write-Host "==> 同步前端到 www/ ..."
$env:STOCK_OBSERVER_API = $resolvedApi
npm run sync

Write-Host "==> 初始化 Capacitor Android（若尚未建立）..."
if (-not (Test-Path "android")) {
    npx cap add android
}

Write-Host "==> Capacitor sync..."
npx cap sync android

$gradlew = Join-Path $mobileDir "android\gradlew.bat"
if (-not (Test-Path $gradlew)) {
    throw "找不到 gradlew.bat，請確認 Android Studio / SDK 已安裝"
}

Write-Host "==> 編譯 Debug APK（首次可能需數分鐘下載 Gradle）..."
Push-Location (Join-Path $mobileDir "android")
try {
    & .\gradlew.bat assembleDebug --no-daemon
} finally {
    Pop-Location
}

$apk = Join-Path $mobileDir "android\app\build\outputs\apk\debug\app-debug.apk"
if (-not (Test-Path $apk)) {
    throw "打包失敗：找不到 $apk"
}

$sizeMb = [math]::Round((Get-Item $apk).Length / 1MB, 1)
Write-Host ""
Write-Host "打包完成：$apk"
Write-Host "檔案大小：${sizeMb} MB"
Write-Host ""
Write-Host "安裝到手機："
Write-Host "  adb install `"$apk`""
Write-Host "  或將 APK 複製到手機後手動安裝"
