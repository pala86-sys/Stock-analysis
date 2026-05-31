"""產業模板、題材關鍵字與公司簡介生成"""

INDUSTRY_PROFILES = {
    "半導體業": {
        "themes": ["半導體", "AI/HPC", "晶圓代工", "先進製程"],
        "intro": "從事積體電路之製造、封裝或測試，位於科技產業鏈核心，受惠 AI、高效能運算、5G 與物聯網等應用帶動的晶片需求。",
        "design_intro": "從事積體電路設計與銷售，屬無晶圓廠模式，產品應用涵蓋手機、通訊、運算、車用及 AIoT 等領域。",
        "design_themes": ["半導體", "IC 設計", "AI/HPC", "5G/手機"],
    },
    "電子零組件業": {
        "themes": ["電子零組件", "PCB/載板", "被動元件", "AI 伺服器"],
        "intro": "提供電子產品所需關鍵零組件，客戶涵蓋消費電子、伺服器、車用與工業等應用，景氣與庫存循環對營運影響較大。",
    },
    "電腦及週邊設備業": {
        "themes": ["PC/伺服器", "AI 伺服器", "代工製造", "雲端硬體"],
        "intro": "從事電腦、伺服器及週邊設備之製造或銷售，與企業資本支出、雲端資料中心建置及 AI 算力需求高度相關。",
    },
    "光電業": {
        "themes": ["面板", "顯示器", "車用顯示", "LED"],
        "intro": "聚焦顯示面板、LED 或其他光電產品，下游應用包含電視、IT 顯示器、智慧手機與車用顯示等。",
    },
    "通信網路業": {
        "themes": ["5G", "網通", "資料中心", "AI 網路"],
        "intro": "提供通訊設備、網路基建或相關解決方案，受惠寬頻升級、5G 部署與資料中心擴建等趨勢。",
    },
    "電子通路業": {
        "themes": ["電子通路", "受惠 AI 換機", "消費電子"],
        "intro": "以電子零組件或資訊產品通路、分銷為主，營運與終端需求、庫存水位及產品週期密切相關。",
    },
    "資訊服務業": {
        "themes": ["軟體", "系統整合", "AI 應用", "數位轉型"],
        "intro": "提供軟體、資訊系統或數位服務，常受企業 IT 預算、政府標案及產業數位化需求驅動。",
    },
    "其他電子業": {
        "themes": ["電子製造", "利基應用", "工業電子"],
        "intro": "從事特殊或利基電子產品之研發製造，應用場景多元，需關注主要客戶與產品組合變化。",
    },
    "生技醫療業": {
        "themes": ["生技", "新藥", "醫材", "CDMO"],
        "intro": "聚焦藥品開發、醫療器材或生技服務，具研發周期長、法規審查嚴格等產業特性。",
    },
    "金融保險業": {
        "themes": ["金融", "升息循環", "股息", "金控"],
        "intro": "以銀行、保險、證券或金控業務為主，獲利與利差、信用品質、資本市場及政策環境高度相關。",
    },
    "航運業": {
        "themes": ["航運", "運價", "紅海/運力", "貨櫃輪"],
        "intro": "從事海運或物流服務，營運受全球貿易量、運價、油價及運力供需影響顯著。",
    },
    "水泥工業": {
        "themes": ["水泥", "基建", "ESG", "綠能轉型"],
        "intro": "以水泥生產及相關建材為主，與公共工程、營建景氣及碳排政策密切相關。",
    },
    "食品工業": {
        "themes": ["食品", "內需", "品牌", "原物料"],
        "intro": "從事食品製造或加工，具備一定防禦性，但原物料成本與品牌競爭仍是關鍵。",
    },
    "電機機械": {
        "themes": ["機械", "工具機", "智慧製造", "車用零組件"],
        "intro": "提供電機、機械或自動化設備，受惠製造業資本支出、車用電子化及智慧工廠需求。",
    },
    "建材營造": {
        "themes": ["營建", "房市", "公共工程", "都更"],
        "intro": "從事營建工程或建材相關業務，景氣與利率、房市政策及推案進度高度連動。",
    },
    "塑膠工業": {
        "themes": ["塑化", "原物料", "化工", "ESG"],
        "intro": "以石化、塑膠或化工產品為主，獲利受油價、產能利用率及下游需求影響。",
    },
    "紡織纖維": {
        "themes": ["紡織", "成衣", "品牌", "機能布料"],
        "intro": "從事纖維、紡紗或成衣相關業務，需關注品牌客戶訂單與全球消費需求。",
    },
    "汽車工業": {
        "themes": ["汽車", "電動車", "車用電子", "零組件"],
        "intro": "提供汽車整車或零組件，電動化、自駕與車用電子為中長期重要題材。",
    },
}

