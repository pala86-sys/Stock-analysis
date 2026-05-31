"""FinMind API 請求（Token、節流、避免 4xx 重試）"""

import os
import time

import requests

from http_client import get_http_session

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"
_LAST_REQUEST_AT = 0.0
# 無 Token 時 FinMind 每 IP 每小時僅 300 次，雲端共用 IP 需拉長間隔
_MIN_INTERVAL = 0.4
_MIN_INTERVAL_WITH_TOKEN = 0.12
# 402 配額用盡 / 403 IP 封鎖：同一程序內不再打 FinMind
_quota_exhausted = False


class FinMindApiError(RuntimeError):
    """FinMind 業務錯誤（含 status / HTTP status）"""

    def __init__(self, message: str, *, status: int | None = None, http_status: int | None = None):
        super().__init__(message)
        self.status = status
        self.http_status = http_status

    @property
    def is_quota_or_ban(self) -> bool:
        if self.http_status in (402, 403):
            return True
        if self.status in (402, 403):
            return True
        lowered = str(self).lower()
        return "upper limit" in lowered or "ip banned" in lowered


def finmind_quota_exhausted() -> bool:
    return _quota_exhausted


def reset_finmind_session() -> None:
    """新一輪分析開始時重置（同一輪內仍會在遇到 402/403 後熔斷）"""
    global _quota_exhausted
    _quota_exhausted = False


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


def _parse_finmind_response(response: requests.Response) -> list | None:
    global _quota_exhausted

    http_status = response.status_code
    try:
        payload = response.json()
    except ValueError:
        payload = {}

    api_status = payload.get("status")
    msg = str(payload.get("msg") or f"HTTP {http_status}")

    if http_status in (401, 402, 403) or api_status in (401, 402, 403):
        if http_status in (402, 403) or api_status in (402, 403):
            _quota_exhausted = True
        raise FinMindApiError(
            msg,
            status=api_status if isinstance(api_status, int) else None,
            http_status=http_status,
        )

    response.raise_for_status()

    if api_status != 200:
        raise FinMindApiError(
            msg,
            status=api_status if isinstance(api_status, int) else None,
            http_status=http_status,
        )

    return payload.get("data") or None


def _request_once(params: dict, *, timeout: int) -> list | None:
    if _quota_exhausted:
        raise FinMindApiError("FinMind 配額用盡或 IP 暫封，已略過本次請求", status=402)

    _throttle()
    session = get_http_session()
    response = session.get(
        FINMIND_API,
        params=params,
        headers=finmind_headers(),
        timeout=timeout,
    )
    return _parse_finmind_response(response)


def request_finmind(stock_code: str, dataset: str, extra_params: dict) -> list | None:
    """發送 FinMind API 請求（僅對網路/5xx 重試，402/403 不重試）"""
    params = {"dataset": dataset, "data_id": stock_code, **extra_params}
    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            return _request_once(params, timeout=30)
        except FinMindApiError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(1.5 ** attempt)

    assert last_error is not None
    raise last_error


def request_finmind_stock_list() -> list[dict]:
    """取得全部台股清單"""
    params = {"dataset": "TaiwanStockInfo", "data_id": ""}
    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            data = _request_once(params, timeout=60)
            return data or []
        except FinMindApiError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(1.5 ** attempt)

    assert last_error is not None
    raise last_error


def request_finmind_delisted_stock_ids() -> set[str]:
    """取得已下市櫃股票代號"""
    params = {"dataset": "TaiwanStockDelisting", "data_id": ""}
    max_retries = 3
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            data = _request_once(params, timeout=60)
            ids: set[str] = set()
            for item in data or []:
                stock_id = str(item.get("stock_id", "")).strip()
                if stock_id:
                    ids.add(stock_id)
            return ids
        except FinMindApiError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(1.5 ** attempt)

    assert last_error is not None
    raise last_error
