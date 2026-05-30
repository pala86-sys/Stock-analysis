"""台股代號 / 名稱搜尋與自動完成"""

import json
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

from http_client import request_with_retry
from settings import _settings_dir, resource_path

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"
STOCK_LIST_CACHE = _settings_dir() / "stock_list_cache.json"
BUNDLED_STOCK_LIST = resource_path("data/stock_list.json")
CACHE_MAX_AGE_DAYS = 7
MARKET_LABEL = {"twse": "上市", "tpex": "上櫃"}


def _parse_stock_list_payload(payload: dict) -> list[dict]:
    return payload.get("stocks") or []


def fetch_stock_list_from_api() -> list[dict]:
    """從 FinMind 取得全部台股清單"""
    response = request_with_retry(
        "GET",
        FINMIND_API,
        params={"dataset": "TaiwanStockInfo", "data_id": ""},
        timeout=60,
    )
    payload = response.json()
    if payload.get("status") != 200:
        raise RuntimeError("無法取得股票清單")

    seen: dict[str, dict] = {}
    for item in payload.get("data") or []:
        stock_id = str(item.get("stock_id", "")).strip()
        stock_name = str(item.get("stock_name", "")).strip()
        if not stock_id or not stock_name:
            continue
        if stock_id not in seen:
            seen[stock_id] = {
                "stock_id": stock_id,
                "stock_name": stock_name,
                "market": item.get("type", "twse"),
            }
    return sorted(seen.values(), key=lambda x: x["stock_id"])


def load_bundled_stock_list() -> list[dict]:
    """載入打包內建的股號清單"""
    if not BUNDLED_STOCK_LIST.exists():
        return []
    try:
        payload = json.loads(BUNDLED_STOCK_LIST.read_text(encoding="utf-8"))
        return _parse_stock_list_payload(payload)
    except Exception:
        return []


def _read_user_cache() -> tuple[list[dict], datetime | None]:
    if not STOCK_LIST_CACHE.exists():
        return [], None
    try:
        cached = json.loads(STOCK_LIST_CACHE.read_text(encoding="utf-8"))
        updated = datetime.fromisoformat(cached.get("updated_at", "2000-01-01"))
        return _parse_stock_list_payload(cached), updated
    except Exception:
        return [], None


def _save_user_cache(stocks: list[dict]):
    STOCK_LIST_CACHE.write_text(
        json.dumps(
            {"updated_at": datetime.now().isoformat(timespec="seconds"), "stocks": stocks},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _cache_is_fresh(updated: datetime | None) -> bool:
    if updated is None:
        return False
    return datetime.now() - updated < timedelta(days=CACHE_MAX_AGE_DAYS)


def load_stock_list(force_refresh: bool = False) -> list[dict]:
    """載入股票清單：使用者快取 → 內建清單 → API"""
    if not force_refresh:
        cached_stocks, updated = _read_user_cache()
        if cached_stocks and _cache_is_fresh(updated):
            return cached_stocks

        bundled = load_bundled_stock_list()
        if bundled:
            return bundled

    stocks = fetch_stock_list_from_api()
    _save_user_cache(stocks)
    return stocks


def refresh_stock_list_async(on_updated=None, on_error=None):
    """背景更新股號清單（已有內建/快取時仍可刷新）"""
    def worker():
        try:
            stocks = fetch_stock_list_from_api()
            _save_user_cache(stocks)
            if on_updated:
                on_updated(stocks)
        except Exception as exc:
            if on_error:
                on_error(str(exc))

    threading.Thread(target=worker, daemon=True).start()


def search_stocks(stocks: list[dict], query: str, limit: int = 15) -> list[dict]:
    """依代號或名稱模糊搜尋"""
    q = query.strip()
    if not q or not stocks:
        return []

    qu = q.upper()
    scored: list[tuple[int, int, dict]] = []

    for idx, stock in enumerate(stocks):
        stock_id = stock["stock_id"]
        stock_name = stock["stock_name"]
        sid_upper = stock_id.upper()

        if sid_upper == qu:
            scored.append((0, idx, stock))
        elif sid_upper.startswith(qu):
            scored.append((1, idx, stock))
        elif qu in sid_upper:
            scored.append((2, idx, stock))
        elif stock_name.startswith(q):
            priority = 3 if not stock_id.startswith("00") else 4
            scored.append((priority, idx, stock))
        elif q in stock_name:
            priority = 4 if not stock_id.startswith("00") else 5
            scored.append((priority, idx, stock))

    scored.sort(key=lambda x: (x[0], x[1]))
    return [item[2] for item in scored[:limit]]


def format_stock_option(stock: dict) -> str:
    market = MARKET_LABEL.get(stock.get("market"), stock.get("market", ""))
    return f"{stock['stock_id']}  {stock['stock_name']}  ({market})"


def resolve_stock_input(text: str, stocks: list[dict]) -> str | None:
    """將輸入文字解析為股票代號"""
    raw = text.strip()
    if not raw:
        return None

    code_match = re.match(r"^([0-9A-Za-z]+)", raw.replace(" ", ""))
    if code_match:
        code = code_match.group(1).upper()
        if not stocks:
            return code
        for stock in stocks:
            if stock["stock_id"].upper() == code:
                return stock["stock_id"]

    for stock in stocks:
        if stock["stock_name"] == raw:
            return stock["stock_id"]

    matches = search_stocks(stocks, raw, limit=2)
    if len(matches) == 1:
        return matches[0]["stock_id"]
    return None


def preload_stock_list(on_ready=None, on_error=None):
    """背景載入股票清單（先內建/快取，再嘗試更新）"""
    def worker():
        try:
            stocks = load_stock_list()
            if on_ready:
                on_ready(stocks)

            cached_stocks, updated = _read_user_cache()
            if _cache_is_fresh(updated) and cached_stocks:
                return

            refresh_stock_list_async(
                on_updated=on_ready,
                on_error=on_error,
            )
        except Exception as exc:
            bundled = load_bundled_stock_list()
            if bundled:
                if on_ready:
                    on_ready(bundled)
            elif on_error:
                on_error(str(exc))

    threading.Thread(target=worker, daemon=True).start()
