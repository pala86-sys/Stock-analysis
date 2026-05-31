"""分析報告匯出（PDF）"""

import html
import tempfile
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

from settings import resource_path

NOTO_FONT = resource_path("assets/fonts/NotoSansTC-Regular.otf")


def _esc(text) -> str:
    return html.escape(str(text) if text is not None else "")


def _table(headers: list[str], rows: list[list]) -> str:
    if not rows:
        return '<p class="muted">無資料</p>'
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body = ""
    for row in rows:
        cells = "".join(f"<td>{_esc(c)}</td>" for c in row)
        body += f"<tr>{cells}</tr>"
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _section(title: str, content: str) -> str:
    return f'<section><h2>{_esc(title)}</h2>{content}</section>'


def _advice_block(advice: dict) -> str:
    tone = advice.get("tone", "neutral")
    tone_class = {
        "bull": "verdict-bull",
        "mild_bull": "verdict-mild-bull",
        "neutral": "verdict-neutral",
        "mild_bear": "verdict-mild-bear",
        "bear": "verdict-bear",
    }.get(tone, "verdict-neutral")

    dim_rows = [
        [name, score, desc]
        for name, score, desc in advice.get("dimensions", [])
    ]
    detail_rows = [
        [item, comment, delta]
        for item, comment, delta in advice.get("details", [])
    ]

    display = advice.get("顯示名稱") or advice.get("公司名稱", "")
    subline = advice.get("副標名稱", "")
    name_html = f"<p class=\"company\">{_esc(display)}</p>"
    if subline:
        name_html += f"<p class=\"company-sub\">{_esc(subline)}</p>"
    price_display = advice.get("目前股價顯示", "")
    if price_display:
        name_html += f"<p class=\"stock-price\">目前股價：{_esc(price_display)}</p>"
    price_label = advice.get("價位評估", "")
    price_reason = advice.get("價位說明", "")
    if price_label and price_label != "無法判定":
        name_html += f"<p class=\"price-level\">目前價位：{_esc(price_label)} ｜ {_esc(price_reason)}</p>"

    return f"""
    <div class="card {tone_class}">
      {name_html}
      <p class="verdict">入手參考：{_esc(advice.get("評等", ""))}</p>
      <p class="score">綜合得分 {_esc(advice.get("綜合得分", ""))}</p>
      <p class="suggestion">{_esc(advice.get("入手參考", ""))}</p>
    </div>
    <h3>各面向得分</h3>
    {_table(["面向", "得分", "說明"], dim_rows)}
    <h3>評估細項</h3>
    {_table(["項目", "評語", "加減"], detail_rows)}
    <p class="disclaimer">{_esc(advice.get("免責聲明", ""))}</p>
    """


def _profile_block(profile: dict) -> str:
    if "錯誤" in profile:
        return f'<p class="error">{_esc(profile["錯誤"])}</p>'

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
    parts = [_table(["項目", "內容"], rows)]

    chinese = profile.get("中文概況", "")
    english = profile.get("原文摘要", "")
    company = profile.get("公司名稱", "")
    if chinese:
        prefix = f"{company} " if company else ""
        parts.append(f"<h3>中文概況</h3><p class=\"intro\">{_esc(prefix + chinese)}</p>")
    if english:
        parts.append(f"<h3>原文摘要</h3><p class=\"intro\">{_esc(english)}</p>")
    if not chinese and not english:
        intro = profile.get("公司簡介", "")
        if intro:
            parts.append(f"<h3>公司簡介</h3><p class=\"intro\">{_esc(intro)}</p>")

    return "\n".join(parts)


def _fundamental_block(fundamental: dict) -> str:
    if "錯誤" in fundamental:
        return f'<p class="error">{_esc(fundamental["錯誤"])}</p>'

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

    parts = [
        "<h3>基本資料</h3>",
        _table(["指標", "數值"], header_rows),
        "<h3>估值指標</h3>",
        _table(["指標", "數值"], valuation_rows),
        "<h3>每月營收</h3>",
        _table(["期間", "營收(億)", "月增率(%)", "年增率(%)"], revenue_rows),
        "<h3>季 EPS</h3>",
        _table(["期間", "EPS(元)", "季增率(%)", "年增率(%)"], eps_rows),
    ]
    return "\n".join(parts)


