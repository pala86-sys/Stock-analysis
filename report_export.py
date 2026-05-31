"""分析報告匯出（PDF，reportlab TrueType 嵌入，WPS / Edge 相容）"""

from __future__ import annotations

import base64
import shutil
import sys
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from settings import resource_path

NOTO_FONT_REL = "assets/fonts/NotoSansTC-Regular.ttf"
FONT_NORMAL = "NotoTC"
FONT_BOLD = "NotoTC-Bold"
_resolved_font_path: Path | None = None
_styles: dict[str, ParagraphStyle] | None = None


def _text(value) -> str:
    return str(value) if value is not None else ""


def _noto_font_path() -> Path:
    """取得 Noto TTF 路徑（打包後複製到 temp 以避免 _MEIPASS 路徑問題）"""
    global _resolved_font_path
    if _resolved_font_path and _resolved_font_path.exists():
        return _resolved_font_path

    src = resource_path(NOTO_FONT_REL)
    if not src.exists():
        raise FileNotFoundError(
            f"找不到 PDF 用 TTF 字型：{src}。"
            "請執行 python scripts/ensure_fonts.py 下載 NotoSansTC-Regular.ttf"
        )

    if getattr(sys, "frozen", False):
        dest = Path(tempfile.gettempdir()) / "StockObserver_NotoSansTC-Regular.ttf"
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            shutil.copyfile(src, dest)
        _resolved_font_path = dest
    else:
        _resolved_font_path = src
    return _resolved_font_path


def _register_fonts() -> None:
    font_path = str(_noto_font_path())
    if FONT_NORMAL not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(FONT_NORMAL, font_path))
        pdfmetrics.registerFont(TTFont(FONT_BOLD, font_path))
        pdfmetrics.registerFontFamily(FONT_NORMAL, normal=FONT_NORMAL, bold=FONT_BOLD)


def _get_styles() -> dict[str, ParagraphStyle]:
    global _styles
    if _styles is not None:
        return _styles

    _register_fonts()
    _styles = {
        "title": ParagraphStyle(
            "title",
            fontName=FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#b71c1c"),
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "meta",
            fontName=FONT_NORMAL,
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "h2",
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#b71c1c"),
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName=FONT_BOLD,
            fontSize=11,
            leading=14,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName=FONT_NORMAL,
            fontSize=10,
            leading=14,
            spaceAfter=4,
        ),
        "muted": ParagraphStyle(
            "muted",
            fontName=FONT_NORMAL,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#888888"),
        ),
        "error": ParagraphStyle(
            "error",
            fontName=FONT_NORMAL,
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#c62828"),
        ),
        "disclaimer": ParagraphStyle(
            "disclaimer",
            fontName=FONT_NORMAL,
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#888888"),
            spaceBefore=6,
        ),
        "tablecell": ParagraphStyle(
            "tablecell",
            fontName=FONT_NORMAL,
            fontSize=8,
            leading=11,
            wordWrap="CJK",
        ),
    }
    return _styles


def _cell_para(text: str) -> Paragraph:
    styles = _get_styles()
    return Paragraph(escape(_text(text)), styles["tablecell"])


def _para(text: str, style_key: str = "body") -> Paragraph:
    styles = _get_styles()
    return Paragraph(escape(_text(text)), styles[style_key])


def _table(
    headers: list[str],
    rows: list[list],
    *,
    col_widths: list[float] | None = None,
    wrap_cols: set[int] | None = None,
) -> Table | Paragraph:
    if not rows:
        return _para("無資料", "muted")

    wrap_cols = wrap_cols or set()
    data = [headers] + [[_text(c) for c in row] for row in rows]
    for row_idx in range(1, len(data)):
        for col_idx in wrap_cols:
            if col_idx < len(data[row_idx]):
                data[row_idx][col_idx] = _cell_para(data[row_idx][col_idx])

    usable = 170 * mm
    if col_widths is None:
        col_count = len(headers)
        col_widths = [usable / col_count] * col_count if col_count else [usable]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), FONT_NORMAL, 9),
                ("FONT", (0, 0), (-1, 0), FONT_BOLD, 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f3f3")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#333333")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _section(title: str, flowables: list) -> list:
    styles = _get_styles()
    return [Paragraph(escape(title), styles["h2"]), *flowables, Spacer(1, 6)]


