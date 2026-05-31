"""共用 UI 元件：表格分頁"""

import tkinter as tk
from tkinter import ttk


def configure_table_styles(style: ttk.Style):
    """設定表格樣式"""
    style.configure(
        "Data.Treeview",
        font=("Microsoft JhengHei", 10),
        rowheight=30,
        background="white",
        fieldbackground="white",
        borderwidth=0,
    )
    style.configure(
        "Data.Treeview.Heading",
        font=("Microsoft JhengHei", 10, "bold"),
        background="#F5F5F7",
        foreground="#333333",
        relief="flat",
    )
    style.map("Data.Treeview", background=[("selected", "#E8F0FE")])
    style.map("Data.Treeview.Heading", background=[("active", "#E5E5EA")])


class TabTable:
    """含標題、表格、備註的分頁表格容器"""

    def __init__(
        self,
        parent_notebook: ttk.Notebook,
        tab_title: str,
        columns: list[tuple[str, str, int, str]],
        note: str = "",
    ):
        """
        columns: [(欄位 id, 標題, 寬度, 對齊 anchor), ...]
        """
        self.frame = tk.Frame(parent_notebook, bg="white")
        parent_notebook.add(self.frame, text=f"  {tab_title}  ")

        self.title_label = tk.Label(
            self.frame,
            text="",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="white",
            fg="#222222",
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=16, pady=(14, 8))

        tree_wrap = tk.Frame(self.frame, bg="white")
        tree_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        col_ids = [c[0] for c in columns]
        self.tree = ttk.Treeview(
            tree_wrap,
            columns=col_ids,
            show="headings",
            style="Data.Treeview",
            selectmode="browse",
        )
        scrollbar = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        for col_id, heading, width, anchor in columns:
            self.tree.heading(col_id, text=heading, anchor="center")
            self.tree.column(col_id, width=width, anchor=anchor, stretch=(col_id == col_ids[-1]))

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("odd", background="#FAFAFA")
        self.tree.tag_configure("even", background="white")
        self.tree.tag_configure("loading", foreground="#888888")
        self.tree.tag_configure("error", foreground="#CC0000")
        self.tree.tag_configure("positive", foreground="#D32F2F")
        self.tree.tag_configure("negative", foreground="#00897B")

        self.note_label = tk.Label(
            self.frame,
            text=note,
            font=("Microsoft JhengHei", 9),
            bg="white",
            fg="#888888",
            anchor="w",
            justify="left",
        )
        if note:
            self.note_label.pack(fill="x", padx=16, pady=(0, 12))

        self._columns = col_ids

    def set_title(self, title: str):
        self.title_label.config(text=title)

    def clear(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def show_loading(self, title: str, message: str = "載入中，請稍候…"):
        self.set_title(title)
        self.clear()
        self.tree.insert("", "end", values=(message,) + ("",) * (len(self._columns) - 1), tags=("loading",))

    def show_error(self, title: str, message: str):
        self.set_title(title)
        self.clear()
        self.tree.insert("", "end", values=(f"❌ {message}",) + ("",) * (len(self._columns) - 1), tags=("error",))

    def fill_rows(self, rows: list[tuple], tag_fn=None):
        """填入資料列，tag_fn(row_index, row_values) -> tag name or None"""
        self.clear()
        for i, row in enumerate(rows):
            tag = tag_fn(i, row) if tag_fn else ("odd" if i % 2 else "even",)
            if isinstance(tag, str):
                tag = (tag,)
            tags = tag if "odd" not in tag and "even" not in tag else tag + (("odd",) if i % 2 else ("even",))
            self.tree.insert("", "end", values=row, tags=tags)


class ProfileTab:
    """公司簡介分頁：基本資料 + 題材標籤 + 中英文簡介"""

    THEME_COLORS = ("#E8F0FE", "#FFF3E0", "#E8F5E9", "#F3E5F5", "#ECEFF1")

    def __init__(self, parent_notebook: ttk.Notebook):
        self.frame = tk.Frame(parent_notebook, bg="white")
        parent_notebook.add(self.frame, text="  公司簡介  ")
        self._website_url = ""

        self.title_label = tk.Label(
            self.frame,
            text="公司簡介與投資題材",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="white",
            fg="#222222",
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=16, pady=(14, 4))

        self.subtitle_label = tk.Label(
            self.frame,
            text="",
            font=("Microsoft JhengHei", 10),
            bg="white",
            fg="#666666",
            anchor="w",
        )
        self.subtitle_label.pack(fill="x", padx=16, pady=(0, 8))

        info_wrap = tk.Frame(self.frame, bg="white")
        info_wrap.pack(fill="x", padx=16, pady=(0, 6))

        self.info_tree = ttk.Treeview(
            info_wrap,
            columns=("item", "value"),
            show="headings",
            style="Data.Treeview",
            height=6,
            selectmode="none",
        )
        self.info_tree.heading("item", text="項目", anchor="center")
        self.info_tree.heading("value", text="內容", anchor="w")
        self.info_tree.column("item", width=100, anchor="center", stretch=False)
        self.info_tree.column("value", width=720, anchor="w", stretch=True)
        self.info_tree.pack(fill="x")
        self.info_tree.bind("<Double-1>", self._on_info_double_click)

        theme_header = tk.Frame(self.frame, bg="white")
        theme_header.pack(fill="x", padx=16, pady=(6, 4))
        tk.Label(
            theme_header,
            text="投資題材",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        ).pack(side="left")
        self.theme_frame = tk.Frame(self.frame, bg="white")
        self.theme_frame.pack(fill="x", padx=16, pady=(0, 8))

        tk.Label(
            self.frame,
            text="公司簡介",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 4))

        intro_wrap = tk.Frame(self.frame, bg="white")
        intro_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        intro_scroll = ttk.Scrollbar(intro_wrap, orient="vertical")
        self.intro_text = tk.Text(
            intro_wrap,
            font=("Microsoft JhengHei", 10),
            wrap="word",
            bd=1,
            relief="solid",
            padx=10,
            pady=10,
            fg="#333333",
            yscrollcommand=intro_scroll.set,
            height=10,
        )
        intro_scroll.config(command=self.intro_text.yview)
        self.intro_text.pack(side="left", fill="both", expand=True)
        intro_scroll.pack(side="right", fill="y")
        self.intro_text.tag_configure(
            "heading", font=("Microsoft JhengHei", 10, "bold"), foreground="#0071E3",
        )
        self.intro_text.tag_configure("link", foreground="#0071E3", underline=True)
        self.intro_text.config(state="disabled")

        tk.Label(
            self.frame,
            text="雙擊官網列可開啟網頁 ｜ 資料來源：FinMind 產業分類 + Yahoo Finance 公司資訊",
            font=("Microsoft JhengHei", 9),
            bg="white",
            fg="#888888",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 10))

    def show_loading(self):
        self.title_label.config(text="公司簡介與投資題材")
        self.subtitle_label.config(text="")
        self._fill_info([("—", "⏳ 載入中，請稍候…")])
        self._render_themes([])
        self._set_intro_sections("", "")

    def show_error(self, message: str):
        self.title_label.config(text="公司簡介與投資題材")
        self.subtitle_label.config(text="")
        self._fill_info([("錯誤", f"❌ {message}")])
        self._render_themes([])
        self._set_intro_sections("", "")

    def render(self, profile_data: dict):
        if "錯誤" in profile_data:
            self.show_error(profile_data["錯誤"])
            return

        company = profile_data.get("公司名稱", "")
        code = profile_data.get("公司代號", "")
        self.title_label.config(text=company or "公司簡介與投資題材")
        self.subtitle_label.config(
            text=f"{code} ｜ {profile_data.get('交易市場', '')} ｜ {profile_data.get('產業分類', '')}"
            if company else "",
        )

        website = profile_data.get("官網", "—")
        self._website_url = website if website.startswith("http") else ""

        rows = [
            ("產業分類", profile_data.get("產業分類", "無資料")),
            ("交易市場", profile_data.get("交易市場", "無資料")),
            ("員工人數", profile_data.get("員工人數", "—")),
            ("總部", profile_data.get("總部", "—")),
            ("官網", website if self._website_url else "—"),
        ]
        self._fill_info(rows)
        self._render_themes(profile_data.get("themes") or [])
        self._set_intro_sections(
            profile_data.get("中文概況", ""),
            profile_data.get("原文摘要", ""),
            company,
        )

    def _render_themes(self, themes: list[str]):
        for widget in self.theme_frame.winfo_children():
            widget.destroy()
        if not themes:
            tk.Label(
                self.theme_frame, text="待觀察",
                font=("Microsoft JhengHei", 9), bg="#F5F5F7", fg="#888888",
                padx=10, pady=4,
            ).pack(side="left")
            return
        for i, theme in enumerate(themes):
            bg = self.THEME_COLORS[i % len(self.THEME_COLORS)]
            tk.Label(
                self.theme_frame,
                text=theme,
                font=("Microsoft JhengHei", 9, "bold"),
                bg=bg,
                fg="#333333",
                padx=10,
                pady=4,
            ).pack(side="left", padx=(0, 6), pady=2)

    def _fill_info(self, rows: list[tuple[str, str]]):
        for item in self.info_tree.get_children():
            self.info_tree.delete(item)
        self.info_tree.configure(height=max(len(rows), 3))
        for i, row in enumerate(rows):
            tag = "odd" if i % 2 else "even"
            self.info_tree.insert("", "end", values=row, tags=(tag,))
        self.info_tree.tag_configure("odd", background="#FAFAFA")
        self.info_tree.tag_configure("even", background="white")

    def _set_intro_sections(self, chinese: str, english: str, company_name: str = ""):
        self.intro_text.config(state="normal")
        self.intro_text.delete("1.0", tk.END)

        if chinese:
            self.intro_text.insert(tk.END, "【中文概況】\n", "heading")
            prefix = f"{company_name} " if company_name else ""
            self.intro_text.insert(tk.END, f"{prefix}{chinese}\n\n")

        if english:
            self.intro_text.insert(tk.END, "【原文摘要】\n", "heading")
            self.intro_text.insert(tk.END, english)

        if not chinese and not english:
            self.intro_text.insert(tk.END, "無公開資料")

        self.intro_text.config(state="disabled")

    def _on_info_double_click(self, event):
        item = self.info_tree.identify_row(event.y)
        if not item or not self._website_url:
            return
        values = self.info_tree.item(item, "values")
        if values and values[0] == "官網":
            import webbrowser
            webbrowser.open(self._website_url)


