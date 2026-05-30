"""股票搜尋輸入框（代號 / 名稱自動完成）"""

import tkinter as tk

from stock_search import format_stock_option, resolve_stock_input, search_stocks


class StockSearchBox:
    """可輸入代號或名稱，並以下拉清單選股"""

    def __init__(self, parent, font=("Microsoft JhengHei", 11), width=28):
        self.parent = parent
        self.font = font
        self.stocks: list[dict] = []
        self._results: list[dict] = []
        self._popup = None
        self._listbox = None
        self._debounce_id = None

        self.frame = tk.Frame(parent, bg=parent.cget("bg"))
        self.entry = tk.Entry(
            self.frame,
            font=font,
            width=width,
            bd=2,
            relief="groove",
        )
        self.entry.pack(side="left")
        self.entry.bind("<KeyRelease>", self._on_keyrelease)
        self.entry.bind("<FocusOut>", self._on_focus_out)
        self.entry.bind("<Down>", self._focus_listbox)
        self.entry.bind("<Up>", self._focus_listbox)
        self.entry.bind("<Escape>", lambda _e: self._hide_popup())

        self._on_select_callback = None

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def set_stocks(self, stocks: list[dict]):
        self.stocks = stocks or []

    def insert(self, text: str):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, text)

    def config(self, **kwargs):
        self.entry.config(**kwargs)

    def bind_return(self, callback):
        self.entry.bind("<Return>", callback)

    def on_select(self, callback):
        self._on_select_callback = callback

    def get_raw(self) -> str:
        return self.entry.get().strip()

    def get_stock_code(self) -> str | None:
        return resolve_stock_input(self.get_raw(), self.stocks)

    def _on_keyrelease(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab"):
            return

        if self._debounce_id:
            self.entry.after_cancel(self._debounce_id)
        self._debounce_id = self.entry.after(120, self._refresh_popup)

    def _refresh_popup(self):
        self._debounce_id = None
        query = self.get_raw()
        if len(query) < 1:
            self._hide_popup()
            return

        self._results = search_stocks(self.stocks, query)
        if not self._results:
            self._hide_popup()
            return

        self._show_popup([format_stock_option(s) for s in self._results])

    def _show_popup(self, options: list[str]):
        if self._popup is None:
            self._popup = tk.Toplevel(self.entry)
            self._popup.wm_overrideredirect(True)
            self._popup.attributes("-topmost", True)
            self._listbox = tk.Listbox(
                self._popup,
                font=self.font,
                height=min(8, len(options)),
                activestyle="dotbox",
                selectmode="browse",
                bd=1,
                relief="solid",
            )
            self._listbox.pack(fill="both", expand=True)
            self._listbox.bind("<ButtonRelease-1>", self._pick_selection)
            self._listbox.bind("<Return>", self._pick_selection)
            self._listbox.bind("<Escape>", lambda _e: self._hide_popup())

        self._listbox.delete(0, tk.END)
        for opt in options:
            self._listbox.insert(tk.END, opt)

        height = min(8, max(3, len(options)))
        self._listbox.config(height=height)

        self.entry.update_idletasks()
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        width = max(self.entry.winfo_width(), 360)
        self._popup.geometry(f"{width}x{height * 22 + 4}+{x}+{y}")
        self._popup.deiconify()

    def _hide_popup(self):
        if self._popup is not None:
            self._popup.withdraw()

    def _on_focus_out(self, _event):
        self.entry.after(150, self._hide_popup)

    def _focus_listbox(self, event):
        if self._popup is None or not self._results:
            return "break" if event.keysym == "Down" else None

        if event.keysym == "Down":
            self._listbox.focus_set()
            if self._listbox.size() > 0:
                self._listbox.selection_clear(0, tk.END)
                self._listbox.selection_set(0)
                self._listbox.activate(0)
        return "break"

    def _pick_selection(self, _event=None):
        if not self._listbox or not self._results:
            return

        selection = self._listbox.curselection()
        if not selection:
            return

        stock = self._results[selection[0]]
        self.insert(f"{stock['stock_id']} {stock['stock_name']}")
        self._hide_popup()
        if self._on_select_callback:
            self._on_select_callback(stock["stock_id"])