def _advice_block(advice: dict) -> list:
    flow: list = []
    display = advice.get("顯示名稱") or advice.get("公司名稱", "")
    if display:
        flow.append(_para(display, "body"))
    subline = advice.get("副標名稱", "")
    if subline:
        flow.append(_para(subline, "body"))
    price_display = advice.get("目前股價顯示", "")
    if price_display:
        flow.append(_para(f"目前股價：{price_display}", "body"))
    price_label = advice.get("價位評估", "")
    price_reason = advice.get("價位說明", "")
    if price_label and price_label != "無法判定":
        flow.append(_para(f"目前價位：{price_label} ｜ {price_reason}", "body"))

    flow.extend(
        [
            _para(f"入手參考：{advice.get('評等', '')}", "body"),
            _para(f"綜合得分 {advice.get('綜合得分', '')}", "body"),
            _para(advice.get("評分說明", ""), "body"),
            _para(advice.get("入手參考", ""), "body"),
        ]
    )
    prob = advice.get("入手機率") or {}
    overall = prob.get("綜合") or {}
    intervals = prob.get("區間") or []
    if overall:
        flow.append(_para("以現價入手 · 賺賠參考機率", "h3"))
        flow.append(
            _para(
                f"綜合參考：賺錢 {overall.get('賺錢機率', '—')}% ／ "
                f"賠錢 {overall.get('賠錢機率', '—')}%",
                "body",
            )
        )
        prob_rows = []
        for row in intervals:
            avg = row.get("平均報酬率")
            avg_text = f"{avg:+.2f}%" if avg is not None else "—"
            prob_rows.append([
                row.get("標籤", ""),
                f"{row.get('賺錢機率', '—')}%",
                f"{row.get('賠錢機率', '—')}%",
                avg_text,
                row.get("樣本數", "—"),
            ])
        flow.append(
            _table(
                ["持有區間", "賺錢機率", "賠錢機率", "平均報酬", "樣本數"],
                prob_rows,
            )
        )
        if prob.get("說明"):
            flow.append(_para(prob["說明"], "body"))
    candles = advice.get("關鍵K棒") or []
    if candles:
        flow.append(_para("關鍵 K 棒訊號", "h3"))
        flow.append(
            _table(
                ["型態", "日期", "說明"],
                [[c.get("名稱", ""), c.get("日期", ""), c.get("說明", "")] for c in candles],
            )
        )
    flow.extend(
        [
            _para("各面向得分", "h3"),
            _table(
                ["面向", "得分", "說明"],
                [[name, score, desc] for name, score, desc in advice.get("dimensions", [])],
            ),
            _para("評估細項", "h3"),
            _table(
                ["項目", "評語", "加減"],
                [[item, comment, delta] for item, comment, delta in advice.get("details", [])],
            ),
            _para(advice.get("免責聲明", ""), "disclaimer"),
        ]
    )
    return flow


def _profile_block(profile: dict) -> list:
    if "錯誤" in profile:
        return [_para(profile["錯誤"], "error")]

    rows = [
        ["公司名稱", profile.get("公司名稱", "")],
        ["公司代號", profile.get("公司代號", "")],
        ["產業分類", profile.get("產業分類", "")],
        ["交易市場", profile.get("交易市場", "")],
        ["員工人數", profile.get("員工人數", "")],
        ["總部", profile.get("總部", "")],
        ["官網", profile.get("官網", "")],
        ["投資題材", profile.get("投資題材", "")],
    ]
    flow: list = [_table(["項目", "內容"], rows)]

    chinese = profile.get("中文概況", "")
    english = profile.get("原文摘要", "")
    company = profile.get("公司名稱", "")
    if chinese:
        prefix = f"{company} " if company else ""
        flow.extend([_para("中文概況", "h3"), _para(prefix + chinese, "body")])
    if english:
        flow.extend([_para("原文摘要", "h3"), _para(english, "body")])
    if not chinese and not english:
        intro = profile.get("公司簡介", "")
        if intro:
            flow.extend([_para("公司簡介", "h3"), _para(intro, "body")])
    return flow


