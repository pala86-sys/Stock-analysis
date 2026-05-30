"""HTTP 請求：共用 Session 與指數退避重試"""

import time
from collections.abc import Callable
from typing import TypeVar

import requests

T = TypeVar("T")

_session: requests.Session | None = None
DEFAULT_RETRIES = 3
DEFAULT_BACKOFF = 1.5


def get_http_session() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
    return _session


def request_with_retry(
    method: str,
    url: str,
    *,
    max_retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
    **kwargs,
) -> requests.Response:
    """發送 HTTP 請求，失敗時指數退避重試"""
    kwargs.setdefault("timeout", 30)
    session = get_http_session()
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(backoff ** attempt)

    assert last_error is not None
    raise last_error


def call_with_retry(
    fn: Callable[[], T],
    *,
    max_retries: int = DEFAULT_RETRIES,
    backoff: float = DEFAULT_BACKOFF,
) -> T:
    """執行可呼叫物件，失敗時指數退避重試"""
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(backoff ** attempt)

    assert last_error is not None
    raise last_error
