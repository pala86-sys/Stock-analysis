"""綜合評估：依基本面、技術面、籌碼面產生入手參考意見（規則式，非投資建議）"""

import pandas as pd

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


def _verdict(total: int) -> tuple[str, str, str]:
    """回傳 (結論, 建議, 燈號顏色 key)"""
    if total >= 8:
        return "偏多", "多項指標同步偏多，可列入入手觀察，但仍需留意個股風險與大盤。", "bull"
    if total >= 4:
        return "中性偏多", "整體不差，可小量試單或等待拉回再評估。", "mild_bull"
    if total >= 0:
        return "中性", "多空因素交雜，建議觀望，等待更明確訊號。", "neutral"
    if total >= -4:
        return "中性偏空", "短中期偏弱，不建議積極追高，可等籌碼或技術面改善。", "mild_bear"
    return "偏空", "多項指標偏空，暫不建議入手，若持有宜控管風險。", "bear"


def build_investment_advice(
    fundamental: dict,
    technical: dict,
    chips: dict,
) -> dict:
    """綜合基本面、技術面、籌碼面產生入手參考評估"""
    fund_score, fund_notes = _score_fundamental(fundamental)
    tech_score, tech_notes = _score_technical(technical)
    sr_score, sr_notes = _score_support_resistance(technical)
    tech_score += sr_score
    tech_notes.extend(sr_notes)
    chip_score, chip_notes = _score_chips(chips)

    total = fund_score + tech_score + chip_score
    verdict, suggestion, tone = _verdict(total)

    metrics = fundamental.get("metrics") or {}
    company = metrics.get("公司名稱", "")
    english = metrics.get("英文名稱", "")
    code = metrics.get("公司代號", "")
    display = metrics.get("顯示名稱") or company
    subline = metrics.get("副標名稱", "")
    if not subline and english and english != company:
        subline = english

    dimension_rows = [
        ("基本面", fund_score, "獲利與估值"),
        ("技術面", tech_score, "均線 / KD / MACD / 支撐壓力"),
        ("籌碼面", chip_score, "三大法人動向"),
    ]

    detail_rows = fund_notes + tech_notes + chip_notes

    return {
        "公司名稱": company,
        "英文名稱": english,
        "公司代號": code,
        "顯示名稱": display,
        "副標名稱": subline,
        "價位評估": metrics.get("價位評估", ""),
        "價位說明": metrics.get("價位說明", ""),
        "價位tone": metrics.get("價位tone", "neutral"),
        "綜合得分": total,
        "評等": verdict,
        "入手參考": suggestion,
        "tone": tone,
        "dimensions": dimension_rows,
        "details": detail_rows,
        "免責聲明": "以上為程式依公開資料自動產生之規則式參考，不構成投資建議，請自行判斷並自負盈虧。",
    }
