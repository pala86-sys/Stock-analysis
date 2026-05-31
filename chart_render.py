"""K 線圖渲染為 PNG（Web / 報告用，無 tkinter）"""

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure

from chart_fonts import configure_chart_fonts
from indicators import compute_support_resistance

configure_chart_fonts()

BG = "#1e1e1e"
PANEL = "#252525"
GRID = "#333333"
TEXT = "#cccccc"
UP = "#ef5350"
DOWN = "#26a69a"
MA_COLORS = {
    "MA5": "#ffeb3b",
    "MA10": "#29b6f6",
    "MA20": "#ab47bc",
    "MA60": "#ffffff",
}


def _style_axis(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=TEXT, labelsize=8)
    ax.grid(True, color=GRID, linewidth=0.5, alpha=0.6)
    for spine in ax.spines.values():
        spine.set_color(GRID)


def _plot_candles(ax, df: pd.DataFrame, x):
    width = 0.6
    opens = df["Open"].to_numpy(dtype=float)
    closes = df["Close"].to_numpy(dtype=float)
    highs = df["High"].to_numpy(dtype=float)
    lows = df["Low"].to_numpy(dtype=float)
    colors = np.where(closes >= opens, UP, DOWN)
    wick_segments = np.stack(
        [np.column_stack([x, lows]), np.column_stack([x, highs])],
        axis=1,
    )
    ax.add_collection(LineCollection(wick_segments, colors=colors, linewidths=1, zorder=2))
    body_low = np.minimum(opens, closes)
    body_height = np.maximum(np.abs(closes - opens), 0.001)
    ax.bar(
        x, body_height, width=width, bottom=body_low,
        color=colors, edgecolor=colors, linewidth=0, align="center", zorder=3,
    )
    ax.set_ylabel("價格", color=TEXT, fontsize=9)


def _plot_moving_averages(ax, df: pd.DataFrame, x):
    for col, color in MA_COLORS.items():
        if col in df.columns:
            ax.plot(x, df[col].to_numpy(dtype=float), color=color, linewidth=1)


def _plot_support_resistance(ax, levels: dict):
    for i, price in enumerate(levels.get("supports") or []):
        ax.axhline(price, color=DOWN, linewidth=0.85, linestyle="--", alpha=0.65)
        ax.text(
            1.01, price, f" S{i + 1} {price:.2f}",
            transform=ax.get_yaxis_transform(),
            color=DOWN, fontsize=7, va="center", ha="left", alpha=0.9,
        )
    for i, price in enumerate(levels.get("resistances") or []):
        ax.axhline(price, color=UP, linewidth=0.85, linestyle="--", alpha=0.65)
        ax.text(
            1.01, price, f" R{i + 1} {price:.2f}",
            transform=ax.get_yaxis_transform(),
            color=UP, fontsize=7, va="center", ha="left", alpha=0.9,
        )


def _plot_volume(ax, df: pd.DataFrame, x):
    closes = df["Close"].to_numpy(dtype=float)
    opens = df["Open"].to_numpy(dtype=float)
    colors = np.where(closes >= opens, UP, DOWN)
    ax.bar(x, df["Volume"].to_numpy(dtype=float), width=0.6, color=colors, alpha=0.85)
    ax.set_ylabel("VOL", color=TEXT, fontsize=9)


def _plot_kd(ax, df: pd.DataFrame, x):
    ax.plot(x, df["K"].to_numpy(dtype=float), color="#ffeb3b", linewidth=1)
    ax.plot(x, df["D"].to_numpy(dtype=float), color="#29b6f6", linewidth=1)
    ax.axhline(80, color="#666666", linewidth=0.8, linestyle="--")
    ax.axhline(20, color="#666666", linewidth=0.8, linestyle="--")
    ax.set_ylim(0, 100)
    ax.set_ylabel("KD", color=TEXT, fontsize=9)


