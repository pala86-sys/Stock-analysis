"""確保報告用 Noto Sans TC TTF 字型存在（PDF 需 TrueType 輪廓，OTF/CFF 部分檢視器會亂碼）"""

from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"
NOTO_TTF = FONT_DIR / "NotoSansTC-Regular.ttf"
NOTO_OTF = FONT_DIR / "NotoSansTC-Regular.otf"
NOTO_TTF_URL = (
    "https://fonts.gstatic.com/s/notosanstc/v39/"
    "-nFuOG829Oofr2wohFbTp9ifNAn722rq0MXz76Cy_Co.ttf"
)
NOTO_OTF_URL = (
    "https://raw.githubusercontent.com/notofonts/noto-cjk/main/"
    "Sans/SubsetOTF/TC/NotoSansTC-Regular.otf"
)


def ensure_noto_ttf() -> Path:
    """下載或確認 TTF 存在，供 PDF 匯出使用"""
    if NOTO_TTF.exists() and NOTO_TTF.stat().st_size > 100_000:
        return NOTO_TTF

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Noto Sans TC TTF -> {NOTO_TTF}")
    urllib.request.urlretrieve(NOTO_TTF_URL, NOTO_TTF)
    return NOTO_TTF


def ensure_noto_otf() -> Path:
    """下載或確認 OTF 存在，供 matplotlib K 線圖使用"""
    if NOTO_OTF.exists() and NOTO_OTF.stat().st_size > 100_000:
        return NOTO_OTF

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading Noto Sans TC OTF -> {NOTO_OTF}")
    urllib.request.urlretrieve(NOTO_OTF_URL, NOTO_OTF)
    return NOTO_OTF


def main() -> None:
    ensure_noto_ttf()
    ensure_noto_otf()
    print("Fonts ready.")


if __name__ == "__main__":
    main()
