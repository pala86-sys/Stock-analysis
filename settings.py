"""使用者設定：記住上次查詢的股票代號"""

import json
import sys
from pathlib import Path

DEFAULT_STOCK = "2330"


def _settings_dir() -> Path:
    """打包成 exe 後，設定檔寫在程式同目錄"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def resource_path(relative: str) -> Path:
    """取得資源檔路徑（開發模式 / PyInstaller 打包）"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).parent / relative


SETTINGS_FILE = _settings_dir() / "settings.json"


def load_last_stock() -> str:
    """讀取上次查詢的股票代號，無紀錄則回傳預設值"""
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            stock = str(data.get("last_stock", "")).strip()
            if stock:
                return stock
    except Exception:
        pass
    return DEFAULT_STOCK


def save_last_stock(stock_id: str):
    """儲存本次成功查詢的股票代號"""
    stock = stock_id.strip()
    if not stock:
        return
    try:
        SETTINGS_FILE.write_text(
            json.dumps({"last_stock": stock}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass
