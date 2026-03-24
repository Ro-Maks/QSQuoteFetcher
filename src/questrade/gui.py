"""Tkinter GUI for the Questrade Price Fetcher (ttkbootstrap themed)."""
from __future__ import annotations

import ctypes
import threading
import tkinter as tk
from datetime import datetime, time as dt_time, timezone, timedelta

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, DISABLED, E, END, LEFT, NORMAL, RIGHT, W, X, Y

from questrade.main import fetch_all_quotes
from questrade.models.errors import (
    QuestradeApiError,
    QuoteUnavailableError,
    RateLimitError,
    SymbolNotFoundError,
    TokenRefreshError,
)
from questrade.models.quote import Quote

# Enable DPI awareness on Windows for crisp rendering.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[union-attr]
except Exception:  # noqa: BLE001
    pass

REFRESH_INTERVALS = [5, 10, 15, 30, 60]
DEFAULT_REFRESH_INTERVAL = 10

# -- Color palette --
CLR_BG_DARK = "#1a1d23"
CLR_BG_HEADER = "#21252b"
CLR_BG_CARD = "#282c34"
CLR_BG_ROW_ALT = "#2c313a"
CLR_ACCENT = "#61afef"
CLR_GREEN = "#98c379"
CLR_RED = "#e06c75"
CLR_ORANGE = "#e5c07b"
CLR_TEXT = "#abb2bf"
CLR_TEXT_BRIGHT = "#d4d7dd"
CLR_TEXT_DIM = "#636d83"
CLR_BORDER = "#3e4451"

FONT_FAMILY = "Segoe UI"


def _fmt_price(value: float | None) -> str:
    return f"${value:,.2f}" if value is not None else "---"


def _fmt_volume(volume: int) -> str:
    if volume >= 1_000_000:
        return f"{volume / 1_000_000:,.1f}M"
    if volume >= 1_000:
        return f"{volume / 1_000:,.1f}K"
    return f"{volume:,}"


