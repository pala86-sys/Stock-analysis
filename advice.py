"""綜合評估：依基本面、技術面、籌碼面產生入手參考意見（規則式，非投資建議）"""

import pandas as pd

from indicators import detect_key_candle_signals
from security_type import security_type_label
from valuation import pb_detail_note, pe_detail_note, pe_invalid_reason, valid_ratio


def _parse_pct(text: str) -> float | None:
    if not text or text == "—":
        return None
    try:
        return float(str(text).replace("%", "").replace("+", ""))
    except ValueError:
        return None


def _numeric(val) -> float | None:
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str) and val not in ("無資料", "無分紅", ""):
        try:
            return float(val.replace(",", ""))
        except ValueError:
            return None
    return None


_STATUS_LEVEL = {"偏低": "low", "合理": "ok", "偏高": "warn", "過高": "bad"}


def _build_valuation_display(metrics: dict) -> tuple[str, list[dict]]:
    """解析估值摘要與 PE/PB 指標，供前端儀表板顯示"""
    reason = metrics.get("價位說明", "") or ""
    prefix = reason.split("（", 1)[0] if "（" in reason else reason
    indicators: list[dict] = []

    raw_pe = metrics.get("本益比 (PE)")
    if raw_pe not in (None, "", "0（無獲利）"):
        if (pe := valid_ratio(raw_pe)) is not None:
            _, note, _ = pe_detail_note(pe)
            status = note.replace(f"PE {pe:g} ", "")
            indicators.append({
                "名稱": "本益比 PE",
                "數值": f"{pe:g}",
                "狀態": status,
                "level": _STATUS_LEVEL.get(status, "neutral"),
            })

    if (pb := valid_ratio(metrics.get("股價淨值比 (PB)"))) is not None:
        _, note, _ = pb_detail_note(pb)
        status = note.replace(f"PB {pb:g} ", "")
        indicators.append({
            "名稱": "股價淨值比 PB",
            "數值": f"{pb:g}",
            "狀態": status,
            "level": _STATUS_LEVEL.get(status, "neutral"),
        })

    return prefix, indicators


def _format_stock_price(val) -> str:
    """格式化查詢當下股價"""
    if val in (None, "", "無資料"):
        return ""
    try:
        price = float(val)
    except (TypeError, ValueError):
        return str(val)
    if abs(price - round(price)) < 1e-6:
        return f"{int(round(price)):,}"
    text = f"{price:,.2f}"
    return text.rstrip("0").rstrip(".")


def _score_fundamental(fundamental: dict) -> tuple[int, list[tuple[str, str, str]]]:
    """回傳 (分數, [(面向, 評語, 加減)])"""
    if "錯誤" in fundamental:
        return 0, [("基本面", fundamental["錯誤"], "—")]

    metrics = fundamental.get("metrics", {})
    revenue = fundamental.get("revenue_history") or []
    eps_hist = fundamental.get("eps_history") or []
    score = 0
    notes: list[tuple[str, str, str]] = []

    price_label = metrics.get("價位評估")
    price_reason = metrics.get("價位說明", "")
    if price_label and price_label != "無法判定":
        notes.append(("價位評估", f"{price_label}（綜合 PE / PB）｜{price_reason}", "—"))

    raw_pe = metrics.get("本益比 (PE)")
    if raw_pe == "0（無獲利）":
        notes.append(("本益比", pe_invalid_reason(0) or "PE 無效", "0"))
    elif (pe := valid_ratio(raw_pe)) is not None:
        pe_score, pe_note, pe_delta = pe_detail_note(pe)
        score += pe_score
        notes.append(("本益比", pe_note, pe_delta))
    else:
        notes.append(("本益比", pe_invalid_reason(raw_pe) or "無 PE 資料", "0"))

    pb = valid_ratio(metrics.get("股價淨值比 (PB)"))
    if pb is not None:
        pb_score, pb_note, pb_delta = pb_detail_note(pb)
        score += pb_score
        notes.append(("股價淨值比", pb_note, pb_delta))

    rev_yoy = _parse_pct(revenue[0]["年增率(%)"]) if revenue else None
    if rev_yoy is not None:
        if rev_yoy >= 20:
            score += 2
            notes.append(("月營收年增", f"最新月營收年增 {rev_yoy:+.1f}%", "+2"))
        elif rev_yoy >= 5:
            score += 1
            notes.append(("月營收年增", f"最新月營收年增 {rev_yoy:+.1f}%", "+1"))
        elif rev_yoy >= 0:
            notes.append(("月營收年增", f"最新月營收年增 {rev_yoy:+.1f}%", "0"))
        else:
            score -= 2
            notes.append(("月營收年增", f"最新月營收年增 {rev_yoy:+.1f}%", "-2"))

    eps_yoy = _parse_pct(eps_hist[0]["年增率(%)"]) if eps_hist else None
    if eps_yoy is not None:
        if eps_yoy >= 20:
            score += 2
            notes.append(("EPS 年增", f"最近一季 EPS 年增 {eps_yoy:+.1f}%", "+2"))
        elif eps_yoy >= 5:
            score += 1
            notes.append(("EPS 年增", f"最近一季 EPS 年增 {eps_yoy:+.1f}%", "+1"))
        elif eps_yoy >= 0:
            notes.append(("EPS 年增", f"最近一季 EPS 年增 {eps_yoy:+.1f}%", "0"))
        else:
            score -= 2
            notes.append(("EPS 年增", f"最近一季 EPS 年增 {eps_yoy:+.1f}%", "-2"))

    div = _numeric(metrics.get("股利殖利率 (%)"))
    if div is not None and div >= 3:
        score += 1
        notes.append(("殖利率", f"殖利率 {div}%，具息票保護", "+1"))

    return score, notes


