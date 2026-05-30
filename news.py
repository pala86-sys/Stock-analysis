"""新聞資料解析：FinMind 台股新聞 + Yahoo Finance 備援"""

from datetime import datetime


def parse_finmind_news(items: list | None, limit: int = 8) -> list:
    """解析 FinMind TaiwanStockNews（中文、含連結）"""
    if not items:
        return []

    sorted_items = sorted(items, key=lambda x: x.get("date", ""), reverse=True)
    results = []
    for item in sorted_items[:limit]:
        pub_time = item.get("date", "")
        if len(pub_time) > 16:
            pub_time = pub_time[:16]
        results.append({
            "標題": item.get("title", "無標題"),
            "來源": item.get("source", "未知"),
            "發布時間": pub_time,
            "連結": item.get("link", ""),
        })
    return results


def parse_yfinance_news(items: list | None, limit: int = 3) -> list:
    """解析 yfinance 新聞（支援新舊格式）"""
    if not items:
        return []

    results = []
    for item in items[:limit]:
        content = item.get("content") if isinstance(item.get("content"), dict) else item

        title = content.get("title") or item.get("title", "無標題")
        provider = content.get("provider") or {}
        source = provider.get("displayName") or item.get("publisher", "Yahoo Finance")

        url = ""
        for key in ("clickThroughUrl", "canonicalUrl"):
            link_obj = content.get(key) or {}
            if isinstance(link_obj, dict) and link_obj.get("url"):
                url = link_obj["url"]
                break
        if not url:
            url = item.get("link", "")

        pub_time = ""
        pub_raw = content.get("pubDate") or content.get("displayTime")
        if pub_raw:
            try:
                dt = datetime.fromisoformat(str(pub_raw).replace("Z", "+00:00"))
                pub_time = dt.astimezone().strftime("%Y-%m-%d %H:%M")
            except ValueError:
                pub_time = str(pub_raw)[:16]
        elif item.get("providerPublishTime"):
            pub_time = datetime.fromtimestamp(item["providerPublishTime"]).strftime("%Y-%m-%d %H:%M")

        results.append({
            "標題": title,
            "來源": source,
            "發布時間": pub_time,
            "連結": url,
        })
    return results


def merge_news(finmind_news: list, yfinance_news: list, limit: int = 8) -> list:
    """合併新聞來源，FinMind 優先，去除重複"""
    seen = set()
    merged = []
    for item in finmind_news + yfinance_news:
        key = item.get("連結") or item.get("標題")
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
        if len(merged) >= limit:
            break
    return merged