class ChipsTab:
    """籌碼面分頁：統計表 + 每日明細表"""

    def __init__(self, parent_notebook: ttk.Notebook):
        self.frame = tk.Frame(parent_notebook, bg="white")
        parent_notebook.add(self.frame, text="  籌碼面架構  ")

        self.title_label = tk.Label(
            self.frame,
            text="三大法人每日買賣超",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="white",
            fg="#222222",
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=16, pady=(14, 6))

        self.summary_subtitle = tk.Label(
            self.frame,
            text="",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        )
        self.summary_subtitle.pack(fill="x", padx=16, pady=(0, 4))

        summary_wrap = tk.Frame(self.frame, bg="white")
        summary_wrap.pack(fill="x", padx=16, pady=(0, 10))

        self.summary_tree = ttk.Treeview(
            summary_wrap,
            columns=("item", "status"),
            show="headings",
            style="Data.Treeview",
            height=4,
            selectmode="none",
        )
        self.summary_tree.heading("item", text="法人", anchor="center")
        self.summary_tree.heading("status", text="近日連續買賣超", anchor="center")
        self.summary_tree.column("item", width=120, anchor="center", stretch=False)
        self.summary_tree.column("status", width=700, anchor="center", stretch=True)
        self.summary_tree.pack(fill="x")

        tk.Label(
            self.frame,
            text="每日明細",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 4))

        daily_wrap = tk.Frame(self.frame, bg="white")
        daily_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        daily_cols = ("date", "foreign", "trust", "dealer", "total")
        self.daily_tree = ttk.Treeview(
            daily_wrap,
            columns=daily_cols,
            show="headings",
            style="Data.Treeview",
            selectmode="browse",
        )
        daily_scroll = ttk.Scrollbar(daily_wrap, orient="vertical", command=self.daily_tree.yview)
        self.daily_tree.configure(yscrollcommand=daily_scroll.set)

        headers = [
            ("date", "日期", 110, "center"),
            ("foreign", "外資(張)", 130, "center"),
            ("trust", "投信(張)", 130, "center"),
            ("dealer", "自營商(張)", 130, "center"),
            ("total", "法人合計(張)", 140, "center"),
        ]
        for col_id, heading, width, anchor in headers:
            self.daily_tree.heading(col_id, text=heading, anchor="center")
            self.daily_tree.column(col_id, width=width, anchor=anchor, stretch=(col_id == "total"))

        self.daily_tree.pack(side="left", fill="both", expand=True)
        daily_scroll.pack(side="right", fill="y")

        self.daily_tree.tag_configure("odd", background="#FAFAFA")
        self.daily_tree.tag_configure("even", background="white")

        tk.Label(
            self.frame,
            text="資料來源：FinMind（證交所盤後公布）｜正數為買超、負數為賣超，單位：張",
            font=("Microsoft JhengHei", 9),
            bg="white",
            fg="#888888",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 12))

    def show_loading(self):
        self.summary_subtitle.config(text="")
        self._clear_tree(self.summary_tree)
        self.summary_tree.insert("", "end", values=("—", "⏳ 載入中，請稍候…"))
        self._clear_tree(self.daily_tree)

    def show_error(self, message: str):
        self.summary_subtitle.config(text="")
        self._clear_tree(self.summary_tree)
        self.summary_tree.insert("", "end", values=("錯誤", f"❌ {message}"))
        self._clear_tree(self.daily_tree)

    def render(self, chips_data: dict):
        records = chips_data.get("records", [])
        summary = chips_data.get("summary", {})

        if not records:
            self.show_error("查無籌碼資料")
            return
        if "錯誤" in records[0]:
            self.show_error(records[0]["錯誤"])
            return

        self._clear_tree(self.summary_tree)
        if summary:
            latest = summary.get("最新日期", "")
            self.summary_subtitle.config(text=f"近日統計（截至 {latest}）")
            for i, key in enumerate(("外資", "投信", "自營商", "三大法人合計")):
                if key in summary:
                    tag = "odd" if i % 2 else "even"
                    self.summary_tree.insert("", "end", values=(key, summary[key]), tags=(tag,))
            self.summary_tree.tag_configure("odd", background="#FAFAFA")
            self.summary_tree.tag_configure("even", background="white")

        self._clear_tree(self.daily_tree)
        for i, row in enumerate(records):
            tag = "odd" if i % 2 else "even"
            self.daily_tree.insert(
                "",
                "end",
                values=(
                    row["日期"],
                    row["外資買賣超(張)"],
                    row["投信買賣超(張)"],
                    row["自營商買賣超(張)"],
                    row["三大法人合計(張)"],
                ),
                tags=(tag,),
            )

    @staticmethod
    def _clear_tree(tree: ttk.Treeview):
        for item in tree.get_children():
            tree.delete(item)