def _score_technical(technical: dict) -> tuple[int, list[tuple[str, str, str]]]:
    if "error" in technical:
        return 0, [("技術面", technical["error"], "—")]

    full_data = technical.get("full_data")
    if full_data is None or (isinstance(full_data, pd.DataFrame) and full_data.empty):
        return 0, [("技術面", "無 K 線資料", "0")]

    row = full_data.iloc[-1]
    price = row["Close"]
    ma20 = row.get("MA20")
    ma60 = row.get("MA60")
    k_val = row.get("K")
    d_val = row.get("D")
    dif = row.get("DIF")
    dea = row.get("DEA")

    score = 0
    notes: list[tuple[str, str, str]] = []

    if pd.notna(ma20) and pd.notna(ma60):
        if price > ma20 > ma60:
            score += 2
            notes.append(("均線結構", "股價 > 月線 > 季線，多頭排列", "+2"))
        elif price > ma20:
            score += 1
            notes.append(("均線結構", "股價在月線之上", "+1"))
        elif price < ma20:
            score -= 1
            notes.append(("均線結構", "股價在月線之下", "-1"))
        if price < ma60:
            score -= 1
            notes.append(("季線位置", "股價在季線之下，中期偏弱", "-1"))

    if pd.notna(k_val) and pd.notna(d_val):
        if k_val > 80 and d_val > 80:
            score -= 1
            notes.append(("KD 指標", f"K={k_val:.0f} D={d_val:.0f}，高檔鈍化", "-1"))
        elif k_val < 20 and d_val < 20:
            score += 1
            notes.append(("KD 指標", f"K={k_val:.0f} D={d_val:.0f}，低檔區", "+1"))
        elif k_val > d_val:
            score += 1
            notes.append(("KD 指標", f"K={k_val:.0f} > D={d_val:.0f}，短線偏強", "+1"))
        else:
            score -= 1
            notes.append(("KD 指標", f"K={k_val:.0f} < D={d_val:.0f}，短線偏弱", "-1"))

    if pd.notna(dif) and pd.notna(dea):
        if dif > dea:
            score += 1
            notes.append(("MACD", "DIF 在 DEA 之上，動能偏多", "+1"))
        else:
            score -= 1
            notes.append(("MACD", "DIF 在 DEA 之下，動能偏空", "-1"))

    return score, notes


