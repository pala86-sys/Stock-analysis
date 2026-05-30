# 在乾淨虛擬環境中打包 StockObserver.exe
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPath = Join-Path $PSScriptRoot ".build-venv"
$distPath = Join-Path $PSScriptRoot "dist"
$buildPath = Join-Path $PSScriptRoot "build"

Write-Host "==> 建立乾淨虛擬環境..."
if (Test-Path $venvPath) {
    Remove-Item $venvPath -Recurse -Force
}
python -m venv $venvPath

$python = Join-Path $venvPath "Scripts\python.exe"
$pip = Join-Path $venvPath "Scripts\pip.exe"

Write-Host "==> 安裝執行與打包依賴..."
& $python -m pip install --upgrade pip
& $pip install -r requirements.txt
& $pip install -r build-requirements.txt

Write-Host "==> 匯出內建股號清單..."
& $python scripts/export_stock_list.py

Write-Host "==> 清理舊的 build 產物..."
if (Test-Path $distPath) { Remove-Item $distPath -Recurse -Force }
if (Test-Path $buildPath) { Remove-Item $buildPath -Recurse -Force }

Write-Host "==> PyInstaller 打包中（約 1-3 分鐘）..."
& $python -m PyInstaller --noconfirm --clean StockObserver.spec

$exe = Join-Path $distPath "StockObserver.exe"
if (-not (Test-Path $exe)) {
    throw "打包失敗：找不到 $exe"
}

Write-Host ""
Write-Host "打包完成：$exe"
Write-Host "檔案大小：$([math]::Round((Get-Item $exe).Length / 1MB, 1)) MB"
Write-Host "執行方式：雙擊 dist\StockObserver.exe"
