"""打包前匯出內建股號清單至 data/stock_list.json"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from finmind_client import request_finmind_delisted_stock_ids  # noqa: E402
from stock_search import fetch_stock_list_from_api  # noqa: E402

OUTPUT = ROOT / "data" / "stock_list.json"
DELISTED_OUTPUT = ROOT / "data" / "delisted_stock_ids.json"


def main():
    print("正在從 FinMind 下載股號清單…")
    delisted_ids = sorted(request_finmind_delisted_stock_ids())
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
    DELISTED_OUTPUT.write_text(
        json.dumps(
            {
                "updated_at": datetime.now().isoformat(timespec="seconds"),
                "stock_ids": delisted_ids,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"已寫入 {len(stocks)} 檔上市上櫃股票 → {OUTPUT}")
    print(f"已寫入 {len(delisted_ids)} 檔下市代號 → {DELISTED_OUTPUT}")


if __name__ == "__main__":
    main()