def _score_candle_signals(technical: dict) -> tuple[int, list[tuple[str, str, str]], list[dict]]:
    """偵測關鍵 K 棒型態，回傳 (加減分, 評估細項, 關鍵K棒列表)"""
    full_data = technical.get("full_data")
    if full_data is None or (isinstance(full_data, pd.DataFrame) and full_data.empty):
        return 0, [], []

    if "error" in technical:
        return 0, [], []

    signals = detect_key_candle_signals(full_data, latest_only=True)
    if not signals:
        return 0, [("關鍵K棒", "最新交易日未出現典型 K 棒型態", "0")], []

    score = 0
    notes: list[tuple[str, str, str]] = []
    for sig in signals:
        delta = sig.get("分數", 0)
        score += delta
        delta_str = f"{delta:+d}" if delta else "0"
        notes.append((sig["名稱"], sig["說明"], delta_str))
    return score, notes, signals


def _score_support_resistance(technical: dict) -> tuple[int, list[tuple[str, str, str]]]:
    """依現價與支撐 / 壓力距離評分"""
    levels = technical.get("levels") or {}
    full_data = technical.get("full_data")
    if full_data is None or (isinstance(full_data, pd.DataFrame) and full_data.empty):
        return 0, [("支撐壓力", "無 K 線資料", "0")]

    price = float(full_data.iloc[-1]["Close"])
    supports = levels.get("supports") or []
    resistances = levels.get("resistances") or []
    score = 0
    notes: list[tuple[str, str, str]] = []

    if supports:
        support = float(supports[0])
        if price < support:
            score -= 1
            notes.append(("支撐壓力", f"現價 {price:.2f} 跌破支撐 {support:.2f}", "-1"))
        else:
            dist_pct = (price - support) / price * 100
            if dist_pct <= 2:
                score += 1
                notes.append(("支撐壓力", f"現價接近支撐 {support:.2f}（距 {dist_pct:.1f}%）", "+1"))
            else:
                notes.append(("支撐壓力", f"第一支撐 {support:.2f}，距現價 {dist_pct:.1f}%", "0"))

    if resistances:
        resistance = float(resistances[0])
        if price > resistance:
            score += 1
            notes.append(("支撐壓力", f"現價 {price:.2f} 站上壓力 {resistance:.2f}", "+1"))
        elif supports or resistances:
            dist_pct = (resistance - price) / price * 100
            if dist_pct <= 2:
                score -= 1
                notes.append(("支撐壓力", f"現價接近壓力 {resistance:.2f}（距 {dist_pct:.1f}%）", "-1"))
            else:
                notes.append(("支撐壓力", f"第一壓力 {resistance:.2f}，距現價 {dist_pct:.1f}%", "0"))

    if not notes:
        notes.append(("支撐壓力", "區間內無明顯支撐壓力", "0"))

    return score, notes


def _streak_days(text: str) -> int:
    if "連續" not in text:
        return 0
    try:
        return int(text.split("連續")[1].split("日")[0])
    except (IndexError, ValueError):
        return 0


def _score_chips(chips: dict) -> tuple[int, list[tuple[str, str, str]]]:
    summary = chips.get("summary") or {}
    records = chips.get("records") or []
    if records and "錯誤" in records[0]:
        return 0, [("籌碼面", records[0]["錯誤"], "—")]

    score = 0
    notes: list[tuple[str, str, str]] = []

    total_text = summary.get("三大法人合計", "")
    if "買超" in total_text:
        days = _streak_days(total_text)
        if days >= 3:
            score += 2
            notes.append(("三大法人", f"{total_text}，法人偏多", "+2"))
        else:
            score += 1
            notes.append(("三大法人", f"{total_text}，法人略偏多", "+1"))
    elif "賣超" in total_text:
        days = _streak_days(total_text)
        if days >= 3:
            score -= 2
            notes.append(("三大法人", f"{total_text}，法人偏空", "-2"))
        else:
            score -= 1
            notes.append(("三大法人", f"{total_text}，法人略偏空", "-1"))
    else:
        notes.append(("三大法人", total_text or "法人動向不明", "0"))

    foreign_text = summary.get("外資", "")
    if "買超" in foreign_text and _streak_days(foreign_text) >= 2:
        score += 1
        notes.append(("外資", f"{foreign_text}，外資加持", "+1"))
    elif "賣超" in foreign_text and _streak_days(foreign_text) >= 2:
        score -= 1
        notes.append(("外資", f"{foreign_text}，外資賣壓", "-1"))

    return score, notes