def _fmt_time(iso_str: str) -> str:
    """Convert ISO 8601 timestamp to readable local format."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%b %d, %I:%M:%S %p")
    except (ValueError, TypeError):
        return iso_str


def _fmt_retrieved(dt: object) -> str:
    """Format the retrieval datetime for the status bar."""
    if isinstance(dt, datetime):
        local = dt.astimezone()
        return local.strftime("%b %d, %I:%M:%S %p")
    return str(dt)


def _fmt_change(quote: Quote) -> str:
    """Format daily price change as '+1.23 (+0.5%)' or '-1.23 (-0.5%)'."""
    if quote.last_trade_price is None or quote.open_price is None:
        return "---"
    change = quote.last_trade_price - quote.open_price
    if quote.open_price != 0:
        pct = (change / quote.open_price) * 100
    else:
        pct = 0.0
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:,.2f} ({sign}{pct:.2f}%)"


def _get_change_value(quote: Quote) -> float | None:
    """Return the raw price change, or None if unavailable."""
    if quote.last_trade_price is None or quote.open_price is None:
        return None
    return quote.last_trade_price - quote.open_price


def _fmt_status(quote: Quote) -> str:
    if quote.is_halted:
        return "HALTED"
    if quote.delay > 0:
        return f"Delayed {quote.delay}m"
    return "Real-Time"


_SPARK_CHARS = "▁▂▃▄▅▆▇█"


def _fmt_sparkline(history: list[float]) -> str:
    """Convert a list of price values to a Unicode sparkline string."""
    if len(history) < 2:
        return ""
    lo, hi = min(history), max(history)
    if hi == lo:
        return _SPARK_CHARS[3] * len(history)
    scale = len(_SPARK_CHARS) - 1
    return "".join(
        _SPARK_CHARS[int((v - lo) / (hi - lo) * scale)] for v in history
    )


def _sort_key_for_column(quote: Quote, column: str) -> tuple[int, float | str]:
    """Return a sortable key for the given column. None values sort last."""
    _COL_MAP: dict[str, object] = {
        "symbol": quote.symbol,
        "last_price": quote.last_trade_price,
        "change": _get_change_value(quote),
        "bid": quote.bid_price,
        "ask": quote.ask_price,
        "volume": quote.volume,
        "last_trade": quote.last_trade_time,
        "status": 0 if quote.is_halted else (1 if quote.delay > 0 else 2),
        "trend": "",
    }
    val = _COL_MAP.get(column, quote.symbol)
    if val is None:
        return (1, 0.0)
    if isinstance(val, str):
        return (0, val)
    return (0, float(val))


_UTC_OFFSET_EST = timezone(timedelta(hours=-5))
_UTC_OFFSET_EDT = timezone(timedelta(hours=-4))


def _now_eastern() -> datetime:
    """Return the current time in US Eastern, accounting for DST.

    DST (EDT, UTC-4) runs from the second Sunday in March at 2 AM
    to the first Sunday in November at 2 AM; otherwise EST (UTC-5).
    """
    utc_now = datetime.now(timezone.utc)
    year = utc_now.year
    # Second Sunday in March: find first day of March that is Sunday, then +7
    mar1_wd = datetime(year, 3, 1).weekday()  # 0=Mon … 6=Sun
    second_sun_mar = 8 + (6 - mar1_wd) % 7  # day-of-month
    dst_start = datetime(year, 3, second_sun_mar, 7, tzinfo=timezone.utc)  # 2 AM EST = 7 AM UTC
    # First Sunday in November
    nov1_wd = datetime(year, 11, 1).weekday()
    first_sun_nov = 1 + (6 - nov1_wd) % 7
    dst_end = datetime(year, 11, first_sun_nov, 6, tzinfo=timezone.utc)  # 2 AM EDT = 6 AM UTC
    tz = _UTC_OFFSET_EDT if dst_start <= utc_now < dst_end else _UTC_OFFSET_EST
    return utc_now.astimezone(tz)


def _get_market_status() -> tuple[str, str]:
    """Return (display_text, style_name) for the current US market session."""
    now = _now_eastern()

    # Weekends
    if now.weekday() >= 5:
        return ("Market Closed", "Mkc.TLabel")

    t = now.time()
    if t < dt_time(4, 0):
        return ("Market Closed", "Mkc.TLabel")
    if t < dt_time(9, 30):
        return ("Pre-Market", "Mkx.TLabel")
    if t < dt_time(16, 0):
        return ("Market Open", "Mko.TLabel")
    if t < dt_time(20, 0):
        return ("After-Hours", "Mkx.TLabel")
    return ("Market Closed", "Mkc.TLabel")


class QuoteApp(ttk.Window):
    """Main application window displaying live Questrade quotes."""

    def __init__(self) -> None:
        super().__init__(title="Questrade Quote Fetcher", themename="darkly")
        self.minsize(1060, 450)
        self.geometry("1200x500")
        self._auto_refresh_on = False
        self._countdown = 0
        self._countdown_timer_id: str | None = None
        self._quote_count = 0
        self._refresh_interval: int = DEFAULT_REFRESH_INTERVAL
        self._sort_column: str = "symbol"
        self._sort_descending: bool = False
        self._quotes: list[Quote] = []
        self._retrieved_at: object = None
        self._price_history: dict[str, list[float]] = {}
        self._selected_symbol: str | None = None
        self._programmatic_select = False

        self.configure(background=CLR_BG_DARK)
        # Style combobox dropdown list for dark theme.
        self.option_add("*TCombobox*Listbox.background", CLR_BG_CARD)
        self.option_add("*TCombobox*Listbox.foreground", CLR_TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", CLR_ACCENT)
        self._configure_styles()
        self._build_ui()
        self._update_market_status()
        # Fetch quotes on startup.
        self.after(100, self._refresh_quotes)

    def _configure_styles(self) -> None:
        style = ttk.Style()

        style.configure(
            "Header.TFrame",
            background=CLR_BG_HEADER,
        )
        style.configure(
            "Card.TFrame",
            background=CLR_BG_CARD,
        )
        style.configure(
            "Dark.TFrame",
            background=CLR_BG_DARK,
        )
        style.configure(
            "Title.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_BRIGHT,
            font=(FONT_FAMILY, 18, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Mko.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_GREEN,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Mkc.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Mkx.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_ORANGE,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "StatusDot.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_GREEN,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "Refreshlbl.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "Refreshval.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "StatusBar.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "StatusOk.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_GREEN,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "StatusError.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_RED,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "Countdown.TLabel",
            background=CLR_BG_DARK,
            foreground=CLR_ACCENT,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "Fetching.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_ACCENT,
            font=(FONT_FAMILY, 11),
        )

        # Treeview styling
        style.configure(
            "Custom.Treeview",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT,
            fieldbackground=CLR_BG_CARD,
            borderwidth=0,
            font=(FONT_FAMILY, 10),
            rowheight=36,
        )
        style.configure(
            "Custom.Treeview.Heading",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            borderwidth=0,
            font=(FONT_FAMILY, 9, "bold"),
            relief="flat",
        )
        style.map(
            "Custom.Treeview.Heading",
            background=[("active", CLR_BG_HEADER)],
        )
        style.map(
            "Custom.Treeview",
            background=[("selected", "#3e4451")],
            foreground=[("selected", CLR_TEXT_BRIGHT)],
        )

        style.configure(
            "Intervallbl.TLabel",
            background=CLR_BG_HEADER,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )

        # Detail panel
        style.configure("Dtl.TFrame", background=CLR_BG_CARD)
        style.configure(
            "DtlHd.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT_BRIGHT,
            font=(FONT_FAMILY, 13, "bold"),
        )
        style.configure(
            "DtlK.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "DtlV.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "DtlHlt.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_RED,
            font=(FONT_FAMILY, 10, "bold"),
        )
        style.configure(
            "DtlGrn.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_GREEN,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "DtlRng.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )
        style.configure(
            "DtlSpk.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_ACCENT,
            font=(FONT_FAMILY, 14),
        )

        # Dialog styles
        style.configure("Dlg.TFrame", background=CLR_BG_CARD)
        style.configure(
            "DlgHd.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT_BRIGHT,
            font=(FONT_FAMILY, 13, "bold"),
        )
        style.configure(
            "DlgLbl.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT,
            font=(FONT_FAMILY, 10),
        )
        style.configure(
            "DlgDim.TLabel",
            background=CLR_BG_CARD,
            foreground=CLR_TEXT_DIM,
            font=(FONT_FAMILY, 9),
        )

        # Buttons
        style.configure(
            "Refresh.TButton",
            font=(FONT_FAMILY, 10),
            padding=(16, 8),
        )
        style.configure(
            "AutoRefresh.TButton",
            font=(FONT_FAMILY, 10),
            padding=(14, 8),
        )

        # Progress bar for countdown
        style.configure(
            "TProgressbar",
            troughcolor=CLR_BG_DARK,
            thickness=3,
        )

    def _build_ui(self) -> None:
        # --- Header ---
        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 16))
        header.pack(fill=X)

        title_area = ttk.Frame(header, style="Header.TFrame")
        title_area.pack(side=LEFT)

        ttk.Label(title_area, text="Questrade Live Quotes", style="Title.TLabel").pack(
            side=LEFT, anchor=W
        )

        self._dot_label = ttk.Label(title_area, text="  \u2022 Connected", style="StatusDot.TLabel")
        self._dot_label.pack(side=LEFT, padx=(12, 0))

        ttk.Label(title_area, text="  \u2022", style="Subtitle.TLabel").pack(side=LEFT)
        self._market_status_label = ttk.Label(title_area, text="", style="Mkc.TLabel")
        self._market_status_label.pack(side=LEFT, padx=(4, 0))

        btn_area = ttk.Frame(header, style="Header.TFrame")
        btn_area.pack(side=RIGHT)

        # Last-updated display between title and buttons
        updated_area = ttk.Frame(header, style="Header.TFrame")
        updated_area.pack(side=RIGHT, padx=(0, 20))

        ttk.Label(updated_area, text="Last Updated  ", style="Refreshlbl.TLabel").pack(side=LEFT)
        self._updated_label = ttk.Label(updated_area, text="--:--:-- --", style="Refreshval.TLabel")
        self._updated_label.pack(side=LEFT)

        self._manage_btn = ttk.Button(
            btn_area,
            text="\u2630  Manage",
            command=self._open_symbol_manager,
            bootstyle="secondary-outline",  # type: ignore[arg-type]
            style="AutoRefresh.TButton",
        )
        self._manage_btn.pack(side=RIGHT, padx=(8, 0))

        self._auto_btn = ttk.Button(
            btn_area,
            text="\u21bb  Auto: OFF",
            command=self._toggle_auto_refresh,
            bootstyle="secondary-outline",  # type: ignore[arg-type]
            style="AutoRefresh.TButton",
        )
        self._auto_btn.pack(side=RIGHT, padx=(8, 0))

        self._refresh_btn = ttk.Button(
            btn_area,
            text="\u27f3  Refresh",
            command=self._refresh_quotes,
            bootstyle="info",  # type: ignore[arg-type]
            style="Refresh.TButton",
        )
        self._refresh_btn.pack(side=RIGHT)

        # Refresh interval selector
        interval_frame = ttk.Frame(btn_area, style="Header.TFrame")
        interval_frame.pack(side=RIGHT, padx=(0, 12))

        ttk.Label(interval_frame, text="Interval:", style="Intervallbl.TLabel").pack(
            side=LEFT, padx=(0, 4)
        )
        self._interval_var = tk.StringVar(value=f"{DEFAULT_REFRESH_INTERVAL}s")
        self._interval_combo = ttk.Combobox(
            interval_frame,
            textvariable=self._interval_var,
            values=[f"{v}s" for v in REFRESH_INTERVALS],
            width=4,
            state="readonly",
        )
        self._interval_combo.pack(side=LEFT)
        self._interval_combo.bind("<<ComboboxSelected>>", self._on_interval_change)

        # --- Thin accent line under header ---
        accent_line = tk.Frame(self, background=CLR_ACCENT, height=2)
        accent_line.pack(fill=X)

        # --- Table area ---
        table_frame = ttk.Frame(self, style="Dark.TFrame", padding=(16, 12, 16, 0))
        table_frame.pack(fill=BOTH, expand=True)
        self._table_frame = table_frame

        columns = ("symbol", "last_price", "change", "bid", "ask", "volume", "last_trade", "trend")
        self._tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            style="Custom.Treeview",
            selectmode="browse",
        )

        self._headings = {
            "symbol": "SYMBOL",
            "last_price": "LAST PRICE",
            "change": "CHANGE",
            "bid": "BID",
            "ask": "ASK",
            "volume": "VOLUME",
            "last_trade": "LAST TRADE",
            "trend": "TREND",
            "status": "STATUS",
        }
        col_config = {
            "symbol":     {"width": 90,  "minwidth": 70,  "anchor": W},
            "last_price": {"width": 100, "minwidth": 90,  "anchor": E},
            "change":     {"width": 140, "minwidth": 110, "anchor": E},
            "bid":        {"width": 90,  "minwidth": 70,  "anchor": E},
            "ask":        {"width": 90,  "minwidth": 70,  "anchor": E},
            "volume":     {"width": 90,  "minwidth": 70,  "anchor": E},
            "last_trade": {"width": 160, "minwidth": 130, "anchor": tk.CENTER},
            "trend":      {"width": 140, "minwidth": 100, "anchor": tk.CENTER},
        }
        for col in columns:
            if col == "trend":
                self._tree.heading(col, text=self._headings[col])
            else:
                self._tree.heading(
                    col, text=self._headings[col],
                    command=lambda c=col: self._on_sort(c),
                )
            cfg = col_config[col]
            self._tree.column(col, width=cfg["width"], minwidth=cfg["minwidth"], anchor=cfg["anchor"])

        self._tree.tag_configure("halted", foreground=CLR_RED)
        self._tree.tag_configure("delayed", foreground=CLR_ORANGE)
        self._tree.tag_configure("stripe", background=CLR_BG_ROW_ALT)
        self._tree.tag_configure("halted_stripe", foreground=CLR_RED, background=CLR_BG_ROW_ALT)
        self._tree.tag_configure("delayed_stripe", foreground=CLR_ORANGE, background=CLR_BG_ROW_ALT)
        self._tree.tag_configure("change_up", foreground=CLR_GREEN)
        self._tree.tag_configure("change_down", foreground=CLR_RED)
        self._tree.tag_configure("change_up_stripe", foreground=CLR_GREEN, background=CLR_BG_ROW_ALT)
        self._tree.tag_configure("change_down_stripe", foreground=CLR_RED, background=CLR_BG_ROW_ALT)

        # Separate status treeview for independent color control
        self._status_tree = ttk.Treeview(
            table_frame,
            columns=("status",),
            show="headings",
            style="Custom.Treeview",
            selectmode="none",
        )
        self._status_tree.heading(
            "status", text="STATUS",
            command=lambda: self._on_sort("status"),
        )
        self._status_tree.column("status", width=100, minwidth=80, anchor=tk.CENTER)

        self._status_tree.tag_configure("realtime", foreground=CLR_TEXT_BRIGHT)
        self._status_tree.tag_configure("realtime_stripe", foreground=CLR_TEXT_BRIGHT, background=CLR_BG_ROW_ALT)
        self._status_tree.tag_configure("halted", foreground=CLR_RED)
        self._status_tree.tag_configure("halted_stripe", foreground=CLR_RED, background=CLR_BG_ROW_ALT)
        self._status_tree.tag_configure("delayed", foreground=CLR_ORANGE)
        self._status_tree.tag_configure("delayed_stripe", foreground=CLR_ORANGE, background=CLR_BG_ROW_ALT)

        # Scrollbar synced to both treeviews
        def _sync_scroll(*args: str) -> None:
            self._tree.yview(*args)
            self._status_tree.yview(*args)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=_sync_scroll)

        def _on_main_scroll(*args: str) -> None:
            scrollbar.set(*args)
            self._status_tree.yview("moveto", args[0])

        def _on_status_scroll(*args: str) -> None:
            scrollbar.set(*args)
            self._tree.yview("moveto", args[0])

        self._tree.configure(yscrollcommand=_on_main_scroll)
        self._status_tree.configure(yscrollcommand=_on_status_scroll)

        def _on_mousewheel(event: tk.Event) -> str:  # type: ignore[type-arg]
            delta = -1 * (event.delta // 120)
            self._tree.yview_scroll(delta, "units")
            self._status_tree.yview_scroll(delta, "units")
            return "break"

        self._tree.bind("<MouseWheel>", _on_mousewheel)
        self._status_tree.bind("<MouseWheel>", _on_mousewheel)

        scrollbar.pack(side=RIGHT, fill=Y)
        self._status_tree.pack(side=RIGHT, fill=Y)
        self._tree.pack(side=LEFT, fill=BOTH, expand=True)

        # Event bindings for row selection (detail panel)
        self._tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self._status_tree.bind("<Button-1>", self._on_status_tree_click)

        # --- Detail panel (hidden initially) ---
        self._detail_outer = ttk.Frame(self, style="Dark.TFrame", padding=(16, 0, 16, 0))
        detail_accent = tk.Frame(self._detail_outer, background=CLR_ACCENT, height=2)
        detail_accent.pack(fill=X)
        detail_inner = ttk.Frame(self._detail_outer, style="Dtl.TFrame", padding=(20, 12))
        detail_inner.pack(fill=X)

        self._detail_fields: dict[str, ttk.Label | tk.Canvas] = {}

        # Row 0: Header (symbol + name) and status badge
        hdr_frame = ttk.Frame(detail_inner, style="Dtl.TFrame")
        hdr_frame.grid(row=0, column=0, columnspan=8, sticky="ew", pady=(0, 8))
        hdr_frame.columnconfigure(0, weight=1)
        self._detail_symbol_lbl = ttk.Label(hdr_frame, text="", style="DtlHd.TLabel")
        self._detail_symbol_lbl.grid(row=0, column=0, sticky=W)
        sts_lbl = ttk.Label(hdr_frame, text="", style="DtlV.TLabel")
        sts_lbl.grid(row=0, column=1, sticky=E)
        self._detail_fields["sts"] = sts_lbl

        # Row 1: Day range bar
        range_frame = ttk.Frame(detail_inner, style="Dtl.TFrame")
        range_frame.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(0, 8))
        ttk.Label(range_frame, text="Day Range", style="DtlK.TLabel").pack(side=LEFT, padx=(0, 8))
        range_lo_lbl = ttk.Label(range_frame, text="---", style="DtlRng.TLabel")
        range_lo_lbl.pack(side=LEFT, padx=(0, 4))
        self._detail_fields["range_lo"] = range_lo_lbl
        range_canvas = tk.Canvas(
            range_frame, height=14, width=300,
            background=CLR_BG_DARK, highlightthickness=0,
        )
        range_canvas.pack(side=LEFT, padx=4, fill=X, expand=True)
        self._detail_fields["range_canvas"] = range_canvas
        range_hi_lbl = ttk.Label(range_frame, text="---", style="DtlRng.TLabel")
        range_hi_lbl.pack(side=LEFT, padx=(4, 0))
        self._detail_fields["range_hi"] = range_hi_lbl

        # Row 2: Key metrics grid
        metrics = [
            ("Open", "open"),
            ("VWAP", "vwap"),
            ("Spread", "spread"),
            ("Bid \u00d7 Size", "bid_depth"),
            ("Ask \u00d7 Size", "ask_depth"),
            ("Last Trade", "last_trade"),
        ]
        for col_idx, (label_text, key) in enumerate(metrics):
            ttk.Label(detail_inner, text=label_text, style="DtlK.TLabel").grid(
                row=2, column=col_idx, sticky=W, padx=(0, 4),
            )
            val_lbl = ttk.Label(detail_inner, text="---", style="DtlV.TLabel")
            val_lbl.grid(row=3, column=col_idx, sticky=W, padx=(0, 20))
            self._detail_fields[key] = val_lbl

        # Row 4: Computed stats + enlarged sparkline
        stats_frame = ttk.Frame(detail_inner, style="Dtl.TFrame")
        stats_frame.grid(row=4, column=0, columnspan=8, sticky="ew", pady=(8, 0))
        from_open_lbl = ttk.Label(stats_frame, text="", style="DtlV.TLabel")
        from_open_lbl.pack(side=LEFT, padx=(0, 20))
        self._detail_fields["from_open"] = from_open_lbl
        off_high_lbl = ttk.Label(stats_frame, text="", style="DtlV.TLabel")
        off_high_lbl.pack(side=LEFT, padx=(0, 20))
        self._detail_fields["off_high"] = off_high_lbl
        spark_lbl = ttk.Label(stats_frame, text="", style="DtlSpk.TLabel")
        spark_lbl.pack(side=LEFT, padx=(0, 8))
        self._detail_fields["sparkline"] = spark_lbl
        spark_stats_lbl = ttk.Label(stats_frame, text="", style="DtlK.TLabel")
        spark_stats_lbl.pack(side=LEFT)
        self._detail_fields["spark_stats"] = spark_stats_lbl

        # --- Countdown progress bar ---
        self._progress = ttk.Progressbar(
            self,
            bootstyle="info",  # type: ignore[arg-type]
            maximum=self._refresh_interval,
            mode="determinate",
        )
        # Starts hidden; shown when auto-refresh is active.

        # --- Status bar ---
        separator = ttk.Separator(self)
        separator.pack(fill=X, padx=16, pady=(8, 0))

        status_frame = ttk.Frame(self, style="Dark.TFrame", padding=(20, 8, 20, 12))
        status_frame.pack(fill=X)

        self._time_label = ttk.Label(status_frame, text="", style="StatusBar.TLabel")
        self._time_label.pack(side=LEFT)

        self._status_label = ttk.Label(status_frame, text="", style="StatusBar.TLabel")
        self._status_label.pack(side=RIGHT)

        self._countdown_label = ttk.Label(status_frame, text="", style="Countdown.TLabel")
        self._countdown_label.pack(side=RIGHT, padx=(0, 16))

    # --- Market status ---

    def _update_market_status(self) -> None:
        text, style = _get_market_status()
        self._market_status_label.configure(text=text, style=style)
        self.after(60_000, self._update_market_status)

    # --- Auto-refresh ---

    def _on_interval_change(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._refresh_interval = int(self._interval_var.get().rstrip("s"))
        self._progress.configure(maximum=self._refresh_interval)
        if self._auto_refresh_on:
            self._cancel_countdown()
            self._start_countdown()
        self.focus_set()

    def _toggle_auto_refresh(self) -> None:
        self._auto_refresh_on = not self._auto_refresh_on
        if self._auto_refresh_on:
            self._auto_btn.configure(
                text="\u21bb  Auto: ON",
                bootstyle="success",  # type: ignore[arg-type]
            )
            self._start_countdown()
        else:
            self._auto_btn.configure(
                text="\u21bb  Auto: OFF",
                bootstyle="secondary-outline",  # type: ignore[arg-type]
            )
            self._cancel_countdown()
            self._countdown_label.configure(text="")
            self._progress.pack_forget()

    def _start_countdown(self) -> None:
        self._countdown = self._refresh_interval
        self._progress.configure(value=self._refresh_interval)
        self._progress.pack(fill=X, padx=16, pady=(4, 0), before=self._get_separator())
        self._tick_countdown()

    def _get_separator(self) -> tk.Widget:
        """Return the separator widget for insertion ordering."""
        for child in self.winfo_children():
            if isinstance(child, ttk.Separator):
                return child
        return self.winfo_children()[-1]

    def _tick_countdown(self) -> None:
        if not self._auto_refresh_on:
            return
        if self._countdown <= 0:
            self._progress.pack_forget()
            self._refresh_quotes()
            return
        self._countdown_label.configure(text=f"Next refresh in {self._countdown}s")
        self._progress.configure(value=self._countdown)
        self._countdown -= 1
        self._countdown_timer_id = self.after(1000, self._tick_countdown)

    def _cancel_countdown(self) -> None:
        if self._countdown_timer_id is not None:
            self.after_cancel(self._countdown_timer_id)
            self._countdown_timer_id = None

    # --- Fetching ---

    def _refresh_quotes(self) -> None:
        self._cancel_countdown()
        self._refresh_btn.configure(state=DISABLED)
        self._status_label.configure(text="\u27f3 Fetching\u2026", style="StatusBar.TLabel")
        self._countdown_label.configure(text="")
        self._progress.pack_forget()

        self._dot_label.configure(text="  \u2022 Fetching\u2026", foreground=CLR_ACCENT)
        threading.Thread(target=self._fetch_worker, daemon=True).start()

    def _fetch_worker(self) -> None:
        try:
            quotes, retrieved_at = fetch_all_quotes()
            self.after(0, self._on_fetch_complete, quotes, retrieved_at)
        except (
            TokenRefreshError,
            SymbolNotFoundError,
            QuoteUnavailableError,
            RateLimitError,
            QuestradeApiError,
            EnvironmentError,
        ) as exc:
            self.after(0, self._on_fetch_error, str(exc))
        except Exception as exc:  # noqa: BLE001
            self.after(0, self._on_fetch_error, f"Unexpected error: {exc}")

    def _on_fetch_complete(self, quotes: list[Quote], retrieved_at: object) -> None:
        self._quotes = quotes
        self._retrieved_at = retrieved_at

        # Accumulate price history for sparklines
        for q in quotes:
            if q.last_trade_price is not None:
                hist = self._price_history.setdefault(q.symbol, [])
                hist.append(q.last_trade_price)
                if len(hist) > 20:
                    hist.pop(0)

        self._sort_and_display()

        self._quote_count = len(quotes)
        self._time_label.configure(
            text=f"Last updated: {_fmt_retrieved(retrieved_at)}  \u2022  {self._quote_count} symbols"
        )
        if isinstance(retrieved_at, datetime):
            self._updated_label.configure(text=retrieved_at.astimezone().strftime("%I:%M:%S %p"))
        self._status_label.configure(text="\u2713 OK", style="StatusOk.TLabel")
        self._refresh_btn.configure(state=NORMAL)
        self._dot_label.configure(text="  \u2022 Connected", foreground=CLR_GREEN)

    # --- Sorting ---

    def _on_sort(self, column: str) -> None:
        if column == self._sort_column:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_column = column
            self._sort_descending = False
        if self._quotes:
            self._sort_and_display()

    def _sort_and_display(self) -> None:
        """Sort stored quotes and repopulate both treeviews."""
        self._programmatic_select = True
        sorted_quotes = sorted(
            self._quotes,
            key=lambda q: _sort_key_for_column(q, self._sort_column),
            reverse=self._sort_descending,
        )

        # Clear both treeviews.
        for item in self._tree.get_children():
            self._tree.delete(item)
        for item in self._status_tree.get_children():
            self._status_tree.delete(item)

        for i, quote in enumerate(sorted_quotes):
            is_stripe = i % 2 == 1
            tags: list[str] = []
            status_tags: list[str] = []

            if quote.is_halted:
                tags = ["halted_stripe" if is_stripe else "halted"]
                status_tags = ["halted_stripe" if is_stripe else "halted"]
            elif quote.delay > 0:
                tags = ["delayed_stripe" if is_stripe else "delayed"]
                status_tags = ["delayed_stripe" if is_stripe else "delayed"]
            else:
                change = _get_change_value(quote)
                if change is not None and change > 0:
                    tags = ["change_up_stripe" if is_stripe else "change_up"]
                elif change is not None and change < 0:
                    tags = ["change_down_stripe" if is_stripe else "change_down"]
                elif is_stripe:
                    tags = ["stripe"]
                status_tags = ["realtime_stripe" if is_stripe else "realtime"]

            self._tree.insert("", END, values=(
                f"  {quote.symbol}",
                _fmt_price(quote.last_trade_price),
                _fmt_change(quote),
                _fmt_price(quote.bid_price),
                _fmt_price(quote.ask_price),
                _fmt_volume(quote.volume),
                _fmt_time(quote.last_trade_time),
                _fmt_sparkline(self._price_history.get(quote.symbol, [])),
            ), tags=tuple(tags) if tags else ())

            self._status_tree.insert("", END, values=(
                _fmt_status(quote),
            ), tags=tuple(status_tags))

        self._update_heading_text()

        # Re-select previously selected row for detail panel
        if self._selected_symbol:
            for item in self._tree.get_children():
                vals = self._tree.item(item, "values")
                if vals and vals[0].strip() == self._selected_symbol:
                    self._tree.selection_set(item)
                    self._show_detail_panel(self._selected_symbol)
                    break

        self.after_idle(self._reset_programmatic_select)

    def _update_heading_text(self) -> None:
        """Update column headings to show sort indicator on the active column."""
        arrow = " \u25b2" if not self._sort_descending else " \u25bc"
        for col in ("symbol", "last_price", "change", "bid", "ask", "volume", "last_trade", "trend"):
            text = self._headings[col]
            if col == self._sort_column and col != "trend":
                text += arrow
            self._tree.heading(col, text=text)

        status_text = self._headings["status"]
        if self._sort_column == "status":
            status_text += arrow
        self._status_tree.heading("status", text=status_text)

        # Restart countdown if auto-refresh is on.
        if self._auto_refresh_on:
            self._start_countdown()

    def _on_fetch_error(self, message: str) -> None:
        self._status_label.configure(text=message, style="StatusError.TLabel")
        self._refresh_btn.configure(state=NORMAL)
        self._dot_label.configure(text="  \u2022 Error", foreground=CLR_RED)

        # Keep auto-refreshing even after errors.
        if self._auto_refresh_on:
            self._start_countdown()

    # --- Detail panel ---

    def _reset_programmatic_select(self) -> None:
        self._programmatic_select = False

    def _on_row_select(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._programmatic_select:
            return
        selection = self._tree.selection()
        if not selection:
            return
        item = selection[0]
        values = self._tree.item(item, "values")
        if not values:
            return
        symbol = values[0].strip()

        # Toggle: click same symbol again to collapse
        if symbol == self._selected_symbol:
            self._hide_detail_panel()
            return

        self._selected_symbol = symbol

        # Sync status tree selection
        main_items = self._tree.get_children()
        status_items = self._status_tree.get_children()
        try:
            idx = list(main_items).index(item)
            if idx < len(status_items):
                self._status_tree.selection_set(status_items[idx])
        except ValueError:
            pass

        self._show_detail_panel(symbol)

    def _on_status_tree_click(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        row_id = self._status_tree.identify_row(event.y)
        if not row_id:
            return
        status_items = list(self._status_tree.get_children())
        main_items = list(self._tree.get_children())
        try:
            idx = status_items.index(row_id)
        except ValueError:
            return
        if 0 <= idx < len(main_items):
            self._tree.selection_set(main_items[idx])
            self._tree.event_generate("<<TreeviewSelect>>")

    def _draw_range_bar(self, canvas: tk.Canvas, low: float, high: float, current: float) -> None:
        """Draw a day range bar on the canvas with a marker for the current price."""
        canvas.delete("all")
        canvas.update_idletasks()
        w = canvas.winfo_width() or 300
        h = canvas.winfo_height() or 14
        pad = 2

        # Track background
        canvas.create_rectangle(pad, 4, w - pad, h - 4, fill=CLR_BORDER, outline="")

        if high > low:
            ratio = (current - low) / (high - low)
            ratio = max(0.0, min(1.0, ratio))
            fill_x = pad + ratio * (w - 2 * pad)

            # Filled portion (low → current)
            canvas.create_rectangle(pad, 4, fill_x, h - 4, fill=CLR_ACCENT, outline="")

            # Current price marker (vertical line)
            canvas.create_line(fill_x, 1, fill_x, h - 1, fill=CLR_TEXT_BRIGHT, width=2)

    def _show_detail_panel(self, symbol: str) -> None:
        quote = next((q for q in self._quotes if q.symbol == symbol), None)
        if quote is None:
            return

        from questrade.config import TARGET_SYMBOLS
        name = next((s.name for s in TARGET_SYMBOLS if s.symbol == symbol), symbol)

        # Header
        self._detail_symbol_lbl.configure(text=f"{symbol}  \u2014  {name}")

        # Status badge
        if quote.is_halted:
            self._detail_fields["sts"].configure(text="\u26d4 HALTED", style="DtlHlt.TLabel")
        elif quote.delay > 0:
            self._detail_fields["sts"].configure(text=f"\u23f1 Delayed {quote.delay}m", style="DtlV.TLabel")
        else:
            self._detail_fields["sts"].configure(text="\u26a1 Real-Time", style="DtlGrn.TLabel")

        # Day range bar
        lo, hi = quote.low_price, quote.high_price
        cur = quote.last_trade_price
        if lo is not None and hi is not None and cur is not None:
            self._detail_fields["range_lo"].configure(text=_fmt_price(lo))
            self._detail_fields["range_hi"].configure(text=_fmt_price(hi))
            canvas = self._detail_fields["range_canvas"]
            self._detail_outer.pack(fill=X, after=self._table_frame)
            self.update_idletasks()
            self._draw_range_bar(canvas, lo, hi, cur)  # type: ignore[arg-type]
        else:
            self._detail_fields["range_lo"].configure(text="---")
            self._detail_fields["range_hi"].configure(text="---")
            canvas = self._detail_fields["range_canvas"]
            canvas.delete("all")  # type: ignore[union-attr]

        # Key metrics
        self._detail_fields["open"].configure(text=_fmt_price(quote.open_price))
        self._detail_fields["vwap"].configure(text=_fmt_price(quote.vwap))

        # Spread
        if quote.bid_price is not None and quote.ask_price is not None:
            spread = quote.ask_price - quote.bid_price
            spread_pct = (spread / quote.ask_price * 100) if quote.ask_price else 0
            self._detail_fields["spread"].configure(text=f"${spread:.2f} ({spread_pct:.2f}%)")
        else:
            self._detail_fields["spread"].configure(text="---")

        # Bid × Size
        if quote.bid_price is not None:
            bid_txt = _fmt_price(quote.bid_price)
            if quote.bid_size is not None:
                bid_txt += f" \u00d7 {quote.bid_size:,}"
            self._detail_fields["bid_depth"].configure(text=bid_txt)
        else:
            self._detail_fields["bid_depth"].configure(text="---")

        # Ask × Size
        if quote.ask_price is not None:
            ask_txt = _fmt_price(quote.ask_price)
            if quote.ask_size is not None:
                ask_txt += f" \u00d7 {quote.ask_size:,}"
            self._detail_fields["ask_depth"].configure(text=ask_txt)
        else:
            self._detail_fields["ask_depth"].configure(text="---")

        # Last Trade (size @ time)
        time_str = _fmt_time(quote.last_trade_time)
        if quote.last_trade_size is not None:
            self._detail_fields["last_trade"].configure(text=f"{quote.last_trade_size:,} @ {time_str}")
        else:
            self._detail_fields["last_trade"].configure(text=time_str)

        # From Open %
        if cur is not None and quote.open_price is not None and quote.open_price != 0:
            from_open_pct = (cur - quote.open_price) / quote.open_price * 100
            sign = "+" if from_open_pct >= 0 else ""
            style = "DtlGrn.TLabel" if from_open_pct >= 0 else "DtlHlt.TLabel"
            self._detail_fields["from_open"].configure(
                text=f"From Open  {sign}{from_open_pct:.2f}%", style=style,
            )
        else:
            self._detail_fields["from_open"].configure(text="From Open  ---", style="DtlV.TLabel")

        # Off High %
        if cur is not None and hi is not None and hi != 0:
            off_high_pct = (cur - hi) / hi * 100
            style = "DtlGrn.TLabel" if off_high_pct >= 0 else "DtlHlt.TLabel"
            self._detail_fields["off_high"].configure(
                text=f"Off High  {off_high_pct:.2f}%", style=style,
            )
        else:
            self._detail_fields["off_high"].configure(text="Off High  ---", style="DtlV.TLabel")

        # Enlarged sparkline + min/max/avg stats
        history = self._price_history.get(symbol, [])
        if len(history) >= 2:
            self._detail_fields["sparkline"].configure(text=_fmt_sparkline(history))
            avg = sum(history) / len(history)
            self._detail_fields["spark_stats"].configure(
                text=f"  Min {_fmt_price(min(history))}  Avg {_fmt_price(avg)}  Max {_fmt_price(max(history))}  ({len(history)} ticks)",
            )
        else:
            self._detail_fields["sparkline"].configure(text="")
            self._detail_fields["spark_stats"].configure(text="  Sparkline available after 2+ refreshes")

        self._detail_outer.pack(fill=X, after=self._table_frame)

    def _hide_detail_panel(self) -> None:
        self._selected_symbol = None
        self._detail_outer.pack_forget()
        self._tree.selection_remove(*self._tree.selection())

    # --- Symbol manager ---

    def _open_symbol_manager(self) -> None:
        from questrade.config import TARGET_SYMBOLS, save_symbols, reload_symbols
        from questrade.models.symbol import SymbolConfig

        dlg = tk.Toplevel(self)
        dlg.title("Manage Symbols")
        dlg.geometry("520x460")
        dlg.configure(background=CLR_BG_CARD)
        dlg.transient(self)
        dlg.grab_set()

        # Header
        hdr = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 12))
        hdr.pack(fill=X)
        ttk.Label(hdr, text="Manage Watchlist", style="DlgHd.TLabel").pack(anchor=W)
        count_lbl = ttk.Label(hdr, text=f"{len(TARGET_SYMBOLS)} symbols", style="DlgDim.TLabel")
        count_lbl.pack(anchor=W)

        # Scrollable symbol list
        list_frame = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 8))
        list_frame.pack(fill=BOTH, expand=True)

        canvas = tk.Canvas(list_frame, background=CLR_BG_CARD, highlightthickness=0)
        list_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas, style="Dlg.TFrame")

        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=list_scrollbar.set)

        list_scrollbar.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        current_symbols: list[SymbolConfig] = list(TARGET_SYMBOLS)

        def _rebuild_list() -> None:
            for w in inner.winfo_children():
                w.destroy()
            for i, sym in enumerate(current_symbols):
                row = ttk.Frame(inner, style="Dlg.TFrame")
                row.pack(fill=X, pady=2)
                ttk.Label(
                    row, text=f"{sym.symbol}  ({sym.exchange})",
                    style="DlgLbl.TLabel", width=20,
                ).pack(side=LEFT)
                ttk.Label(row, text=sym.name, style="DlgDim.TLabel").pack(side=LEFT, padx=(8, 0))
                ttk.Button(
                    row, text="\u2715", width=3,
                    bootstyle="danger-outline",  # type: ignore[arg-type]
                    command=lambda idx=i: _remove(idx),
                ).pack(side=RIGHT)
            count_lbl.configure(text=f"{len(current_symbols)} symbols")

        def _remove(idx: int) -> None:
            current_symbols.pop(idx)
            _rebuild_list()

        _rebuild_list()

        # Add symbol area
        add_frame = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 8, 16, 12))
        add_frame.pack(fill=X)

        tk.Frame(add_frame, background=CLR_BORDER, height=1).pack(fill=X, pady=(0, 8))

        entry_row = ttk.Frame(add_frame, style="Dlg.TFrame")
        entry_row.pack(fill=X)

        sym_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=sym_var, width=10).pack(side=LEFT, padx=(0, 4))

        exchanges = ["NASDAQ", "NYSE", "TSX", "TSX-V", "ARCA"]
        exch_var = tk.StringVar(value="NASDAQ")
        ttk.Combobox(
            entry_row, textvariable=exch_var, values=exchanges,
            width=8, state="readonly",
        ).pack(side=LEFT, padx=(0, 4))

        name_var = tk.StringVar()
        ttk.Entry(entry_row, textvariable=name_var, width=20).pack(side=LEFT, padx=(0, 4))

        def _add() -> None:
            s = sym_var.get().strip().upper()
            if not s:
                return
            if any(c.symbol == s and c.exchange == exch_var.get() for c in current_symbols):
                return
            n = name_var.get().strip() or s
            current_symbols.append(SymbolConfig(symbol=s, exchange=exch_var.get(), name=n))
            sym_var.set("")
            name_var.set("")
            _rebuild_list()

        ttk.Button(entry_row, text="Add", bootstyle="success", command=_add).pack(side=LEFT)  # type: ignore[arg-type]

        # Bottom buttons
        btn_row = ttk.Frame(dlg, style="Dlg.TFrame", padding=(16, 0, 16, 12))
        btn_row.pack(fill=X)

        def _save() -> None:
            save_symbols(current_symbols)
            reload_symbols()
            # Clean stale price history
            valid = {s.symbol for s in current_symbols}
            for k in [k for k in self._price_history if k not in valid]:
                del self._price_history[k]
            # Hide detail panel if selected symbol was removed
            if self._selected_symbol and self._selected_symbol not in valid:
                self._hide_detail_panel()
            dlg.destroy()
            self._refresh_quotes()

        ttk.Button(
            btn_row, text="Save", bootstyle="success",  # type: ignore[arg-type]
            command=_save,
        ).pack(side=RIGHT, padx=(4, 0))
        ttk.Button(
            btn_row, text="Cancel", bootstyle="secondary-outline",  # type: ignore[arg-type]
            command=dlg.destroy,
        ).pack(side=RIGHT)


def main() -> None:
    """Launch the GUI application."""
    app = QuoteApp()
    app.mainloop()


if __name__ == "__main__":
    main()