def _fundamental_block(fundamental: dict) -> list:
    if "錯誤" in fundamental:
        return [_para(fundamental["錯誤"], "error")]

    metrics = fundamental.get("metrics") or {}
    header_rows = [
        ["公司名稱", metrics.get("公司名稱", "")],
        ["公司代號", metrics.get("公司代號", "")],
        ["英文名稱", metrics.get("英文名稱", "")],
        ["目前股價", metrics.get("目前股價", "")],
        ["價位評估", metrics.get("價位評估", "")],
    ]
    valuation_keys = ("市值 (億)", "本益比 (PE)", "股價淨值比 (PB)", "每股盈餘 (EPS)", "股利殖利率 (%)")
    valuation_rows = [[k, metrics.get(k, "")] for k in valuation_keys if k in metrics]
    if metrics.get("價位說明"):
        valuation_rows.insert(0, ["價位說明", metrics["價位說明"]])
    revenue_rows = [
        [r.get("期間", ""), r.get("營收(億)", ""), r.get("月增率(%)", ""), r.get("年增率(%)", "")]
        for r in fundamental.get("revenue_history") or []
    ]
    eps_rows = [
        [r.get("期間", ""), r.get("EPS(元)", ""), r.get("季增率(%)", ""), r.get("年增率(%)", "")]
        for r in fundamental.get("eps_history") or []
    ]

    return [
        _para("基本資料", "h3"),
        _table(["指標", "數值"], header_rows),
        _para("估值指標", "h3"),
        _table(["指標", "數值"], valuation_rows),
        _para("每月營收", "h3"),
        _table(["期間", "營收(億)", "月增率(%)", "年增率(%)"], revenue_rows),
        _para("季 EPS", "h3"),
        _table(["期間", "EPS(元)", "季增率(%)", "年增率(%)"], eps_rows),
    ]


def _technical_block(technical: dict) -> list:
    if "error" in technical:
        return [_para(technical["error"], "error")]

    summary = technical.get("summary") or {}
    levels = technical.get("levels") or {}
    rows = [[k, v] for k, v in summary.items()]

    sr_rows = []
    for i, price in enumerate(levels.get("supports") or [], 1):
        sr_rows.append([f"支撐 {i}", f"{price:.2f}"])
    for i, price in enumerate(levels.get("resistances") or [], 1):
        sr_rows.append([f"壓力 {i}", f"{price:.2f}"])
    if levels.get("period_high") is not None:
        sr_rows.append(["區間最高", f"{levels['period_high']:.2f}"])
        sr_rows.append(["區間最低", f"{levels['period_low']:.2f}"])

    flow = [_table(["指標", "數值"], rows), _para("支撐 / 壓力", "h3")]
    if sr_rows:
        flow.append(_table(["價位", "數值"], sr_rows))
    else:
        flow.append(_para("無支撐壓力資料", "muted"))
    return flow


def _chips_block(chips: dict) -> list:
    records = chips.get("records") or []
    summary = chips.get("summary") or {}
    if not records:
        return [_para("查無籌碼資料", "muted")]
    if "錯誤" in records[0]:
        return [_para(records[0]["錯誤"], "error")]

    summary_rows = [[k, v] for k, v in summary.items()]
    daily_rows = [
        [
            r.get("日期", ""),
            r.get("外資買賣超(張)", ""),
            r.get("投信買賣超(張)", ""),
            r.get("自營商買賣超(張)", ""),
            r.get("三大法人合計(張)", ""),
        ]
        for r in records
    ]
    return [
        _para("法人摘要", "h3"),
        _table(["法人", "近日連續買賣超"], summary_rows),
        _para("每日明細", "h3"),
        _table(["日期", "外資(張)", "投信(張)", "自營商(張)", "法人合計(張)"], daily_rows),
    ]


