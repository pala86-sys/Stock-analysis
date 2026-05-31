"""台股多維度分析核心邏輯"""

import threading
from collections.abc import Callable

from data_sources import StockDataSource
from indicators import (
    build_technical_summary,
    compute_support_resistance,
    compute_technical_indicators,
    format_dividend_yield,
    format_support_resistance,
    parse_chips_records,
    parse_monthly_revenue,
    parse_quarterly_eps,
    pick_metric,
)
from industry import (
    build_chinese_overview,
    build_company_intro,
    detect_themes,
    format_business_summary,
    format_employees,
    format_headquarters,
    parse_finmind_industry,
    resolve_company_names,
)
from news import merge_news, parse_finmind_news, parse_yfinance_news
from security_type import security_type_label
from valuation import assess_price_level

SECTION_REQUIRES = {
    "chips": {"finmind_chips"},
    "news": {"finmind_news", "news"},
    "profile": {"info", "finmind_industry"},
    "fundamental": {"info", "finmind_per", "finmind_revenue", "finmind_financial"},
    "technical": {"history", "info"},
}

SECTION_ORDER = ("chips", "news", "profile", "fundamental", "technical")


def _format_pe_display(pe, raw_pe) -> str | float:
    if pe != "無資料":
        return pe
    if isinstance(raw_pe, (int, float)) and raw_pe <= 0:
        return "0（無獲利）"
    return "無資料"