def _plot_macd(ax, df: pd.DataFrame, x):
    hist = df["MACD_hist"].to_numpy(dtype=float)
    colors = np.where(hist >= 0, UP, DOWN)
    ax.bar(x, hist, width=0.6, color=colors, alpha=0.85)
    ax.plot(x, df["DIF"].to_numpy(dtype=float), color="#ffeb3b", linewidth=1)
    ax.plot(x, df["DEA"].to_numpy(dtype=float), color="#29b6f6", linewidth=1)
    ax.set_ylabel("MACD", color=TEXT, fontsize=9)


def render_chart_png(
    full_df: pd.DataFrame,
    summary: dict,
    stock_name: str = "",
    display_days: int = 90,
) -> bytes | None:
    """將 K 線圖渲染為 PNG bytes"""
    if full_df is None or full_df.empty:
        return None

    display_days = min(display_days, len(full_df))
    df = full_df.tail(display_days)
    levels = compute_support_resistance(df)
    x = mdates.date2num(df.index.to_pydatetime())

    supports = levels.get("supports") or []
    resistances = levels.get("resistances") or []
    sr_hint = "  ".join(
        part for part in (
            f"支撐 {supports[0]:.0f}" if supports else "",
            f"壓力 {resistances[0]:.0f}" if resistances else "",
        ) if part
    )

    figure = Figure(figsize=(8.5, 7.5), dpi=100, facecolor=BG)
    gs = figure.add_gridspec(4, 1, height_ratios=[3.2, 1, 1, 1], hspace=0.08)
    ax_price = figure.add_subplot(gs[0])
    ax_vol = figure.add_subplot(gs[1], sharex=ax_price)
    ax_kd = figure.add_subplot(gs[2], sharex=ax_price)
    ax_macd = figure.add_subplot(gs[3], sharex=ax_price)

    _plot_candles(ax_price, df, x)
    _plot_moving_averages(ax_price, df, x)
    _plot_support_resistance(ax_price, levels)
    _plot_volume(ax_vol, df, x)
    ax_price.set_title(
        f"{stock_name or '技術分析'}  |  近{display_days}日  |  {summary.get('技術短評', '')}  |  {sr_hint}",
        color=TEXT, fontsize=10, loc="left", pad=8,
    )
    _plot_kd(ax_kd, df, x)
    _plot_macd(ax_macd, df, x)

    for ax in (ax_price, ax_vol, ax_kd, ax_macd):
        _style_axis(ax)
    ax_price.tick_params(labelbottom=False)
    ax_vol.tick_params(labelbottom=False)
    ax_kd.tick_params(labelbottom=False)
    ax_macd.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))

    figure.subplots_adjust(left=0.07, right=0.96, top=0.94, bottom=0.06)

    buf = io.BytesIO()
    figure.savefig(buf, format="png", facecolor=figure.get_facecolor(), bbox_inches="tight")
    plt.close(figure)
    buf.seek(0)
    return buf.read()


def _num(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return round(float(value), 4)


def serialize_chart_bars(full_df: pd.DataFrame, max_days: int = 180) -> list[dict]:
    """將 K 線序列化供 Web 互動圖表 / 查價使用"""
    if full_df is None or full_df.empty:
        return []

    df = full_df.tail(max_days)
    rows: list[dict] = []
    for idx, row in df.iterrows():
        if hasattr(idx, "strftime"):
            date_str = idx.strftime("%Y-%m-%d")
        else:
            date_str = str(idx)[:10]
        rows.append(
            {
                "date": date_str,
                "open": _num(row.get("Open")),
                "high": _num(row.get("High")),
                "low": _num(row.get("Low")),
                "close": _num(row.get("Close")),
                "volume": _num(row.get("Volume")),
                "MA5": _num(row.get("MA5")),
                "MA10": _num(row.get("MA10")),
                "MA20": _num(row.get("MA20")),
                "MA60": _num(row.get("MA60")),
                "K": _num(row.get("K")),
                "D": _num(row.get("D")),
                "DIF": _num(row.get("DIF")),
                "DEA": _num(row.get("DEA")),
                "MACD_hist": _num(row.get("MACD_hist")),
            }
        )
    return rows