def _day_technical_score(row) -> int:
    """單日技術面得分（供歷史相似型態比對）"""
    price = row["Close"]
    ma20 = row.get("MA20")
    ma60 = row.get("MA60")
    k_val = row.get("K")
    d_val = row.get("D")
    dif = row.get("DIF")
    dea = row.get("DEA")

    score = 0
    if pd.notna(ma20) and pd.notna(ma60):
        if price > ma20 > ma60:
            score += 2
        elif price > ma20:
            score += 1
        elif price < ma20:
            score -= 1
        if price < ma60:
            score -= 1

    if pd.notna(k_val) and pd.notna(d_val):
        if k_val > 80 and d_val > 80:
            score -= 1
        elif k_val < 20 and d_val < 20:
            score += 1
        elif k_val > d_val:
            score += 1
        else:
            score -= 1

    if pd.notna(dif) and pd.notna(dea):
        if dif > dea:
            score += 1
        else:
            score -= 1

    return score


def _score_based_win_probability(total: int) -> float:
    """依綜合得分推估參考勝率（規則式，收斂於 30～70%）"""
    return max(30.0, min(70.0, 50.0 + total * 2.0))


def _estimate_entry_probability(total: int, tech_score: int, technical: dict) -> dict:
    """
    估算以現價入手的賺錢 / 賠錢參考機率。
    結合綜合得分與歷史相似技術型態之後續報酬統計（規則式參考，非保證）。
    """
    score_win = _score_based_win_probability(total)
    horizons = (
        (5, "短線約 1 週"),
        (20, "中線約 1 個月"),
        (60, "長線約 3 個月"),
    )
    interval_rows: list[dict] = []

    full_data = technical.get("full_data")
    has_history = (
        full_data is not None
        and isinstance(full_data, pd.DataFrame)
        and not full_data.empty
        and len(full_data) > 80
        and "error" not in technical
    )

    closes = full_data["Close"].values if has_history else None

    for days, label in horizons:
        hist_win: float | None = None
        avg_return: float | None = None
        sample = 0
        source = "綜合得分推估"

        if has_history and closes is not None:
            returns: list[float] = []
            last_i = len(full_data) - days - 1
            for i in range(60, last_i + 1):
                if abs(_day_technical_score(full_data.iloc[i]) - tech_score) > 4:
                    continue
                entry = closes[i]
                exit_price = closes[i + days]
                if entry <= 0:
                    continue
                returns.append((exit_price - entry) / entry)

            sample = len(returns)
            if sample >= 8:
                hist_win = sum(1 for r in returns if r > 0) / sample * 100
                avg_return = sum(returns) / sample * 100
                source = "歷史相似型態 + 綜合得分"

        if hist_win is not None:
            weight = min(0.65, sample / 40)
            win = weight * hist_win + (1 - weight) * score_win
        else:
            win = score_win

        win = round(max(30.0, min(70.0, win)), 1)
        loss = round(100.0 - win, 1)
        row = {
            "持有天數": days,
            "標籤": label,
            "賺錢機率": win,
            "賠錢機率": loss,
            "樣本數": sample,
            "資料來源": source,
        }
        if avg_return is not None:
            row["平均報酬率"] = round(avg_return, 2)
        interval_rows.append(row)

    composite_win = interval_rows[1]["賺錢機率"] if len(interval_rows) > 1 else round(score_win, 1)
    composite_loss = round(100.0 - composite_win, 1)

    return {
        "說明": (
            "依目前綜合得分與歷史相似技術型態之後續漲跌統計推估，"
            "僅供參考，不代表未來實際結果或保證獲利。"
        ),
        "綜合": {
            "賺錢機率": composite_win,
            "賠錢機率": composite_loss,
        },
        "區間": interval_rows,
    }


def _is_etf(fundamental: dict) -> bool:
    metrics = fundamental.get("metrics") or {}
    if metrics.get("商品類型") == "ETF":
        return True
    code = metrics.get("公司代號", "")
    return security_type_label(code) == "ETF" if code else False


def _weighted_scores(
    fund_score: int, tech_score: int, chip_score: int, is_etf: bool
) -> tuple[int, int, int, int]:
    """ETF 不計基本面，技術 / 籌碼權重提高"""
    if not is_etf:
        return fund_score, tech_score, chip_score, fund_score + tech_score + chip_score

    tech_weighted = round(tech_score * 1.5)
    chip_weighted = round(chip_score * 1.5)
    return 0, tech_weighted, chip_weighted, tech_weighted + chip_weighted


