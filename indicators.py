"""技術指標計算與籌碼、基本面數值格式化"""

import pandas as pd


def compute_technical_indicators(history: pd.DataFrame) -> pd.DataFrame:
    """計算均線、KD、MACD 等技術指標"""
    df = history.copy()
    close = df["Close"]

    df["MA5"] = close.rolling(5).mean()
    df["MA10"] = close.rolling(10).mean()
    df["MA20"] = close.rolling(20).mean()
    df["MA60"] = close.rolling(60).mean()

    low_min = df["Low"].rolling(9).min()
    high_max = df["High"].rolling(9).max()
    rsv = (close - low_min) / (high_max - low_min).replace(0, pd.NA) * 100
    df["K"] = rsv.ewm(com=2, adjust=False).mean()
    df["D"] = df["K"].ewm(com=2, adjust=False).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["DIF"] = ema12 - ema26
    df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD_hist"] = (df["DIF"] - df["DEA"]) * 2

    return df.dropna()


def build_technical_summary(latest: pd.Series) -> dict:
    """建立技術面摘要字典"""
    latest_price = latest["Close"]
    return {
        "MA5": round(latest["MA5"], 2),
        "MA10": round(latest["MA10"], 2),
        "MA20": round(latest["MA20"], 2),
        "MA60": round(latest["MA60"], 2),
        "5日均線 (MA5)": round(latest["MA5"], 2),
        "20日月線 (MA20)": round(latest["MA20"], 2),
        "60日季線 (MA60)": round(latest["MA60"], 2),
        "技術短評": "股價在月線之上（偏多）" if latest_price > latest["MA20"] else "股價在月線之下（偏空）",
    }


