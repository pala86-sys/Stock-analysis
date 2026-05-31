"""Web 版分析服務：重用核心邏輯並輸出 JSON"""

import base64
from typing import Any

import pandas as pd

from advice import build_investment_advice
from chart_render import render_chart_png, serialize_chart_bars
from logic import StockAnalyzer
from report_export import build_pdf_report
from stock_search import format_stock_option, load_bundled_stock_list, resolve_stock_input, search_stocks


def _json_safe(value: Any) -> Any:
    if isinstance(value, pd.DataFrame):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _prepare_technical(technical: dict, display_days: int = 90) -> dict:
    if "error" in technical:
        return {"error": technical["error"]}

    full_data = technical.get("full_data")
    bars: list[dict] = []
    if full_data is not None and not getattr(full_data, "empty", True):
        bars = serialize_chart_bars(full_data, max_days=180)

    return {
        "summary": _json_safe(technical.get("summary", {})),
        "levels": _json_safe(technical.get("levels", {})),
        "stock_name": technical.get("stock_name", ""),
        "display_days": min(display_days, len(bars)) if bars else display_days,
        "bars": bars,
    }


def get_stock_suggestions(query: str, limit: int = 12) -> list[dict]:
    stocks = load_bundled_stock_list()
    if not stocks:
        return []
    matches = search_stocks(stocks, query, limit=limit)
    return [
        {
            "stock_id": s["stock_id"],
            "stock_name": s["stock_name"],
            "market": s.get("market", ""),
            "label": format_stock_option(s),
        }
        for s in matches
    ]


def resolve_stock(query: str) -> str | None:
    stocks = load_bundled_stock_list()
    return resolve_stock_input(query, stocks)


def run_analysis(stock_id: str, display_days: int = 90) -> dict:
    """執行完整分析，回傳 JSON 可序列化結果"""
    analyzer = StockAnalyzer(stock_id)
    sections = analyzer.analyze_all()
    errors = analyzer.get_data_error_summary()

    advice = build_investment_advice(
        sections.get("fundamental", {}),
        sections.get("technical", {}),
        sections.get("chips", {}),
    )

    technical_raw = sections.get("technical", {})
    if "error" not in technical_raw:
        technical_raw = analyzer.get_technical_chart_data(display_days=display_days)

    chart_b64 = None
    if "error" not in technical_raw and technical_raw.get("full_data") is not None:
        png = render_chart_png(
            technical_raw["full_data"],
            technical_raw.get("summary", {}),
            technical_raw.get("stock_name", ""),
            display_days=display_days,
        )
        if png:
            chart_b64 = base64.b64encode(png).decode("ascii")

    return {
        "stock_id": analyzer.stock_code,
        "errors": errors,
        "advice": _json_safe(advice),
        "sections": {
            "profile": _json_safe(sections.get("profile", {})),
            "fundamental": _json_safe(sections.get("fundamental", {})),
            "technical": _prepare_technical(technical_raw, display_days),
            "chips": _json_safe(sections.get("chips", {})),
            "news": _json_safe(sections.get("news", [])),
        },
        "chart_base64": chart_b64,
    }


def build_report_pdf(stock_id: str, result: dict) -> bytes:
    """由分析結果產生 PDF 報告"""
    chart_bytes = None
    if result.get("chart_base64"):
        chart_bytes = base64.b64decode(result["chart_base64"])

    sections = dict(result.get("sections", {}))
    if chart_bytes and "technical" in sections:
        sections["technical"] = dict(sections["technical"])

    return build_pdf_report(
        stock_id,
        result.get("advice", {}),
        sections,
        chart_png_bytes=chart_bytes,
        data_errors=result.get("errors") or None,
    )