def score_verdict_legend() -> dict:
    """綜合得分區間說明（與 _verdict 門檻一致，供 UI 顯示）"""
    return {
        "股票": [
            {"區間": "≥ 8", "評等": "偏多（看多）", "tone": "bull"},
            {"區間": "4～7", "評等": "中性偏多", "tone": "mild_bull"},
            {"區間": "0～3", "評等": "中性（觀望）", "tone": "neutral"},
            {"區間": "-4～-1", "評等": "中性偏空", "tone": "mild_bear"},
            {"區間": "≤ -5", "評等": "偏空（看空）", "tone": "bear"},
        ],
        "ETF": [
            {"區間": "≥ 12", "評等": "偏多（看多）", "tone": "bull"},
            {"區間": "6～11", "評等": "中性偏多", "tone": "mild_bull"},
            {"區間": "0～5", "評等": "中性（觀望）", "tone": "neutral"},
            {"區間": "-6～-1", "評等": "中性偏空", "tone": "mild_bear"},
            {"區間": "≤ -7", "評等": "偏空（看空）", "tone": "bear"},
        ],
        "備註": "ETF 不計基本面；技術面與籌碼面權重 ×1.5。",
    }


def score_verdict_legend_for(product_type: str = "股票") -> dict:
    """依商品類型回傳對應的得分區間說明（供 UI 只顯示一種）"""
    full = score_verdict_legend()
    if product_type == "ETF":
        return {
            "類型": "ETF",
            "項目": full["ETF"],
            "備註": full["備註"],
        }
    return {
        "類型": "股票",
        "項目": full["股票"],
        "備註": "綜合得分 = 基本面 + 技術面 + 籌碼面。",
    }


def _verdict(total: int, *, is_etf: bool = False) -> tuple[str, str, str]:
    """回傳 (結論, 建議, 燈號顏色 key)"""
    if is_etf:
        if total >= 12:
            return (
                "偏多",
                "ETF 技術與籌碼偏多，可列入觀察，但仍需留意大盤與追蹤誤差。",
                "bull",
            )
        if total >= 6:
            return "中性偏多", "整體不差，可小量布局或等待拉回。", "mild_bull"
        if total >= 0:
            return "中性", "多空因素交雜，建議觀望。", "neutral"
        if total >= -6:
            return "中性偏空", "短中期偏弱，不建議積極追高。", "mild_bear"
        return "偏空", "技術與籌碼偏空，暫不建議積極入手。", "bear"

    if total >= 8:
        return "偏多", "多項指標同步偏多，可列入入手觀察，但仍需留意個股風險與大盤。", "bull"
    if total >= 4:
        return "中性偏多", "整體不差，可小量試單或等待拉回再評估。", "mild_bull"
    if total >= 0:
        return "中性", "多空因素交雜，建議觀望，等待更明確訊號。", "neutral"
    if total >= -4:
        return "中性偏空", "短中期偏弱，不建議積極追高，可等籌碼或技術面改善。", "mild_bear"
    return "偏空", "多項指標偏空，暫不建議入手，若持有宜控管風險。", "bear"


def _fmt_range(low: float, high: float) -> str:
    low = round(float(low), 2)
    high = round(float(high), 2)
    if abs(low - high) < 1e-9:
        return f"{low:.2f}"
    return f"{low:.2f}～{high:.2f}"


def _suggest_buy_range(fundamental: dict, technical: dict) -> tuple[str, str]:
    """
    回傳 (買入區間文字, 說明)
    規則：以「第一支撐」附近作為偏保守的分批布局區間；若缺資料則回傳 "—"。
    """
    metrics = fundamental.get("metrics") or {}
    price = _numeric(metrics.get("目前股價"))
    if price is None:
        full = technical.get("full_data")
        if isinstance(full, pd.DataFrame) and not full.empty and "Close" in full.columns:
            try:
                price = float(full["Close"].iloc[-1])
            except Exception:
                price = None
    if price is None or price <= 0:
        return "—", "查無現價，無法估算買入區間"

    levels = technical.get("levels") or {}
    supports = levels.get("supports") or []
    support1 = supports[0] if supports else None
    if isinstance(support1, (int, float)) and support1 > 0:
        low = float(support1)
        high = min(price, low * 1.02)
        if high < low:
            high = low
        return _fmt_range(low, high), "以第一支撐附近分批布局（約 0%～+2%）"

    # 沒有支撐價時，以現價下方保守區間呈現（避免鼓勵追價）
    low = price * 0.97
    high = price * 0.99
    return _fmt_range(low, high), "支撐價不足，改以現價下方 1%～3% 作為保守參考區間"


