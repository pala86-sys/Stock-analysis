"""FinMind API 請求（Token、節流、重試）"""

import os
import time

from http_client import call_with_retry, request_with_retry

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"
_LAST_REQUEST_AT = 0.0
# 無 Token 時 FinMind 每 IP 每小時僅 300 次，雲端共用 IP 需拉長間隔
_MIN_INTERVAL = 0.4
_MIN_INTERVAL_WITH_TOKEN = 0.12


def finmind_token() -> str:
    return os.environ.get("FINMIND_TOKEN", "").strip()


def finmind_headers() -> dict[str, str]:
    token = finmind_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _throttle() -> None:
    global _LAST_REQUEST_AT
    interval = _MIN_INTERVAL_WITH_TOKEN if finmind_token() else _MIN_INTERVAL
    now = time.monotonic()
    wait = interval - (now - _LAST_REQUEST_AT)
    if wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_AT = time.monotonic()


def request_finmind(stock_code: str, dataset: str, extra_params: dict) -> list | None:
    """發送 FinMind API 請求（含重試）"""
    params = {"dataset": dataset, "data_id": stock_code, **extra_params}

    def _fetch():
        _throttle()
        response = request_with_retry(
            "GET",
            FINMIND_API,
            params=params,
            headers=finmind_headers(),
            timeout=30,
        )
        payload = response.json()
        status = payload.get("status")
        if status != 200:
            msg = payload.get("msg") or f"HTTP status={status}"
            raise RuntimeError(str(msg))
        return payload.get("data") or None

    retries = 2 if finmind_token() else 3
    return call_with_retry(_fetch, max_retries=retries)


def request_finmind_stock_list() -> list[dict]:
    """取得全部台股清單"""
    def _fetch():
        _throttle()
        response = request_with_retry(
            "GET",
            FINMIND_API,
            params={"dataset": "TaiwanStockInfo", "data_id": ""},
            headers=finmind_headers(),
            timeout=60,
        )
        payload = response.json()
        if payload.get("status") != 200:
            raise RuntimeError(payload.get("msg") or "無法取得股票清單")
        return payload.get("data") or []

    return call_with_retry(_fetch)
