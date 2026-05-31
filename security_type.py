"""商品類型辨識（股票 / ETF）"""

import re


def is_etf(stock_code: str, stock_info: dict | None = None, stock_name: str | None = None) -> bool:
    """判斷是否為 ETF（FinMind 產業別優先，其次名稱與代號規則）"""
    info = stock_info or {}
    name = (stock_name or info.get("stock_name") or "").strip()
    category = (info.get("industry_category") or "").strip().upper()

    if category == "ETF" or "ETF" in category:
        return True
    if "ETF" in name.upper():
        return True

    code = str(stock_code or "").strip().upper()
    if re.match(r"^00[0-9A-Z]", code):
        return True
    return False


def security_type_label(stock_code: str, stock_info: dict | None = None, stock_name: str | None = None) -> str:
    return "ETF" if is_etf(stock_code, stock_info, stock_name) else "股票"