def compute_support_resistance(df: pd.DataFrame, swing_window: int = 5) -> dict:
    """
    計算支撐 / 壓力價位
    綜合波段高低點、區間極值與均線，取距離現價最近的各兩檔
    """
    if df is None or df.empty:
        return {"supports": [], "resistances": [], "period_high": None, "period_low": None}

    close = float(df.iloc[-1]["Close"])
    highs = df["High"].values
    lows = df["Low"].values
    w = min(swing_window, max(1, len(df) // 10))

    swing_highs: list[float] = []
    swing_lows: list[float] = []
    for i in range(w, len(df) - w):
        segment_h = highs[i - w : i + w + 1]
        segment_l = lows[i - w : i + w + 1]
        if highs[i] >= segment_h.max():
            swing_highs.append(float(highs[i]))
        if lows[i] <= segment_l.min():
            swing_lows.append(float(lows[i]))

    period_high = float(df["High"].max())
    period_low = float(df["Low"].min())

    latest = df.iloc[-1]
    ma_levels: list[float] = []
    for col in ("MA5", "MA10", "MA20", "MA60"):
        if col in latest.index and pd.notna(latest[col]):
            ma_levels.append(float(latest[col]))

    resistance_pool: set[float] = {round(v, 2) for v in swing_highs + [period_high] if v > close}
    support_pool: set[float] = {round(v, 2) for v in swing_lows + [period_low] if v < close}
    for val in ma_levels:
        rounded = round(val, 2)
        if rounded > close:
            resistance_pool.add(rounded)
        elif rounded < close:
            support_pool.add(rounded)

    supports = sorted(support_pool, reverse=True)[:2]
    resistances = sorted(resistance_pool)[:2]

    return {
        "supports": supports,
        "resistances": resistances,
        "period_high": round(period_high, 2),
        "period_low": round(period_low, 2),
        "current_price": round(close, 2),
    }


def format_support_resistance(levels: dict) -> dict:
    """將支撐壓力轉為摘要文字"""
    supports = levels.get("supports") or []
    resistances = levels.get("resistances") or []
    result = {}

    if supports:
        result["第一支撐"] = supports[0]
        result["支撐說明"] = f"近端支撐 {supports[0]}" + (f"、{supports[1]}" if len(supports) > 1 else "")
    else:
        result["第一支撐"] = "—"
        result["支撐說明"] = "現價接近區間低點"

    if resistances:
        result["第一壓力"] = resistances[0]
        result["壓力說明"] = f"近端壓力 {resistances[0]}" + (f"、{resistances[1]}" if len(resistances) > 1 else "")
    else:
        result["第一壓力"] = "—"
        result["壓力說明"] = "現價接近區間高點"

    if levels.get("period_high") is not None:
        result["區間最高"] = levels["period_high"]
        result["區間最低"] = levels["period_low"]
    return result


def format_lots(shares: int) -> str:
    """將股數轉換為張數並加上正負號與千分位"""
    lots = shares / 1000
    if lots > 0:
        return f"+{lots:,.0f}"
    if lots < 0:
        return f"{lots:,.0f}"
    return "0"


def _foreign_net(daily: dict[str, int]) -> int:
    return daily.get("Foreign_Investor", 0) + daily.get("Foreign_Dealer_Self", 0)


def _trust_net(daily: dict[str, int]) -> int:
    return daily.get("Investment_Trust", 0)


def _dealer_net(daily: dict[str, int]) -> int:
    return daily.get("Dealer_self", 0) + daily.get("Dealer_Hedging", 0)


def count_consecutive_streak(nets: list[int]) -> str:
    """依時間由舊到新，計算最近連續買超或賣超天數"""
    if not nets:
        return "無資料"

    latest = nets[-1]
    if latest == 0:
        return "今日持平"

    direction = "買超" if latest > 0 else "賣超"
    count = 0
    for net in reversed(nets):
        if latest > 0 and net > 0:
            count += 1
        elif latest < 0 and net < 0:
            count += 1
        elif net == 0:
            break
        else:
            break
    return f"連續{count}日{direction}"


def parse_chips_records(data: list | None, days: int = 10) -> dict:
    """解析 FinMind 三大法人買賣超資料（含自營商、合計與連續天數）"""
    if not data:
        return {
            "records": [{"錯誤": "查無三大法人買賣超資料，請確認股票代號是否正確"}],
            "summary": {},
        }

    by_date: dict[str, dict[str, int]] = {}
    for item in data:
        date = item["date"]
        name = item["name"]
        net = item["buy"] - item["sell"]
        by_date.setdefault(date, {})[name] = net

    if not by_date:
        return {
            "records": [{"錯誤": "近期無法人買賣超紀錄"}],
            "summary": {},
        }

    chronological_dates = sorted(by_date.keys())
    foreign_series: list[int] = []
    trust_series: list[int] = []
    dealer_series: list[int] = []
    total_series: list[int] = []

    for date in chronological_dates:
        daily = by_date[date]
        foreign = _foreign_net(daily)
        trust = _trust_net(daily)
        dealer = _dealer_net(daily)
        foreign_series.append(foreign)
        trust_series.append(trust)
        dealer_series.append(dealer)
        total_series.append(foreign + trust + dealer)

    records = []
    for date in reversed(chronological_dates):
        daily = by_date[date]
        foreign = _foreign_net(daily)
        trust = _trust_net(daily)
        dealer = _dealer_net(daily)
        total = foreign + trust + dealer
        records.append({
            "日期": date,
            "外資買賣超(張)": format_lots(foreign),
            "投信買賣超(張)": format_lots(trust),
            "自營商買賣超(張)": format_lots(dealer),
            "三大法人合計(張)": format_lots(total),
        })
        if len(records) >= days:
            break

    latest_date = chronological_dates[-1]
    summary = {
        "最新日期": latest_date,
        "外資": count_consecutive_streak(foreign_series),
        "投信": count_consecutive_streak(trust_series),
        "自營商": count_consecutive_streak(dealer_series),
        "三大法人合計": count_consecutive_streak(total_series),
    }
    return {"records": records, "summary": summary}


def format_dividend_yield(info: dict) -> str | float:
    """解析 yfinance 殖利率（台股 dividendYield 可能已是百分比）"""
    if info.get("trailingAnnualDividendYield") is not None:
        return round(info["trailingAnnualDividendYield"] * 100, 2)

    price = info.get("regularMarketPrice") or info.get("previousClose")
    div_rate = info.get("trailingAnnualDividendRate") or info.get("dividendRate")
    if price and div_rate:
        return round(div_rate / price * 100, 2)

    dy = info.get("dividendYield")
    if dy is None:
        return "無分紅"
    return round(dy, 2) if dy > 0.2 else round(dy * 100, 2)


def pick_metric(finmind_val, yfinance_val, decimals: int = 2, *, positive_only: bool = False):
    """優先使用 FinMind 數值，無資料時退回 yfinance"""
    for val in (finmind_val, yfinance_val):
        if val is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            continue
        if positive_only and num <= 0:
            continue
        return round(num, decimals)
    return "無資料"


def _format_pct_change(current: float, previous: float) -> str:
    if not previous:
        return "—"
    return f"{(current - previous) / abs(previous) * 100:+.1f}"


def parse_monthly_revenue(data: list | None, limit: int = 24) -> list[dict]:
    """解析 FinMind 月營收（含月增率、年增率）"""
    if not data:
        return []

    by_period: dict[tuple[int, int], dict] = {}
    for item in data:
        year = item.get("revenue_year")
        month = item.get("revenue_month")
        if year is None or month is None:
            continue
        by_period[(year, month)] = item

    periods = sorted(by_period.keys(), reverse=True)[:limit]
    records = []
    for year, month in periods:
        item = by_period[(year, month)]
        revenue = item.get("revenue", 0)

        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year = year - 1

        mom = "—"
        prev_item = by_period.get((prev_year, prev_month))
        if prev_item and prev_item.get("revenue"):
            mom = _format_pct_change(revenue, prev_item["revenue"])

        yoy = "—"
        ly_item = by_period.get((year - 1, month))
        if ly_item and ly_item.get("revenue"):
            yoy = _format_pct_change(revenue, ly_item["revenue"])

        records.append({
            "期間": f"{year}/{month:02d}",
            "營收(億)": f"{revenue / 1e8:,.1f}",
            "月增率(%)": mom,
            "年增率(%)": yoy,
        })
    return records


def _quarter_from_date(date_str: str) -> tuple[int, int]:
    month = int(date_str[5:7])
    year = int(date_str[:4])
    quarter = (month - 1) // 3 + 1
    return year, quarter


def parse_quarterly_eps(data: list | None, limit: int = 12) -> list[dict]:
    """解析 FinMind 季 EPS（含季增率、年增率）"""
    if not data:
        return []

    by_quarter: dict[tuple[int, int], float] = {}
    for item in data:
        if item.get("type") != "EPS":
            continue
        yq = _quarter_from_date(item["date"])
        by_quarter[yq] = float(item["value"])

    records = []
    for year, quarter in sorted(by_quarter.keys(), reverse=True)[:limit]:
        eps = by_quarter[(year, quarter)]

        prev_q = (year, quarter - 1) if quarter > 1 else (year - 1, 4)
        qoq = "—"
        if prev_q in by_quarter and by_quarter[prev_q]:
            qoq = _format_pct_change(eps, by_quarter[prev_q])

        yoy_q = (year - 1, quarter)
        yoy = "—"
        if yoy_q in by_quarter and by_quarter[yoy_q]:
            yoy = _format_pct_change(eps, by_quarter[yoy_q])

        records.append({
            "期間": f"{year} Q{quarter}",
            "EPS(元)": round(eps, 2),
            "季增率(%)": qoq,
            "年增率(%)": yoy,
        })
    return records
