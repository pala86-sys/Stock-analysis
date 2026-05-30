"""股價價位評估：依本益比、股價淨值比判斷便宜 / 合理 / 昂貴"""


def valid_ratio(val) -> float | None:
    """有效比率須為正數（0 或負值視為無效）"""
    if isinstance(val, (int, float)):
        v = float(val)
        return v if v > 0 else None
    if isinstance(val, str) and val not in ("無資料", "—", ""):
        try:
            v = float(str(val).replace(",", ""))
            return v if v > 0 else None
        except ValueError:
            return None
    return None


def pe_invalid_reason(raw_pe) -> str | None:
    """PE 無效時的回覆說明"""
    if raw_pe in (0, 0.0, "0", "0.0"):
        return "PE 0（尚無獲利），不納入價位評估"
    if isinstance(raw_pe, (int, float)) and raw_pe < 0:
        return "PE 為負（虧損），不納入價位評估"
    return None


def _score_pe(pe: float) -> int:
    if pe < 12:
        return -1
    if pe <= 22:
        return 0
    return 1


def _score_pb(pb: float) -> int:
    if pb < 1.2:
        return -1
    if pb <= 2.5:
        return 0
    return 1


def pe_detail_note(pe: float) -> tuple[int, str, str]:
    """本益比細項：(加減分, 評語, 加減文字)"""
    if pe < 12:
        return 2, f"PE {pe:g} 偏低", "+2"
    if pe <= 22:
        return 1, f"PE {pe:g} 合理", "+1"
    if pe <= 35:
        return 0, f"PE {pe:g} 偏高", "0"
    return -1, f"PE {pe:g} 過高", "-1"


def pb_detail_note(pb: float) -> tuple[int, str, str]:
    """股價淨值比細項：(加減分, 評語, 加減文字)"""
    if pb < 1.2:
        return 1, f"PB {pb:g} 偏低", "+1"
    if pb <= 2.5:
        return 0, f"PB {pb:g} 合理", "0"
    if pb <= 4:
        return -1, f"PB {pb:g} 偏高", "-1"
    return -1, f"PB {pb:g} 過高", "-1"


def _pe_comment(pe: float) -> str:
    if pe < 12:
        return f"PE {pe:g} 偏低"
    if pe <= 22:
        return f"PE {pe:g} 合理"
    if pe <= 35:
        return f"PE {pe:g} 偏高"
    return f"PE {pe:g} 過高"


def _pb_comment(pb: float) -> str:
    if pb < 1.2:
        return f"PB {pb:g} 偏低"
    if pb <= 2.5:
        return f"PB {pb:g} 合理"
    if pb <= 4:
        return f"PB {pb:g} 偏高"
    return f"PB {pb:g} 過高"


def assess_price_level(pe, pb, raw_pe=None) -> dict:
    """
    綜合 PE / PB 評估目前價位（價位評估為唯一結論，PE/PB 無效時自動略過）。
    回傳：價位評估、價位說明、tone（cheap / fair / expensive / neutral）
    """
    pe_val = valid_ratio(pe if raw_pe is None else raw_pe)
    pb_val = valid_ratio(pb)
    pe_invalid = pe_invalid_reason(raw_pe if raw_pe is not None else pe)

    parts: list[str] = []
    scores: list[int] = []

    if pe_val is not None:
        scores.append(_score_pe(pe_val))
        parts.append(_pe_comment(pe_val))
    elif pe_invalid:
        parts.append(pe_invalid)

    if pb_val is not None:
        scores.append(_score_pb(pb_val))
        parts.append(_pb_comment(pb_val))

    if not scores:
        hint = pe_invalid or "缺少有效的本益比與股價淨值比"
        return {
            "價位評估": "無法判定",
            "價位說明": f"{hint}，無法評估價位",
            "tone": "neutral",
        }

    avg = sum(scores) / len(scores)
    reason = "、".join(parts)

    if avg <= -0.5:
        label, prefix, tone = "便宜", "估值偏低", "cheap"
    elif avg >= 0.5:
        label, prefix, tone = "昂貴", "估值偏高", "expensive"
    else:
        label, prefix, tone = "合理", "估值合理", "fair"

    return {
        "價位評估": label,
        "價位說明": f"{prefix}（{reason}）",
        "tone": tone,
    }
