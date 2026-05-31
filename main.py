import threading
import tempfile
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from logic import StockAnalyzer
from charts import TechnicalChart
from settings import load_last_stock, save_last_stock
from widgets import AdviceTab, ChipsTab, FundamentalTab, ProfileTab, TabTable, configure_table_styles
from advice import build_investment_advice
from report_export import export_pdf_report, report_download_filename
from stock_search import preload_stock_list
from stock_search_box import StockSearchBox


class StockApp:
    """
    台股多維度視覺化看板系統 UI 類別
    """
    def __init__(self, root):
        self.root = root
        self.root.title("台股多維度全方位觀測儀")
        self.root.geometry("900x780")
        self.root.configure(bg="#F5F5F7")

        self.is_loading = False
        self._analysis_id = 0
        self.btn_search = None
        self.stock_search = None
        self.entry_stock = None
        self.status_label = None
        self.progress = None

        self._section_cache: dict = {}
        self._current_stock_id = ""
        self._last_advice: dict = {}
        self._last_data_errors: list = []

        self.create_widgets()

    def create_widgets(self):
        """
        建立配置 UI 組件
        """
        search_frame = tk.Frame(self.root, bg="#F5F5F7", pady=15)
        search_frame.pack(fill="x")

        lbl_prompt = tk.Label(
            search_frame, text="請輸入股票名稱或代碼",
            font=("Microsoft JhengHei", 11, "bold"), bg="#F5F5F7", fg="#333333",
        )
        lbl_prompt.pack(side="left", padx=(20, 10))

        self.stock_search = StockSearchBox(search_frame, width=28)
        self.stock_search.pack(side="left", padx=5)
        self.stock_search.insert(load_last_stock())
        self.stock_search.bind_return(self._on_search_return)
        self.stock_search.on_select(lambda _code: self.start_analysis())
        self.entry_stock = self.stock_search.entry

        self.btn_search = tk.Button(
            search_frame, text="開始全方位診斷", command=self.start_analysis,
            font=("Microsoft JhengHei", 10, "bold"), bg="#0071E3", fg="white",
            padx=15, relief="flat", cursor="hand2",
        )
        self.btn_search.pack(side="left", padx=10)

        self.status_label = tk.Label(
            search_frame, text="", font=("Microsoft JhengHei", 9),
            bg="#F5F5F7", fg="#666666",
        )
        self.status_label.pack(side="left", padx=(8, 0))

        self.progress = ttk.Progressbar(search_frame, mode="indeterminate", length=120)
        self.progress.pack(side="left", padx=(8, 0))
        self.progress.pack_forget()

        self.style = ttk.Style()
        configure_table_styles(self.style)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.advice_tab = AdviceTab(self.notebook)
        self.advice_tab.set_export_callback(self.export_report)
        self.profile_tab = ProfileTab(self.notebook)
        self.fundamental_tab = FundamentalTab(self.notebook)
        self.technical_frame, self.technical_chart = self.create_technical_tab("技術面形態")
        self.chips_tab = ChipsTab(self.notebook)
        self.news_table, self._news_urls = self.create_news_table_tab("消息面情報")

        self.status_label.config(text="載入股號清單…")
        preload_stock_list(
            on_ready=lambda stocks: self.root.after(0, lambda: self._on_stocks_loaded(stocks)),
            on_error=lambda msg: self.root.after(0, lambda: self._on_stocks_load_failed(msg)),
        )

        self.root.after(100, self.start_analysis)

    def _on_stocks_loaded(self, stocks: list):
        self.stock_search.set_stocks(stocks)
        if not self.is_loading:
            self.status_label.config(text=f"已載入 {len(stocks)} 檔股票")

    def _on_stocks_load_failed(self, message: str):
        if not self.is_loading:
            self.status_label.config(text="股號清單載入失敗，仍可輸入代號")

    def _on_search_return(self, event):
        """Enter：若有下拉選單則選第一項，否則開始分析"""
        popup = self.stock_search._popup
        if popup is not None and popup.winfo_viewable() and self.stock_search._results:
            lb = self.stock_search._listbox
            if lb.size() > 0:
                lb.selection_clear(0, tk.END)
                lb.selection_set(0)
                self.stock_search._pick_selection()
                return "break"
        self.start_analysis()
        return "break"

    def create_technical_tab(self, tab_title: str):
        """建立技術面圖表分頁"""
        frame = tk.Frame(self.notebook, bg="#1e1e1e")
        self.notebook.add(frame, text=f"  {tab_title}  ")
        chart = TechnicalChart(frame)
        return frame, chart

    def create_news_table_tab(self, tab_title: str):
        """建立消息面表格分頁（雙擊或點選連結欄開啟瀏覽器）"""
        table = TabTable(
            self.notebook,
            tab_title,
            [
                ("idx", "#", 40, "center"),
                ("title", "標題", 380, "w"),
                ("source", "來源", 120, "center"),
                ("time", "發布時間", 130, "center"),
                ("link", "連結", 70, "center"),
            ],
            note="資料來源：FinMind 台股新聞 + Yahoo Finance ｜ 雙擊列或點「開啟」開啟新聞",
        )
        urls: dict[str, str] = {}

        def open_news(_event=None):
            selected = table.tree.selection()
            if not selected:
                return
            url = urls.get(selected[0], "")
            if url:
                webbrowser.open(url)

        def on_click(event):
            region = table.tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            col = table.tree.identify_column(event.x)
            if col != "#5":
                return
            item = table.tree.identify_row(event.y)
            if item and urls.get(item):
                webbrowser.open(urls[item])

        table.tree.bind("<Double-1>", open_news)
        table.tree.bind("<Button-1>", on_click, add="+")
        return table, urls

    def _set_loading(self, loading: bool, status: str = ""):
        """切換載入狀態：禁用輸入並顯示進度條"""
        self.is_loading = loading
        state = "disabled" if loading else "normal"

        self.stock_search.config(state=state)
        self.btn_search.config(state=state, text="分析中..." if loading else "開始全方位診斷")

        if loading:
            self.status_label.config(text=status or "載入中，請稍候…")
            self.progress.pack(side="left", padx=(8, 0))
            self.progress.start(12)
        else:
            self.status_label.config(text=status)
            self.progress.stop()
            self.progress.pack_forget()

    SECTION_STATUS = {
        "chips": "籌碼面",
        "news": "消息面",
        "profile": "公司簡介",
        "fundamental": "基本面",
        "technical": "技術面圖表",
    }

    def _show_loading_placeholders(self):
        """各分頁顯示載入占位"""
        self._section_cache = {}
        self.advice_tab.show_loading()
        self.profile_tab.show_loading()
        self.fundamental_tab.show_loading()
        self.chips_tab.show_loading()
        self.technical_chart.show_loading()
        self.news_table.show_loading("消息面情報 (最新市場快訊)")

    def start_analysis(self):
        """
        觸發分析流程：背景漸進抓取資料，各分頁完成即更新
        """
        raw = self.stock_search.get_raw()
        stock_id = self.stock_search.get_stock_code()
        if not raw:
            messagebox.showwarning("提示", "請先輸入股票代號或名稱！")
            return
        if not stock_id:
            messagebox.showwarning(
                "提示",
                "找不到符合的股票，請從下拉清單選擇，或輸入更完整的代號 / 名稱。",
            )
            return

        self.stock_search.insert(stock_id)

        self._current_stock_id = stock_id
        self._last_advice = {}
        self._last_data_errors = []
        self.advice_tab.set_export_enabled(False)

        self._analysis_id += 1
        analysis_id = self._analysis_id
        self._set_loading(True, "正在連線資料源…")
        self._show_loading_placeholders()
        threading.Thread(
            target=self._fetch_analysis,
            args=(stock_id, analysis_id),
            daemon=True,
        ).start()

    def _fetch_analysis(self, stock_id: str, analysis_id: int):
        """背景執行緒：漸進抓取分析資料"""
        try:
            analyzer = StockAnalyzer(stock_id)

            def on_section(section: str, data):
                self.root.after(
                    0,
                    lambda s=section, d=data: self._apply_section(s, d, analysis_id),
                )

            def on_complete():
                errors = analyzer.get_data_error_summary()
                self.root.after(
                    0,
                    lambda e=errors: self._finish_analysis(stock_id, analysis_id, e),
                )

            analyzer.analyze_progressive(on_section, on_complete)
        except Exception as e:
            self.root.after(
                0,
                lambda: self._on_analysis_failed(str(e), analysis_id),
            )

    def _apply_section(self, section: str, data, analysis_id: int):
        """主執行緒：更新單一分頁"""
        if analysis_id != self._analysis_id:
            return

        self._section_cache[section] = data

        if section == "profile":
            self.render_profile(data)
        elif section == "fundamental":
            self.render_fundamental(data)
        elif section == "technical":
            self.render_technical(data)
        elif section == "chips":
            self.render_chips(data)
        elif section == "news":
            self.render_news(data)

        label = self.SECTION_STATUS.get(section, section)
        self.status_label.config(text=f"已載入{label}…")

    def _finish_analysis(self, stock_id: str, analysis_id: int, data_errors: list | None = None):
        if analysis_id != self._analysis_id:
            return

        advice = build_investment_advice(
            self._section_cache.get("fundamental", {}),
            self._section_cache.get("technical", {}),
            self._section_cache.get("chips", {}),
        )
        self.advice_tab.render(advice)
        self._last_advice = advice
        self._last_data_errors = data_errors or []

        company = advice.get("顯示名稱") or advice.get("公司名稱") or stock_id
        self.root.title(f"台股多維度全方位觀測儀 — {company}")

        save_last_stock(stock_id)
        status = "分析完成"
        if data_errors:
            status = f"分析完成（部分資料未能載入：{'、'.join(data_errors)}）"
        self._set_loading(False, status)
        self.advice_tab.set_export_enabled(True)
        self.notebook.select(self.advice_tab.frame)

    def export_report(self):
        """匯出 PDF 分析報告"""
        if not self._last_advice or not self._section_cache:
            messagebox.showwarning("提示", "請先完成股票分析再匯出報告。")
            return

        default_name = report_download_filename(self._current_stock_id, self._last_advice)

        path = filedialog.asksaveasfilename(
            title="匯出 PDF 報告",
            defaultextension=".pdf",
            filetypes=[("PDF 報告", "*.pdf"), ("所有檔案", "*.*")],
            initialfile=default_name,
        )
        if not path:
            return

        chart_bytes = None
        if self.technical_chart.figure is not None:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            try:
                if self.technical_chart.save_png(tmp_path):
                    chart_bytes = tmp_path.read_bytes()
            finally:
                tmp_path.unlink(missing_ok=True)

        try:
            export_pdf_report(
                Path(path),
                self._current_stock_id,
                self._last_advice,
                self._section_cache,
                chart_png_bytes=chart_bytes,
                data_errors=self._last_data_errors or None,
            )
        except Exception as exc:
            messagebox.showerror("匯出失敗", f"無法寫入報告：\n{exc}")
            return

        if messagebox.askyesno("匯出完成", f"報告已儲存至：\n{path}\n\n是否開啟 PDF？"):
            webbrowser.open(Path(path).as_uri())

    def _on_analysis_failed(self, message: str, analysis_id: int | None = None):
        if analysis_id is not None and analysis_id != self._analysis_id:
            return
        messagebox.showerror("分析失敗", f"資料抓取時發生錯誤：\n{message}")
        self._set_loading(False)

    def render_profile(self, profile_data: dict):
        """渲染公司簡介分頁"""
        self.profile_tab.render(profile_data)

    def render_fundamental(self, data: dict):
        """渲染基本面分頁（指標 + 月營收 + 季 EPS）"""
        self.fundamental_tab.render(data)

    def render_technical(self, result: dict):
        """渲染技術面 K 線與指標圖表"""
        if "error" in result:
            self.technical_chart.show_error(result["error"])
            return

        full_data = result.get("full_data", result.get("data"))
        self.technical_chart.render(
            full_data,
            result["summary"],
            result.get("stock_name", ""),
            display_days=result.get("display_days", 90),
        )

    def render_chips(self, chips_data: dict):
        """渲染籌碼面表格"""
        self.chips_tab.render(chips_data)

    def render_news(self, news_data: list):
        """渲染消息面表格（雙擊開啟連結）"""
        title = "消息面情報 (最新市場快訊)"
        self._news_urls.clear()
        self.news_table.set_title(title)
        self.news_table.clear()

        for idx, news in enumerate(news_data, 1):
            url = news.get("連結", "")
            link_text = "開啟" if url else "—"
            tag = "odd" if idx % 2 else "even"
            item_id = self.news_table.tree.insert(
                "",
                "end",
                values=(
                    idx,
                    news.get("標題", ""),
                    news.get("來源", ""),
                    news.get("發布時間", ""),
                    link_text,
                ),
                tags=(tag,),
            )
            if url:
                self._news_urls[item_id] = url

        self.news_table.tree.tag_configure("odd", background="#FAFAFA")
        self.news_table.tree.tag_configure("even", background="white")


if __name__ == "__main__":
    try:
        root = tk.Tk()

        style = ttk.Style()
        style.theme_use("clam")
        configure_table_styles(style)
        style.configure("TNotebook", background="#F5F5F7", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Microsoft JhengHei", 10), padding=[12, 6], background="#E5E5EA")
        style.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", "#0071E3")])

        app = StockApp(root)
        root.mainloop()
    except Exception as e:
        print(f"環境初始化或系統執行時發生致命錯誤: {str(e)}")