def build_investment_advice(
    fundamental: dict,
    technical: dict,
    chips: dict,
) -> dict:
    """綜合基本面、技術面、籌碼面產生入手參考評估"""
    is_etf = _is_etf(fundamental)
    fund_score, fund_notes = _score_fundamental(fundamental)
    tech_score, tech_notes = _score_technical(technical)
    candle_score, candle_notes, candle_signals = _score_candle_signals(technical)
    tech_score += candle_score
    tech_notes.extend(candle_notes)
    sr_score, sr_notes = _score_support_resistance(technical)
    tech_score += sr_score
    tech_notes.extend(sr_notes)
    chip_score, chip_notes = _score_chips(chips)

    fund_display, tech_display, chip_display, total = _weighted_scores(
        fund_score, tech_score, chip_score, is_etf
    )
    verdict, suggestion, tone = _verdict(total, is_etf=is_etf)

    metrics = fundamental.get("metrics") or {}
    company = metrics.get("公司名稱", "")
    english = metrics.get("英文名稱", "")
    code = metrics.get("公司代號", "")
    display = metrics.get("顯示名稱") or company
    subline = metrics.get("副標名稱", "")
    if not subline and english and english != company:
        subline = english

    if is_etf:
        dimension_rows = [
            ("基本面", "—", "ETF 為多檔持股集合，不納入評分"),
            ("技術面", tech_display, "均線 / KD / MACD / 關鍵K棒 / 支撐壓力（權重 ×1.5）"),
            ("籌碼面", chip_display, "三大法人動向（權重 ×1.5）"),
        ]
        score_note = "ETF 評分：技術面 + 籌碼面（不含基本面，權重 ×1.5）"
        detail_rows = [
            ("評分方式", score_note, "—"),
            *tech_notes,
            *chip_notes,
        ]
    else:
        dimension_rows = [
            ("基本面", fund_display, "獲利與估值"),
            ("技術面", tech_display, "均線 / KD / MACD / 關鍵K棒 / 支撐壓力"),
            ("籌碼面", chip_display, "三大法人動向"),
        ]
        score_note = "綜合得分 = 基本面 + 技術面 + 籌碼面"
        detail_rows = fund_notes + tech_notes + chip_notes

    price_raw = metrics.get("目前股價")
    price_text = _format_stock_price(price_raw)
    val_summary, val_indicators = _build_valuation_display(metrics)
    entry_probability = _estimate_entry_probability(total, tech_score, technical)
    buy_range, buy_range_note = _suggest_buy_range(fundamental, technical)

    return {
        "公司名稱": company,
        "英文名稱": english,
        "公司代號": code,
        "顯示名稱": display,
        "副標名稱": subline,
        "商品類型": metrics.get("商品類型", "股票"),
        "目前股價": price_raw if price_raw not in (None, "") else "",
        "目前股價顯示": f"{price_text} 元" if price_text else "",
        "價位評估": metrics.get("價位評估", ""),
        "價位說明": metrics.get("價位說明", ""),
        "價位tone": metrics.get("價位tone", "neutral"),
        "估值摘要": val_summary,
        "估值指標": val_indicators,
        "綜合得分": total,
        "評等": verdict,
        "入手參考": suggestion,
        "建議買入區間": buy_range,
        "買入區間說明": buy_range_note,
        "tone": tone,
        "評分說明": score_note,
        "dimensions": dimension_rows,
        "details": detail_rows,
        "關鍵K棒": candle_signals,
        "入手機率": entry_probability,
        "得分區間說明": score_verdict_legend_for(metrics.get("商品類型", "股票")),
        "免責聲明": (
            "以上數值依公開資料參考而來，不構成投資建議，請自行判斷並自負盈虧。"
            "賺賠機率為統計推估，並非對個別交易結果之保證或預測。"
        ),
    }
