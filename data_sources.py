"""外部資料來源：yfinance、FinMind API 請求與快取"""

import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

from finmind_client import FinMindApiError, finmind_quota_exhausted, request_finmind, reset_finmind_session
from http_client import call_with_retry, request_with_retry
from stock_search import lookup_bundled_stock

FINMIND_API = "https://api.finmindtrade.com/api/v4/data"
MARKET_SUFFIX = {"twse": ".TW", "tpex": ".TWO"}
MARKET_LABEL = {"twse": "上市", "tpex": "上櫃"}

SOURCE_LABELS = {
    "info": "Yahoo 股價",
    "history": "Yahoo K線",
    "finmind_price": "FinMind K線",
    "news": "Yahoo 新聞",
    "finmind_per": "FinMind 本益比",
    "finmind_industry": "FinMind 產業",
    "finmind_chips": "FinMind 籌碼",
    "finmind_news": "FinMind 新聞",
    "finmind_revenue": "FinMind 月營收",
    "finmind_financial": "FinMind 財報",
    "stock_info": "FinMind 股號",
}


def empty_cache_value(key: str):
    """各快取鍵的預設空值"""
    if key == "info":
        return {}
    if key == "news":
        return []
    if key == "history":
        return pd.DataFrame()
    return None


def finmind_price_to_history(raw: list | None) -> pd.DataFrame:
    """將 FinMind TaiwanStockPrice 轉成與 yfinance 相容的 OHLCV DataFrame"""
    if not raw:
        return pd.DataFrame()
    df = pd.DataFrame(raw)
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date", keep="last")
    df = df.set_index("date")
    rename = {
        "open": "Open",
        "max": "High",
        "min": "Low",
        "close": "Close",
        "Trading_Volume": "Volume",
    }
    for src, dst in rename.items():
        if src in df.columns:
            df[dst] = pd.to_numeric(df[src], errors="coerce")
    needed = ["Open", "High", "Low", "Close", "Volume"]
    if not all(col in df.columns for col in needed):
        return pd.DataFrame()
    return df[needed].dropna(how="any")