THEME_KEYWORDS = {
    "AI/HPC": ["artificial intelligence", "machine learning", " ai ", "hpc", "gpu", "datacenter", "data center", "cloud"],
    "電動車": ["electric vehicle", " ev ", "automotive", "vehicle"],
    "5G": ["5g", "wireless", "telecom"],
    "伺服器": ["server", "data center", "datacenter"],
    "晶圓代工": ["foundry", "wafer", "semiconductor manufacturing"],
    "記憶體": ["memory", "dram", "nand"],
    "IC 設計": ["fabless", "chip design", "integrated circuit design"],
    "生技/新藥": ["biotech", "pharmaceutical", "drug", "clinical"],
    "綠能": ["solar", "renewable", "green energy", "wind"],
}

GENERIC_INDUSTRIES = {"電子工業", "生技醫療業"}

SECTOR_ZH = {
    "Technology": "科技",
    "Healthcare": "醫療保健",
    "Financial Services": "金融",
    "Consumer Cyclical": "消費循環",
    "Consumer Defensive": "必需消費",
    "Industrials": "工業",
    "Basic Materials": "原物料",
    "Energy": "能源",
    "Utilities": "公用事業",
    "Real Estate": "房地產",
    "Communication Services": "通訊服務",
}


def parse_finmind_industry(data: list | None) -> str | None:
    """從 FinMind 產業分類資料解析最精確的產業名稱"""
    if not data:
        return None
    categories = [
        item["industry_category"]
        for item in data
        if item.get("industry_category")
        and "全部" not in item["industry_category"]
        and "不含" not in item["industry_category"]
    ]
    if not categories:
        return None
    specific = [c for c in categories if c not in GENERIC_INDUSTRIES]
    return specific[0] if specific else categories[0]


def is_ic_design(summary_lower: str) -> bool:
    """判斷半導體公司是否偏 IC 設計而非晶圓代工"""
    if any(k in summary_lower for k in ["foundry", "wafer fabrication", "fabrication facility"]):
        return False
    if "packages" in summary_lower and "tests" in summary_lower:
        return False
    if any(k in summary_lower for k in ["fabless", "without owning fabrication"]):
        return True
    if "integrated circuits" in summary_lower and "marketing" in summary_lower:
        return True
    return any(k in summary_lower for k in ["design, development", "designs and sells"])


def detect_themes(industry: str | None, summary: str) -> list[str]:
    """依產業與英文簡介關鍵字推估投資題材"""
    themes: list[str] = []
    summary_lower = f" {summary.lower()} "
    ic_design = industry == "半導體業" and is_ic_design(summary_lower)

    if industry and industry in INDUSTRY_PROFILES:
        profile = INDUSTRY_PROFILES[industry]
        if ic_design and "design_themes" in profile:
            themes.extend(profile["design_themes"])
        else:
            themes.extend(profile["themes"])

    for theme, keywords in THEME_KEYWORDS.items():
        if theme not in themes and any(k in summary_lower for k in keywords):
            themes.append(theme)

    if industry and industry not in themes and len(themes) < 4:
        themes.insert(0, industry)

    seen = set()
    unique_themes = []
    for theme in themes:
        if theme not in seen:
            seen.add(theme)
            unique_themes.append(theme)
    return unique_themes[:5]


