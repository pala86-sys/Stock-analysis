"""打包前匯出內建股號清單至 data/stock_list.json"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from stock_search import fetch_stock_list_from_api  # noqa: E402

OUTPUT = ROOT / "data" / "stock_list.json"


def main():
    print("正在從 FinMind 下載股號清單…")
    stocks = fetch_stock_list_from_api()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(
            {
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "stocks": stocks,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"已寫入 {len(stocks)} 檔股票 → {OUTPUT}")


if __name__ == "__main__":
    main()