class FundamentalTab:
    """基本面分頁：核心指標 + 月營收 + 季 EPS"""

    HEADER_METRICS = ("公司名稱", "公司代號", "英文名稱", "目前股價", "價位評估")
    VALUATION_METRICS = ("市值 (億)", "本益比 (PE)", "股價淨值比 (PB)", "每股盈餘 (EPS)", "股利殖利率 (%)")

    def __init__(self, parent_notebook: ttk.Notebook):
        self.frame = tk.Frame(parent_notebook, bg="white")
        parent_notebook.add(self.frame, text="  基本面診斷  ")

        outer = tk.Frame(self.frame, bg="white")
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg="white", highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self.container = tk.Frame(canvas, bg="white")

        self._canvas_window = canvas.create_window((0, 0), window=self.container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def on_canvas_configure(event):
            canvas.itemconfig(self._canvas_window, width=event.width)

        def on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind("<Configure>", on_canvas_configure)
        self.container.bind("<Configure>", on_frame_configure)
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.title_label = tk.Label(
            self.container,
            text="基本面財務核心指標",
            font=("Microsoft JhengHei", 12, "bold"),
            bg="white",
            fg="#222222",
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=16, pady=(14, 8))

        metrics_wrap = tk.Frame(self.container, bg="white")
        metrics_wrap.pack(fill="x", padx=16, pady=(0, 10))
        self.metrics_tree = self._create_tree(
            metrics_wrap,
            [("metric", "財務指標", 180, "w"), ("value", "數值", 640, "e")],
            height=5,
        )

        self.valuation_subtitle = tk.Label(
            self.container,
            text="估值指標",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        )
        self.valuation_subtitle.pack(fill="x", padx=16, pady=(4, 4))

        valuation_wrap = tk.Frame(self.container, bg="white")
        valuation_wrap.pack(fill="x", padx=16, pady=(0, 10))
        self.valuation_tree = self._create_tree(
            valuation_wrap,
            [("metric", "財務指標", 180, "w"), ("value", "數值", 640, "e")],
            height=5,
        )

        self.revenue_subtitle = tk.Label(
            self.container,
            text="每月營收（近 24 個月）",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        )
        self.revenue_subtitle.pack(fill="x", padx=16, pady=(4, 4))

        revenue_wrap = tk.Frame(self.container, bg="white")
        revenue_wrap.pack(fill="x", padx=16, pady=(0, 10))
        self.revenue_tree = self._create_tree(
            revenue_wrap,
            [
                ("period", "期間", 90, "center"),
                ("revenue", "營收(億)", 120, "e"),
                ("mom", "月增率(%)", 100, "center"),
                ("yoy", "年增率(%)", 100, "center"),
            ],
            height=8,
        )

        self.eps_subtitle = tk.Label(
            self.container,
            text="季 EPS（近 12 季）",
            font=("Microsoft JhengHei", 10, "bold"),
            bg="white",
            fg="#444444",
            anchor="w",
        )
        self.eps_subtitle.pack(fill="x", padx=16, pady=(4, 4))

        eps_wrap = tk.Frame(self.container, bg="white")
        eps_wrap.pack(fill="x", padx=16, pady=(0, 12))
        self.eps_tree = self._create_tree(
            eps_wrap,
            [
                ("period", "期間", 90, "center"),
                ("eps", "EPS(元)", 100, "e"),
                ("qoq", "季增率(%)", 100, "center"),
                ("yoy", "年增率(%)", 100, "center"),
            ],
            height=8,
        )

        tk.Label(
            self.container,
            text="資料來源：FinMind 月營收 / 財報 EPS + Yahoo Finance 股價",
            font=("Microsoft JhengHei", 9),
            bg="white",
            fg="#888888",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 14))

    def _create_tree(self, parent, columns, height=6):
        col_ids = [c[0] for c in columns]
        tree = ttk.Treeview(
            parent,
            columns=col_ids,
            show="headings",
            style="Data.Treeview",
            height=height,
            selectmode="none",
        )
        for col_id, heading, width, anchor in columns:
            tree.heading(col_id, text=heading, anchor="center")
            tree.column(col_id, width=width, anchor=anchor, stretch=(col_id == col_ids[-1]))
        tree.pack(fill="x")
        tree.tag_configure("odd", background="#FAFAFA")
        tree.tag_configure("even", background="white")
        tree.tag_configure("loading", foreground="#888888")
        tree.tag_configure("error", foreground="#CC0000")
        return tree

    def show_loading(self):
        self.title_label.config(text="基本面財務核心指標")
        self._fill_tree(self.metrics_tree, [("—", "⏳ 載入中，請稍候…")], tags=("loading",))
        self._clear_tree(self.valuation_tree)
        self._clear_tree(self.revenue_tree)
        self._clear_tree(self.eps_tree)

    def show_error(self, message: str):
        self.title_label.config(text="基本面財務核心指標")
        self._fill_tree(self.metrics_tree, [(f"❌ {message}", "")], tags=("error",))
        self._clear_tree(self.valuation_tree)
        self._clear_tree(self.revenue_tree)
        self._clear_tree(self.eps_tree)

    def render(self, data: dict):
        if "錯誤" in data:
            self.show_error(data["錯誤"])
            return

        metrics = data.get("metrics", {})
        self.title_label.config(text="基本面財務核心指標")

        header_rows = [
            (key, metrics.get(key, "—"))
            for key in self.HEADER_METRICS
        ]
        self._fill_tree(self.metrics_tree, header_rows)

        valuation_rows = [
            (key, metrics.get(key, "—"))
            for key in self.VALUATION_METRICS
            if key in metrics
        ]
        if metrics.get("價位說明"):
            valuation_rows.insert(0, ("價位說明", metrics["價位說明"]))
        self._fill_tree(self.valuation_tree, valuation_rows)

        revenue_rows = [
            (r["期間"], r["營收(億)"], r["月增率(%)"], r["年增率(%)"])
            for r in data.get("revenue_history", [])
        ]
        if revenue_rows:
            self._fill_tree(self.revenue_tree, revenue_rows)
        else:
            self._fill_tree(self.revenue_tree, [("—", "查無月營收資料", "—", "—")])

        eps_rows = [
            (r["期間"], r["EPS(元)"], r["季增率(%)"], r["年增率(%)"])
            for r in data.get("eps_history", [])
        ]
        if eps_rows:
            self._fill_tree(self.eps_tree, eps_rows)
        else:
            self._fill_tree(self.eps_tree, [("—", "查無 EPS 資料", "—", "—")])

    def _fill_tree(self, tree, rows, tags=None):
        self._clear_tree(tree)
        for i, row in enumerate(rows):
            if tags:
                tree.insert("", "end", values=row, tags=tags)
            else:
                tag = "odd" if i % 2 else "even"
                tree.insert("", "end", values=row, tags=(tag,))

    @staticmethod
    def _clear_tree(tree):
        for item in tree.get_children():
            tree.delete(item)


