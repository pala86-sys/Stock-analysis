"""輕量工具：避免啟動時載入 reportlab / 分析模組"""


def report_download_filename(stock_id: str, advice: dict) -> str:
    """下載檔名：股票代碼 + 股票名稱 + 報告.pdf"""
    sid = str(stock_id or "").strip()
    name = str(advice.get("公司名稱") or "").strip()
    if not name:
        display = str(advice.get("顯示名稱") or "").strip()
        for token in (f"（{sid}）", f"({sid})", sid):
            display = display.replace(token, "")
        name = display.strip(" 　（）()")
    if not name:
        name = sid
    for ch in '\\/:*?"<>|\n\r\t':
        sid = sid.replace(ch, "")
        name = name.replace(ch, "")
    return f"{sid}{name}報告.pdf"
