"""Matplotlib 中文字型（內建 Noto Sans TC，跨 Windows / Linux / 打包）"""

from __future__ import annotations

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from settings import resource_path

_CONFIGURED = False
FONT_REL = "assets/fonts/NotoSansTC-Regular.otf"


def configure_chart_fonts() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    font_path = resource_path(FONT_REL)
    if font_path.exists():
        fm.fontManager.addfont(str(font_path))
        family = fm.FontProperties(fname=str(font_path)).get_name()
        plt.rcParams["font.family"] = "sans-serif"
        plt.rcParams["font.sans-serif"] = [family, "DejaVu Sans"]
    else:
        plt.rcParams["font.sans-serif"] = [
            "Noto Sans CJK TC",
            "Noto Sans TC",
            "WenQuanYi Micro Hei",
            "Microsoft JhengHei",
            "SimHei",
            "Arial Unicode MS",
            "DejaVu Sans",
        ]

    plt.rcParams["axes.unicode_minus"] = False
    _CONFIGURED = True