class AdviceTab:
    """綜合評估分頁：入手參考意見"""

    TONE_COLORS = {
        "bull": ("#D32F2F", "#FFEBEE"),
        "mild_bull": ("#0071E3", "#E8F0FE"),
        "neutral": ("#666666", "#F5F5F7"),
        "mild_bear": ("#F57C00", "#FFF3E0"),
        "bear": ("#546E7A", "#ECEFF1"),
    }
    PRICE_TONE_COLORS = {
        "cheap": "#00897B",
        "fair": "#0071E3",
        "expensive": "#D32F2F",
        "neutral": "#888888",
    }

    def __init__(self, parent_notebook: ttk.Notebook):
        self.frame = tk.Frame(parent_notebook, bg="white")
        parent_notebook.add(self.frame, text="  綜合評估  ")

        self.card = tk.Frame(self.frame, bg="#F5F5F7", bd=0)
        self.card.pack(fill="x", padx=16, pady=(14, 10))

        self.company_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 14, "bold"),
            bg="#F5F5F7", fg="#222222", anchor="w",
        )
        self.company_label.pack(fill="x", padx=14, pady=(12, 0))

        self.company_sub_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 9),
            bg="#F5F5F7", fg="#888888", anchor="w",
        )
        self.company_sub_label.pack(fill="x", padx=14, pady=(0, 0))

        self.stock_price_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 12, "bold"),
            bg="#F5F5F7", fg="#111111", anchor="w",
        )
        self.stock_price_label.pack(fill="x", padx=14, pady=(6, 0))

        self.price_level_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 11, "bold"),
            bg="#F5F5F7", fg="#333333", anchor="w",
        )
        self.price_level_label.pack(fill="x", padx=14, pady=(6, 0))

        self.verdict_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 20, "bold"),
            bg="#F5F5F7", fg="#222222", anchor="w",
        )
        self.verdict_label.pack(fill="x", padx=14, pady=(4, 0))

        self.score_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 10),
            bg="#F5F5F7", fg="#666666", anchor="w",
        )
        self.score_label.pack(fill="x", padx=14, pady=(0, 4))

        self.suggestion_label = tk.Label(
            self.card, text="", font=("Microsoft JhengHei", 11),
            bg="#F5F5F7", fg="#333333", anchor="w", justify="left", wraplength=820,
        )
        self.suggestion_label.pack(fill="x", padx=14, pady=(0, 12))

        tk.Label(
            self.frame, text="各面向得分",
            font=("Microsoft JhengHei", 10, "bold"), bg="white", fg="#444444", anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 4))

        dim_wrap = tk.Frame(self.frame, bg="white")
        dim_wrap.pack(fill="x", padx=16, pady=(0, 10))
        self.dim_tree = ttk.Treeview(
            dim_wrap,
            columns=("name", "score", "desc"),
            show="headings",
            style="Data.Treeview",
            height=3,
            selectmode="none",
        )
        for col, head, w in [("name", "面向", 100), ("score", "得分", 80), ("desc", "說明", 620)]:
            self.dim_tree.heading(col, text=head, anchor="center")
            self.dim_tree.column(col, width=w, anchor="center" if col == "score" else "w")
        self.dim_tree.pack(fill="x")

        tk.Label(
            self.frame, text="評估細項",
            font=("Microsoft JhengHei", 10, "bold"), bg="white", fg="#444444", anchor="w",
        ).pack(fill="x", padx=16, pady=(4, 4))

        detail_wrap = tk.Frame(self.frame, bg="white")
        detail_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        detail_scroll = ttk.Scrollbar(detail_wrap, orient="vertical")
        self.detail_tree = ttk.Treeview(
            detail_wrap,
            columns=("item", "comment", "delta"),
            show="headings",
            style="Data.Treeview",
            selectmode="none",
        )
        self.detail_tree.configure(yscrollcommand=detail_scroll.set)
        detail_scroll.config(command=self.detail_tree.yview)
        for col, head, w, anc in [
            ("item", "項目", 100, "center"),
            ("comment", "評語", 580, "w"),
            ("delta", "加減", 70, "center"),
        ]:
            self.detail_tree.heading(col, text=head, anchor="center")
            self.detail_tree.column(col, width=w, anchor=anc)
        self.detail_tree.pack(side="left", fill="both", expand=True)
        detail_scroll.pack(side="right", fill="y")

        self.disclaimer_label = tk.Label(
            self.frame, text="",
            font=("Microsoft JhengHei", 9), bg="white", fg="#999999",
            anchor="w", justify="left", wraplength=820,
        )
        self.disclaimer_label.pack(fill="x", padx=16, pady=(0, 8))

        export_row = tk.Frame(self.frame, bg="white")
        export_row.pack(fill="x", padx=16, pady=(0, 12))
        self.export_btn = tk.Button(
            export_row,
            text="匯出 HTML 報告",
            font=("Microsoft JhengHei", 10),
            bg="#0071E3",
            fg="white",
            padx=14,
            pady=5,
            relief="flat",
            cursor="hand2",
            state="disabled",
            command=self._on_export_click,
        )
        self.export_btn.pack(side="right")
        self._export_callback = None

    def set_export_callback(self, callback):
        self._export_callback = callback

    def set_export_enabled(self, enabled: bool):
        self.export_btn.config(state="normal" if enabled else "disabled")

    def _on_export_click(self):
        if self._export_callback:
            self._export_callback()

    def show_loading(self):
        self._set_card("⏳ 分析中…", "", "正在彙整基本面、技術面、籌碼面資料…", "neutral")
        self.company_label.config(text="")
        self.company_sub_label.config(text="")
        self.stock_price_label.config(text="")
        self.price_level_label.config(text="")
        self._clear(self.dim_tree)
        self._clear(self.detail_tree)
        self.disclaimer_label.config(text="")
        self.set_export_enabled(False)

    def render(self, data: dict):
        display = data.get("顯示名稱") or data.get("公司名稱", "")
        subline = data.get("副標名稱", "")
        verdict = data.get("評等", "—")
        score = data.get("綜合得分", 0)
        suggestion = data.get("入手參考", "")
        tone = data.get("tone", "neutral")

        self.company_label.config(text=display or "—")
        if subline:
            self.company_sub_label.config(text=subline)
            self.company_sub_label.pack(fill="x", padx=14, pady=(0, 0))
        else:
            self.company_sub_label.config(text="")
            self.company_sub_label.pack_forget()

        price_display = data.get("目前股價顯示", "")
        if price_display:
            self.stock_price_label.config(text=f"目前股價：{price_display}")
            self.stock_price_label.pack(fill="x", padx=14, pady=(6, 0))
        else:
            self.stock_price_label.config(text="")
            self.stock_price_label.pack_forget()

        price_label = data.get("價位評估", "")
        price_reason = data.get("價位說明", "")
        price_tone = data.get("價位tone", "neutral")
        if price_label and price_label != "無法判定":
            fg = self.PRICE_TONE_COLORS.get(price_tone, self.PRICE_TONE_COLORS["neutral"])
            self.price_level_label.config(
                text=f"目前價位：{price_label} ｜ {price_reason}",
                fg=fg,
            )
            self.price_level_label.pack(fill="x", padx=14, pady=(6, 0))
        else:
            self.price_level_label.config(text="")
            self.price_level_label.pack_forget()

        self._set_card(
            f"入手參考：{verdict}",
            f"綜合得分 {score}（基本面 + 技術面 + 籌碼面）",
            suggestion,
            tone,
        )

        self._clear(self.dim_tree)
        for i, (name, dim_score, desc) in enumerate(data.get("dimensions", [])):
            tag = "odd" if i % 2 else "even"
            self.dim_tree.insert("", "end", values=(name, dim_score, desc), tags=(tag,))
        self.dim_tree.tag_configure("odd", background="#FAFAFA")
        self.dim_tree.tag_configure("even", background="white")

        self._clear(self.detail_tree)
        for i, (item, comment, delta) in enumerate(data.get("details", [])):
            tag = "odd" if i % 2 else "even"
            self.detail_tree.insert("", "end", values=(item, comment, delta), tags=(tag,))
        self.detail_tree.tag_configure("odd", background="#FAFAFA")
        self.detail_tree.tag_configure("even", background="white")

        self.disclaimer_label.config(text=data.get("免責聲明", ""))

    def _set_card(self, verdict: str, score_text: str, suggestion: str, tone: str):
        fg, bg = self.TONE_COLORS.get(tone, self.TONE_COLORS["neutral"])
        self.card.config(bg=bg)
        self.company_label.config(bg=bg)
        self.company_sub_label.config(bg=bg)
        self.price_level_label.config(bg=bg)
        self.verdict_label.config(text=verdict, fg=fg, bg=bg)
        self.score_label.config(text=score_text, bg=bg)
        self.suggestion_label.config(text=suggestion, bg=bg)

    @staticmethod
    def _clear(tree):
        for item in tree.get_children():
            tree.delete(item)
