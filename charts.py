import tkinter as tk
import numpy as np
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
import pandas as pd
from indicators import compute_support_resistance

import matplotlib.pyplot as plt

from chart_fonts import configure_chart_fonts

configure_chart_fonts()


class TechnicalChart:
    """技術面 K 線與指標圖表（台股：紅漲綠跌）"""

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
    INFO_COLUMNS = [
        ("開盤價", "Open", "MA5"),
        ("最高價", "High", "MA10"),
        ("最低價", "Low", "MA20"),
        ("收盤價", "Close", "MA60"),
    ]
    INFO_X_COLS = [0.01, 0.17, 0.33, 0.49]
    PERIOD_OPTIONS = ((30, "30日"), (90, "90日"), (180, "180日"))

    def __init__(self, parent_frame):
        self.parent_frame = parent_frame
        self.canvas = None
        self.figure = None
        self.chart_container = None
        self.probe_btn = None
        self.period_btns: dict[int, tk.Button] = {}

        self.probe_mode = True
        self.full_df = None
        self.df = None
        self.display_days = 90
        self.stock_name = ""
        self.x = None
        self.summary = {}
        self.levels = {}
        self.price_axes = []
        self.vlines = []
        self.info_texts = {}
        self.ax_price = None
        self.ax_kd = None
        self.ax_macd = None
        self._motion_cid = None

        self._build_toolbar()

    def _build_toolbar(self):
        toolbar = tk.Frame(self.parent_frame, bg=self.BG)
        toolbar.pack(fill="x", padx=8, pady=(6, 0))

        tk.Label(
            toolbar, text="滑鼠在圖上左右移動可查看當日價格（按「查價」可關閉）",
            font=("Microsoft JhengHei", 9), bg=self.BG, fg="#888888",
        ).pack(side="left")

        period_frame = tk.Frame(toolbar, bg=self.BG)
        period_frame.pack(side="left", padx=(16, 0))

        tk.Label(
            period_frame, text="K 線週期",
            font=("Microsoft JhengHei", 9), bg=self.BG, fg="#888888",
        ).pack(side="left", padx=(0, 6))

        for days, label in self.PERIOD_OPTIONS:
            btn = tk.Button(
                period_frame, text=label,
                command=lambda d=days: self.set_period(d),
                font=("Microsoft JhengHei", 9, "bold"),
                bg="#333333", fg="#cccccc", activebackground="#444444",
                activeforeground="#ffffff", relief="flat", padx=10, pady=2,
                cursor="hand2",
            )
            btn.pack(side="left", padx=2)
            self.period_btns[days] = btn

        self.probe_btn = tk.Button(
            toolbar, text="查價", command=self.toggle_probe,
            font=("Microsoft JhengHei", 10, "bold"),
            bg="#333333", fg="#cccccc", activebackground="#444444",
            activeforeground="#ffffff", relief="flat", padx=12, pady=2,
            cursor="hand2",
        )
        self.probe_btn.pack(side="right")

        self.chart_container = tk.Frame(self.parent_frame, bg=self.BG)
        self.chart_container.pack(fill="both", expand=True)

    def set_period(self, display_days: int):
        """切換 K 線顯示週期（不需重抓 API）"""
        if self.full_df is None or self.full_df.empty:
            return

        self.display_days = min(display_days, len(self.full_df))
        self._update_period_buttons()
        if self.figure is not None and self.canvas is not None:
            self._draw_chart()
            self.canvas.draw_idle()
        else:
            self.render(
                self.full_df,
                self.summary,
                self.stock_name,
                display_days=self.display_days,
            )

    def _update_period_buttons(self):
        for days, btn in self.period_btns.items():
            if days == self.display_days:
                btn.config(bg="#0071E3", fg="#ffffff")
            else:
                btn.config(bg="#333333", fg="#cccccc")

    def toggle_probe(self):
        self.probe_mode = not self.probe_mode
        if self.probe_mode:
            self.probe_btn.config(bg="#0071E3", fg="#ffffff")
        else:
            self.probe_btn.config(bg="#333333", fg="#cccccc")
            self._clear_probe()

    def show_error(self, message: str):
        self.full_df = None
        self.clear()
        tk.Label(
            self.chart_container, text=f"❌ {message}",
            font=("Microsoft JhengHei", 11), bg=self.BG, fg=self.UP,
        ).pack(expand=True)

    def show_loading(self, message: str = "載入 K 線圖表中，請稍候…"):
        self.full_df = None
        self.clear()
        tk.Label(
            self.chart_container, text=f"⏳ {message}",
            font=("Microsoft JhengHei", 11), bg=self.BG, fg="#888888",
        ).pack(expand=True)

    def clear(self):
        if self._motion_cid and self.canvas:
            self.canvas.mpl_disconnect(self._motion_cid)
        self._motion_cid = None

        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if self.figure:
            plt.close(self.figure)
            self.figure = None
        self.canvas = None
        self.vlines = []
        self.info_texts = {}
        self.ax_price = None
        self.price_axes = []

    def render(
        self,
        full_df: pd.DataFrame,
        summary: dict,
        stock_name: str = "",
        display_days: int = 90,
    ):
        self.full_df = full_df
        self.summary = summary
        self.stock_name = stock_name
        self.display_days = min(display_days, len(full_df))

        self.clear()
        self.probe_mode = True
        if self.probe_btn:
            self.probe_btn.config(bg="#0071E3", fg="#ffffff")
        self._update_period_buttons()
        self._setup_figure()
        self._draw_chart()
        self.canvas.draw()
        self._motion_cid = self.canvas.mpl_connect("motion_notify_event", self._on_mouse_move)

    def _setup_figure(self):
        """建立 figure / canvas（僅首次或 clear 後）"""
        self.figure = Figure(figsize=(8.5, 7.5), dpi=100, facecolor=self.BG)
        gs = self.figure.add_gridspec(4, 1, height_ratios=[3.2, 1, 1, 1], hspace=0.08)

        ax_price = self.figure.add_subplot(gs[0])
        self.ax_price = ax_price
        ax_vol = self.figure.add_subplot(gs[1], sharex=ax_price)
        ax_kd = self.figure.add_subplot(gs[2], sharex=ax_price)
        ax_macd = self.figure.add_subplot(gs[3], sharex=ax_price)
        self.ax_kd = ax_kd
        self.ax_macd = ax_macd
        self.price_axes = [ax_price, ax_vol, ax_kd, ax_macd]

        self.figure.subplots_adjust(left=0.07, right=0.96, top=0.94, bottom=0.06)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.chart_container)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _draw_chart(self):
        """繪製 / 重繪圖表內容（可重複呼叫，切換週期時重用 canvas）"""
        self.df = self.full_df.tail(self.display_days)
        self.levels = compute_support_resistance(self.df)
        self.x = mdates.date2num(self.df.index.to_pydatetime())
        self.vlines = []

        ax_price, ax_vol, ax_kd, ax_macd = self.price_axes
        for ax in self.price_axes:
            ax.clear()

        self._plot_candles(ax_price, self.df, self.x)
        self._plot_moving_averages(ax_price, self.df, self.x)
        self._plot_support_resistance(ax_price)
        self._plot_volume(ax_vol, self.df, self.x)

        sr_hint = self._levels_hint()
        title = self.stock_name or "技術分析"
        ax_price.set_title(
            f"{title}  |  近{self.display_days}日  |  {self.summary.get('技術短評', '')}  |  {sr_hint}",
            color=self.TEXT, fontsize=10, loc="left", pad=8,
        )
        self._build_info_panel(ax_price)

        self._plot_kd(ax_kd, self.df, self.x)
        self._plot_macd(ax_macd, self.df, self.x)
        self._update_info_panel(len(self.df) - 1)

        for ax in self.price_axes:
            self._style_axis(ax)

        ax_price.tick_params(labelbottom=False)
        ax_vol.tick_params(labelbottom=False)
        ax_kd.tick_params(labelbottom=False)
        ax_macd.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
        ax_macd.tick_params(axis="x", rotation=0)

    def _build_info_panel(self, ax):
        """建立左上角 OHLC / 均線 對齊資訊列"""
        self.info_texts = {}
        self.info_texts["date"] = ax.text(
            0.01, 0.98, "", transform=ax.transAxes,
            color="#888888", fontsize=7, va="top", ha="left",
        )
        self.info_texts["volume"] = ax.text(
            0.65, 0.98, "", transform=ax.transAxes,
            color=self.TEXT, fontsize=8, va="top", ha="left",
        )
        self.info_texts["support"] = ax.text(
            0.62, 0.76, "", transform=ax.transAxes,
            color=self.DOWN, fontsize=8, va="top", ha="left",
        )
        self.info_texts["resistance"] = ax.text(
            0.62, 0.69, "", transform=ax.transAxes,
            color=self.UP, fontsize=8, va="top", ha="left",
        )
        self._update_level_labels()
        for i, (ohlc_label, _, ma_key) in enumerate(self.INFO_COLUMNS):
            color = self.MA_COLORS[ma_key]
            x = self.INFO_X_COLS[i]
            self.info_texts[f"ohlc_{i}"] = ax.text(
                x, 0.91, "", transform=ax.transAxes,
                color=color, fontsize=8, va="top", ha="left",
            )
            self.info_texts[f"ma_{i}"] = ax.text(
                x, 0.84, "", transform=ax.transAxes,
                color=color, fontsize=8, va="top", ha="left",
            )

    def _levels_hint(self) -> str:
        supports = self.levels.get("supports") or []
        resistances = self.levels.get("resistances") or []
        parts = []
        if supports:
            parts.append(f"支撐 {supports[0]:.0f}")
        if resistances:
            parts.append(f"壓力 {resistances[0]:.0f}")
        return "  ".join(parts) if parts else ""

    def _update_level_labels(self):
        if "support" not in self.info_texts:
            return
        supports = self.levels.get("supports") or []
        resistances = self.levels.get("resistances") or []

        if supports:
            s_text = "  ".join(f"S{i + 1} {p:.2f}" for i, p in enumerate(supports))
            self.info_texts["support"].set_text(f"支撐 {s_text}")
        else:
            low = self.levels.get("period_low")
            self.info_texts["support"].set_text(
                f"支撐 區間低 {low:.2f}" if low else "支撐 —"
            )

        if resistances:
            r_text = "  ".join(f"R{i + 1} {p:.2f}" for i, p in enumerate(resistances))
            self.info_texts["resistance"].set_text(f"壓力 {r_text}")
        else:
            high = self.levels.get("period_high")
            self.info_texts["resistance"].set_text(
                f"壓力 區間高 {high:.2f}" if high else "壓力 —"
            )

    def _plot_support_resistance(self, ax):
        """在 K 線圖上標示支撐 / 壓力水平線"""
        for i, price in enumerate(self.levels.get("supports") or []):
            ax.axhline(price, color=self.DOWN, linewidth=0.85, linestyle="--", alpha=0.65)
            ax.text(
                1.01, price, f" 支撐{i + 1} {price:.2f}",
                transform=ax.get_yaxis_transform(),
                color=self.DOWN, fontsize=7, va="center", ha="left", alpha=0.9,
            )

        for i, price in enumerate(self.levels.get("resistances") or []):
            ax.axhline(price, color=self.UP, linewidth=0.85, linestyle="--", alpha=0.65)
            ax.text(
                1.01, price, f" 壓力{i + 1} {price:.2f}",
                transform=ax.get_yaxis_transform(),
                color=self.UP, fontsize=7, va="center", ha="left", alpha=0.9,
            )

    def _update_info_panel(self, idx: int):
        """更新左上角開高低收與均線數值"""
        if self.df is None or not self.info_texts:
            return

        row = self.df.iloc[idx]
        up = row["Close"] >= row["Open"]
        vol_color = self.UP if up else self.DOWN
        self.info_texts["date"].set_text(self.df.index[idx].strftime("%Y-%m-%d"))
        self.info_texts["volume"].set_text(f"成交量 {int(row['Volume']):,}")
        self.info_texts["volume"].set_color(vol_color)

        for i, (ohlc_label, ohlc_key, ma_key) in enumerate(self.INFO_COLUMNS):
            color = self.MA_COLORS[ma_key]
            ohlc_val = row[ohlc_key]
            ma_val = row[ma_key] if ma_key in self.df.columns and pd.notna(row[ma_key]) else None

            self.info_texts[f"ohlc_{i}"].set_text(f"{ohlc_label} {ohlc_val:.2f}")
            self.info_texts[f"ohlc_{i}"].set_color(color)
            self.info_texts[f"ma_{i}"].set_text(
                f"{ma_key} {ma_val:.2f}" if ma_val is not None else f"{ma_key} --"
            )
            self.info_texts[f"ma_{i}"].set_color(color)

        self._update_kd_label(idx)
        self._update_macd_label(idx)

    @staticmethod
    def _kd_status(k_val: float, d_val: float) -> str:
        if k_val > 80 and d_val > 80:
            return "  高檔鈍化"
        if k_val < 20 and d_val < 20:
            return "  低檔鈍化"
        return ""

    def _update_kd_label(self, idx: int):
        if "kd" not in self.info_texts or self.df is None:
            return
        row = self.df.iloc[idx]
        k_val, d_val = row["K"], row["D"]
        label = f"K:{k_val:.1f}  D:{d_val:.1f}{self._kd_status(k_val, d_val)}"
        self.info_texts["kd"].set_text(label)

    def _update_macd_label(self, idx: int):
        if "macd" not in self.info_texts or self.df is None:
            return
        row = self.df.iloc[idx]
        label = f"DIF:{row['DIF']:.2f}  DEA:{row['DEA']:.2f}  MACD:{row['MACD_hist']:.2f}"
        self.info_texts["macd"].set_text(label)

    def _on_mouse_move(self, event):
        if not self.probe_mode or event.xdata is None or self.df is None or self.x is None:
            return
        if event.inaxes not in self.price_axes:
            return

        idx = int(np.searchsorted(self.x, event.xdata))
        idx = max(0, min(idx, len(self.x) - 1))
        if idx > 0 and abs(self.x[idx - 1] - event.xdata) < abs(self.x[idx] - event.xdata):
            idx -= 1
        self._show_probe(idx)

    def _ensure_probe_lines(self):
        if len(self.vlines) == len(self.price_axes):
            return
        self.vlines = []
        for ax in self.price_axes:
            line = ax.axvline(
                self.x[0], color="#aaaaaa", linewidth=0.9, linestyle="--", alpha=0.75, visible=False,
            )
            self.vlines.append(line)

    def _show_probe(self, idx: int):
        self._update_info_panel(idx)
        self._ensure_probe_lines()

        x_val = self.x[idx]
        for line in self.vlines:
            line.set_xdata([x_val, x_val])
            line.set_visible(True)

        self.canvas.draw_idle()

    def _clear_probe(self):
        for line in self.vlines:
            line.set_visible(False)
        if self.df is not None and len(self.df) > 0:
            self._update_info_panel(len(self.df) - 1)
        if self.canvas:
            self.canvas.draw_idle()

    def save_png(self, path) -> bool:
        """將目前圖表存成 PNG（供報告匯出）"""
        if self.figure is None:
            return False
        try:
            self.figure.savefig(path, dpi=120, facecolor=self.figure.get_facecolor(), bbox_inches="tight")
            return True
        except Exception:
            return False

    def _style_axis(self, ax):
        ax.set_facecolor(self.PANEL)
        ax.tick_params(colors=self.TEXT, labelsize=8)
        ax.grid(True, color=self.GRID, linewidth=0.5, alpha=0.6)
        for spine in ax.spines.values():
            spine.set_color(self.GRID)

    def _plot_candles(self, ax, df: pd.DataFrame, x):
        """向量化繪製 K 線（LineCollection + bar，避免逐根 patch）"""
        width = 0.6
        opens = df["Open"].to_numpy(dtype=float)
        closes = df["Close"].to_numpy(dtype=float)
        highs = df["High"].to_numpy(dtype=float)
        lows = df["Low"].to_numpy(dtype=float)
        up = closes >= opens
        colors = np.where(up, self.UP, self.DOWN)

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
        ax.set_ylabel("價格", color=self.TEXT, fontsize=9)
        ax.set_xlim(x[0] - width, x[-1] + width)

    def _plot_moving_averages(self, ax, df: pd.DataFrame, x):
        for col, color in self.MA_COLORS.items():
            if col in df.columns:
                values = df[col].to_numpy(dtype=float)
                ax.plot(x, values, color=color, linewidth=1, label=col)

    def _plot_volume(self, ax, df: pd.DataFrame, x):
        width = 0.6
        closes = df["Close"].to_numpy(dtype=float)
        opens = df["Open"].to_numpy(dtype=float)
        colors = np.where(closes >= opens, self.UP, self.DOWN)
        ax.bar(x, df["Volume"].to_numpy(dtype=float), width=width, color=colors, alpha=0.85)
        ax.set_ylabel("VOL", color=self.TEXT, fontsize=9)

    def _plot_kd(self, ax, df: pd.DataFrame, x):
        ax.plot(x, df["K"].to_numpy(dtype=float), color="#ffeb3b", linewidth=1, label="K")
        ax.plot(x, df["D"].to_numpy(dtype=float), color="#29b6f6", linewidth=1, label="D")
        ax.axhline(80, color="#666666", linewidth=0.8, linestyle="--")
        ax.axhline(20, color="#666666", linewidth=0.8, linestyle="--")
        ax.set_ylim(0, 100)
        ax.set_ylabel("KD", color=self.TEXT, fontsize=9)
        self.info_texts["kd"] = ax.text(
            0.01, 0.85, "", transform=ax.transAxes, color=self.TEXT, fontsize=8,
        )

    def _plot_macd(self, ax, df: pd.DataFrame, x):
        hist = df["MACD_hist"].to_numpy(dtype=float)
        hist_colors = np.where(hist >= 0, self.UP, self.DOWN)
        ax.bar(x, hist, width=0.6, color=hist_colors, alpha=0.85)
        ax.plot(x, df["DIF"].to_numpy(dtype=float), color="#ffeb3b", linewidth=1)
        ax.plot(x, df["DEA"].to_numpy(dtype=float), color="#29b6f6", linewidth=1)
        ax.set_ylabel("MACD", color=self.TEXT, fontsize=9)
        self.info_texts["macd"] = ax.text(
            0.01, 0.85, "", transform=ax.transAxes, color=self.TEXT, fontsize=8,
        )