def resolve_company_names(
    stock_code: str,
    stock_info: dict | None = None,
    info: dict | None = None,
) -> dict:
    """解析公司顯示名稱：中文名優先，附代號與英文名"""
    from stock_search import lookup_bundled_stock

    stock_info = stock_info or {}
    info = info or {}
    code = str(stock_code or "").strip()
    bundled = lookup_bundled_stock(code) or {}
    chinese = str(stock_info.get("stock_name") or bundled.get("stock_name") or "").strip()
    english = str(info.get("longName") or info.get("shortName") or "").strip()

    primary = chinese or english or code
    if chinese and code:
        display = f"{chinese}（{code}）"
    elif code and english:
        display = f"{code} {english}"
    else:
        display = primary

    subline = ""
    if english and chinese and english.casefold() != chinese.casefold():
        subline = english

    return {
        "公司名稱": primary,
        "中文名稱": chinese,
        "英文名稱": english,
        "公司代號": code,
        "顯示名稱": display,
        "副標名稱": subline,
    }


def build_chinese_overview(industry: str | None, info: dict, stock_info: dict | None = None) -> str:
    """產生中文產業概況（不含公司名稱前缀，名稱由 UI 標題顯示）"""
    summary = info.get("longBusinessSummary", "")
    summary_lower = f" {summary.lower()} "

    if industry and industry in INDUSTRY_PROFILES:
        profile = INDUSTRY_PROFILES[industry]
        if industry == "半導體業" and is_ic_design(summary_lower):
            return profile["design_intro"]
        return profile["intro"]

    sector = info.get("sector")
    sector_zh = SECTOR_ZH.get(sector, sector or "相關")
    intro = f"該公司隸屬 {sector_zh} 類股"
    if industry:
        intro += f"，產業分類為 {industry}"
    intro += "，主要從事其核心業務之研發、生產或銷售。"
    return intro


def format_business_summary(text: str, max_chars: int = 1200) -> str:
    """整理 Yahoo 英文業務摘要為易讀段落"""
    if not text or not text.strip():
        return ""

    cleaned = " ".join(text.split())
    if len(cleaned) <= max_chars:
        body = cleaned
    else:
        body = cleaned[:max_chars].rsplit(" ", 1)[0] + "…"

    sentences = []
    for part in body.replace("? ", "?\n").replace(". ", ".\n").split("\n"):
        part = part.strip()
        if part:
            sentences.append(part)

    if len(sentences) <= 2:
        return body

    paragraphs: list[str] = []
    chunk: list[str] = []
    for sentence in sentences:
        chunk.append(sentence)
        if len(chunk) >= 2:
            paragraphs.append(" ".join(chunk))
            chunk = []
    if chunk:
        paragraphs.append(" ".join(chunk))
    return "\n\n".join(paragraphs)


def format_employees(info: dict) -> str:
    count = info.get("fullTimeEmployees")
    if count is None:
        return ""
    try:
        return f"{int(count):,} 人"
    except (TypeError, ValueError):
        return str(count)


def format_headquarters(info: dict) -> str:
    city = info.get("city") or ""
    country = info.get("country") or ""
    parts = [p for p in (city, country) if p]
    return "，".join(parts)


def build_company_intro(
    industry: str | None,
    info: dict,
    stock_info: dict | None = None,
) -> str:
    """組合完整公司簡介文字（供匯出報告等向下相容）"""
    stock_info = stock_info or {}
    company_name = (
        stock_info.get("stock_name")
        or info.get("longName")
        or info.get("shortName")
        or ""
    )
    chinese = build_chinese_overview(industry, info, stock_info)
    english = format_business_summary(info.get("longBusinessSummary", ""))

    parts: list[str] = []
    if company_name and chinese:
        parts.append(f"【中文概況】\n{company_name} {chinese}")
    elif chinese:
        parts.append(f"【中文概況】\n{chinese}")
    if english:
        parts.append(f"【原文摘要】\n{english}")
    return "\n\n".join(parts) if parts else "無公開資料"