def _technical_block(technical: dict) -> str:
    if "error" in technical:
        return f'<p class="error">{_esc(technical["error"])}</p>'

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

    parts = [
        _table(["指標", "數值"], rows),
        "<h3>支撐 / 壓力</h3>",
        _table(["價位", "數值"], sr_rows) if sr_rows else '<p class="muted">無支撐壓力資料</p>',
    ]
    return "\n".join(parts)


def _chips_block(chips: dict) -> str:
    records = chips.get("records") or []
    summary = chips.get("summary") or {}
    if not records:
        return '<p class="muted">查無籌碼資料</p>'
    if "錯誤" in records[0]:
        return f'<p class="error">{_esc(records[0]["錯誤"])}</p>'

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
    return (
        "<h3>法人摘要</h3>"
        + _table(["法人", "近日連續買賣超"], summary_rows)
        + "<h3>每日明細</h3>"
        + _table(["日期", "外資(張)", "投信(張)", "自營商(張)", "法人合計(張)"], daily_rows)
    )


def _news_block(news: list) -> str:
    if not news:
        return '<p class="muted">查無新聞</p>'
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
    return _table(["#", "標題", "來源", "發布時間", "連結"], rows)


def _build_report_body_html(
    stock_id: str,
    advice: dict,
    sections: dict,
    *,
    chart_img_html: str = "",
    data_errors: list[str] | None = None,
) -> str:
    """組裝報告 HTML 內容（供 PDF 轉換）"""
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    company = advice.get("顯示名稱") or advice.get("公司名稱") or stock_id

    warn_html = ""
    if data_errors:
        warn_html = f'<p><b>部分資料未能載入：</b>{_esc("、".join(data_errors))}</p>'

    body_sections = [
        _section("綜合評估", _advice_block(advice)),
        _section("公司簡介", _profile_block(sections.get("profile") or {})),
        _section("基本面", _fundamental_block(sections.get("fundamental") or {})),
        _section("技術面", _technical_block(sections.get("technical") or {})),
        _section("籌碼面", _chips_block(sections.get("chips") or {})),
        _section("消息面", _news_block(sections.get("news") or [])),
    ]
    if chart_img_html:
        body_sections.insert(4, _section("K 線圖", chart_img_html))

    return f"""
    <h1>{_esc(company)}（{_esc(stock_id)}）</h1>
    <p>台股多維度全方位觀測儀 · 報告產生時間 {generated_at}</p>
    {warn_html}
    {"".join(body_sections)}
    """


def _register_noto_font(pdf: FPDF) -> None:
    if not NOTO_FONT.exists():
        raise FileNotFoundError(f"找不到報告用字型：{NOTO_FONT}")
    font_path = str(NOTO_FONT)
    pdf.add_font("Noto", "", font_path)
    pdf.add_font("Noto", "B", font_path)


def build_pdf_report(
    stock_id: str,
    advice: dict,
    sections: dict,
    *,
    chart_png_bytes: bytes | None = None,
    data_errors: list[str] | None = None,
) -> bytes:
    """由分析結果產生 PDF 報告"""
    chart_file: Path | None = None
    try:
        chart_img_html = ""
        if chart_png_bytes:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(chart_png_bytes)
            tmp.close()
            chart_file = Path(tmp.name)
            chart_img_html = f'<img src="{chart_file.resolve().as_uri()}" width="700" alt="K 線圖">'

        html_body = _build_report_body_html(
            stock_id,
            advice,
            sections,
            chart_img_html=chart_img_html,
            data_errors=data_errors,
        )

        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=True, margin=15)
        _register_noto_font(pdf)
        pdf.set_font("Noto", "", 10)
        pdf.add_page()
        pdf.write_html(html_body)
        return bytes(pdf.output())
    finally:
        if chart_file:
            chart_file.unlink(missing_ok=True)


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