class StockAnalyzer:
    """
    台股多維度分析核心邏輯類別
    負責協調資料抓取、指標計算與各面向分析結果組裝
    """

    def __init__(self, stock_id: str):
        self._source = StockDataSource(stock_id)

    @property
    def stock_code(self) -> str:
        return self._source.stock_code

    @property
    def stock_symbol(self) -> str | None:
        return self._source.stock_symbol

    @property
    def market_type(self) -> str | None:
        return self._source.market_type

    @property
    def ticker(self):
        return self._source.ticker

    def get_profile(self) -> dict:
        """取得公司簡介、產業分類與投資題材"""
        try:
            info = self._source.get_info()
            stock_info = self._source.fetch_stock_info() or {}
            industry = parse_finmind_industry(self._source.get_finmind_industry_raw())
            summary = info.get("longBusinessSummary", "")
            themes = detect_themes(industry, summary)

            if not industry and info.get("industry"):
                industry = info.get("industry")

            names = resolve_company_names(self.stock_code, stock_info, info)
            employees = format_employees(info)
            headquarters = format_headquarters(info)
            website = (info.get("website") or "").strip()
            chinese_overview = build_chinese_overview(industry, info, stock_info)
            english_summary = format_business_summary(summary)

            return {
                **names,
                "產業分類": industry or "無公開資料",
                "交易市場": self._source.get_market_label(),
                "員工人數": employees or "—",
                "總部": headquarters or "—",
                "官網": website or "—",
                "投資題材": "、".join(themes) if themes else "待觀察",
                "themes": themes,
                "中文概況": chinese_overview,
                "原文摘要": english_summary,
                "公司簡介": build_company_intro(industry, info, stock_info),
            }
        except Exception as e:
            return {"錯誤": f"公司簡介抓取失敗: {str(e)}"}

    def get_fundamental(self) -> dict:
        """獲取基本面數據（PER/PBR/殖利率 + 歷史營收與 EPS）"""
        try:
            info = self._source.get_info()
            price = self._source.refresh_market_price()
            if price is None:
                raise ValueError("無法取得該股票的股價（Yahoo 與 K 線皆無資料）")

            finmind = self._source.get_finmind_per()
            raw_pe = pick_metric(
                finmind.get("PER") if finmind else None,
                info.get("trailingPE"),
                positive_only=False,
            )
            pe = pick_metric(
                finmind.get("PER") if finmind else None,
                info.get("trailingPE"),
                positive_only=True,
            )
            pb = pick_metric(
                finmind.get("PBR") if finmind else None,
                info.get("priceToBook"),
                positive_only=True,
            )

            if finmind and finmind.get("dividend_yield") is not None:
                dividend_yield = round(finmind["dividend_yield"], 2)
            else:
                dividend_yield = format_dividend_yield(info)

            if finmind and finmind.get("PER") and finmind["PER"] > 0:
                eps = round(price / finmind["PER"], 2)
            elif info.get("trailingEps") is not None and info.get("trailingEps") > 0:
                eps = round(info["trailingEps"], 2)
            else:
                eps = "無資料"

            stock_info = self._source.fetch_stock_info() or {}
            names = resolve_company_names(self.stock_code, stock_info, info)
            price_level = assess_price_level(pe, pb, raw_pe=raw_pe)
            product_type = security_type_label(
                self.stock_code, stock_info, names.get("公司名稱")
            )

            metrics = {
                **names,
                "商品類型": product_type,
                "目前股價": price,
                "價位評估": price_level["價位評估"],
                "價位說明": price_level["價位說明"],
                "價位tone": price_level["tone"],
                "市值 (億)": round(info.get("marketCap", 0) / 100000000, 2) if info.get("marketCap") else "無資料",
                "本益比 (PE)": _format_pe_display(pe, raw_pe),
                "股價淨值比 (PB)": pb,
                "每股盈餘 (EPS)": eps,
                "股利殖利率 (%)": dividend_yield,
            }

            revenue_history = parse_monthly_revenue(self._source.get_finmind_revenue_raw(), limit=36)
            eps_history = parse_quarterly_eps(self._source.get_finmind_financial_raw(), limit=16)

            return {
                "metrics": metrics,
                "revenue_history": revenue_history,
                "eps_history": eps_history,
            }
        except Exception as e:
            return {"錯誤": f"基本面抓取失敗: {str(e)}"}

    def get_technical(self) -> dict:
        """獲取技術面數據摘要"""
        result = self.get_technical_chart_data()
        if "error" in result:
            return {"錯誤": result["error"]}
        return result["summary"]

    def get_technical_chart_data(self, display_days: int = 90) -> dict:
        """獲取技術面圖表資料：K 線 + 均線 + 成交量 + KD + MACD"""
        try:
            history = self._source.get_history()
            if history.empty:
                return {"error": "查無近期 K 線資料"}

            df = compute_technical_indicators(history)
            if df.empty:
                return {"error": "K 線資料不足，無法繪製圖表"}

            info = self._source.get_info()
            stock_info = self._source.fetch_stock_info() or {}
            names = resolve_company_names(self.stock_code, stock_info, info)
            stock_name = names["顯示名稱"]
            display_days = min(display_days, len(df))
            display_df = df.tail(display_days)
            levels = compute_support_resistance(display_df)
            summary = build_technical_summary(df.iloc[-1])
            summary.update(format_support_resistance(levels))

            return {
                "full_data": df,
                "data": display_df,
                "display_days": display_days,
                "summary": summary,
                "levels": levels,
                "stock_name": stock_name,
            }
        except Exception as e:
            return {"error": f"技術面分析失敗: {str(e)}"}

    def get_chips(self, days: int = 10) -> dict:
        """獲取籌碼面：外資、投信、自營商每日買賣超與連續天數"""
        try:
            return parse_chips_records(self._source.get_finmind_chips_raw(), days)
        except Exception as e:
            return {
                "records": [{"錯誤": f"籌碼面分析失敗: {str(e)}"}],
                "summary": {},
            }

    def get_news(self, limit: int = 8) -> list:
        """獲取消息面：FinMind 台股新聞為主，Yahoo Finance 為輔"""
        try:
            finmind_news = parse_finmind_news(self._source.get_finmind_news_raw(), limit)
            yfinance_news = parse_yfinance_news(self._source.get_news_raw(), limit=3)
            news_list = merge_news(finmind_news, yfinance_news, limit)

            if not news_list:
                return [{"標題": "近期無重大市場新聞", "來源": "-", "連結": "", "發布時間": ""}]
            return news_list
        except Exception as e:
            return [{"標題": f"新聞抓取失敗: {str(e)}", "來源": "錯誤", "連結": "", "發布時間": ""}]

    def analyze_all(self) -> dict:
        """一次抓取所有分析資料（供背景執行緒使用）"""
        self._source.preload()
        return {
            "profile": self.get_profile(),
            "fundamental": self.get_fundamental(),
            "technical": self.get_technical_chart_data(),
            "chips": self.get_chips(),
            "news": self.get_news(),
        }

    def get_data_errors(self) -> dict[str, str]:
        return self._source.get_errors()

    def get_data_error_summary(self) -> list[str]:
        return self._source.get_error_summary()

    def analyze_progressive(
        self,
        on_section: Callable[[str, object], None],
        on_complete: Callable[[], None] | None = None,
    ):
        """漸進式分析：各資料源完成後立即推送對應分頁結果"""
        ready_keys: set[str] = set()
        emitted: set[str] = set()
        lock = threading.Lock()

        def build_section(section: str):
            if section == "profile":
                return self.get_profile()
            if section == "fundamental":
                return self.get_fundamental()
            if section == "technical":
                return self.get_technical_chart_data()
            if section == "chips":
                return self.get_chips()
            if section == "news":
                return self.get_news()
            raise ValueError(f"未知分頁: {section}")

        def try_emit(section: str):
            with lock:
                if section in emitted:
                    return
                if not SECTION_REQUIRES[section] <= ready_keys:
                    return
                emitted.add(section)
            on_section(section, build_section(section))

        def on_data_ready(key: str):
            with lock:
                ready_keys.add(key)
            for section in SECTION_ORDER:
                try_emit(section)

        self._source.preload_progressive(on_data_ready)

        for section in SECTION_ORDER:
            try_emit(section)

        if on_complete:
            on_complete()