def _news_block(news: list) -> list:
    if not news:
        return [_para("查無新聞", "muted")]
    rows = [
        [
            i,
            n.get("標題", ""),
            n.get("來源", ""),
            n.get("發布時間", ""),
            n.get("連結", ""),
        ]
        for i, n in enumerate(news, 1)
    ]
    usable = 170 * mm
    return [
        _table(
            ["#", "標題", "來源", "發布時間", "連結"],
            rows,
            col_widths=[10 * mm, 52 * mm, 28 * mm, 30 * mm, usable - 120 * mm],
            wrap_cols={1, 2, 4},
        )
    ]


def report_download_filename(stock_id: str, advice: dict) -> str:
    """下載檔名：股票代碼 + 股票名稱 + 報告.pdf"""
    sid = _text(stock_id).strip()
    name = _text(advice.get("公司名稱")).strip()
    if not name:
        display = _text(advice.get("顯示名稱")).strip()
        for token in (f"（{sid}）", f"({sid})", sid):
            display = display.replace(token, "")
        name = display.strip(" 　（）()")
    if not name:
        name = sid
    for ch in '\\/:*?"<>|\n\r\t':
        sid = sid.replace(ch, "")
        name = name.replace(ch, "")
    return f"{sid}{name}報告.pdf"


def _chart_block(chart_png_bytes: bytes) -> list:
    img = Image(BytesIO(chart_png_bytes))
    max_w = 170 * mm
    scale = min(1.0, max_w / float(img.drawWidth))
    img.drawWidth *= scale
    img.drawHeight *= scale
    return [img, Spacer(1, 6)]


def _build_report_flowables(
    stock_id: str,
    advice: dict,
    sections: dict,
    *,
    chart_png_bytes: bytes | None = None,
    data_errors: list[str] | None = None,
) -> list:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    company = advice.get("顯示名稱") or advice.get("公司名稱") or stock_id
    sid = str(stock_id).strip()
    title = company if sid and sid in str(company) else f"{company}（{sid}）"

    styles = _get_styles()
    story: list = [
        Paragraph(escape(title), styles["title"]),
        Paragraph(
            escape(f"台股多維度全方位觀測儀 · 報告產生時間 {generated_at}"),
            styles["meta"],
        ),
    ]
    if data_errors:
        story.append(
            _para(f"部分資料未能載入：{'、'.join(data_errors)}", "error")
        )

    story.extend(_section("綜合評估", _advice_block(advice)))
    story.extend(_section("公司簡介", _profile_block(sections.get("profile") or {})))
    story.extend(_section("基本面", _fundamental_block(sections.get("fundamental") or {})))
    story.extend(_section("技術面", _technical_block(sections.get("technical") or {})))
    if chart_png_bytes:
        story.extend(_section("K 線圖", _chart_block(chart_png_bytes)))
    story.extend(_section("籌碼面", _chips_block(sections.get("chips") or {})))
    story.extend(_section("消息面", _news_block(sections.get("news") or [])))
    return story


def build_pdf_report(
    stock_id: str,
    advice: dict,
    sections: dict,
    *,
    chart_png_bytes: bytes | None = None,
    data_errors: list[str] | None = None,
) -> bytes:
    """由分析結果產生 PDF 報告"""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
        title=f"{stock_id} 台股分析報告",
    )
    doc.build(
        _build_report_flowables(
            stock_id,
            advice,
            sections,
            chart_png_bytes=chart_png_bytes,
            data_errors=data_errors,
        )
    )
    return buf.getvalue()


def export_pdf_report(
    path: Path,
    stock_id: str,
    advice: dict,
    sections: dict,
    *,
    chart_png_bytes: bytes | None = None,
    data_errors: list[str] | None = None,
) -> Path:
    """寫入 PDF 報告檔"""
    path = Path(path)
    path.write_bytes(
        build_pdf_report(
            stock_id,
            advice,
            sections,
            chart_png_bytes=chart_png_bytes,
            data_errors=data_errors,
        )
    )
    return path