class StockDataSource:
    """股票資料抓取與快取"""

    def __init__(self, stock_id: str):
        cleaned_id = stock_id.strip().upper()

        if "." in cleaned_id:
            code, suffix = cleaned_id.split(".", 1)
            self.stock_code = code
            self.stock_symbol = f"{code}.{suffix}"
            self.market_type = "tpex" if suffix == "TWO" else "twse"
        elif cleaned_id.isdigit():
            self.stock_code = cleaned_id
            self.stock_symbol = None
            self.market_type = None
        else:
            self.stock_code = cleaned_id
            self.stock_symbol = cleaned_id
            self.market_type = None

        self._ticker = None
        self._cache: dict = {}
        self._errors: dict[str, str] = {}
        self._preloaded = False
        self._preload_in_progress = False

    @property
    def ticker(self):
        self.resolve_symbol()
        return self._ticker

    def get_errors(self) -> dict[str, str]:
        return dict(self._errors)

    def get_error_summary(self) -> list[str]:
        lines = []
        for key, err in self._errors.items():
            label = SOURCE_LABELS.get(key, key)
            detail = str(err).strip()
            if detail:
                lines.append(f"{label}：{detail[:120]}")
            else:
                lines.append(label)
        return lines

    def resolve_symbol(self):
        """依 FinMind 判斷上市 (.TW) 或上櫃 (.TWO) 並建立 yfinance Ticker"""
        if self.stock_symbol is not None:
            if self._ticker is None:
                self._ticker = yf.Ticker(self.stock_symbol)
            return

        stock_info = self.fetch_stock_info()
        market = (stock_info or {}).get("type")
        if not market:
            bundled = lookup_bundled_stock(self.stock_code) or {}
            market = bundled.get("market", "twse")
        self.market_type = market
        suffix = MARKET_SUFFIX.get(market, ".TW")
        self.stock_symbol = f"{self.stock_code}{suffix}"
        self._ticker = yf.Ticker(self.stock_symbol)

    def fetch_stock_info(self) -> dict | None:
        """從 FinMind 取得股票基本資訊（含上市/上櫃別）"""
        if "stock_info" in self._cache:
            return self._cache["stock_info"]
        try:
            data = request_finmind(self.stock_code, "TaiwanStockInfo", {})
            info = data[0] if data else None
            self._cache["stock_info"] = info
            if info and self.market_type is None:
                self.market_type = info.get("type")
            return info
        except Exception as exc:
            self._cache["stock_info"] = None
            self._errors["stock_info"] = str(exc)
            return None

    def get_market_label(self) -> str:
        if self.market_type in MARKET_LABEL:
            return MARKET_LABEL[self.market_type]
        if self.stock_symbol and self.stock_symbol.endswith(".TWO"):
            return "上櫃"
        if self.stock_symbol and self.stock_symbol.endswith(".TW"):
            return "上市"
        return "未知"

    def preload(self):
        """一次並行抓取所有外部資料並快取（阻塞直到全部完成）"""
        if self._preloaded:
            return
        if self._preload_in_progress:
            return
        self._run_preload()

    def preload_progressive(self, on_ready=None):
        """並行抓取資料，每完成一項即觸發 on_ready(cache_key)"""
        if self._preloaded:
            if on_ready:
                for key in (
                    "info", "history", "news",
                    "finmind_per", "finmind_industry", "finmind_chips", "finmind_news",
                    "finmind_revenue", "finmind_financial",
                ):
                    on_ready(key)
            return
        if self._preload_in_progress:
            return
        self._run_preload(on_ready=on_ready)

    def _fetch_yfinance_info(self):
        return call_with_retry(
            lambda: self.ticker.info or {},
            max_retries=4,
            backoff=2.0,
        )

    def _fetch_yfinance_history(self):
        return call_with_retry(lambda: self.ticker.history(period="1y"))

    def _fetch_yfinance_news(self):
        return call_with_retry(lambda: self.ticker.news or [])

    def _fetch_finmind_history(self):
        start = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        raw = request_finmind(self.stock_code, "TaiwanStockPrice", {"start_date": start})
        return finmind_price_to_history(raw)

    def _ensure_history_from_finmind(self) -> pd.DataFrame:
        """Yahoo K 線為空時，改抓 FinMind 日線（ETF 等較常需要）"""
        if self._cache.get("_finmind_history_tried"):
            history = self._cache.get("history")
            return history if isinstance(history, pd.DataFrame) else pd.DataFrame()

        self._cache["_finmind_history_tried"] = True
        try:
            fm_df = self._fetch_finmind_history()
            if not fm_df.empty:
                self._cache["history"] = fm_df
                self._errors.pop("history", None)
                return fm_df
        except Exception as exc:
            if "history" not in self._errors:
                self._errors["history"] = str(exc)
            self._errors["finmind_price"] = str(exc)
        history = self._cache.get("history")
        return history if isinstance(history, pd.DataFrame) else pd.DataFrame()

    def _run_preload(self, on_ready=None):
        self._preload_in_progress = True
        self._errors.clear()
        reset_finmind_session()
        self.resolve_symbol()

        end_date = datetime.now().strftime("%Y-%m-%d")
        chips_start = (datetime.now() - timedelta(days=45)).strftime("%Y-%m-%d")
        per_start = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
        news_start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        revenue_start = (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d")
        financial_start = (datetime.now() - timedelta(days=365 * 4)).strftime("%Y-%m-%d")
        stock_code = self.stock_code

        yahoo_tasks = {
            "info": self._fetch_yfinance_info,
            "history": self._fetch_yfinance_history,
            "news": self._fetch_yfinance_news,
        }
        finmind_tasks = {
            "finmind_per": lambda: request_finmind(
                stock_code, "TaiwanStockPER", {"start_date": per_start}
            ),
            "finmind_industry": lambda: request_finmind(
                stock_code, "TaiwanStockInfoWithWarrant", {}
            ),
            "finmind_chips": lambda: request_finmind(
                stock_code,
                "TaiwanStockInstitutionalInvestorsBuySell",
                {"start_date": chips_start, "end_date": end_date},
            ),
            "finmind_news": lambda: request_finmind(
                stock_code, "TaiwanStockNews", {"start_date": news_start}
            ),
            "finmind_revenue": lambda: request_finmind(
                stock_code, "TaiwanStockMonthRevenue", {"start_date": revenue_start}
            ),
            "finmind_financial": lambda: request_finmind(
                stock_code, "TaiwanStockFinancialStatements", {"start_date": financial_start}
            ),
        }

        def _store(key: str, value, exc: Exception | None = None):
            if exc is not None:
                self._cache[key] = empty_cache_value(key)
                self._errors[key] = str(exc)
            else:
                self._cache[key] = value
            if on_ready:
                on_ready(key)

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {key: executor.submit(task) for key, task in yahoo_tasks.items()}
            for future in as_completed(futures.values()):
                key = next(k for k, f in futures.items() if f is future)
                try:
                    _store(key, future.result())
                except Exception as exc:
                    _store(key, None, exc)

        history = self._cache.get("history")
        if not isinstance(history, pd.DataFrame) or history.empty:
            if not finmind_quota_exhausted():
                try:
                    fm_df = self._fetch_finmind_history()
                    if not fm_df.empty:
                        self._cache["history"] = fm_df
                        self._errors.pop("history", None)
                except Exception as exc:
                    self._errors["finmind_price"] = str(exc)
                    if "history" not in self._errors:
                        self._errors["history"] = str(exc)
            self._cache["_finmind_history_tried"] = True

        for key, task in finmind_tasks.items():
            if finmind_quota_exhausted():
                _store(
                    key,
                    None,
                    FinMindApiError("FinMind 配額用盡或 IP 暫封，已略過後續請求", status=402),
                )
                continue
            try:
                _store(key, task())
            except FinMindApiError as exc:
                _store(key, None, exc)
            except Exception as exc:
                _store(key, None, exc)

        self._retry_failed_preload(yahoo_tasks, finmind_tasks)

        self._preloaded = True
        self._preload_in_progress = False

    def _retry_failed_preload(self, yahoo_tasks: dict, finmind_tasks: dict) -> None:
        """預載結束後再試一次失敗的來源（網路偶發失敗時，避免使用者需手動重查）"""
        for key in list(self._errors.keys()):
            err = str(self._errors[key]).lower()
            if any(token in err for token in ("402", "403", "quota", "banned", "upper limit", "配額")):
                continue
            if finmind_quota_exhausted() and key.startswith("finmind"):
                continue
            task = yahoo_tasks.get(key) or finmind_tasks.get(key)
            if not task:
                continue
            try:
                self._cache[key] = task()
                del self._errors[key]
            except Exception as exc:
                self._errors[key] = str(exc)

    def _price_from_info(self, info: dict) -> float | None:
        for key in ("regularMarketPrice", "previousClose", "currentPrice", "open"):
            value = info.get(key)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
        return None

    def get_market_price(self) -> float | None:
        """目前股價：Yahoo info 優先，失敗時改用最後收盤價"""
        self._ensure_preloaded()
        price = self._price_from_info(self._cache.get("info") or {})
        if price is not None:
            return price

        history = self.get_history()
        if not history.empty and "Close" in history.columns:
            closes = history["Close"].dropna()
            if not closes.empty:
                last = float(closes.iloc[-1])
                if last > 0:
                    return last
        return None

    def refresh_market_price(self) -> float | None:
        """info 無股價時再向 Yahoo 重試一次"""
        price = self.get_market_price()
        if price is not None:
            return price
        try:
            self._cache["info"] = self._fetch_yfinance_info()
            self._errors.pop("info", None)
        except Exception as exc:
            self._errors["info"] = str(exc)
        return self.get_market_price()

    def _ensure_preloaded(self):
        if not self._preloaded and not self._preload_in_progress:
            self.preload()

    def get_info(self) -> dict:
        self._ensure_preloaded()
        return self._cache.get("info") or {}

    def get_history(self) -> pd.DataFrame:
        self._ensure_preloaded()
        history = self._cache.get("history")
        if isinstance(history, pd.DataFrame) and not history.empty:
            return history
        return self._ensure_history_from_finmind()

    def get_news_raw(self) -> list:
        self._ensure_preloaded()
        return self._cache.get("news") or []

    def get_finmind_per(self) -> dict | None:
        self._ensure_preloaded()
        data = self._cache.get("finmind_per")
        return data[-1] if data else None

    def get_finmind_industry_raw(self) -> list | None:
        self._ensure_preloaded()
        return self._cache.get("finmind_industry")

    def get_finmind_chips_raw(self) -> list | None:
        self._ensure_preloaded()
        return self._cache.get("finmind_chips")

    def get_finmind_news_raw(self) -> list | None:
        self._ensure_preloaded()
        return self._cache.get("finmind_news")

    def get_finmind_revenue_raw(self) -> list | None:
        self._ensure_preloaded()
        return self._cache.get("finmind_revenue")

    def get_finmind_financial_raw(self) -> list | None:
        self._ensure_preloaded()
        return self._cache.get("finmind_financial")
